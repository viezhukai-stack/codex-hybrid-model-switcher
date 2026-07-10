from __future__ import annotations

import json
import ssl
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from codex_hybrid_switcher import hot_router
from codex_hybrid_switcher.config import AppConfig
from codex_hybrid_switcher.hot_router import (
    cloud_provider_for_model,
    filter_catalog_models,
    local_catalog_entry,
    local_model_ids,
    merge_local_models,
    primary_cloud_provider,
    read_upstream,
    resolve_model_alias,
    responses_sse_body,
    should_route_local,
    should_shim_cloud_responses_stream,
    stream_shim_payload,
)


def config_for_hot_router(tmp_path):
    return AppConfig(
        tmp_path / "config.json",
        {
            "providers": [
                {
                    "id": "cloud-gpt-main",
                    "kind": "cloud",
                    "base_url": "https://example.test/v1",
                    "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
                    "model": "provider-gpt-main",
                    "route": "bridge",
                },
                {
                    "id": "local-gemma",
                    "kind": "local",
                    "base_url": "http://127.0.0.1:19030/v1",
                    "model": "local/gemma",
                },
            ],
            "local_model": {
                "id": "local/gemma",
                "display_name": "Local Gemma",
                "context_window": 8192,
            },
        },
    )


def test_local_models_come_from_config_not_machine_specific_defaults(tmp_path):
    config = config_for_hot_router(tmp_path)

    assert local_model_ids(config) == ["local/gemma"]
    assert "12b" not in json.dumps(local_catalog_entry("local/gemma", config)).lower()


def test_hot_router_routes_local_prefixes_and_single_cloud_provider(tmp_path):
    config = config_for_hot_router(tmp_path)

    assert should_route_local("local/gemma")
    assert should_route_local("local-gemma")
    assert not should_route_local("gpt-5.5")
    assert cloud_provider_for_model(config, "gpt-5.5")["base_url"] == "https://example.test/v1"


def test_hot_router_routes_future_model_through_configured_default_provider(tmp_path):
    config = AppConfig(
        tmp_path / "config.json",
        {
            "hot_router": {"default_cloud_provider_id": "cloud-b"},
            "providers": [
                {"id": "cloud-a", "kind": "cloud", "base_url": "https://a.example/v1", "model": "model-a"},
                {"id": "cloud-b", "kind": "cloud", "base_url": "https://b.example/v1", "model": "model-b"},
            ],
        },
    )

    provider = cloud_provider_for_model(config, "future-model-2027")

    assert provider is not None
    assert provider["id"] == "cloud-b"
    assert provider["model"] == "future-model-2027"
    assert primary_cloud_provider(config)["id"] == "cloud-b"


def test_hot_router_reuses_shared_connection_for_unlisted_model(tmp_path):
    config = AppConfig(
        tmp_path / "config.json",
        {
            "providers": [
                {
                    "id": "cloud-a",
                    "kind": "cloud",
                    "base_url": "https://shared.example/v1",
                    "api_key_env": "KEY",
                    "route": "bridge",
                    "model": "model-a",
                },
                {
                    "id": "cloud-b",
                    "kind": "cloud",
                    "base_url": "https://shared.example/v1/",
                    "api_key_env": "KEY",
                    "route": "bridge",
                    "model": "model-b",
                },
            ]
        },
    )

    provider = cloud_provider_for_model(config, "gpt-5.6-sol")

    assert provider is not None
    assert provider["base_url"].rstrip("/") == "https://shared.example/v1"
    assert provider["model"] == "gpt-5.6-sol"


def test_hot_router_refuses_ambiguous_unlisted_model(tmp_path):
    config = AppConfig(
        tmp_path / "config.json",
        {
            "providers": [
                {"id": "cloud-a", "kind": "cloud", "base_url": "https://a.example/v1", "model": "model-a"},
                {"id": "cloud-b", "kind": "cloud", "base_url": "https://b.example/v1", "model": "model-b"},
            ]
        },
    )

    assert cloud_provider_for_model(config, "future-model-2027") is None


def test_hot_router_aliases_and_catalog_filters_are_config_driven(tmp_path):
    config = AppConfig(
        tmp_path / "config.json",
        {
            "hot_router": {
                "model_aliases": {"old-model": "stable-model"},
                "hidden_model_ids": ["hidden-model"],
            },
            "providers": [],
        },
    )
    body = json.dumps(
        {
            "models": [
                {"slug": "gpt-5.6-sol"},
                {"slug": "future-model-2027"},
                {"slug": "hidden-model"},
                {"slug": "local/gemma"},
            ]
        }
    ).encode("utf-8")

    filtered, hidden, visible, shape = filter_catalog_models(
        body,
        set(config.hot_router.visible_model_ids),
        set(config.hot_router.hidden_model_ids),
    )
    ids = [item["slug"] for item in json.loads(filtered)["models"]]

    assert resolve_model_alias(config, "old-model") == "stable-model"
    assert ids == ["gpt-5.6-sol", "future-model-2027", "local/gemma"]
    assert hidden == 1
    assert visible == 0
    assert shape == "models"


