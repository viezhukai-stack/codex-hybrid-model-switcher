from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import AppConfig, load_config


@dataclass(frozen=True)
class JsonResult:
    ok: bool
    status: int | None
    data: dict[str, Any] | None
    error: str | None = None


def port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def fetch_json(url: str, *, timeout: float = 2.0) -> JsonResult:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8-sig")
            data = json.loads(body or "{}")
            if not isinstance(data, dict):
                return JsonResult(False, resp.status, None, "response was not a JSON object")
            return JsonResult(200 <= resp.status < 300, resp.status, data)
    except urllib.error.HTTPError as exc:
        return JsonResult(False, exc.code, None, f"HTTP {exc.code}")
    except json.JSONDecodeError:
        return JsonResult(False, None, None, "response was not valid JSON")
    except OSError as exc:
        return JsonResult(False, None, None, exc.__class__.__name__)


def bridge_required_reasons(config: AppConfig) -> list[str]:
    reasons: list[str] = []
    for provider in config.providers:
        provider_id = str(provider.get("id") or "<unknown>")
        kind = str(provider.get("kind") or "")
        if kind == "local":
            reasons.append(f"{provider_id} (local)")
        elif kind == "cloud" and str(provider.get("route") or "direct") == "bridge":
            reasons.append(f"{provider_id} (cloud bridge)")
    return reasons


def expected_bridge_models(config: AppConfig) -> list[str]:
    models: list[str] = []
    for provider in config.providers:
        kind = str(provider.get("kind") or "")
        route = str(provider.get("route") or "direct")
        model = str(provider.get("model") or "")
        if not model:
            continue
        if kind == "local" or (kind == "cloud" and route == "bridge"):
            models.append(model)
    local_id = str(config.local_model.get("id") or "")
    if local_id and any(provider.get("kind") == "local" for provider in config.providers):
        models.append(local_id)
    return sorted(set(models))


def bridge_cloud_env_status(config: AppConfig) -> list[tuple[str, str, bool]]:
    statuses: list[tuple[str, str, bool]] = []
    for provider in config.providers:
        if provider.get("kind") != "cloud" or str(provider.get("route") or "direct") != "bridge":
            continue
        provider_id = str(provider.get("id") or "<unknown>")
        env_name = str(provider.get("api_key_env") or "").strip() or "<missing>"
        statuses.append((provider_id, env_name, bool(os.environ.get(env_name))))
    return statuses


def model_ids_from_models_payload(data: dict[str, Any] | None) -> list[str]:
    if not data:
        return []
    items = data.get("data")
    if not isinstance(items, list):
        return []
    models: list[str] = []
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            models.append(str(item["id"]))
    return sorted(set(models))


def model_ids_from_health_payload(data: dict[str, Any] | None) -> list[str]:
    if not data:
        return []
    items = data.get("models")
    if not isinstance(items, list):
        return []
    return sorted({str(item) for item in items if item})


def quote_arg(value: str) -> str:
    if os.name == "nt":
        return subprocess_quote_windows(value)
    return shlex.quote(value)


def subprocess_quote_windows(value: str) -> str:
    if not value:
        return '""'
    if not any(ch.isspace() or ch in '"&|<>()^' for ch in value):
        return value
    return '"' + value.replace('"', r'\"') + '"'


def bridge_command(config: AppConfig) -> str:
    config_arg = quote_arg(str(config.path))
    if os.name == "nt":
        return f"py -3 -m codex_hybrid_switcher bridge --config {config_arg}"
    return f"python3 -m codex_hybrid_switcher bridge --config {config_arg}"


def env_help_command(config: AppConfig) -> str:
    config_arg = quote_arg(str(config.path))
    if os.name == "nt":
        return f"py -3 -m codex_hybrid_switcher env-help --config {config_arg}"
    return f"python3 -m codex_hybrid_switcher env-help --config {config_arg}"


def render_check(label: str, result: JsonResult) -> str:
    if result.ok:
        return f"OK {label}: HTTP {result.status}"
    detail = result.error or "request failed"
    if result.status is not None:
        detail = f"HTTP {result.status}"
    return f"FAIL {label}: {detail}"


def run_bridge_health(config_path: str | None = None, *, strict: bool = False, timeout: float = 2.0) -> int:
    config = load_config(config_path)
    bridge = config.bridge
    required_reasons = bridge_required_reasons(config)
    expected_models = expected_bridge_models(config)
    env_statuses = bridge_cloud_env_status(config)
    endpoint = f"http://{bridge.host}:{bridge.port}/v1"
    ok = True

    print("Bridge health")
    print("=============")
    print(f"config: {config.path}")
    print(f"bridge endpoint: {endpoint}")
    if required_reasons:
        print("required by:")
        for reason in required_reasons:
            print(f"  - {reason}")
    else:
        print("required by: no bridge-routed providers in this config")

    if env_statuses:
        print("API key environment variables:")
        for provider_id, env_name, is_set in env_statuses:
            state = "set" if is_set else "unset"
            print(f"  - {provider_id}: {env_name} ({state})")
            if not is_set:
                ok = False
    else:
        print("API key environment variables: none required by bridge-routed cloud providers")

    tcp_open = port_open(bridge.host, bridge.port)
    print(f"{'OPEN' if tcp_open else 'CLOSED'} bridge TCP port: {bridge.host}:{bridge.port}")
    if not tcp_open:
        if strict or required_reasons:
            ok = False
        print("Next steps:")
        if any(not is_set for _, _, is_set in env_statuses):
            print(f"  - Set missing API key environment variables with: {env_help_command(config)}")
        print(f"  - Start the bridge in a terminal with: {bridge_command(config)}")
        print("  - Keep that terminal open while testing Codex, or rerun guarded-switch so it can start the managed bridge.")
        return 0 if ok else 1

    health = fetch_json(f"{endpoint}/health", timeout=timeout)
    models = fetch_json(f"{endpoint}/models", timeout=timeout)
    print(render_check("/v1/health", health))
    print(render_check("/v1/models", models))

    if strict or required_reasons:
        ok &= health.ok and models.ok

    health_models = model_ids_from_health_payload(health.data)
    listed_models = model_ids_from_models_payload(models.data)
    if health_models:
        print("Models from /v1/health:")
        for model in health_models:
            print(f"  - {model}")
    if listed_models:
        print("Models from /v1/models:")
        for model in listed_models:
            print(f"  - {model}")

    missing = [model for model in expected_models if model not in listed_models]
    if missing:
        ok = False
        print("Missing expected bridge models:")
        for model in missing:
            print(f"  - {model}")

    if ok:
        print("Bridge health passed.")
        return 0

    print("Next steps:")
    if any(not is_set for _, _, is_set in env_statuses):
        print(f"  - Set missing API key environment variables with: {env_help_command(config)}")
    if not health.ok or not models.ok:
        print("  - The port is open but the bridge HTTP API is not healthy. Another service may be using the port.")
        print(f"  - Stop the conflicting service or start this project's bridge with: {bridge_command(config)}")
    if missing:
        print("  - Restart the bridge so it reloads the current private config.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args(argv)
    return run_bridge_health(args.config, strict=args.strict, timeout=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
