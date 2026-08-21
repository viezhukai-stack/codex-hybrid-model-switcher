from __future__ import annotations

import argparse
import email.utils
import json
import os
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from .config import AppConfig, load_config

LOCAL_MODEL_PREFIXES = ("local/", "local-")
DEFAULT_CLOUD_RESPONSE_STREAM_SHIM_MODELS = {"gemini-pro-agent"}
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
CATALOG_CONDITIONAL_HEADERS = {"if-match", "if-none-match", "if-modified-since", "if-unmodified-since", "if-range"}
CATALOG_VALIDATOR_HEADERS = {"etag", "last-modified", "expires"}
MAX_WEBSOCKET_HEADER_BYTES = 64 * 1024


def build_tls_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError, ssl.SSLError):
        pass
    for candidate in (
        "/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
        "/usr/local/etc/openssl@3/cert.pem",
        "/opt/homebrew/etc/openssl@3/cert.pem",
    ):
        if not Path(candidate).is_file():
            continue
        try:
            return ssl.create_default_context(cafile=candidate)
        except (OSError, ssl.SSLError):
            continue
    return ssl.create_default_context()


TLS_CONTEXT = build_tls_context()


def configure_proxy_environment(config: AppConfig) -> None:
    """Optionally bypass stale Windows system-proxy entries for this router only."""

    if not config.hot_router.ignore_system_proxy:
        return
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


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
    for local in config.local_catalog_models:
        model = local.get("id")
        if isinstance(model, str) and model and model not in ids:
            ids.append(model)
    local_id = config.local_model.get("id")
    if isinstance(local_id, str) and local_id and local_id not in ids:
        ids.append(local_id)
    return ids


def cloud_providers(config: AppConfig) -> list[dict[str, Any]]:
    return [provider for provider in config.providers if provider.get("kind") == "cloud" and provider.get("base_url")]


def cloud_provider_by_id(config: AppConfig, provider_id: str | None) -> dict[str, Any] | None:
    if not provider_id:
        return None
    try:
        provider = config.provider(provider_id)
    except KeyError:
        return None
    return dict(provider) if provider.get("kind") == "cloud" and provider.get("base_url") else None


def cloud_connection_key(provider: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(provider.get("base_url") or "").rstrip("/"),
        str(provider.get("api_key_env") or ""),
        str(provider.get("route") or "direct"),
        str(provider.get("wire_api") or "responses"),
    )


def primary_cloud_provider(config: AppConfig) -> dict[str, Any] | None:
    configured = cloud_provider_by_id(config, config.hot_router.default_cloud_provider_id)
    if configured:
        return configured
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
    configured = cloud_provider_by_id(config, config.hot_router.default_cloud_provider_id)
    if configured:
        if model:
            configured["model"] = model
        return configured
    clouds = cloud_providers(config)
    if len(clouds) == 1:
        return dict(clouds[0])
    if clouds and len({cloud_connection_key(provider) for provider in clouds}) == 1:
        shared = dict(clouds[0])
        if model:
            shared["model"] = model
        return shared
    return None


def resolve_model_alias(config: AppConfig, model: str | None) -> str | None:
    if not model:
        return model
    return config.hot_router.model_aliases.get(model, model)


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


def filtered_incoming_headers(
    handler: BaseHTTPRequestHandler,
    body_len: int | None = None,
    *,
    catalog: bool = False,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in handler.headers.items():
        lower = name.lower()
        if hop_by_hop_header(name) or lower in SENSITIVE_HEADERS or (catalog and lower in CATALOG_CONDITIONAL_HEADERS):
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


def is_websocket_upgrade(handler: BaseHTTPRequestHandler) -> bool:
    upgrade = str(handler.headers.get("Upgrade") or "").strip().lower()
    connection_tokens = {
        token.strip().lower()
        for token in str(handler.headers.get("Connection") or "").split(",")
        if token.strip()
    }
    return upgrade == "websocket" and "upgrade" in connection_tokens


def websocket_target_parts(upstream_base: str, path: str) -> tuple[str, int, str, bool, str]:
    url = target_url(upstream_base, path)
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"unsupported WebSocket upstream URL: {url}")
    secure = parsed.scheme == "https"
    port = parsed.port or (443 if secure else 80)
    request_target = parsed.path or "/"
    if parsed.query:
        request_target += f"?{parsed.query}"
    default_port = 443 if secure else 80
    host_header = parsed.hostname if port == default_port else f"{parsed.hostname}:{port}"
    return parsed.hostname, port, request_target, secure, host_header


