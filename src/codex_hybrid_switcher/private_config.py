from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

from .config import DEFAULT_CONFIG, AppConfig, expand_path, load_config


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_platform() -> str:
    return "windows" if os.name == "nt" else "macos"


def example_config_path(platform: str | None = None) -> Path:
    name = platform or default_platform()
    if name not in {"macos", "windows"}:
        raise ValueError("platform must be macos or windows")
    return repo_root() / "config" / "examples" / f"config.{name}.example.json"


def private_marker(path: Path) -> str:
    if path == DEFAULT_CONFIG:
        return str(path)
    return "<private-config>"


def redact_url(value: object) -> str:
    parsed = urlparse(str(value or ""))
    if not parsed.scheme:
        return "<redacted-url>"
    path = parsed.path or ""
    return f"{parsed.scheme}://<redacted>{path}"


def env_status(name: str) -> str:
    return "set" if os.environ.get(name) else "unset"


def init_config(
    *,
    output: str | None = None,
    platform: str | None = None,
    template: str | None = None,
    force: bool = False,
) -> int:
    target = expand_path(output or DEFAULT_CONFIG)
    source = expand_path(template) if template else example_config_path(platform)
    if not source.exists():
        print(f"template not found: {source}")
        return 1
    if target.exists() and not force:
        print(f"config already exists: {target}")
        print("Use --force to replace it.")
        return 2
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print(f"Created private config: {target}")
    return 0


def validate_config(config: AppConfig, *, check_paths: bool = False) -> list[str]:
    errors: list[str] = []
    providers = config.providers
    if not providers:
        errors.append("providers must contain at least one provider")

    seen: set[str] = set()
    has_local_provider = False
    for provider in providers:
        provider_id = str(provider.get("id") or "")
        kind = str(provider.get("kind") or "")
        if provider_id in seen:
            errors.append(f"duplicate provider id: {provider_id}")
        seen.add(provider_id)
        if kind not in {"official", "cloud", "local"}:
            errors.append(f"{provider_id}: kind must be official, cloud, or local")
        if not provider.get("model"):
            errors.append(f"{provider_id}: model is required")
        if kind == "cloud":
            route = str(provider.get("route") or "direct")
            if route not in {"direct", "bridge"}:
                errors.append(f"{provider_id}: route must be direct or bridge")
            if not provider.get("base_url"):
                errors.append(f"{provider_id}: base_url is required")
            if not provider.get("api_key_env"):
                errors.append(f"{provider_id}: api_key_env is required")
        if kind == "local":
            has_local_provider = True

    local = config.local_model
    if has_local_provider:
        for key in ("llama_server_path", "model_path", "mmproj_path"):
            if not local.get(key):
                errors.append(f"local_model.{key} is required for local providers")
            elif check_paths and not expand_path(local[key]).exists():
                errors.append(f"local_model.{key} path does not exist")
    return errors


def print_validation(config: AppConfig, *, check_paths: bool = False) -> None:
    print("Private config validation")
    print(f"config: {private_marker(config.path)}")
    print("codex_home: configured")
    print(f"bridge: {config.bridge.host}:{config.bridge.port} -> llama:{config.bridge.llama_port}")
    print("providers:")
    for provider in config.providers:
        provider_id = provider.get("id")
        kind = provider.get("kind")
        model = provider.get("model") or "<missing>"
        line = f"  - {provider_id} [{kind}] model={model}"
        if kind == "cloud":
            env_name = str(provider.get("api_key_env") or "<missing>")
            route = str(provider.get("route") or "direct")
            line += f" route={route} base_url={redact_url(provider.get('base_url'))} api_key_env={env_name}({env_status(env_name)})"
        print(line)
    if any(provider.get("kind") == "local" for provider in config.providers):
        print("local_model:")
        for key in ("llama_server_path", "model_path", "mmproj_path"):
            value = config.local_model.get(key)
            if not value:
                print(f"  - {key}: missing")
                continue
            if check_paths:
                print(f"  - {key}: {'exists' if expand_path(value).exists() else 'missing'}")
            else:
                print(f"  - {key}: configured")


def run_validate_config(config_path: str | None = None, *, check_paths: bool = False) -> int:
    config = load_config(config_path)
    print_validation(config, check_paths=check_paths)
    errors = validate_config(config, check_paths=check_paths)
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Config validation passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--output")
    init.add_argument("--platform", choices=["macos", "windows"])
    init.add_argument("--template")
    init.add_argument("--force", action="store_true")
    validate = sub.add_parser("validate")
    validate.add_argument("--config")
    validate.add_argument("--check-paths", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "init":
        return init_config(output=args.output, platform=args.platform, template=args.template, force=args.force)
    if args.command == "validate":
        return run_validate_config(args.config, check_paths=args.check_paths)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