def test_local_only_catalog_can_be_built_without_cloud_provider(tmp_path):
    config = config_for_hot_router(tmp_path)
    local_only = AppConfig(
        tmp_path / "local.json",
        {
            "providers": [provider for provider in config.providers if provider.get("kind") == "local"],
            "local_model": config.local_model,
        },
    )

    merged, added, shape = merge_local_models(b'{"models":[]}', local_model_ids(local_only), local_only)
    models = json.loads(merged)["models"]

    assert added == 1
    assert shape == "models"
    assert models[0]["slug"] == "local/gemma"


def test_local_only_http_catalog_returns_model_without_cloud_key(tmp_path, monkeypatch):
    config = AppConfig(
        tmp_path / "local.json",
        {
            "providers": [{"id": "local-gemma", "kind": "local", "model": "local/gemma"}],
            "local_model": {"id": "local/gemma", "display_name": "Local Gemma"},
        },
    )
    router = hot_router.HotRouter(config, host="127.0.0.1", port=19032)
    monkeypatch.setattr(hot_router, "port_open", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(hot_router, "log_event", lambda *_args, **_kwargs: None)
    server = ThreadingHTTPServer(("127.0.0.1", 0), hot_router.handler_for(router))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v1/models", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == 200
    assert [item["slug"] for item in payload["models"]] == ["local/gemma"]


def test_read_upstream_uses_verified_tls_context_for_https(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, **kwargs):
        captured["url"] = request.full_url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("codex_hybrid_switcher.hot_router.urllib.request.urlopen", fake_urlopen)

    status, headers, body = read_upstream("https://provider.example/v1/models", "GET", {})

    assert status == 200
    assert headers["Content-Type"] == "application/json"
    assert body == b"{}"
    assert captured["url"] == "https://provider.example/v1/models"
    assert captured["timeout"] == 30
    assert isinstance(captured["context"], ssl.SSLContext)


def test_hot_router_uses_config_host_and_port_when_cli_overrides_are_absent(tmp_path):
    config = AppConfig(
        tmp_path / "config.json",
        {"hot_router": {"host": "127.0.0.2", "port": 19132}, "providers": []},
    )

    router = hot_router.HotRouter(config)

    assert router.host == "127.0.0.2"
    assert router.port == 19132


def test_catalog_fallback_adds_codex_model_messages_for_models_shape(tmp_path):
    config = config_for_hot_router(tmp_path)
    cloud_body = json.dumps({"models": [{"id": "gpt-5.5", "display_name": "GPT-5.5"}]}).encode("utf-8")

    merged, added, shape = merge_local_models(cloud_body, ["local/gemma"], config)
    data = json.loads(merged.decode("utf-8"))

    assert added == 1
    assert shape == "models"
    local = next(item for item in data["models"] if item["id"] == "local/gemma")
    assert local["display_name"] == "Local Gemma"
    assert "model_messages" in local
    assert local["supports_parallel_tool_calls"] is False


def test_catalog_data_shape_gets_openai_compatible_local_model(tmp_path):
    config = config_for_hot_router(tmp_path)
    cloud_body = json.dumps({"object": "list", "data": [{"id": "gpt-5.5", "object": "model"}]}).encode("utf-8")

    merged, added, shape = merge_local_models(cloud_body, ["local/gemma"], config)
    data = json.loads(merged.decode("utf-8"))

    assert added == 1
    assert shape == "data"
    assert {"id": "local/gemma", "object": "model", "owned_by": "local"} in data["data"]


def test_gemini_high_uses_default_cloud_stream_shim():
    provider = {"id": "cloud-main", "kind": "cloud", "base_url": "https://example.test/v1"}

    assert should_shim_cloud_responses_stream(provider, "gemini-pro-agent", "/v1/responses", True)
    assert not should_shim_cloud_responses_stream(provider, "gemini-3.1-pro-preview", "/v1/responses", True)
    assert not should_shim_cloud_responses_stream(provider, "gemini-pro-agent", "/v1/responses", False)


def test_cloud_stream_shim_can_be_disabled_per_provider():
    provider = {
        "id": "cloud-main",
        "kind": "cloud",
        "base_url": "https://example.test/v1",
        "response_stream_shim_models": [],
    }

    assert not should_shim_cloud_responses_stream(provider, "gemini-pro-agent", "/v1/responses", True)


def test_stream_shim_payload_forces_non_streaming_upstream_request():
    raw = json.dumps({"model": "gemini-pro-agent", "input": "hi", "stream": True}).encode("utf-8")

    data = json.loads(stream_shim_payload(raw).decode("utf-8"))

    assert data["model"] == "gemini-pro-agent"
    assert data["stream"] is False


def test_responses_sse_body_has_codex_completion_events():
    body = responses_sse_body("gemini-pro-agent", "ok").decode("utf-8")

    assert "event: response.created" in body
    assert "event: response.in_progress" in body
    assert "event: response.output_text.delta" in body
    assert "event: response.completed" in body
    assert "data: [DONE]" in body
    assert '"model": "gemini-pro-agent"' in body
    assert '"delta": "ok"' in body