def websocket_upstream_headers(
    handler: BaseHTTPRequestHandler,
    provider: dict[str, Any],
    host_header: str,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    provider_has_auth = bool(os.environ.get(str(provider.get("api_key_env") or "")))
    for name, value in handler.headers.items():
        lower = name.lower()
        if lower in {"host", "content-length", "proxy-authenticate", "proxy-authorization", "accept-encoding"}:
            continue
        if lower in {"cookie", "set-cookie", "x-api-key", "openai-api-key"}:
            continue
        if lower == "authorization" and provider_has_auth:
            continue
        if lower in {"connection", "upgrade"}:
            continue
        headers[name] = value
    headers["Host"] = host_header
    headers["Connection"] = "Upgrade"
    headers["Upgrade"] = "websocket"
    apply_provider_auth(headers, provider)
    return headers


def websocket_request_bytes(request_target: str, headers: dict[str, str]) -> bytes:
    if "\r" in request_target or "\n" in request_target:
        raise ValueError("invalid WebSocket request target")
    lines = [f"GET {request_target} HTTP/1.1"]
    for name, value in headers.items():
        if "\r" in name or "\n" in name or "\r" in value or "\n" in value:
            raise ValueError("invalid WebSocket request header")
        lines.append(f"{name}: {value}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")


def read_http_response_head(sock: socket.socket) -> tuple[bytes, bytes]:
    data = bytearray()
    marker = b"\r\n\r\n"
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("upstream closed before the WebSocket handshake completed")
        data.extend(chunk)
        if len(data) > MAX_WEBSOCKET_HEADER_BYTES:
            raise ValueError("upstream WebSocket handshake headers are too large")
    split_at = data.index(marker) + len(marker)
    return bytes(data[:split_at]), bytes(data[split_at:])


def parse_http_response_head(head: bytes) -> tuple[int, dict[str, str]]:
    lines = head.decode("latin-1").split("\r\n")
    status_parts = lines[0].split(" ", 2)
    if len(status_parts) < 2 or not status_parts[1].isdigit():
        raise ValueError(f"invalid upstream WebSocket status line: {lines[0]!r}")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    return int(status_parts[1]), headers


def relay_http_response_body(
    upstream: socket.socket,
    client: socket.socket,
    initial: bytes,
    headers: dict[str, str],
) -> int:
    total = 0
    if initial:
        client.sendall(initial)
        total += len(initial)
    try:
        remaining = max(0, int(headers.get("content-length") or "0") - len(initial))
    except ValueError:
        remaining = 0
    while remaining:
        chunk = upstream.recv(min(64 * 1024, remaining))
        if not chunk:
            break
        client.sendall(chunk)
        total += len(chunk)
        remaining -= len(chunk)
    return total


def relay_websocket_streams(client: socket.socket, upstream: socket.socket, initial: bytes = b"") -> tuple[int, int]:
    counters = {"client_to_upstream": 0, "upstream_to_client": 0}
    stop = threading.Event()

    if initial:
        client.sendall(initial)
        counters["upstream_to_client"] += len(initial)

    def pump(source: socket.socket, destination: socket.socket, counter: str) -> None:
        try:
            while not stop.is_set():
                chunk = source.recv(64 * 1024)
                if not chunk:
                    break
                destination.sendall(chunk)
                counters[counter] += len(chunk)
        except (OSError, ssl.SSLError):
            pass
        finally:
            if not stop.is_set():
                stop.set()
                for connection in (client, upstream):
                    try:
                        connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass

    client_thread = threading.Thread(
        target=pump,
        args=(client, upstream, "client_to_upstream"),
        daemon=True,
    )
    upstream_thread = threading.Thread(
        target=pump,
        args=(upstream, client, "upstream_to_client"),
        daemon=True,
    )
    client_thread.start()
    upstream_thread.start()
    client_thread.join()
    upstream_thread.join()
    return counters["client_to_upstream"], counters["upstream_to_client"]


def read_upstream(url: str, method: str, headers: dict[str, str], *, data: bytes | None = None, timeout: float = 30) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    open_kwargs: dict[str, Any] = {"timeout": timeout}
    if urllib.parse.urlsplit(url).scheme.lower() == "https":
        open_kwargs["context"] = TLS_CONTEXT
    try:
        with urllib.request.urlopen(request, **open_kwargs) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


def header_value(headers: dict[str, str], name: str) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value
    return None


def retry_after_seconds(value: str | None, *, now: float | None = None) -> float | None:
    if not value:
        return None
    text = value.strip()
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    current = time.time() if now is None else now
    return max(0.0, parsed.timestamp() - current)


def read_upstream_with_429_retry(
    url: str,
    method: str,
    headers: dict[str, str],
    *,
    data: bytes | None = None,
    timeout: float = 30,
    max_retries: int = 2,
    max_retry_after_seconds: float = 30,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[int, dict[str, str], bytes, dict[str, Any]]:
    retries = 0
    waited = 0.0
    retry_after_values: list[str] = []
    while True:
        status, response_headers, body = read_upstream(
            url,
            method,
            headers,
            data=data,
            timeout=timeout,
        )
        if status != 429 or retries >= max(0, max_retries):
            return status, response_headers, body, {
                "upstream_retries": retries,
                "retry_wait_seconds": round(waited, 3),
                "retry_after": retry_after_values,
            }
        raw_retry_after = header_value(response_headers, "Retry-After")
        parsed_delay = retry_after_seconds(raw_retry_after)
        if parsed_delay is None:
            parsed_delay = float(2**retries)
        delay = min(max(0.0, parsed_delay), max(0.0, max_retry_after_seconds))
        retry_after_values.append(raw_retry_after or "fallback")
        if delay:
            sleep(delay)
            waited += delay
        retries += 1


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
    local = config.local_catalog_model(model)
    display = local.get("display_name")
    if not isinstance(display, str) or not display:
        display = "Local " + " ".join(part.capitalize() for part in model.split("/", 1)[-1].replace("-", " ").split())
    instructions = str(local.get("system_prompt") or "You are a concise local coding assistant running through llama.cpp.")
    try:
        context = max(1, int(local.get("context_window") or 8192))
    except (TypeError, ValueError):
        context = 8192
    try:
        max_context = max(context, int(local.get("max_context_window") or context))
    except (TypeError, ValueError):
        max_context = context
    input_modalities = local.get("input_modalities")
    if not isinstance(input_modalities, list) or any(not isinstance(value, str) or not value for value in input_modalities):
        input_modalities = ["text", "image"]
    supported_reasoning_levels = local.get("supported_reasoning_levels")
    if supported_reasoning_levels and isinstance(supported_reasoning_levels, list) and all(
        isinstance(value, str) and value for value in supported_reasoning_levels
    ):
        supported_reasoning_levels = [
            {"effort": value, "description": f"Local {value} reasoning"}
            for value in supported_reasoning_levels
        ]
    if not supported_reasoning_levels or not isinstance(supported_reasoning_levels, list) or any(
        not isinstance(value, dict) for value in supported_reasoning_levels
    ):
        supported_reasoning_levels = [{"effort": "low", "description": "Local lightweight reasoning"}]
    experimental_tools = local.get("experimental_supported_tools")
    if not isinstance(experimental_tools, list):
        experimental_tools = []
    try:
        priority = int(local.get("priority") or 9000)
    except (TypeError, ValueError):
        priority = 9000
    return {
        "slug": model,
        "id": model,
        "display_name": display,
        "description": str(local.get("description") or "Local llama.cpp model routed through Codex Hot Router"),
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
        "max_context_window": max_context,
        "default_reasoning_level": str(local.get("default_reasoning_level") or "low"),
        "supported_reasoning_levels": supported_reasoning_levels,
        "shell_type": "shell_command",
        "visibility": "list",
        "supported_in_api": True,
        "priority": priority,
        "input_modalities": input_modalities,
        "supports_parallel_tool_calls": bool(local.get("supports_parallel_tool_calls", False)),
        "supports_reasoning_summaries": bool(local.get("supports_reasoning_summaries", False)),
        "support_verbosity": bool(local.get("support_verbosity", False)),
        "truncation_policy": {"mode": "tokens", "limit": context},
        "experimental_supported_tools": experimental_tools,
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


def filter_catalog_models(
    body: bytes,
    visible_ids: set[str],
    hidden_ids: set[str],
    display_names: dict[str, str] | None = None,
) -> tuple[bytes, int, int, str]:
    try:
        obj = json.loads(body.decode("utf-8-sig"))
    except Exception:
        return body, 0, 0, "unknown"

    items = catalog_items(obj)
    if not items:
        return body, 0, 0, type(obj).__name__
    kept: list[dict[str, Any]] = []
    hidden_removed = 0
    visible_removed = 0
    for item in items:
        mid = model_id(item)
        if mid and mid in hidden_ids:
            hidden_removed += 1
            continue
        if visible_ids and mid not in visible_ids:
            visible_removed += 1
            continue
        normalized = dict(item)
        # An explicit visible_model_ids allowlist is the operator's final menu
        # decision. Some upstream catalogs keep otherwise usable legacy models
        # as visibility="hide"; leaving that value intact makes Codex Desktop
        # silently remove an allowlisted item from the picker.
        if visible_ids and mid in visible_ids:
            normalized["visibility"] = "list"
        display_name = (display_names or {}).get(mid or "")
        if display_name:
            normalized["display_name"] = display_name
        kept.append(normalized)

    if isinstance(obj, dict) and isinstance(obj.get("data"), list):
        result = dict(obj)
        result["data"] = kept
        shape = "data"
    elif isinstance(obj, dict) and isinstance(obj.get("models"), list):
        result = dict(obj)
        result["models"] = kept
        shape = "models"
    elif isinstance(obj, list):
        result = kept
        shape = "list"
    else:
        return body, hidden_removed, visible_removed, type(obj).__name__
    return json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), hidden_removed, visible_removed, shape


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


def _text_from_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_text_from_value(item) for item in value)
    if isinstance(value, dict):
        for key in ("text", "content", "value"):
            if key in value:
                text = _text_from_value(value.get(key))
                if text:
                    return text
    return ""


def _arguments_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _normalize_message_content(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        return [{"type": "output_text", "text": value, "annotations": []}]
    if not isinstance(value, list):
        return []
    parts: list[dict[str, Any]] = []
    for raw_part in value:
        if isinstance(raw_part, str):
            parts.append({"type": "output_text", "text": raw_part, "annotations": []})
            continue
        if not isinstance(raw_part, dict):
            continue
        part = dict(raw_part)
        part_type = str(part.get("type") or "")
        if part_type in {"text", "output_text"} or (not part_type and isinstance(part.get("text"), str)):
            part["type"] = "output_text"
            part["text"] = _text_from_value(part.get("text"))
            if not isinstance(part.get("annotations"), list):
                part["annotations"] = []
        elif part_type == "refusal":
            part["refusal"] = _text_from_value(part.get("refusal") or part.get("text"))
        parts.append(part)
    return parts


def _normalize_reasoning_parts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        return [{"type": "summary_text", "text": value}]
    if not isinstance(value, list):
        return []
    parts: list[dict[str, Any]] = []
    for raw_part in value:
        if isinstance(raw_part, str):
            parts.append({"type": "summary_text", "text": raw_part})
        elif isinstance(raw_part, dict):
            part = dict(raw_part)
            part.setdefault("type", "summary_text")
            if "text" in part:
                part["text"] = _text_from_value(part.get("text"))
            parts.append(part)
    return parts


def _normalize_output_item(raw_item: dict[str, Any]) -> dict[str, Any]:
    item = dict(raw_item)
    item_type = str(item.get("type") or "")
    nested_function = item.get("function")
    if item_type in {"function", "tool_call"} and isinstance(nested_function, dict):
        item_type = "function_call"
        item["type"] = item_type
    if item_type == "message":
        item.setdefault("id", "msg_" + uuid.uuid4().hex)
        item.setdefault("status", "completed")
        item.setdefault("role", "assistant")
        item["content"] = _normalize_message_content(item.get("content"))
    elif item_type == "function_call":
        function = nested_function if isinstance(nested_function, dict) else {}
        call_id = item.get("call_id") or item.get("tool_call_id") or item.get("id")
        item.setdefault("id", "fc_" + uuid.uuid4().hex)
        item["call_id"] = str(call_id or ("call_" + uuid.uuid4().hex))
        item["name"] = str(item.get("name") or function.get("name") or "")
        item["arguments"] = _arguments_text(item.get("arguments", function.get("arguments")))
        item.setdefault("status", "completed")
        item.pop("function", None)
    elif item_type == "reasoning":
        item.setdefault("id", "rs_" + uuid.uuid4().hex)
        item.setdefault("status", "completed")
        item["summary"] = _normalize_reasoning_parts(item.get("summary"))
        if isinstance(item.get("content"), list):
            item["content"] = _normalize_reasoning_parts(item.get("content"))
    else:
        item.setdefault("id", "item_" + uuid.uuid4().hex)
        if item_type:
            item.setdefault("status", "completed")
    return item


def _chat_completion_output(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    output: list[dict[str, Any]] = []
    final_status = "completed"
    choices = data.get("choices")
    if not isinstance(choices, list):
        return output, final_status
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        finish_reason = str(choice.get("finish_reason") or "")
        if finish_reason == "length":
            final_status = "incomplete"
        message = choice.get("message")
        if not isinstance(message, dict):
            text = _text_from_value(choice.get("text"))
            if text:
                output.append(
                    _normalize_output_item(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": text,
                        }
                    )
                )
            continue

        reasoning = _text_from_value(
            message.get("reasoning_content")
            or message.get("reasoning")
            or choice.get("reasoning_content")
            or choice.get("reasoning")
        )
        if reasoning:
            output.append(
                _normalize_output_item(
                    {
                        "type": "reasoning",
                        "summary": [{"type": "summary_text", "text": reasoning}],
                    }
                )
            )

        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                function = tool_call.get("function")
                if not isinstance(function, dict):
                    function = {}
                output.append(
                    _normalize_output_item(
                        {
                            "type": "function_call",
                            "call_id": tool_call.get("id"),
                            "name": function.get("name") or tool_call.get("name"),
                            "arguments": function.get("arguments", tool_call.get("arguments")),
                        }
                    )
                )
        legacy_function = message.get("function_call")
        if isinstance(legacy_function, dict):
            output.append(
                _normalize_output_item(
                    {
                        "type": "function_call",
                        "name": legacy_function.get("name"),
                        "arguments": legacy_function.get("arguments"),
                    }
                )
            )

        content = _normalize_message_content(message.get("content"))
        refusal = _text_from_value(message.get("refusal"))
        if refusal:
            content.append({"type": "refusal", "refusal": refusal})
        if content:
            output.append(
                _normalize_output_item(
                    {
                        "type": "message",
                        "role": message.get("role") or "assistant",
                        "content": content,
                    }
                )
            )
    return output, final_status


def _normalize_usage(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    usage = dict(value)
    if "input_tokens" not in usage and "prompt_tokens" in usage:
        usage["input_tokens"] = usage.get("prompt_tokens")
    if "output_tokens" not in usage and "completion_tokens" in usage:
        usage["output_tokens"] = usage.get("completion_tokens")
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    usage["input_tokens"] = input_tokens
    usage["output_tokens"] = output_tokens
    usage["total_tokens"] = int(usage.get("total_tokens") or (input_tokens + output_tokens))
    return usage


def response_json_from_upstream(data: dict[str, Any], fallback_model: str) -> dict[str, Any]:
    native_output = data.get("output")
    is_native = data.get("object") == "response" or isinstance(native_output, list)
    response: dict[str, Any] = dict(data) if is_native else {}
    if isinstance(native_output, list) and native_output:
        output = [_normalize_output_item(item) for item in native_output if isinstance(item, dict)]
        status = str(data.get("status") or "completed")
    else:
        output, status = _chat_completion_output(data)
        if not output:
            text = response_text_from_json(data)
            if text:
                output = [
                    _normalize_output_item(
                        {"type": "message", "role": "assistant", "content": text}
                    )
                ]
        if is_native and isinstance(data.get("status"), str):
            status = str(data["status"])
    if data.get("error") and status == "completed":
        status = "failed"
    response["id"] = str(data.get("id") or ("resp_" + uuid.uuid4().hex))
    response["object"] = "response"
    response["created_at"] = int(data.get("created_at") or data.get("created") or time.time())
    response["status"] = status
    response["model"] = str(data.get("model") or fallback_model)
    response["output"] = output
    response["usage"] = _normalize_usage(data.get("usage"))
    text_chunks: list[str] = []
    for item in output:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text_chunks.append(_text_from_value(part.get("text")))
    response["output_text"] = (
        data["output_text"]
        if isinstance(data.get("output_text"), str)
        else "".join(text_chunks)
    )
    response.pop("choices", None)
    return response


def sse_payload(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def responses_sse_body_from_json(data: dict[str, Any], fallback_model: str) -> bytes:
    response = response_json_from_upstream(data, fallback_model)
    chunks: list[bytes] = []
    sequence_number = 0

    def add(event: str, payload: dict[str, Any]) -> None:
        nonlocal sequence_number
        enriched = dict(payload)
        enriched.setdefault("type", event)
        enriched.setdefault("sequence_number", sequence_number)
        sequence_number += 1
        chunks.append(sse_payload(event, enriched))

    opening = dict(response)
    opening["status"] = "in_progress"
    opening["output"] = []
    opening.pop("output_text", None)
    opening["usage"] = None
    add("response.created", {"response": opening})
    add("response.in_progress", {"response": opening})

    for output_index, final_item in enumerate(response.get("output") or []):
        if not isinstance(final_item, dict):
            continue
        item = dict(final_item)
        item_type = str(item.get("type") or "")
        item_id = str(item.get("id") or ("item_" + uuid.uuid4().hex))
        item["id"] = item_id
        added_item = dict(item)
        if "status" in added_item:
            added_item["status"] = "in_progress"
        if item_type == "message":
            added_item["content"] = []
        elif item_type == "function_call":
            added_item["arguments"] = ""
        elif item_type == "reasoning":
            added_item["summary"] = []
            if "content" in added_item:
                added_item["content"] = []
        add(
            "response.output_item.added",
            {"output_index": output_index, "item": added_item},
        )

        if item_type == "message":
            for content_index, part in enumerate(item.get("content") or []):
                if not isinstance(part, dict):
                    continue
                part_type = str(part.get("type") or "")
                if part_type == "output_text":
                    text = _text_from_value(part.get("text"))
                    empty_part = dict(part)
                    empty_part["text"] = ""
                    add(
                        "response.content_part.added",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "part": empty_part,
                        },
                    )
                    if text:
                        add(
                            "response.output_text.delta",
                            {
                                "item_id": item_id,
                                "output_index": output_index,
                                "content_index": content_index,
                                "delta": text,
                            },
                        )
                    add(
                        "response.output_text.done",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "text": text,
                        },
                    )
                    add(
                        "response.content_part.done",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "part": part,
                        },
                    )
                elif part_type == "refusal":
                    refusal = _text_from_value(part.get("refusal"))
                    add(
                        "response.content_part.added",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "part": {"type": "refusal", "refusal": ""},
                        },
                    )
                    if refusal:
                        add(
                            "response.refusal.delta",
                            {
                                "item_id": item_id,
                                "output_index": output_index,
                                "content_index": content_index,
                                "delta": refusal,
                            },
                        )
                    add(
                        "response.refusal.done",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "refusal": refusal,
                        },
                    )
                    add(
                        "response.content_part.done",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "part": part,
                        },
                    )
                else:
                    add(
                        "response.content_part.added",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "part": part,
                        },
                    )
                    add(
                        "response.content_part.done",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "part": part,
                        },
                    )
        elif item_type == "function_call":
            arguments = _arguments_text(item.get("arguments"))
            if arguments:
                add(
                    "response.function_call_arguments.delta",
                    {
                        "item_id": item_id,
                        "output_index": output_index,
                        "delta": arguments,
                    },
                )
            add(
                "response.function_call_arguments.done",
                {
                    "item_id": item_id,
                    "output_index": output_index,
                    "arguments": arguments,
                },
            )
        elif item_type == "reasoning":
            for summary_index, part in enumerate(item.get("summary") or []):
                if not isinstance(part, dict):
                    continue
                text = _text_from_value(part.get("text"))
                empty_part = dict(part)
                empty_part["text"] = ""
                add(
                    "response.reasoning_summary_part.added",
                    {
                        "item_id": item_id,
                        "output_index": output_index,
                        "summary_index": summary_index,
                        "part": empty_part,
                    },
                )
                if text:
                    add(
                        "response.reasoning_summary_text.delta",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "summary_index": summary_index,
                            "delta": text,
                        },
                    )
                add(
                    "response.reasoning_summary_text.done",
                    {
                        "item_id": item_id,
                        "output_index": output_index,
                        "summary_index": summary_index,
                        "text": text,
                    },
                )
                add(
                    "response.reasoning_summary_part.done",
                    {
                        "item_id": item_id,
                        "output_index": output_index,
                        "summary_index": summary_index,
                        "part": part,
                    },
                )
            for content_index, part in enumerate(item.get("content") or []):
                if not isinstance(part, dict):
                    continue
                text = _text_from_value(part.get("text"))
                if text:
                    add(
                        "response.reasoning_text.delta",
                        {
                            "item_id": item_id,
                            "output_index": output_index,
                            "content_index": content_index,
                            "delta": text,
                        },
                    )
                add(
                    "response.reasoning_text.done",
                    {
                        "item_id": item_id,
                        "output_index": output_index,
                        "content_index": content_index,
                        "text": text,
                    },
                )

        add(
            "response.output_item.done",
            {"output_index": output_index, "item": item},
        )

    status = str(response.get("status") or "completed")
    terminal_event = {
        "failed": "response.failed",
        "incomplete": "response.incomplete",
        "cancelled": "response.failed",
    }.get(status, "response.completed")
    add(terminal_event, {"response": response})
    chunks.append(b"data: [DONE]\n\n")
    return b"".join(chunks)


