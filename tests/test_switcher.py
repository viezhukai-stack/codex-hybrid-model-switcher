from __future__ import annotations

import json
import subprocess

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


def write_realistic_codex_home(codex_home):
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        """model_provider = "openai"
model = "gpt-5.5"

[mcp_servers.example]
command = "example"
""",
        encoding="utf-8",
    )
    (codex_home / "auth.json").write_text('{"auth":true}', encoding="utf-8")
    (codex_home / "models_cache.json").write_text('{"models":[]}', encoding="utf-8")
    (codex_home / "state_5.sqlite").write_bytes(b"sqlite-placeholder")


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


def test_rendered_config_preserves_custom_provider_extra_fields(tmp_path):
    config_path, _codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    provider = config.provider("cloud-gpt-main")
    existing = """model_provider = "custom"
model = "old-model"

[model_providers.custom]
name = "Old"
base_url = "https://old.example/v1"
wire_api = "responses"
requires_openai_auth = true
experimental_bearer_token = "secret-token"
sandbox_mode = "workspace-write"

[plugins.example]
enabled = true
"""

    rendered = switcher.build_config_text(existing, provider, config)
    diff = switcher.unified_diff(tmp_path / "config.toml", existing, rendered)

    assert 'base_url = "https://example.test/v1"' in rendered
    assert 'base_url = "https://old.example/v1"' not in rendered
    assert 'experimental_bearer_token = "secret-token"' in rendered
    assert 'sandbox_mode = "workspace-write"' in rendered
    assert "[plugins.example]" in rendered
    assert "secret-token" not in diff
    assert '-experimental_bearer_token = "<redacted>"' not in diff


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


def test_file_hash_returns_none_for_missing_file(tmp_path):
    assert switcher.file_hash(tmp_path / "missing") is None


def test_codex_is_running_treats_process_query_failure_as_running(monkeypatch):
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="")

    monkeypatch.setattr(switcher.subprocess, "run", fake_run)

    assert switcher.codex_is_running() is True


def test_codex_is_running_detects_windows_codex_process(monkeypatch):
    def fake_run(args, **_kwargs):
        assert args == ["tasklist"]
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="Codex.exe  1234 Console")

    monkeypatch.setattr(switcher.sys, "platform", "win32")
    monkeypatch.setattr(switcher.subprocess, "run", fake_run)

    assert switcher.codex_is_running() is True


def test_switch_refuses_when_codex_is_running_without_writing(tmp_path, monkeypatch, capsys):
    config_path, codex_home = write_config(tmp_path)
    write_realistic_codex_home(codex_home)
    config_toml = codex_home / "config.toml"
    before = config_toml.read_text(encoding="utf-8")

    monkeypatch.setattr(switcher, "codex_is_running", lambda: True)
    monkeypatch.setattr(switcher, "stop_bridge", lambda _config: (_ for _ in ()).throw(AssertionError("should not stop bridge")))

    code = switcher.switch_provider("cloud-gpt-main", str(config_path))
    out = capsys.readouterr().out

    assert code == 2
    assert "Codex Desktop appears to be running" in out
    assert config_toml.read_text(encoding="utf-8") == before
    assert list(codex_home.glob("config.toml.bak-codex-hybrid-*")) == []


def test_unified_diff_redacts_private_config_values(tmp_path):
    before = 'base_url = "https://private.example/v1"\nexperimental_bearer_token = "secret-token"\nmodel = "old"\n'
    after = 'base_url = "https://planned.example/v1"\nexperimental_bearer_token = "new-secret"\nmodel = "new"\n'

    diff = switcher.unified_diff(tmp_path / "config.toml", before, after)

    assert "private.example" not in diff
    assert "planned.example" not in diff
    assert "secret-token" not in diff
    assert 'base_url = "<redacted>"' in diff
    assert '-model = "old"' in diff
    assert '+model = "new"' in diff


def test_guarded_switch_dry_run_has_no_side_effects(tmp_path, monkeypatch, capsys):
    config_path, codex_home = write_config(tmp_path)
    write_realistic_codex_home(codex_home)
    before = {path.name: switcher.file_hash(path) for path in codex_home.iterdir()}

    monkeypatch.setattr(switcher, "codex_is_running", lambda: (_ for _ in ()).throw(AssertionError("should not check Codex")))

    code = switcher.guarded_switch_provider("cloud-gpt-main", str(config_path), dry_run=True)
    out = capsys.readouterr().out
    after = {path.name: switcher.file_hash(path) for path in codex_home.iterdir()}

    assert code == 0
    assert "Protected file hashes before switch" in out
    assert before == after


def test_guarded_switch_changes_only_config_toml(tmp_path, monkeypatch, capsys):
    config_path, codex_home = write_config(tmp_path)
    write_realistic_codex_home(codex_home)
    protected_before = switcher.protected_hashes(load_config(str(config_path)))

    monkeypatch.setattr(switcher, "codex_is_running", lambda: False)
    monkeypatch.setattr(switcher, "stop_bridge", lambda _config: None)

    code = switcher.guarded_switch_provider("cloud-gpt-main", str(config_path))
    out = capsys.readouterr().out

    assert code == 0
    assert "Protected Codex files unchanged." in out
    assert switcher.protected_hashes(load_config(str(config_path))) == protected_before
    assert 'model_provider = "custom"' in (codex_home / "config.toml").read_text(encoding="utf-8")
    assert list(codex_home.glob("config.toml.bak-codex-hybrid-*"))


def test_guarded_switch_rejects_local_provider(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    write_realistic_codex_home(codex_home)
    monkeypatch.setattr(switcher, "start_bridge", lambda _config: (_ for _ in ()).throw(AssertionError("should not start bridge")))

    assert switcher.guarded_switch_provider("local-gemma", str(config_path)) == 2
