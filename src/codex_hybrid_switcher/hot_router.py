from __future__ import annotations

import argparse
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .config import AppConfig, load_config

LOCAL_MODEL_PREFIXES = ("local/", "local-")
SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key", "openai-api-key"}
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "accept-encoding",
}


def runtime_root() -> Path:
    root = Path.home() / ".codex-hybrid-model-switcher" / "hot-router"
    root.mkdir(parents=True, exist_ok=True)
    return root


def log_file() -> Path:
    return runtime_root() / "router.jsonl"


def state_file() -> Path:
    return runtime_root() / "state.json"


def log_event(event: str, **fields: Any) -> None:
    payload = {"ts": int(time.time()), "event": event, **fields}
    with log_file().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def parse_json_body(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def extract_model(body: dict[str, Any]) -> str | None:
    value = body.get("model")
    return value if isinstance(value, str) and value else None


def extract_reasoning(body: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    reasoning = body.get("reasoning")
    if isinstance(reasoning, dict):
        for key in ("effort", "summary"):
            if isinstance(reasoning.get(key), str):
                result[key] = reasoning[key]
    for key in ("reasoning_effort", "model_reasoning_effort"):
        if isinstance(body.get(key), str):
            result[key] = body[key]
    return result


def should_route_local(model: str | None) -> bool:
    return bool(model and model.startswith(LOCAL_MODEL_PREFIXES))


def local_model_ids(config: AppConfig) -> list[str]:
    ids: list[str] = []
    for provider in config.providers:
        if provider.get("kind") != "local":
            continue
        model = provider.get("model")
        if isinstance(model, str) and model and model not in ids:
            ids.append(model)
    local_id = config.local_model.get("id")
    if ids and isinstance(local_id, str) and local_id and local_id not in ids:
        ids.append(local_id)
    return ids


def cloud_providers(config: AppConfig) -> list[dict[str, Any]]:
    return [provider for provider in config.providers if provider.get("kind") == "cloud" and provider.get("base_url")]


def primary_cloud_provider(config: AppConfig) -> dict[str, Any] | None:
    clouds = cloud_providers(config)
    if not clouds:
        return None
    bridge_clouds = [provider for provider in clouds if str(provider.get("route") or "direct") == "bridge"]
    return bridge_clouds[0] if bridge_clouds else clouds[0]


def cloud_provider_for_model(config: AppConfig, model: str | None) -> dict[str, Any] | None:
    if model:
        provider = config.provider_for_model(model)
        if provider and provider.get("kind") == "cloud":
            return provider
    clouds = cloud_providers(config)
    if len(clouds) == 1:
        return dict(clouds[0])
    bridge_clouds = [provider for provider in clouds if str(provider.get("route") or "direct") == "bridge"]
    if len(bridge_clouds) == 1:
        return dict(bridge_clouds[0])
    return None


def target_url(upstream_base: str, path: str) -> str:
    parsed = urllib.parse.urlsplit(path)
    upstream_path = parsed.path
    if upstream_path.startswith("/v1/"):
        upstream_path = upstream_path[3:]
    elif upstream_path == "/v1":
        upstream_path = ""
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{upstream_base.rstrip('/')}{upstream_path}{query}"


def hop_by_hop_header(name: str) -> bool:
    return name.lower() in HOP_BY_HOP_HEADERS


def filtered_incoming_headers(handler: BaseHTTPRequestHandler, body_len: int | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in handler.headers.items():
        lower = name.lower()
        if hop_by_hop_header(name) or lower in SENSITIVE_HEADERS:
            continue
        headers[name] = value
    if body_len is not None:
        headers["Content-Length"] = str(body_len)
    return headers


def apply_provider_auth(headers: dict[str, str], provider: dict[str, Any]) -> None:
    env_name = str(provider.get("api_key_env") or "")
    secret_value = os.environ.get(env_name) if env_name else None
    if secret_value:
        headers["Authorization"] = f"Bearer {secret_value}"


def read_upstream(url: str, method: str, headers: dict[str, str], *, data: bytes | None = None, timeout: float = 30) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


def port_open(host: str, port: int, *, timeout: float = 0.2) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def model_id(item: dict[str, Any]) -> str | None:
    value = item.get("id") or item.get("slug") or item.get("name") or item.get("model")
    return value if isinstance(value, str) and value else None


def catalog_items(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, dict) and isinstance(obj.get("data"), list):
        return [item for item in obj["data"] if isinstance(item, dict)]
    if isinstance(obj, dict) and isinstance(obj.get("models"), list):
        return [item for item in obj["models"] if isinstance(item, dict)]
    if isinstance(obj, list):
        return [item for item in obj if isinstance(item, dict)]
    return []


def local_catalog_entry(model: str, config: AppConfig) -> dict[str, Any]:
    local = config.local_model
    display = local.get("display_name") if local.get("id") == model else None
    if not isinstance(display, str) or not display:
        display = "Local " + " ".join(part.capitalize() for part in model.split("/", 1)[-1].replace("-", " ").split())
    instructions = str(local.get("system_prompt") or "You are a concise local coding assistant running through llama.cpp.")
    context = int(local.get("context_window") or 8192)
    return {
        "slug": model,
        "id": model,
        "display_name": display,
        "description": "Local llama.cpp model routed through Codex Hot Router",
        "base_instructions": instructions,
        "model_messages": {
            "instructions_template": instructions,
            "instructions_variables": {
                "personality_default": "",
                "personality_friendly": "",
                "personality_pragmatic": "",
            },
        },
        "context_window": context,
        "max_context_window": context,
        "default_reasoning_level": "low",
        "supported_reasoning_levels": [{"effort": "low", "description": "Local lightweight reasoning"}],
        "shell_type": "shell_command",
        "visibility": "list",
        "supported_in_api": True,
        "priority": 9000,
        "input_modalities": ["text", "image"],
        "supports_parallel_tool_calls": False,
        "supports_reasoning_summaries": False,
        "support_verbosity": False,
        "truncation_policy": {"mode": "tokens", "limit": context},
        "experimental_supported_tools": [],
    }


def local_ids_from_catalog(raw: bytes) -> list[str]:
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except Exception:
        return []
    ids: list[str] = []
    for item in catalog_items(obj):
        mid = model_id(item)
        if mid and should_route_local(mid) and mid not in ids:
            ids.append(mid)
    return ids


def merge_local_models(cloud_body: bytes, local_ids: list[str], config: AppConfig) -> tuple[bytes, int, str]:
    if not local_ids:
        return cloud_body, 0, "none"
    try:
        cloud_obj = json.loads(cloud_body.decode("utf-8-sig"))
    except Exception:
        return cloud_body, 0, "unknown"

    if isinstance(cloud_obj, dict) and isinstance(cloud_obj.get("data"), list):
        existing = {model_id(item) for item in cloud_obj["data"] if isinstance(item, dict)}
        additions = [{"id": mid, "object": "model", "owned_by": "local"} for mid in local_ids if mid not in existing]
        if not additions:
            return cloud_body, 0, "data"
        merged = dict(cloud_obj)
        merged["data"] = list(cloud_obj["data"]) + additions
        return json.dumps(merged, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), len(additions), "data"

    if isinstance(cloud_obj, dict) and isinstance(cloud_obj.get("models"), list):
        existing = {model_id(item) for item in cloud_obj["models"] if isinstance(item, dict)}
        additions = [local_catalog_entry(mid, config) for mid in local_ids if mid not in existing]
        if not additions:
            return cloud_body, 0, "models"
        merged = dict(cloud_obj)
        merged["models"] = list(cloud_obj["models"]) + additions
        return json.dumps(merged, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), len(additions), "models"

    if isinstance(cloud_obj, list):
        existing = {model_id(item) for item in cloud_obj if isinstance(item, dict)}
        additions = [local_catalog_entry(mid, config) for mid in local_ids if mid not in existing]
        if not additions:
            return cloud_body, 0, "list"
        return json.dumps(list(cloud_obj) + additions, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), len(additions), "list"

    return cloud_body, 0, type(cloud_obj).__name__


def response_text_from_json(data: dict[str, Any]) -> str:
    value = data.get("output_text")
    if isinstance(value, str):
        return value
    chunks: list[str] = []
    output = data.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    chunks.append(part["text"])
    if chunks:
        return "".join(chunks)
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(first.get("text"), str):
                return first["text"]
    return ""


def response_json(model: str, text: str) -> dict[str, Any]:
    item_id = "msg_" + uuid.uuid4().hex
    return {
        "id": "resp_" + uuid.uuid4().hex,
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


def sse_payload(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


class HotRouter:
    def __init__(self, config: AppConfig, host: str = "127.0.0.1", port: int = 19032, local_catalog_timeout: float = 2.0) -> None:
        self.config = config
        self.host = host
        self.port = port
        self.local_catalog_timeout = local_catalog_timeout
        self.catalog_cache: dict[str, Any] = {"expires_at": 0.0}

    @property
    def local_upstream(self) -> str:
        bridge = self.config.bridge
        return f"http://{bridge.host}:{bridge.port}/v1"

    def route_for_model(self, model: str | None) -> tuple[str, str, dict[str, Any] | None]:
        if should_route_local(model):
            return "local", self.local_upstream, None
        provider = cloud_provider_for_model(self.config, model)
        if not provider:
            return "error", "", None
        return "cloud", str(provider["base_url"]).rstrip("/"), provider

    def cache_key(self, path: str) -> str:
        return urllib.parse.urlsplit(path).query

    def cached_catalog(self, path: str) -> tuple[int, dict[str, str], bytes, dict[str, Any]] | None:
        if time.time() >= float(self.catalog_cache.get("expires_at") or 0):
            return None
        if self.catalog_cache.get("key") != self.cache_key(path):
            return None
        status = self.catalog_cache.get("status")
        headers = self.catalog_cache.get("headers")
        body = self.catalog_cache.get("body")
        meta = self.catalog_cache.get("meta")
        if not isinstance(status, int) or not isinstance(headers, dict) or not isinstance(body, bytes):
            return None
        return status, dict(headers), body, dict(meta) if isinstance(meta, dict) else {}

    def store_catalog(self, path: str, status: int, headers: dict[str, str], body: bytes, meta: dict[str, Any]) -> None:
        if 200 <= status < 300:
            self.catalog_cache.update(
                {
                    "key": self.cache_key(path),
                    "expires_at": time.time() + 15,
                    "status": status,
                    "headers": dict(headers),
                    "body": body,
                    "meta": dict(meta),
                }
            )

    def write_state(self) -> None:
        provider = primary_cloud_provider(self.config)
        data = {
            "pid": os.getpid(),
            "port": self.port,
            "cloudUpstream": str(provider.get("base_url")).rstrip("/") if provider else None,
            "localUpstream": self.local_upstream,
            "config": str(self.config.path),
            "logFile": str(log_file()),
            "localModels": local_model_ids(self.config),
        }
        state_file().write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class HotRouterHandler(BaseHTTPRequestHandler):
    server_version = "CodexHotRouter/1.0"
    router: HotRouter

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def write_json(self, status: int, obj: Any) -> None:
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_upstream(self, status: int, headers: dict[str, str], body: bytes) -> None:
        self.send_response(status)
        for name, value in headers.items():
            if hop_by_hop_header(name) or name.lower() in SENSITIVE_HEADERS or name.lower() == "content-length":
                continue
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        endpoint = urllib.parse.urlsplit(self.path).path
        if endpoint in {"/health", "/v1/health"}:
            provider = primary_cloud_provider(self.router.config)
            self.write_json(
                200,
                {
                    "ok": True,
                    "router": "codex-hot-router",
                    "port": self.router.port,
                    "cloud_upstream": str(provider.get("base_url")).rstrip("/") if provider else None,
                    "local_upstream": self.router.local_upstream,
                    "log_file": str(log_file()),
                    "local_models": local_model_ids(self.router.config),
                },
            )
            return
        if endpoint.endswith("/models") or endpoint in {"/models", "/v1/models"}:
            self.proxy_models_request()
            return
        self.proxy_request()

    def do_POST(self) -> None:
        self.proxy_request()

    def proxy_models_request(self) -> None:
        request_id = uuid.uuid4().hex
        endpoint = urllib.parse.urlsplit(self.path).path
        provider = primary_cloud_provider(self.router.config)
        if not provider:
            self.write_json(502, {"error": "no cloud provider configured for hot router catalog"})
            return

        log_event("request", request_id=request_id, method=self.command, endpoint=endpoint, model=None, route="catalog")
        cached = self.router.cached_catalog(self.path)
        if cached is not None:
            status, headers, body, meta = cached
            self.send_upstream(status, headers, body)
            log_event("response", request_id=request_id, status=status, route="catalog", response_bytes=len(body), **meta)
            return

        headers = filtered_incoming_headers(self)
        apply_provider_auth(headers, provider)
        try:
            status, response_headers, body = read_upstream(
                target_url(str(provider["base_url"]), self.path),
                self.command,
                headers,
                timeout=30,
            )
        except Exception as exc:
            payload = {"error": f"cloud catalog unavailable: {type(exc).__name__}: {exc}"}
            self.write_json(502, payload)
            log_event("response", request_id=request_id, status=502, route="catalog", error=payload["error"], response_bytes=0)
            return

        local_source = "none"
        local_error = None
        local_ids = local_model_ids(self.router.config)
        local_found = 0
        local_added = 0
        shape = "unknown"
        if 200 <= status < 300 and local_ids:
            bridge = self.router.config.bridge
            if port_open(bridge.host, bridge.port):
                try:
                    local_status, _, local_body = read_upstream(
                        target_url(self.router.local_upstream, self.path),
                        self.command,
                        {"Accept": "application/json"},
                        timeout=self.router.local_catalog_timeout,
                    )
                    if 200 <= local_status < 300:
                        upstream_ids = local_ids_from_catalog(local_body)
                        local_found = len(upstream_ids)
                        body, local_added, shape = merge_local_models(body, upstream_ids or local_ids, self.router.config)
                        local_source = "upstream"
                    else:
                        body, local_added, shape = merge_local_models(body, local_ids, self.router.config)
                        local_error = f"local catalog status {local_status}"
                        local_source = "fallback"
                except Exception as exc:
                    body, local_added, shape = merge_local_models(body, local_ids, self.router.config)
                    local_error = f"{type(exc).__name__}: {exc}"
                    local_source = "fallback"
            else:
                body, local_added, shape = merge_local_models(body, local_ids, self.router.config)
                local_error = "local upstream port is not listening"
                local_source = "fallback"

        meta = {
            "local_models_added": local_added,
            "local_models_found": local_found,
            "local_catalog_source": local_source,
            "local_catalog_error": local_error,
            "catalog_shape": shape,
        }
        self.router.store_catalog(self.path, status, response_headers, body, meta)
        self.send_upstream(status, response_headers, body)
        log_event("response", request_id=request_id, status=status, route="catalog", response_bytes=len(body), **meta)

    def proxy_request(self) -> None:
        request_id = uuid.uuid4().hex
        raw = b""
        if self.command in {"POST", "PUT", "PATCH"}:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length else b""
        body = parse_json_body(raw)
        model = extract_model(body)
        route, upstream, provider = self.router.route_for_model(model)
        endpoint = urllib.parse.urlsplit(self.path).path
        stream = body.get("stream") if isinstance(body.get("stream"), bool) else None

        log_event(
            "request",
            request_id=request_id,
            method=self.command,
            endpoint=endpoint,
            model=model,
            route=route,
            reasoning=extract_reasoning(body),
            stream=stream,
            content_length=len(raw),
        )

        if route == "error":
            self.write_json(400, {"error": f"no configured upstream for model: {model or '<missing>'}"})
            log_event("response", request_id=request_id, status=400, route=route, response_bytes=0)
            return

        if self.command == "POST" and route == "local" and endpoint.endswith("/responses") and stream is True:
            self.proxy_local_responses_stream(request_id, raw, model or "local/unknown")
            return

        headers = filtered_incoming_headers(self, len(raw) if self.command in {"POST", "PUT", "PATCH"} else None)
        if provider:
            apply_provider_auth(headers, provider)
        try:
            status, response_headers, response_body = read_upstream(
                target_url(upstream, self.path),
                self.command,
                headers,
                data=raw if self.command in {"POST", "PUT", "PATCH"} else None,
                timeout=600,
            )
            self.send_upstream(status, response_headers, response_body)
            log_event("response", request_id=request_id, status=status, route=route, response_bytes=len(response_body))
        except Exception as exc:
            payload = {"error": f"{type(exc).__name__}: {exc}"}
            self.write_json(502, payload)
            log_event("response", request_id=request_id, status=502, route=route, error=payload["error"], response_bytes=0)

    def proxy_local_responses_stream(self, request_id: str, raw: bytes, model: str) -> None:
        try:
            payload = json.loads(raw.decode("utf-8-sig") or "{}")
            payload["stream"] = False
            upstream_raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            status, response_headers, response_body = read_upstream(
                target_url(self.router.local_upstream, self.path),
                "POST",
                {"Content-Type": "application/json", "Content-Length": str(len(upstream_raw))},
                data=upstream_raw,
                timeout=600,
            )
            if not (200 <= status < 300):
                self.send_upstream(status, response_headers, response_body)
                log_event("response", request_id=request_id, status=status, route="local", response_bytes=len(response_body), stream_shim=True)
                return
            parsed = json.loads(response_body.decode("utf-8-sig") or "{}")
            text = response_text_from_json(parsed if isinstance(parsed, dict) else {})
            response = response_json(model, text)
            chunks = [
                sse_payload("response.created", {k: v for k, v in response.items() if k != "output"}),
                sse_payload("response.output_item.added", {"output_index": 0, "item": response["output"][0]}),
                sse_payload("response.content_part.added", {"item_id": response["output"][0]["id"], "output_index": 0, "content_index": 0, "part": response["output"][0]["content"][0]}),
                sse_payload("response.output_text.delta", {"item_id": response["output"][0]["id"], "output_index": 0, "content_index": 0, "delta": text}),
                sse_payload("response.output_text.done", {"item_id": response["output"][0]["id"], "output_index": 0, "content_index": 0, "text": text}),
                sse_payload("response.completed", {"response": response}),
                b"data: [DONE]\n\n",
            ]
            body = b"".join(chunks)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            log_event("response", request_id=request_id, status=200, route="local", response_bytes=len(body), stream_shim=True)
        except Exception as exc:
            payload = {"error": f"{type(exc).__name__}: {exc}"}
            self.write_json(502, payload)
            log_event("response", request_id=request_id, status=502, route="local", error=payload["error"], response_bytes=0, stream_shim=True)


def handler_for(router: HotRouter) -> type[HotRouterHandler]:
    class BoundHotRouterHandler(HotRouterHandler):
        pass

    BoundHotRouterHandler.router = router
    return BoundHotRouterHandler


def run_hot_router(config_path: str | None = None, *, host: str = "127.0.0.1", port: int = 19032) -> int:
    config = load_config(config_path)
    router = HotRouter(config, host=host, port=port)
    router.write_state()
    server = ThreadingHTTPServer((host, port), handler_for(router))
    print(f"Codex hot router listening on http://{host}:{port}/v1")
    print(f"Cloud provider: {primary_cloud_provider(config).get('id') if primary_cloud_provider(config) else '<missing>'}")
    print(f"Local bridge: {router.local_upstream}")
    print(f"Log: {log_file()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Codex hot router.")
    parser.add_argument("--config")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19032)
    args = parser.parse_args(argv)
    return run_hot_router(args.config, host=args.host, port=args.port)
