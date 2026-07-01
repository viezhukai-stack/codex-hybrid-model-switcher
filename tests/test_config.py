from __future__ import annotations

import json

from codex_hybrid_switcher.config import expand_path, load_config


def test_load_config_and_expand_paths(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("TEST_CODEX_HOME", str(home / ".codex"))
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "codex_home": "$TEST_CODEX_HOME",
                "cc_switch_home": "~/cc-switch-placeholder",
                "bridge": {"port": 19040, "llama_port": 19041, "idle_seconds": 7},
                "providers": [
                    {"id": "cloud", "kind": "cloud", "model": "provider-model"},
                    {"id": "local", "kind": "local", "model": "local/test"},
                ],
                "local_model": {"id": "local/test"},
            }
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config.path == config_path
    assert config.codex_home == home / ".codex"
    assert config.bridge.port == 19040
    assert config.bridge.llama_port == 19041
    assert config.bridge.idle_seconds == 7
    assert config.provider("cloud")["model"] == "provider-model"
    assert config.provider_for_model("local/test")["kind"] == "local"


def test_expand_path_supports_user_and_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ROOT", str(tmp_path / "models"))

    expanded = expand_path("$MODEL_ROOT/model.gguf")

    assert expanded == tmp_path / "models" / "model.gguf"


def test_provider_for_official_model_uses_single_bridge_cloud_fallback(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "providers": [
                    {"id": "openai-official", "kind": "official", "model": "gpt-5.5"},
                    {
                        "id": "cloud-gpt-main",
                        "kind": "cloud",
                        "model": "gpt-5.4",
                        "route": "bridge",
                        "base_url": "https://example.test/v1",
                        "api_key_env": "PRIVATE_KEY",
                    },
                ],
                "local_model": {"id": "local/gemma"},
            }
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    official = config.provider_for_model("gpt-5.5")
    assert official is not None
    assert official["kind"] == "cloud"
    assert official["model"] == "gpt-5.5"
    assert official["base_url"] == "https://example.test/v1"
    assert config.provider_for_model("codex-auto-review")["model"] == "codex-auto-review"
    assert config.provider_for_model("local/gemma") is None


def test_provider_for_official_model_does_not_guess_between_multiple_bridge_clouds(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "providers": [
                    {"id": "openai-official", "kind": "official", "model": "gpt-5.5"},
                    {"id": "cloud-a", "kind": "cloud", "model": "provider-a", "route": "bridge"},
                    {"id": "cloud-b", "kind": "cloud", "model": "provider-b", "route": "bridge"},
                ],
            }
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config.provider_for_model("gpt-5.5") is None
    assert config.provider_for_model("codex-auto-review") is None
