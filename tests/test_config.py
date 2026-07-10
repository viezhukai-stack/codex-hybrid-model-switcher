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
                "hot_router": {
                    "host": "127.0.0.2",
                    "port": 19042,
                    "default_cloud_provider_id": "cloud",
                    "hidden_model_ids": ["hidden-model"],
                    "model_aliases": {"old-model": "new-model"},
                    "catalog_cache_seconds": 9,
                },
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
    assert config.hot_router.host == "127.0.0.2"
    assert config.hot_router.port == 19042
    assert config.hot_router.default_cloud_provider_id == "cloud"
    assert config.hot_router.hidden_model_ids == ("hidden-model",)
    assert config.hot_router.model_aliases == {"old-model": "new-model"}
    assert config.hot_router.catalog_cache_seconds == 9
    assert config.provider("cloud")["model"] == "provider-model"
    assert config.provider_for_model("local/test")["kind"] == "local"


def test_load_config_accepts_utf8_bom(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('\ufeff{"providers":[{"id":"cloud","kind":"cloud","model":"m","base_url":"https://example.test/v1","api_key_env":"KEY"}]}', encoding="utf-8")

    config = load_config(str(config_path))

    assert config.provider("cloud")["model"] == "m"


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


def test_hot_router_defaults_are_dynamic_and_local_only_safe(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"providers": [{"id": "local", "kind": "local", "model": "local/gemma"}]}),
        encoding="utf-8",
    )

    router = load_config(str(config_path)).hot_router

    assert router.host == "127.0.0.1"
    assert router.port == 19032
    assert router.default_cloud_provider_id is None
    assert router.visible_model_ids == ()
    assert router.hidden_model_ids == ()
