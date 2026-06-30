from __future__ import annotations

import json

from codex_hybrid_switcher.config import load_config
from codex_hybrid_switcher.setup_wizard import (
    build_first_run_config,
    default_codex_home,
    looks_like_secret,
    run_setup_wizard,
)


def test_default_codex_home_is_platform_specific():
    assert default_codex_home("macos") == "~/.codex"
    assert default_codex_home("windows") == "~\\.codex"


def test_build_first_run_config_defaults_to_cloud_without_local_provider():
    data = build_first_run_config(base_url="https://provider.example/v1")

    provider_ids = [provider["id"] for provider in data["providers"]]

    assert provider_ids == ["openai-official", "cloud-gpt-main"]
    assert data["providers"][1]["kind"] == "cloud"
    assert data["providers"][1]["api_key_env"] == "OPENAI_COMPATIBLE_API_KEY"
    assert data["providers"][1]["route"] == "bridge"
    assert data["local_model"]["model_path"] == "~/path/to/model.gguf"


def test_setup_non_interactive_generates_private_config_only(tmp_path, capsys):
    output = tmp_path / "private" / "config.json"
    codex_home = tmp_path / "codex-home"

    code = run_setup_wizard(
        output=str(output),
        platform="macos",
        codex_home=str(codex_home),
        provider_id="cloud-main",
        provider_label="Cloud Main",
        base_url="https://provider.example/v1",
        model="provider-model",
        api_key_env="PRIVATE_PROVIDER_KEY",
        non_interactive=True,
    )
    out = capsys.readouterr().out
    raw = json.loads(output.read_text(encoding="utf-8"))
    config = load_config(str(output))

    assert code == 0
    assert raw["codex_home"] == str(codex_home)
    assert config.provider("cloud-main")["model"] == "provider-model"
    assert not (codex_home / "config.toml").exists()
    assert "guarded-switch cloud-main --dry-run" in out
    assert "does not rewrite Codex history" in out


def test_setup_non_interactive_requires_base_url(tmp_path):
    assert run_setup_wizard(output=str(tmp_path / "config.json"), non_interactive=True) == 2


def test_setup_refuses_api_key_literal_in_env_field(tmp_path, capsys):
    output = tmp_path / "config.json"

    code = run_setup_wizard(
        output=str(output),
        base_url="https://provider.example/v1",
        api_key_env="sk-" + "a" * 32,
        non_interactive=True,
    )
    out = capsys.readouterr().out

    assert code == 2
    assert "environment variable name" in out
    assert not output.exists()


def test_setup_refuses_unknown_cloud_route(tmp_path, capsys):
    output = tmp_path / "config.json"

    code = run_setup_wizard(
        output=str(output),
        base_url="https://provider.example/v1",
        cloud_route="sideways",
        non_interactive=True,
    )
    out = capsys.readouterr().out

    assert code == 2
    assert "cloud route" in out
    assert not output.exists()


def test_setup_can_generate_direct_cloud_route(tmp_path):
    output = tmp_path / "config.json"

    assert (
        run_setup_wizard(
            output=str(output),
            base_url="https://provider.example/v1",
            cloud_route="direct",
            non_interactive=True,
        )
        == 0
    )

    config = load_config(str(output))
    assert config.provider("cloud-gpt-main")["route"] == "direct"


def test_setup_can_include_local_provider_when_explicit(tmp_path):
    output = tmp_path / "config.json"

    assert (
        run_setup_wizard(
            output=str(output),
            base_url="https://provider.example/v1",
            include_local=True,
            llama_server_path=str(tmp_path / "llama-server"),
            model_path=str(tmp_path / "model.gguf"),
            mmproj_path=str(tmp_path / "mmproj.gguf"),
            non_interactive=True,
        )
        == 0
    )

    config = load_config(str(output))
    assert config.provider("local-gemma")["kind"] == "local"
    assert config.local_model["model_path"] == str(tmp_path / "model.gguf")


def test_looks_like_secret_allows_environment_names():
    assert looks_like_secret("OPENAI_COMPATIBLE_API_KEY") is False
    assert looks_like_secret("$OPENAI_COMPATIBLE_API_KEY") is False
    assert looks_like_secret("sk-" + "a" * 32) is True
