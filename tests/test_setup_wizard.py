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
    assert "model" not in data["providers"][0]
    assert data["hot_router"]["default_cloud_provider_id"] == "cloud-gpt-main"
    assert data["hot_router"]["port"] == 19032
    assert data["hot_router"]["max_429_retries"] == 2
    assert data["hot_router"]["max_retry_after_seconds"] == 30
    assert data["hot_router"]["ignore_system_proxy"] is False
    assert data["local_model"]["model_path"] == "~/path/to/model.gguf"


def test_build_first_run_config_can_skip_cloud_for_local_only():
    data = build_first_run_config(
        include_cloud=False,
        include_local=True,
        llama_server_path="C:/llama/llama-server.exe",
        model_path="C:/models/gemma.gguf",
        mmproj_path="C:/models/mmproj.gguf",
    )

    provider_ids = [provider["id"] for provider in data["providers"]]

    assert provider_ids == ["openai-official", "local-gemma"]
    assert data["providers"][1]["kind"] == "local"
    assert data["hot_router"]["default_cloud_provider_id"] is None
    assert data["local_model"]["llama_server_path"] == "C:/llama/llama-server.exe"


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
    assert "bridge-health" in out
    assert "guarded-switch cloud-main --dry-run" in out
    assert "setup-report" in out
    assert "canary-report" in out
    assert "real-canary-template" in out
    assert "final-check" in out
    assert "FINAL_CHECK.md" in out
    assert "does not rewrite Codex history" in out


def test_setup_next_steps_are_platform_specific_for_windows(tmp_path, capsys):
    output = tmp_path / "private" / "config.json"

    code = run_setup_wizard(
        output=str(output),
        platform="windows",
        base_url="https://provider.example/v1",
        non_interactive=True,
    )
    out = capsys.readouterr().out

    assert code == 0
    assert r"%USERPROFILE%\Desktop\codex-hybrid-setup-report.md" in out
    assert r"%USERPROFILE%\Desktop\codex-hybrid-canary-evidence.md" in out
    assert r"%USERPROFILE%\Desktop\codex-hybrid-real-clean-machine-canary.md" in out
    assert r"%USERPROFILE%\Desktop\codex-hybrid-final-check.md" in out
    assert "~/Desktop/codex-hybrid-setup-report.md" not in out


def test_setup_non_interactive_requires_base_url(tmp_path):
    assert run_setup_wizard(output=str(tmp_path / "config.json"), non_interactive=True) == 2


def test_setup_non_interactive_allows_local_only_without_base_url(tmp_path, capsys):
    output = tmp_path / "config.json"

    code = run_setup_wizard(
        output=str(output),
        include_cloud=False,
        include_local=True,
        llama_server_path=str(tmp_path / "llama-server.exe"),
        model_path=str(tmp_path / "model.gguf"),
        mmproj_path=str(tmp_path / "mmproj.gguf"),
        non_interactive=True,
    )
    out = capsys.readouterr().out
    config = load_config(str(output))

    assert code == 0
    assert config.provider("local-gemma")["kind"] == "local"
    assert "Local-only config: no cloud API key is required." in out
    assert "guarded-switch local-gemma --dry-run" in out


def test_setup_non_interactive_refuses_empty_local_only(tmp_path, capsys):
    code = run_setup_wizard(
        output=str(tmp_path / "config.json"),
        include_cloud=False,
        include_local=False,
        non_interactive=True,
    )
    out = capsys.readouterr().out

    assert code == 2
    assert "--skip-cloud requires --include-local" in out


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
