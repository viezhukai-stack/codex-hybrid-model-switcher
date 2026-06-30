from __future__ import annotations

import argparse
import os
import platform
import time
from pathlib import Path
from urllib.parse import urlparse

from .config import AppConfig, load_config
from .private_config import validate_config
from .switcher import file_hash


PROTECTED_FILES = ("auth.json", "models_cache.json", "state_5.sqlite")
SECTION_MARKERS = {
    "mcp": "[mcp_servers.",
    "plugins": "[plugins.",
    "projects": "[projects.",
    "desktop": "[desktop]",
    "features": "[features]",
}


def redact_path(path: Path) -> str:
    return "<configured>" if path.exists() else "<missing>"


def redact_url(value: object) -> str:
    parsed = urlparse(str(value or ""))
    if not parsed.scheme:
        return "<redacted-url>"
    suffix = parsed.path or ""
    return f"{parsed.scheme}://<redacted>{suffix}"


def read_config_toml(config: AppConfig) -> str:
    path = config.codex_home / "config.toml"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def current_model_fields(config_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in config_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            break
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key in {"model_provider", "model", "review_model"}:
            fields[key] = value.strip().strip('"')
    return fields


def section_presence(config_text: str) -> dict[str, bool]:
    return {name: marker in config_text for name, marker in SECTION_MARKERS.items()}


def newest_backup(config: AppConfig) -> str:
    backups = sorted(config.codex_home.glob("config.toml.bak-codex-hybrid-*"))
    if not backups:
        return "missing"
    return backups[-1].name


def protected_file_lines(config: AppConfig) -> list[str]:
    lines: list[str] = []
    for name in PROTECTED_FILES:
        path = config.codex_home / name
        digest = file_hash(path)
        status = "missing" if digest is None else f"present sha256={digest[:12]}"
        lines.append(f"- `{name}`: {status}")
    sessions = config.codex_home / "sessions"
    rollouts = config.codex_home / "rollouts"
    lines.append(f"- `sessions/`: {'present' if sessions.exists() else 'missing'}")
    lines.append(f"- `rollouts/`: {'present' if rollouts.exists() else 'missing'}")
    return lines


def provider_lines(config: AppConfig) -> list[str]:
    lines: list[str] = []
    for provider in config.providers:
        provider_id = provider.get("id") or "<missing>"
        kind = provider.get("kind") or "<missing>"
        model = provider.get("model") or "<missing>"
        line = f"- `{provider_id}`: kind=`{kind}` model=`{model}`"
        if kind == "cloud":
            line += f" base_url=`{redact_url(provider.get('base_url'))}`"
            env_name = str(provider.get("api_key_env") or "<missing>")
            line += f" api_key_env=`{env_name}` status=`{'set' if os.environ.get(env_name) else 'unset'}`"
        lines.append(line)
    return lines


def local_model_lines(config: AppConfig) -> list[str]:
    local = config.local_model
    if not local:
        return ["- not configured"]
    lines = []
    for key in ("llama_server_path", "model_path", "mmproj_path"):
        value = local.get(key)
        if not value:
            lines.append(f"- `{key}`: missing")
            continue
        lines.append(f"- `{key}`: {redact_path(Path(os.path.expanduser(os.path.expandvars(str(value)))))}")
    return lines


def render_report(config_path: str | None = None) -> str:
    config = load_config(config_path)
    config_text = read_config_toml(config)
    fields = current_model_fields(config_text)
    sections = section_presence(config_text)
    errors = validate_config(config)
    lines = [
        "# Codex Hybrid Setup Report",
        "",
        "## Summary",
        "",
        f"- generated_at: `{time.strftime('%Y-%m-%d %H:%M:%S %z')}`",
        f"- platform: `{platform.system() or os.name}`",
        f"- config_file: `<private-config>`",
        f"- codex_home: `{redact_path(config.codex_home)}`",
        f"- config_validation: `{'passed' if not errors else 'failed'}`",
        f"- active_model_provider: `{fields.get('model_provider', '<missing>')}`",
        f"- active_model: `{fields.get('model', '<missing>')}`",
        f"- newest_config_backup: `{newest_backup(config)}`",
        "",
        "## Providers",
        "",
        *provider_lines(config),
        "",
        "## Protected Codex Files",
        "",
        *protected_file_lines(config),
        "",
        "## Preserved Config Sections",
        "",
    ]
    for name, present in sections.items():
        lines.append(f"- `{name}`: {'present' if present else 'missing'}")
    lines.extend(
        [
            "",
            "## Local Model",
            "",
            *local_model_lines(config),
            "",
            "## User Success Checklist",
            "",
            "- [ ] Codex Desktop opens without an error page.",
            "- [ ] Account information is still visible.",
            "- [ ] Plugin and MCP entry points are still visible.",
            "- [ ] The project list is still visible.",
            "- [ ] A new test conversation responds using the configured provider.",
            "- [ ] The report has been reviewed for accidental secrets before sharing.",
            "",
            "## Safety Notes",
            "",
            "- This report redacts provider hostnames and local paths.",
            "- This report does not include API keys, account tokens, session content, or database content.",
            "- `auth.json`, `models_cache.json`, `state_5.sqlite`, `sessions/`, and `rollouts/` should not be shared.",
        ]
    )
    if errors:
        lines.extend(["", "## Validation Errors", ""])
        lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines) + "\n"


def run_setup_report(config_path: str | None = None, *, output: str | None = None) -> int:
    report = render_report(config_path)
    if output:
        path = Path(os.path.expanduser(os.path.expandvars(output)))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        print(f"Wrote setup report: {path}")
    else:
        print(report, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    return run_setup_report(args.config, output=args.output)


if __name__ == "__main__":
    raise SystemExit(main())