def responses_sse_body(model: str, text: str) -> bytes:
    return responses_sse_body_from_json(response_json(model, text), model)


def stream_shim_payload(raw: bytes) -> bytes:
    payload = json.loads(raw.decode("utf-8-sig") or "{}")
    if not isinstance(payload, dict):
        payload = {}
    payload["stream"] = False
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def cloud_response_stream_shim_models(provider: dict[str, Any]) -> set[str]:
    configured = provider.get("response_stream_shim_models")
    if configured is None:
        return set(DEFAULT_CLOUD_RESPONSE_STREAM_SHIM_MODELS)
    if isinstance(configured, list):
        return {item for item in configured if isinstance(item, str) and item}
    return set()


def cloud_response_stream_shim_empty_retries(provider: dict[str, Any] | None) -> int:
    if provider is None:
        return 0
    value = provider.get("response_stream_shim_empty_retries", 2)
    try:
        return max(0, min(int(value), 2))
    except (TypeError, ValueError):
        return 2


def response_has_meaningful_output(response: dict[str, Any]) -> bool:
    output = response.get("output")
    if isinstance(output, list) and any(isinstance(item, dict) for item in output):
        return True
    return bool(_text_from_value(response.get("output_text")))


def should_shim_cloud_responses_stream(provider: dict[str, Any] | None, model: str | None, endpoint: str, stream: bool | None) -> bool:
    if not provider or not model:
        return False
    return endpoint.endswith("/responses") and stream is True and model in cloud_response_stream_shim_models(provider)


