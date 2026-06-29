from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .config import AppConfig, expand_path, load_config


LOCAL_API_KEY = "codex-local-bridge"


class BridgeRuntime:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.local_proc: subprocess.Popen[str] | None = None
        self.last_local_use = 0.0
        self.lock = threading.Lock()

    @property
    def local_model_id(self) -> str:
        return str(self.config.local_model.get("id") or "local/gemma")

    def check_http(self, path: str, port: int | None = None) -> bool:
        try:
            bridge = self.config.bridge
            with urllib.request.urlopen(f"http://{bridge.host}:{port or bridge.llama_port}{path}", timeout=2) as resp:
                return 200 <= resp.status < 500
        except Exception:
            return False

    def wait_local(self) -> bool:
        for _ in range(120):
            if self.check_http("/health"):
                return True
            time.sleep(1)
        return False

    def ensure_local(self) -> None:
        with self.lock:
            self.last_local_use = time.time()
            if self.local_proc and self.local_proc.poll() is None and self.check_http("/health"):
                return
            if self.check_http("/health"):
                return

            local = self.config.local_model
            required = [
                expand_path(local["llama_server_path"]),
                expand_path(local["model_path"]),
                expand_path(local["mmproj_path"]),
            ]
            for path in required:
                if not path.exists():
                    raise RuntimeError(f"required local file missing: {path}")

            bridge = self.config.bridge
            cmd = [
                str(required[0]),
                "-m",
                str(required[1]),
                "--mmproj",
                str(required[2]),
                "--host",
                bridge.host,
                "--port",
                str(bridge.llama_port),
                "--api-key",
                LOCAL_API_KEY,
                "-c",
                str(local.get("context_window") or 8192),
            ]
            cmd.extend(str(x) for x in local.get("extra_args", []))
            self.local_proc = subprocess.Popen(
                cmd,
                cwd=str(required[0].parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )

        if not self.wait_local():
            self.stop_local("health-timeout")
            raise RuntimeError("local llama-server did not become healthy")

    def stop_local(self, _reason: str) -> None:
        with self.lock:
            proc = self.local_proc
            self.local_proc = None
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    def local_reaper(self) -> None:
        while True:
            time.sleep(15)
            with self.lock:
                proc = self.local_proc
                last = self.last_local_use
            if proc and proc.poll() is None and last:
                if time.time() - last > self.config.bridge.idle_seconds:
                    self.stop_local("idle-timeout")


def http_json(status: int, obj: Any) -> tuple[int, list[tuple[str, str]], bytes]:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))], body


