from __future__ import annotations

import json

from codex_hybrid_switcher.config import load_config
from codex_hybrid_switcher.env_help import collect_env_vars, render_env_help, run_env_help


def write_env_config(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "codex_home": str(tmp_path / "codex-home"),
                "providers": [
                    {
                        "id": "cloud-main",
                        "kind": "cloud",
                        "base_url": "https://private.example/v1",
                        "api_key_env": "PRIVATE_PROVIDER_KEY",
                        "model": "private-model",
                        "route": "bridge",
                    },
                    {
                        "id": "cloud-second",
                        "kind": "cloud",
                        "base_url": "https://private.example/v1",
                        "api_key_env": "PRIVATE_PROVIDER_KEY",
                        "model": "second-model",
                        "route": "bridge",
                    },
                    {
                        "id": "local-gemma",
                        "kind": "local",
                        "model": "local/gemma",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return config_path


def test_collect_env_vars_groups_cloud_providers(tmp_path, monkeypatch):
    config = load_config(str(write_env_config(tmp_path)))
    monkeypatch.setenv("PRIVATE_PROVIDER_KEY", "secret-value")

    infos = collect_env_vars(config)

    assert len(infos) == 1
    assert infos[0].name == "PRIVATE_PROVIDER_KEY"
    assert infos[0].is_set is True
    assert infos[0].providers == ("cloud-main", "cloud-second")
    assert infos[0].routes == ("bridge",)


def test_render_env_help_redacts_key_value_and_shows_macos_commands(tmp_path, monkeypatch):
    config = load_config(str(write_env_config(tmp_path)))
    monkeypatch.setenv("PRIVATE_PROVIDER_KEY", "secret-value")

    text = render_env_help(config, platform="macos")

    assert "PRIVATE_PROVIDER_KEY: set" in text
    assert 'export PRIVATE_PROVIDER_KEY="replace-with-your-provider-key"' in text
    assert "secret-value" not in text
    assert "private.example" not in text
    assert "does not read, print, or store API keys" in text


def test_run_env_help_shows_windows_commands_for_unset_var(tmp_path, monkeypatch, capsys):
    config_path = write_env_config(tmp_path)
    monkeypatch.delenv("PRIVATE_PROVIDER_KEY", raising=False)

    assert run_env_help(str(config_path), platform="windows") == 0
    out = capsys.readouterr().out

    assert "PRIVATE_PROVIDER_KEY: unset" in out
    assert '$env:PRIVATE_PROVIDER_KEY = "replace-with-your-provider-key"' in out
    assert '[Environment]::SetEnvironmentVariable("PRIVATE_PROVIDER_KEY", "replace-with-your-provider-key", "User")' in out


def test_run_env_help_filters_by_name(tmp_path, capsys):
    config_path = write_env_config(tmp_path)

    assert run_env_help(str(config_path), platform="macos", name="MISSING_ENV") == 0
    out = capsys.readouterr().out

    assert "none found" in out
    assert "PRIVATE_PROVIDER_KEY" not in out
