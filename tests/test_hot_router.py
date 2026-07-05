from __future__ import annotations

import json

from codex_hybrid_switcher.config import AppConfig
from codex_hybrid_switcher.hot_router import (
    cloud_provider_for_model,
    local_catalog_entry,
    local_model_ids,
    merge_local_models,
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
