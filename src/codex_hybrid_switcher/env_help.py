from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass

from .config import AppConfig, load_config


VALID_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class EnvVarInfo:
    name: str
    providers: tuple[str, ...]
    routes: tuple[str, ...]
    is_set: bool


def default_platform() -> str:
    return "windows" if os.name == "nt" else "macos"


def collect_env_vars(config: AppConfig, *, name: str | None = None) -> list[EnvVarInfo]:
    grouped: dict[str, dict[str, set[str]]] = {}
    for provider in config.providers:
        if provider.get("kind") != "cloud":
            continue
        env_name = str(provider.get("api_key_env") or "").strip()
        if not env_name:
            continue
        if name and env_name != name:
            continue
        entry = grouped.setdefault(env_name, {"providers": set(), "routes": set()})
        entry["providers"].add(str(provider.get("id") or "<unknown>"))
        entry["routes"].add(str(provider.get("route") or "direct"))
    return [
        EnvVarInfo(
            name=env_name,
            providers=tuple(sorted(data["providers"])),
            routes=tuple(sorted(data["routes"])),
            is_set=bool(os.environ.get(env_name)),
        )
        for env_name, data in sorted(grouped.items())
    ]


def shell_examples(env_name: str, *, platform: str) -> list[str]:
    placeholder = "replace-with-your-provider-key"
    if platform == "windows":
        return [
            "Temporary for the current PowerShell window:",
            f'  $env:{env_name} = "{placeholder}"',
            "",
            "Persistent for your Windows user account:",
            f'  [Environment]::SetEnvironmentVariable("{env_name}", "{placeholder}", "User")',
            "",
            "After persistent setup, close and reopen Codex Desktop and any terminal windows.",
        ]
    return [
        "Temporary for the current shell window:",
        f'  export {env_name}="{placeholder}"',
        "",
        "Persistent for zsh on macOS:",
        f'  printf \'\\nexport {env_name}="{placeholder}"\\n\' >> ~/.zshrc',
        "  source ~/.zshrc",
        "",
        "Persistent for bash:",
        f'  printf \'\\nexport {env_name}="{placeholder}"\\n\' >> ~/.bashrc',
        "  source ~/.bashrc",
        "",
        "After persistent setup, close and reopen Codex Desktop and any terminal windows.",
    ]


def render_env_help(config: AppConfig, *, platform: str | None = None, name: str | None = None) -> str:
    target_platform = platform or default_platform()
    env_vars = collect_env_vars(config, name=name)
    lines = [
        "API key environment help",
        "========================",
        "",
        "This command does not read, print, or store API keys.",
        "Use the commands below outside this repository, replacing the placeholder with your provider key.",
        "",
        "Configured API key variables:",
    ]
    if not env_vars:
        lines.extend(["  - none found", ""])
    for info in env_vars:
        validity = "valid" if VALID_ENV_NAME.match(info.name) else "invalid-name"
        status = "set" if info.is_set else "unset"
        lines.append(
            f"  - {info.name}: {status}, {validity}, providers={','.join(info.providers)}, routes={','.join(info.routes)}"
        )
    lines.append("")

    for info in env_vars:
        if not VALID_ENV_NAME.match(info.name):
            lines.extend(
                [
                    f"Skip command examples for invalid environment variable name: {info.name}",
                    "Use a name like OPENAI_COMPATIBLE_API_KEY instead.",
                    "",
                ]
            )
            continue
        lines.append(f"How to set {info.name} on {target_platform}:")
        lines.extend(shell_examples(info.name, platform=target_platform))
        lines.append("")

    lines.extend(
        [
            "After setting the variable, rerun:",
            f"  codex-hybrid-switcher validate-config --config {config.path}",
            "Then rerun your guarded dry-run before any real switch.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_env_help(config_path: str | None = None, *, platform: str | None = None, name: str | None = None) -> int:
    if platform and platform not in {"macos", "windows"}:
        print("platform must be macos or windows")
        return 2
    try:
        config = load_config(config_path)
    except FileNotFoundError as exc:
        print(f"config not found: {exc.filename}")
        return 1
    print(render_env_help(config, platform=platform, name=name), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--platform", choices=["macos", "windows"])
    parser.add_argument("--name", help="show help for one environment variable name")
    args = parser.parse_args(argv)
    return run_env_help(args.config, platform=args.platform, name=args.name)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
