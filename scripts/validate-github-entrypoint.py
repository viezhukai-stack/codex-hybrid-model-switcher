#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_URL = "https://github.com/viezhukai-stack/codex-hybrid-model-switcher"


HANDOFF_REQUIRED = (
    DEFAULT_REPO_URL,
    "stock Codex Desktop",
    "OpenAI-compatible",
    "base_url",
    "model",
    "api_key_env",
    "cloud_route: bridge",
    "Do not paste a raw API key",
    "HANDOFF_TO_CODEX.md",
    "START_HERE.md",
    "AGENTS.md",
    "FINAL_CHECK.md",
    "validate-agent-handoff-drill.py",
    "bootstrap.py",
    "validate-config",
    "env-help",
    "bridge-health",
    "guarded-switch --dry-run",
    "quit Codex Desktop",
    "config.toml",
    "setup-report",
    "canary-report",
    "real-canary-template",
    "auth.json",
    "models_cache.json",
    "state_5.sqlite",
    "sessions/",
    "rollout logs",
    "LaunchAgent",
    "KeepAlive",
    "scheduled tasks",
    "recovery loops",
)


DOC_LINK_REQUIREMENTS = {
    "README.md": ("HANDOFF_TO_CODEX.md", "START_HERE.md", "AGENTS.md"),
    "START_HERE.md": ("HANDOFF_TO_CODEX.md", "START_HERE.md", "AGENTS.md"),
    "AGENTS.md": ("HANDOFF_TO_CODEX.md", "START_HERE.md", "FINAL_CHECK.md"),
}


def assert_contains(path: Path, required: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"{path.relative_to(ROOT)} missing required GitHub handoff text: {missing}")


def assert_handoff_has_no_private_examples(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    forbidden = (
        "cpamc.kevintj.com",
        "10.0." + "0.",
        "/Users/" + "mac",
        "C:\\Users" + "\\",
        "Bearer ",
        "sk-",
        "990828",
        "966612",
    )
    leaked = [item for item in forbidden if item in text]
    if leaked:
        raise SystemExit(f"{path.relative_to(ROOT)} contains private-looking handoff content: {leaked}")


def validate(repo_url: str) -> int:
    handoff = ROOT / "HANDOFF_TO_CODEX.md"
    if not handoff.exists():
        raise SystemExit("HANDOFF_TO_CODEX.md is missing")
    required = tuple(repo_url if item == DEFAULT_REPO_URL else item for item in HANDOFF_REQUIRED)
    assert_contains(handoff, required)
    assert_handoff_has_no_private_examples(handoff)
    for rel_path, markers in DOC_LINK_REQUIREMENTS.items():
        assert_contains(ROOT / rel_path, markers)
    print("github handoff entrypoint validation passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the GitHub-to-Codex handoff entrypoint.")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    args = parser.parse_args(argv)
    return validate(args.repo_url)


if __name__ == "__main__":
    raise SystemExit(main())
