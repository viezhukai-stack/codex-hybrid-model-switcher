from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None

from .config import load_config
from .switcher import backup_file, codex_config_path, codex_is_running, runtime_dir

DEFAULT_ROUTER_URL = "http://127.0.0.1:19032/v1"


class HotRouterModeError(RuntimeError):
    pass


def active_file(config_path: Path) -> Path:
    stem = config_path.name.replace(".", "-")
    return runtime_dir(load_config(str(config_path))) / f"hot-router-active-{stem}.json"


def parse_toml_scalar(raw: str) -> Any:
    value = raw.strip()
    if value in {"true", "false"}:
        return value == "true"
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def simple_toml_loads(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current: dict[str, Any] = root
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = root
            for part in line[1:-1].split("."):
                nested = current.setdefault(part, {})
                if not isinstance(nested, dict):
                    nested = {}
                    current[part] = nested
                current = nested
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key.strip()] = parse_toml_scalar(value)
    return root


def parse_toml(text: str) -> dict[str, Any]:
    if tomllib is not None:
        return tomllib.loads(text)
    return simple_toml_loads(text)


def require_router_online(router_url: str) -> None:
    base = router_url[:-3] if router_url.endswith("/v1") else router_url
    health_url = base.rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(health_url, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8-sig") or "{}")
    except Exception as exc:
        raise HotRouterModeError(f"hot router is not healthy at {health_url}: {exc}") from exc
    if not isinstance(data, dict) or data.get("router") != "codex-hot-router":
        raise HotRouterModeError(f"port is not running codex-hot-router: {health_url}")


def patch_custom_base_url(config_text: str, new_base_url: str) -> tuple[str, str]:
    parsed = parse_toml(config_text)
    if parsed.get("model_provider") != "custom":
        raise HotRouterModeError('expected model_provider = "custom"; refusing to enable hot router mode')
    providers = parsed.get("model_providers")
    custom = providers.get("custom") if isinstance(providers, dict) else None
    if not isinstance(custom, dict):
        raise HotRouterModeError("missing [model_providers.custom] block")
    old_base_url = custom.get("base_url")
    if not isinstance(old_base_url, str) or not old_base_url:
        raise HotRouterModeError("custom provider has no base_url")

    lines = config_text.splitlines()
    section_start = None
    for index, line in enumerate(lines):
        if line.strip() == "[model_providers.custom]":
            section_start = index
            break
    if section_start is None:
        raise HotRouterModeError("could not find [model_providers.custom] section")

    section_end = len(lines)
    for index in range(section_start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section_end = index
            break

    replacement = f"base_url = {json.dumps(new_base_url)}"
    for index in range(section_start + 1, section_end):
        if re.match(r"^\s*base_url\s*=", lines[index]):
            lines[index] = replacement
            break
    else:
        lines.insert(section_end, replacement)
    patched = "\n".join(lines).rstrip() + "\n"
    parse_toml(patched)
    return patched, old_base_url


def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def run_hot_router_mode(
    command: str,
    config_path: str | None = None,
    *,
    router_url: str = DEFAULT_ROUTER_URL,
    allow_codex_running: bool = False,
) -> int:
    config = load_config(config_path)
    codex_config = codex_config_path(config)
    marker = active_file(config.path)

    if command == "status":
        exists = marker.exists()
        print(json.dumps({"active": exists, "marker": str(marker), "codex_config": str(codex_config)}, indent=2))
        return 0

    if codex_is_running() and not allow_codex_running:
        print("Codex Desktop appears to be running. Quit Codex completely before changing hot router mode.")
        return 2

    if command == "enable":
        require_router_online(router_url)
        original = codex_config.read_text(encoding="utf-8", errors="replace")
        patched, old_base_url = patch_custom_base_url(original, router_url)
        backup = backup_file(codex_config)
        write_text_atomic(codex_config, patched)
        marker.write_text(
            json.dumps(
                {
                    "enabled_at": int(time.time()),
                    "router_url": router_url,
                    "old_base_url": old_base_url,
                    "backup": str(backup) if backup else None,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Enabled Codex hot router mode: {old_base_url} -> {router_url}")
        if backup:
            print(f"Backed up config.toml: {backup}")
        return 0

    if command == "restore":
        if not marker.exists():
            print(f"No active hot router marker found: {marker}")
            return 2
        data = json.loads(marker.read_text(encoding="utf-8-sig"))
        backup = Path(str(data.get("backup") or ""))
        if not backup.exists():
            print(f"Config backup is missing: {backup}")
            return 2
        write_text_atomic(codex_config, backup.read_text(encoding="utf-8", errors="replace"))
        marker.unlink(missing_ok=True)
        print(f"Restored Codex config.toml from: {backup}")
        return 0

    print(f"Unknown hot-router-mode command: {command}")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enable or restore Codex hot router mode.")
    parser.add_argument("command", choices=["enable", "restore", "status"])
    parser.add_argument("--config")
    parser.add_argument("--router-url", default=DEFAULT_ROUTER_URL)
    parser.add_argument("--allow-codex-running", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run_hot_router_mode(
            args.command,
            args.config,
            router_url=args.router_url,
            allow_codex_running=args.allow_codex_running,
        )
    except HotRouterModeError as exc:
        print(f"ERROR: {exc}")
        return 1
