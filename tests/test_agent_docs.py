from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_agents_runbook_contains_required_safety_invariants():
    text = read("AGENTS.md")

    for protected in ("auth.json", "models_cache.json", "state_5.sqlite", "sessions/"):
        assert protected in text
    for forbidden in ("KeepAlive", "LaunchAgents", "scheduled tasks", "recovery loops"):
        assert forbidden in text
    assert "Never switch providers while Codex Desktop is running" in text
    assert "guarded-switch --dry-run" in text
    assert "config.toml.bak-codex-hybrid-*" in text


def test_agents_runbook_points_to_beginner_docs_and_local_smoke():
    text = read("AGENTS.md")

    assert "docs/first-run-wizard.md" in text
    assert "docs/agent-assisted-setup.md" in text
    assert "docs/recovery.md" in text
    assert "docs/local-llama-smoke.md" in text
    assert "codex-hybrid-switcher local-smoke" in text
    assert "codex-hybrid-switcher guarded-switch local-gemma --allow-local" in text


def test_agent_assisted_setup_has_copy_paste_prompt_and_history_caveat():
    text = read("docs/agent-assisted-setup.md")

    assert "Copy-paste prompt for Codex" in text
    assert "AGENTS.md" in text
    assert "api_key_env" in text
    assert "不要修改 auth.json" in text
    assert "openai" in text
    assert "custom" in text
    assert "does not rewrite history" in text


def test_setup_intake_warns_against_raw_secret_collection():
    text = read("docs/setup-intake.md")

    assert "Do not write the API key itself here" in text
    assert "API key environment variable name" in text
    assert "auth.json" in text
    assert "models_cache.json" in text
    assert "state_5.sqlite" in text


def test_readme_links_agent_assisted_path():
    text = read("README.md")

    assert "docs/agent-assisted-setup.md" in text
    assert "docs/setup-intake.md" in text
    assert "AGENTS.md" in text
