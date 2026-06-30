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

    assert "START_HERE.md" in text
    assert "FINAL_CHECK.md" in text
    assert "docs/first-run-wizard.md" in text
    assert "docs/bootstrap.md" in text
    assert "docs/agent-assisted-setup.md" in text
    assert "docs/recovery.md" in text
    assert "docs/local-llama-smoke.md" in text
    assert "docs/stock-codex-handoff-validation.md" in text
    assert "docs/user-success-criteria.md" in text
    assert "validate-stock-codex-handoff.py" in text
    assert "codex-hybrid-switcher local-smoke" in text
    assert "codex-hybrid-switcher guarded-switch local-gemma --allow-local" in text
    assert "setup-report" in text


def test_agent_assisted_setup_has_copy_paste_prompt_and_history_caveat():
    text = read("docs/agent-assisted-setup.md")

    assert "Copy-paste prompt for Codex" in text
    assert "START_HERE.md" in text
    assert "AGENTS.md" in text
    assert "bootstrap.py" in text
    assert "api_key_env" in text
    assert "不要修改 auth.json" in text
    assert "openai" in text
    assert "custom" in text
    assert "does not rewrite history" in text
    assert "setup-report" in text


def test_setup_intake_warns_against_raw_secret_collection():
    text = read("docs/setup-intake.md")

    assert "Do not write the API key itself here" in text
    assert "API key environment variable name" in text
    assert "auth.json" in text
    assert "models_cache.json" in text
    assert "state_5.sqlite" in text


def test_readme_links_agent_assisted_path():
    text = read("README.md")

    assert "START_HERE.md" in text
    assert "FINAL_CHECK.md" in text
    assert "docs/agent-assisted-setup.md" in text
    assert "docs/setup-intake.md" in text
    assert "docs/bootstrap.md" in text
    assert "docs/setup-report.md" in text
    assert "docs/user-success-criteria.md" in text
    assert "docs/stock-codex-handoff-validation.md" in text
    assert "AGENTS.md" in text


def test_user_success_criteria_covers_visible_codex_completion():
    text = read("docs/user-success-criteria.md")

    assert "Codex Desktop opens without an error page" in text
    assert "Account information is still visible" in text
    assert "Plugin and MCP entry points are still visible" in text
    assert "project list is still visible" in text
    assert "A new test conversation responds" in text
    assert "not complete yet" in text
    for protected in ("auth.json", "models_cache.json", "state_5.sqlite", "sessions/"):
        assert protected in text


def test_chinese_tutorial_points_to_stock_handoff():
    text = read("docs/tutorial.zh-CN.md")

    assert "START_HERE.md" in text
    assert "可以直接复制给 Codex 的任务单" in text


def test_start_here_is_safe_stock_codex_handoff():
    text = read("START_HERE.md")

    assert "stock Codex Desktop" in text
    assert "Copy This Prompt Into Codex" in text
    assert "FINAL_CHECK.md" in text
    assert "bootstrap.py" in text
    assert "guarded-switch --dry-run" in text
    assert "setup-report" in text
    assert "base_url" in text
    assert "model" in text
    assert "api_key_env" in text
    assert "不要填 API key 原文" in text
    for protected in ("auth.json", "models_cache.json", "state_5.sqlite", "sessions/"):
        assert protected in text
    for forbidden in ("LaunchAgent", "KeepAlive", "scheduled", "recovery loops"):
        assert forbidden in text
    assert "config.toml.bak-codex-hybrid-*" in text


def test_final_check_prompt_defines_completion_verdicts_and_safety_boundary():
    text = read("FINAL_CHECK.md")

    assert "Copy This Prompt Into Codex" in text
    for verdict in ("Complete", "Partially complete", "Not complete", "Needs rollback"):
        assert verdict in text
    for visible in (
        "账号信息",
        "插件/MCP",
        "项目列表",
        "新建测试对话",
        "setup report",
    ):
        assert visible in text
    for protected in ("auth.json", "models_cache.json", "state_5.sqlite", "sessions", "rollout logs"):
        assert protected in text
    assert "请不要修改任何文件" in text