class HotRouter:
    def __init__(
        self,
        config: AppConfig,
        host: str | None = None,
        port: int | None = None,
        local_catalog_timeout: float = 2.0,
    ) -> None:
        self.config = config
        self.host = host or config.hot_router.host
        self.port = port or config.hot_router.port
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
                    "expires_at": time.time() + self.config.hot_router.catalog_cache_seconds,
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
            "defaultCloudProviderId": self.config.hot_router.default_cloud_provider_id,
            "hiddenModelIds": list(self.config.hot_router.hidden_model_ids),
            "visibleFilterEnabled": bool(self.config.hot_router.visible_model_ids),
        }
        state_file().write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class HotRouterHandler(BaseHTTPRequestHandler):
    server_version = "CodexHotRouter/1.0"
    protocol_version = "HTTP/1.1"
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
        if is_websocket_upgrade(self):
            self.proxy_websocket_request()
            return
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
                    "default_cloud_provider_id": self.router.config.hot_router.default_cloud_provider_id,
                    "visible_filter_enabled": bool(self.router.config.hot_router.visible_model_ids),
                    "visible_models": list(self.router.config.hot_router.visible_model_ids),
                    "hidden_models": list(self.router.config.hot_router.hidden_model_ids),
                },
            )
            return
        if endpoint.endswith("/models") or endpoint in {"/models", "/v1/models"}:
            self.proxy_models_request()
            return
        self.proxy_request()

    def do_POST(self) -> None:
        self.proxy_request()

    def proxy_websocket_request(self) -> None:
        request_id = uuid.uuid4().hex
        endpoint = urllib.parse.urlsplit(self.path).path
        provider = primary_cloud_provider(self.router.config)
        self.close_connection = True
        log_event(
            "request",
            request_id=request_id,
            method=self.command,
            endpoint=endpoint,
            model=None,
            route="cloud",
            transport="websocket",
        )
        if not provider:
            self.write_json(502, {"error": "no cloud provider configured for WebSocket forwarding"})
            log_event(
                "response",
                request_id=request_id,
                status=502,
                route="cloud",
                transport="websocket",
                response_bytes=0,
            )
            return

        upstream_socket: socket.socket | None = None
        response_started = False
        try:
            hostname, port, request_target, secure, host_header = websocket_target_parts(
                str(provider["base_url"]),
                self.path,
            )
            upstream_socket = socket.create_connection((hostname, port), timeout=30)
            if secure:
                upstream_socket = TLS_CONTEXT.wrap_socket(upstream_socket, server_hostname=hostname)
            headers = websocket_upstream_headers(self, provider, host_header)
            upstream_socket.sendall(websocket_request_bytes(request_target, headers))
            response_head, initial = read_http_response_head(upstream_socket)
            status, response_headers = parse_http_response_head(response_head)
            self.connection.sendall(response_head)
            response_started = True
            if status != 101:
                response_bytes = relay_http_response_body(
                    upstream_socket,
                    self.connection,
                    initial,
                    response_headers,
                )
                log_event(
                    "response",
                    request_id=request_id,
                    status=status,
                    route="cloud",
                    transport="websocket",
                    response_bytes=response_bytes,
                )
                return

            self.connection.settimeout(None)
            upstream_socket.settimeout(None)
            sent_bytes, received_bytes = relay_websocket_streams(
                self.connection,
                upstream_socket,
                initial,
            )
            log_event(
                "response",
                request_id=request_id,
                status=101,
                route="cloud",
                transport="websocket",
                client_to_upstream_bytes=sent_bytes,
                upstream_to_client_bytes=received_bytes,
            )
        except Exception as exc:
            payload = {"error": f"{type(exc).__name__}: {exc}"}
            if not response_started:
                try:
                    self.write_json(502, payload)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
            log_event(
                "response",
                request_id=request_id,
                status=502,
                route="cloud",
                transport="websocket",
                error=payload["error"],
                response_bytes=0,
            )
        finally:
            if upstream_socket is not None:
                try:
                    upstream_socket.close()
                except OSError:
                    pass

    def proxy_models_request(self) -> None:
        request_id = uuid.uuid4().hex
        endpoint = urllib.parse.urlsplit(self.path).path
        provider = primary_cloud_provider(self.router.config)
        local_ids = local_model_ids(self.router.config)
        if not provider and not local_ids:
            self.write_json(502, {"error": "no cloud or local provider configured for hot router catalog"})
            return

        log_event("request", request_id=request_id, method=self.command, endpoint=endpoint, model=None, route="catalog")
        cached = self.router.cached_catalog(self.path)
        if cached is not None:
            status, headers, body, meta = cached
            self.send_upstream(status, headers, body)
            log_event("response", request_id=request_id, status=status, route="catalog", response_bytes=len(body), **meta)
            return

        if provider:
            headers = filtered_incoming_headers(self, catalog=True)
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
        else:
            status = 200
            response_headers = {"Content-Type": "application/json"}
            body = json.dumps({"models": []}, separators=(",", ":")).encode("utf-8")

        local_source = "none"
        local_error = None
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

        visible_ids = set(self.router.config.hot_router.visible_model_ids)
        hidden_ids = set(self.router.config.hot_router.hidden_model_ids)
        body, hidden_removed, visible_removed, filter_shape = filter_catalog_models(
            body,
            visible_ids,
            hidden_ids,
            self.router.config.hot_router.model_display_names,
        )
        if shape in {"unknown", "none"}:
            shape = filter_shape

        response_headers = {
            name: value
            for name, value in response_headers.items()
            if name.lower() not in CATALOG_VALIDATOR_HEADERS
        }
        response_headers["Cache-Control"] = "no-store"

        meta = {
            "local_models_added": local_added,
            "local_models_found": local_found,
            "local_catalog_source": local_source,
            "local_catalog_error": local_error,
            "catalog_shape": shape,
            "hidden_models_removed": hidden_removed,
            "visible_models_removed": visible_removed,
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
        upstream_model = resolve_model_alias(self.router.config, model)
        upstream_raw = raw
        if upstream_model != model and body:
            upstream_body = dict(body)
            upstream_body["model"] = upstream_model
            upstream_raw = json.dumps(upstream_body, ensure_ascii=False).encode("utf-8")
        route, upstream, provider = self.router.route_for_model(upstream_model)
        endpoint = urllib.parse.urlsplit(self.path).path
        stream = body.get("stream") if isinstance(body.get("stream"), bool) else None

        log_event(
            "request",
            request_id=request_id,
            method=self.command,
            endpoint=endpoint,
            model=model,
            upstream_model=upstream_model,
            route=route,
            reasoning=extract_reasoning(body),
            stream=stream,
            content_length=len(raw),
            upstream_content_length=len(upstream_raw),
        )

        if route == "error":
            self.write_json(400, {"error": f"no configured upstream for model: {model or '<missing>'}"})
            log_event("response", request_id=request_id, status=400, route=route, response_bytes=0)
            return

        if self.command == "POST" and route == "local" and endpoint.endswith("/responses") and stream is True:
            self.proxy_responses_stream_shim(
                request_id,
                upstream_raw,
                upstream_model or "local/unknown",
                upstream,
                "local",
                None,
                {"stream_shim": True},
            )
            return

        if self.command == "POST" and route == "cloud" and should_shim_cloud_responses_stream(provider, upstream_model, endpoint, stream):
            self.proxy_responses_stream_shim(
                request_id,
                upstream_raw,
                upstream_model or "cloud/unknown",
                upstream,
                "cloud",
                provider,
                {"cloud_stream_shim": True},
            )
            return

        headers = filtered_incoming_headers(
            self,
            len(upstream_raw) if self.command in {"POST", "PUT", "PATCH"} else None,
        )
        if provider:
            apply_provider_auth(headers, provider)
        try:
            status, response_headers, response_body, retry_meta = read_upstream_with_429_retry(
                target_url(upstream, self.path),
                self.command,
                headers,
                data=upstream_raw if self.command in {"POST", "PUT", "PATCH"} else None,
                timeout=600,
                max_retries=self.router.config.hot_router.max_429_retries,
                max_retry_after_seconds=self.router.config.hot_router.max_retry_after_seconds,
            )
            self.send_upstream(status, response_headers, response_body)
            log_event(
                "response",
                request_id=request_id,
                status=status,
                route=route,
                response_bytes=len(response_body),
                **retry_meta,
            )
        except Exception as exc:
            payload = {"error": f"{type(exc).__name__}: {exc}"}
            self.write_json(502, payload)
            log_event("response", request_id=request_id, status=502, route=route, error=payload["error"], response_bytes=0)

    def proxy_responses_stream_shim(
        self,
        request_id: str,
        raw: bytes,
        model: str,
        upstream: str,
        route: str,
        provider: dict[str, Any] | None,
        log_fields: dict[str, Any],
    ) -> None:
        try:
            upstream_raw = stream_shim_payload(raw)
            headers = {"Content-Type": "application/json", "Content-Length": str(len(upstream_raw))}
            if provider:
                apply_provider_auth(headers, provider)
            empty_output_retries = 0
            empty_retry_wait = 0.0
            retry_meta: dict[str, Any] = {
                "upstream_retries": 0,
                "retry_wait_seconds": 0.0,
                "retry_after": [],
            }
            max_empty_retries = cloud_response_stream_shim_empty_retries(provider)
            while True:
                remaining_429_retries = max(
                    0,
                    self.router.config.hot_router.max_429_retries
                    - int(retry_meta.get("upstream_retries") or 0),
                )
                status, response_headers, response_body, attempt_retry_meta = read_upstream_with_429_retry(
                    target_url(upstream, self.path),
                    "POST",
                    headers,
                    data=upstream_raw,
                    timeout=600,
                    max_retries=remaining_429_retries,
                    max_retry_after_seconds=self.router.config.hot_router.max_retry_after_seconds,
                )
                retry_meta["upstream_retries"] += int(attempt_retry_meta.get("upstream_retries") or 0)
                retry_meta["retry_wait_seconds"] = round(
                    float(retry_meta.get("retry_wait_seconds") or 0)
                    + float(attempt_retry_meta.get("retry_wait_seconds") or 0),
                    3,
                )
                retry_meta["retry_after"].extend(attempt_retry_meta.get("retry_after") or [])
                if not (200 <= status < 300):
                    self.send_upstream(status, response_headers, response_body)
                    log_event(
                        "response",
                        request_id=request_id,
                        status=status,
                        route=route,
                        response_bytes=len(response_body),
                        empty_output_retries=empty_output_retries,
                        **retry_meta,
                        **log_fields,
                    )
                    return
                parsed = json.loads(response_body.decode("utf-8-sig") or "{}")
                converted = response_json_from_upstream(
                    parsed if isinstance(parsed, dict) else {},
                    model,
                )
                should_retry_empty = (
                    str(converted.get("status") or "completed") == "completed"
                    and not response_has_meaningful_output(converted)
                    and empty_output_retries < max_empty_retries
                )
                if not should_retry_empty:
                    break
                empty_output_retries += 1
                delay = min(0.25, self.router.config.hot_router.max_retry_after_seconds)
                if delay:
                    time.sleep(delay)
                    empty_retry_wait += delay
            body = responses_sse_body_from_json(converted, model)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            log_event(
                "response",
                request_id=request_id,
                status=200,
                route=route,
                upstream_response_bytes=len(response_body),
                response_bytes=len(body),
                converted_output_items=len(converted.get("output") or []),
                converted_status=converted.get("status"),
                empty_output_retries=empty_output_retries,
                empty_retry_wait_seconds=round(empty_retry_wait, 3),
                **retry_meta,
                **log_fields,
            )
        except Exception as exc:
            payload = {"error": f"{type(exc).__name__}: {exc}"}
            self.write_json(502, payload)
            log_event("response", request_id=request_id, status=502, route=route, error=payload["error"], response_bytes=0, **log_fields)


def handler_for(router: HotRouter) -> type[HotRouterHandler]:
    class BoundHotRouterHandler(HotRouterHandler):
        pass

    BoundHotRouterHandler.router = router
    return BoundHotRouterHandler


def run_hot_router(config_path: str | None = None, *, host: str | None = None, port: int | None = None) -> int:
    config = load_config(config_path)
    configure_proxy_environment(config)
    router = HotRouter(config, host=host, port=port)
    router.write_state()
    server = ThreadingHTTPServer((router.host, router.port), handler_for(router))
    print(f"Codex hot router listening on http://{router.host}:{router.port}/v1")
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
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args(argv)
    return run_hot_router(args.config, host=args.host, port=args.port)
