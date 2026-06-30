from __future__ import annotations

import json

from codex_hybrid_switcher.report import render_report, run_setup_report


def write_codex_home(tmp_path):
    codex_home = tmp_path / "private-codex-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        """model_provider = "custom"
model = "private-model"
review_model = "private-model"
model_reasoning_effort = "high"

[model_providers.custom]
name = "Private Provider"
base_url = "https://private-provider.example/v1"
wire_api = "responses"
requires_openai_auth = true

[mcp_servers.example]
command = "example"

[plugins.example]
enabled = true

[projects."/private/project"]
trust_level = "trusted"

[features]
web_search = true
""",
        encoding="utf-8",
    )
    (codex_home / "auth.json").write_text('{"token":"do-not-print"}', encoding="utf-8")
    (codex_home / "models_cache.json").write_text('{"models":[]}', encoding="utf-8")
    (codex_home / "state_5.sqlite").write_bytes(b"do-not-print-sqlite")
    (codex_home / "sessions").mkdir()
    (codex_home / "sessions" / "session.jsonl").write_text("do-not-print-session", encoding="utf-8")
    (codex_home / "rollouts").mkdir()
    (codex_home / "rollouts" / "rollout.log").write_text("do-not-print-rollout", encoding="utf-8")
    (codex_home / "config.toml.bak-codex-hybrid-20260630-000000").write_text("backup", encoding="utf-8")
    return codex_home


def write_private_config(tmp_path, codex_home):
    config_path = tmp_path / "config.json"
    private_model_path = tmp_path / "private-model.gguf"
    config_path.write_text(
        json.dumps(
            {
                "codex_home": str(codex_home),
                "providers": [
                    {
                        "id": "cloud-main",
                        "label": "Private Cloud",
                        "kind": "cloud",
                        "base_url": "https://private-provider.example/v1",
                        "api_key_env": "PRIVATE_PROVIDER_KEY",
                        "model": "private-model",
                        "wire_api": "responses",
                        "route": "bridge",
                    },
                    {
                        "id": "local-gemma",
                        "label": "Local Gemma",
                        "kind": "local",
                        "model": "local/gemma",
                    },
                ],
                "local_model": {
                    "id": "local/gemma",
                    "llama_server_path": str(tmp_path / "llama-server"),
                    "model_path": str(private_model_path),
                    "mmproj_path": str(tmp_path / "mmproj.gguf"),
                },
            }
        ),
        encoding="utf-8",
    )
    return config_path


def test_render_report_redacts_private_values(tmp_path):
    codex_home = write_codex_home(tmp_path)
    config_path = write_private_config(tmp_path, codex_home)

    report = render_report(str(config_path))

    assert "Codex Hybrid Setup Report" in report
    assert "https://<redacted>/v1" in report
    assert "route=`bridge`" in report
    assert "private-provider.example" not in report
    assert str(tmp_path) not in report
    assert "do-not-print" not in report
    assert "active_model_provider: `custom`" in report
    assert "newest_config_backup: `config.toml.bak-codex-hybrid-20260630-000000`" in report
    assert "`mcp`: present" in report
    assert "`plugins`: present" in report
    assert "`projects`: present" in report
    assert "`auth.json`: present sha256=" in report
    assert "`state_5.sqlite`: present sha256=" in report
    assert "## User Success Checklist" in report
    assert "Account information is still visible" in report
    assert "A new test conversation responds" in report


def test_run_setup_report_writes_output(tmp_path):
    codex_home = write_codex_home(tmp_path)
    config_path = write_private_config(tmp_path, codex_home)
    output = tmp_path / "report.md"

    assert run_setup_report(str(config_path), output=str(output)) == 0

    text = output.read_text(encoding="utf-8")
    assert "Codex Hybrid Setup Report" in text
    assert "User Success Checklist" in text
    assert "private-provider.example" not in text