def response_json(model: str, text: str) -> dict[str, Any]:
    response_id = "resp_" + uuid.uuid4().hex
    item_id = "msg_" + uuid.uuid4().hex
    return {
        "id": response_id,
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": model,
        "output": [
            {
                "id": item_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "output_text": text,
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }


def clean_local_text(text: str) -> str:
    text = re.sub(r"<\|channel\>.*?<channel\|>", "", text, flags=re.DOTALL)
    text = re.sub(r"<\|channel\>[^\n]*\n?", "", text)
    text = text.replace("<channel|>", "")
    text = re.sub(r"</?start_of_turn>[^\n]*\n?", "", text)
    text = text.replace("<end_of_turn>", "")
    text = re.sub(r"<\|[^>]+?\|>", "", text)
    return text.strip()


def extract_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(extract_text(x) for x in content if extract_text(x))
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        if "content" in content:
            return extract_text(content["content"])
    return ""


def sanitize_text(text: str) -> str:
    return re.sub(r"<image\b.*?</image>|<image\b[^>]*>|</image>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()


def image_url_from_part(part: dict[str, Any]) -> str | None:
    image_url = part.get("image_url")
    if isinstance(image_url, str) and image_url:
        return image_url
    if isinstance(image_url, dict) and isinstance(image_url.get("url"), str):
        return image_url["url"]
    for key in ("url", "data", "image", "b64_json"):
        value = part.get(key)
        if isinstance(value, str) and value:
            if value.startswith(("data:image/", "http://", "https://")):
                return value
            media_type = str(part.get("media_type") or part.get("mime_type") or "image/png")
            return f"data:{media_type};base64,{value}"
    source = part.get("source")
    if isinstance(source, dict) and isinstance(source.get("data"), str):
        media_type = str(source.get("media_type") or source.get("mime_type") or "image/png")
        return f"data:{media_type};base64,{source['data']}"
    return None


def chat_parts_from_content(content: Any, *, allow_images: bool) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    if isinstance(content, str):
        text = sanitize_text(content)
        if text:
            parts.append({"type": "text", "text": text[-12000:]})
        return parts
    if isinstance(content, list):
        for item in content:
            parts.extend(chat_parts_from_content(item, allow_images=allow_images))
        return parts
    if isinstance(content, dict):
        item_type = str(content.get("type") or "").lower()
        if "image" in item_type or "image_url" in content or "source" in content:
            url = image_url_from_part(content)
            if allow_images and url:
                parts.append({"type": "image_url", "image_url": {"url": url}})
            return parts
        text = sanitize_text(extract_text(content))
        if text:
            parts.append({"type": "text", "text": text[-12000:]})
    return parts


def content_value(parts: list[dict[str, Any]]) -> str | list[dict[str, Any]]:
    if len(parts) == 1 and parts[0].get("type") == "text":
        return str(parts[0].get("text") or "")
    return parts


def responses_input_to_messages(req: dict[str, Any], system_prompt: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    raw = req.get("input")
    if isinstance(raw, str):
        messages.append({"role": "user", "content": sanitize_text(raw)})
    elif isinstance(raw, list):
        if raw and all(isinstance(x, dict) and "role" not in x for x in raw):
            raw = [{"role": "user", "content": raw}]
        for item in raw:
            if isinstance(item, str):
                messages.append({"role": "user", "content": sanitize_text(item)})
            elif isinstance(item, dict):
                role = item.get("role") or "user"
                if role not in {"user", "assistant"}:
                    continue
                content = item.get("content") if "content" in item else item
                parts = chat_parts_from_content(content, allow_images=role == "user")
                if parts:
                    messages.append({"role": role, "content": content_value(parts)})
    if len(messages) == 1:
        messages.append({"role": "user", "content": "Hello"})
    return [messages[0]] + messages[1:][-8:]


def sse(handler: BaseHTTPRequestHandler, event: str, data: dict[str, Any]) -> None:
    payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
    handler.wfile.write(payload)
    handler.wfile.flush()


def build_handler(runtime: BridgeRuntime) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def send_payload(self, status: int, headers: list[tuple[str, str]], body: bytes) -> None:
            self.send_response(status)
            for key, value in headers:
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            if path in {"/health", "/v1/health"}:
                models = [str(p.get("model")) for p in runtime.config.providers if p.get("model")]
                if runtime.local_model_id not in models:
                    models.append(runtime.local_model_id)
                self.send_payload(200, *http_json(200, {"ok": True, "models": models, "port": runtime.config.bridge.port})[1:])
                return
            if path in {"/models", "/v1/models"}:
                data = [{"id": str(p.get("model")), "object": "model"} for p in runtime.config.providers if p.get("model")]
                data.append({"id": runtime.local_model_id, "object": "model"})
                self.send_payload(200, *http_json(200, {"object": "list", "data": data})[1:])
                return
            self.send_payload(404, *http_json(404, {"error": "not found"})[1:])

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(length)
            try:
                req = json.loads(body.decode("utf-8-sig") or "{}")
            except json.JSONDecodeError:
                self.send_payload(400, *http_json(400, {"error": "invalid json"})[1:])
                return

            model = req.get("model")
            provider = runtime.config.provider_for_model(str(model))
            if provider and provider.get("kind") == "local":
                self.handle_local(req)
                return
            if provider and provider.get("kind") == "cloud":
                self.handle_cloud(provider, body)
                return
            self.send_payload(400, *http_json(400, {"error": f"unknown model: {model}"})[1:])

        def handle_cloud(self, provider: dict[str, Any], body: bytes) -> None:
            base_url = str(provider["base_url"]).rstrip("/")
            api_key = os.environ.get(str(provider.get("api_key_env") or ""))
            headers = {"Content-Type": "application/json", "Accept": self.headers.get("Accept", "*/*")}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            path = urllib.parse.urlparse(self.path).path
            if path.startswith("/v1/"):
                path = path[3:]
            request = urllib.request.Request(base_url + path, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=900) as resp:
                    data = resp.read()
                    out_headers = [("Content-Type", resp.headers.get("Content-Type", "application/json")), ("Content-Length", str(len(data)))]
                    self.send_payload(resp.status, out_headers, data)
            except urllib.error.HTTPError as exc:
                data = exc.read()
                self.send_payload(exc.code, [("Content-Type", "application/json"), ("Content-Length", str(len(data)))], data)

        def local_text(self, req: dict[str, Any]) -> str:
            runtime.ensure_local()
            local = runtime.config.local_model
            messages = responses_input_to_messages(req, str(local.get("system_prompt") or "You are a concise assistant."))
            payload = {
                "model": runtime.local_model_id,
                "messages": messages,
                "temperature": req.get("temperature", 0.2),
                "stream": False,
                "max_tokens": min(int(req.get("max_output_tokens") or req.get("max_tokens") or local.get("max_output_tokens") or 512), int(local.get("max_output_tokens") or 512)),
            }
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            bridge = runtime.config.bridge
            request = urllib.request.Request(
                f"http://{bridge.host}:{bridge.llama_port}/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {LOCAL_API_KEY}"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=900) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
            choices = parsed.get("choices") or []
            if not choices:
                return ""
            message = choices[0].get("message") or {}
            return clean_local_text(str(message.get("content") or ""))

        def handle_local(self, req: dict[str, Any]) -> None:
            path = urllib.parse.urlparse(self.path).path
            stream = bool(req.get("stream"))
            try:
                text = self.local_text(req)
            except Exception as exc:
                self.send_payload(500, *http_json(500, {"error": str(exc)})[1:])
                return

            if path.endswith("/chat/completions"):
                body = {"choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}]}
                self.send_payload(200, *http_json(200, body)[1:])
                return

            if not stream:
                self.send_payload(200, *http_json(200, response_json(runtime.local_model_id, text))[1:])
                return

            response_id = "resp_" + uuid.uuid4().hex
            item_id = "msg_" + uuid.uuid4().hex
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            sse(self, "response.created", {"type": "response.created", "response": {"id": response_id, "status": "in_progress", "model": runtime.local_model_id, "created_at": int(time.time())}})
            sse(self, "response.output_item.added", {"type": "response.output_item.added", "output_index": 0, "item": {"id": item_id, "type": "message", "status": "in_progress", "role": "assistant", "content": []}})
            sse(self, "response.content_part.added", {"type": "response.content_part.added", "item_id": item_id, "output_index": 0, "content_index": 0, "part": {"type": "output_text", "text": "", "annotations": []}})
            if text:
                sse(self, "response.output_text.delta", {"type": "response.output_text.delta", "item_id": item_id, "output_index": 0, "content_index": 0, "delta": text})
            sse(self, "response.output_text.done", {"type": "response.output_text.done", "item_id": item_id, "output_index": 0, "content_index": 0, "text": text})
            sse(self, "response.content_part.done", {"type": "response.content_part.done", "item_id": item_id, "output_index": 0, "content_index": 0, "part": {"type": "output_text", "text": text, "annotations": []}})
            sse(self, "response.output_item.done", {"type": "response.output_item.done", "output_index": 0, "item": {"id": item_id, "type": "message", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": text, "annotations": []}]}})
            sse(self, "response.completed", {"type": "response.completed", "response": response_json(runtime.local_model_id, text)})
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return Handler


def run_bridge(config_path: str | None = None) -> int:
    config = load_config(config_path)
    runtime = BridgeRuntime(config)
    threading.Thread(target=runtime.local_reaper, daemon=True).start()

    def shutdown(_signum: int, _frame: Any) -> None:
        runtime.stop_local("bridge-shutdown")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    bridge = config.bridge
    server = ThreadingHTTPServer((bridge.host, bridge.port), build_handler(runtime))
    print(f"codex hybrid bridge listening on http://{bridge.host}:{bridge.port}/v1")
    server.serve_forever()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args(argv)
    return run_bridge(args.config)


if __name__ == "__main__":
    raise SystemExit(main())

