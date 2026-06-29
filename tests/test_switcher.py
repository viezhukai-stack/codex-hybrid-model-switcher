from __future__ import annotations

import json

from codex_hybrid_switcher import switcher
from codex_hybrid_switcher.config import load_config


def write_config(tmp_path, *, codex_home=None):
    codex_home = codex_home or tmp_path / "codex-home"
    config_path = tmp_path / "switcher-config.json"
    config_path.write_text(
        json.dumps(
            {
                "codex_home": str(codex_home),
                "providers": [
                    {
                        "id": "cloud-gpt-main",
                        "label": "Cloud GPT Main",
                        "kind": "cloud",
                        "base_url": "https://example.test/v1",
                        "model": "provider-gpt-main",
                        "wire_api": "responses",
                    },
                    {
                        "id": "local-gemma",
                        "label": "Local Gemma",
                        "kind": "local",
                        "model": "local/gemma",
                        "wire_api": "responses",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return config_path, codex_home


def test_strip_managed_config_preserves_unrelated_sections():
    existing = """model_provider = "openai"
model = "gpt-5.5"
review_model = "gpt-5.5"

[model_providers.custom]
name = "Old"
base_url = "http://127.0.0.1:1/v1"
wire_api = "responses"

[mcp_servers.example]
command = "example"

[features]
web_search = true
"""

    stripped = switcher.strip_managed_config(existing)

    assert 'model_provider = "openai"' not in stripped
    assert "[model_providers.custom]" not in stripped
    assert "[mcp_servers.example]" in stripped
    assert 'command = "example"' in stripped
    assert "[features]" in stripped
    assert "web_search = true" in stripped


def test_rendered_config_replaces_model_provider_and_keeps_mcp_blocks(tmp_path):
    config_path, _codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    provider = config.provider("cloud-gpt-main")
    existing = """model_provider = "openai"
model = "gpt-5.5"

[model_providers.custom]
name = "Old"
base_url = "http://127.0.0.1:1/v1"

[mcp_servers.example]
command = "example"
"""

    rendered = switcher.build_config_text(existing, provider, config)

    assert 'model_provider = "custom"' in rendered
    assert 'model = "provider-gpt-main"' in rendered
    assert 'base_url = "https://example.test/v1"' in rendered
    assert 'base_url = "http://127.0.0.1:1/v1"' not in rendered
    assert "[mcp_servers.example]" in rendered
    assert 'command = "example"' in rendered
    assert rendered.index('model_provider = "custom"') < rendered.index("[mcp_servers.example]")


def test_switch_dry_run_has_no_side_effects(tmp_path, monkeypatch, capsys):
    config_path, codex_home = write_config(tmp_path)
    codex_home.mkdir()
    config_toml = codex_home / "config.toml"
    before = """model_provider = "openai"
model = "gpt-5.5"

[mcp_servers.example]
command = "example"
"""
    config_toml.write_text(before, encoding="utf-8")

    monkeypatch.setattr(switcher, "codex_is_running", lambda: (_ for _ in ()).throw(AssertionError("should not check Codex")))
    monkeypatch.setattr(switcher, "start_bridge", lambda _config: (_ for _ in ()).throw(AssertionError("should not start bridge")))
    monkeypatch.setattr(switcher, "stop_bridge", lambda _config: (_ for _ in ()).throw(AssertionError("should not stop bridge")))

    code = switcher.switch_provider("local-gemma", str(config_path), dry_run=True)
    out = capsys.readouterr().out

    assert code == 0
    assert "Dry run" in out
    assert "+model_provider = \"custom\"" in out
    assert config_toml.read_text(encoding="utf-8") == before
    assert list(codex_home.glob("*.bak-codex-hybrid-*")) == []
