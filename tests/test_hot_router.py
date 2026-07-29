from __future__ import annotations

import json
import io
import socket
import socketserver
import ssl
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from codex_hybrid_switcher import hot_router
from codex_hybrid_switcher.config import AppConfig
from codex_hybrid_switcher.hot_router import (
    cloud_provider_for_model,
    cloud_response_stream_shim_empty_retries,
    filter_catalog_models,
    local_catalog_entry,
    local_model_ids,
    merge_local_models,
    primary_cloud_provider,
    read_upstream,
    read_upstream_with_429_retry,
    resolve_model_alias,
    response_json_from_upstream,
    response_has_meaningful_output,
    responses_sse_body,
    responses_sse_body_from_json,
    should_route_local,
    should_shim_cloud_responses_stream,
    stream_shim_payload,
)


def parse_sse_events(body: bytes):
    events = []
    for block in body.decode("utf-8").split("\n\n"):
        if not block or block == "data: [DONE]":
            continue
        lines = block.splitlines()
        event = next((line.split(":", 1)[1].strip() for line in lines if line.startswith("event:")), None)
        data = next((line.split(":", 1)[1].strip() for line in lines if line.startswith("data:")), None)
        if event and data:
            events.append((event, json.loads(data)))
    return events


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


def test_multiple_local_catalog_models_keep_per_model_metadata(tmp_path):
    config = AppConfig(
        tmp_path / "config.json",
        {
            "providers": [{"id": "local-gemma", "kind": "local", "model": "local/gemma"}],
            "local_model": {"id": "local/gemma", "context_window": 8192},
            "local_catalog_models": [
                {
                    "id": "local/gemma",
                    "display_name": "Local Gemma 12B",
                    "context_window": 65536,
                    "input_modalities": ["text", "image"],
                },
                {
                    "id": "local/qwen-vl",
                    "display_name": "Local Qwen VL",
                    "context_window": 8192,
                    "input_modalities": ["text", "image"],
                },
            ],
        },
    )

    assert local_model_ids(config) == ["local/gemma", "local/qwen-vl"]
    gemma = local_catalog_entry("local/gemma", config)
    qwen = local_catalog_entry("local/qwen-vl", config)
    assert gemma["display_name"] == "Local Gemma 12B"
    assert gemma["context_window"] == 65536
    assert qwen["display_name"] == "Local Qwen VL"
    assert qwen["context_window"] == 8192
    assert qwen["supports_parallel_tool_calls"] is False
    assert qwen["experimental_supported_tools"] == []
    assert qwen["model_messages"]["instructions_template"]


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


def test_hot_router_tunnels_websocket_upgrade_with_http_11_and_provider_auth(tmp_path, monkeypatch):
    captured: dict[str, object] = {}

    class FakeWebSocketUpstream(socketserver.BaseRequestHandler):
        def handle(self):
            raw = bytearray()
            while b"\r\n\r\n" not in raw:
                chunk = self.request.recv(4096)
                if not chunk:
                    return
                raw.extend(chunk)
            head = bytes(raw).split(b"\r\n\r\n", 1)[0].decode("latin-1")
            lines = head.split("\r\n")
            captured["request_line"] = lines[0]
            captured["headers"] = {
                name.lower(): value.strip()
                for line in lines[1:]
                if ":" in line
                for name, value in [line.split(":", 1)]
            }
            self.request.sendall(
                b"HTTP/1.1 101 Switching Protocols\r\n"
                b"Connection: Upgrade\r\n"
                b"Upgrade: websocket\r\n"
                b"Sec-WebSocket-Accept: test-only\r\n\r\n"
            )
            payload = self.request.recv(4096)
            captured["payload"] = payload
            self.request.sendall(b"upstream:" + payload)

    upstream = socketserver.ThreadingTCPServer(("127.0.0.1", 0), FakeWebSocketUpstream)
    upstream.daemon_threads = True
    upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    upstream_thread.start()

    monkeypatch.setenv("HOT_ROUTER_TEST_KEY", "provider-secret")
    config = AppConfig(
        tmp_path / "config.json",
        {
            "hot_router": {"default_cloud_provider_id": "cloud-main"},
            "providers": [
                {
                    "id": "cloud-main",
                    "kind": "cloud",
                    "base_url": f"http://127.0.0.1:{upstream.server_address[1]}/v1",
                    "api_key_env": "HOT_ROUTER_TEST_KEY",
                    "model": "gpt-test",
                }
            ],
        },
    )
    router = hot_router.HotRouter(config, host="127.0.0.1", port=19032)
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), hot_router.handler_for(router))
    proxy.daemon_threads = True
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()

    client = socket.create_connection(proxy.server_address, timeout=5)
    try:
        client.sendall(
            b"GET /v1/live/rtc_test?mode=voice HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Connection: keep-alive, Upgrade\r\n"
            b"Upgrade: websocket\r\n"
            b"Sec-WebSocket-Version: 13\r\n"
            b"Sec-WebSocket-Key: test-key\r\n"
            b"Sec-WebSocket-Protocol: realtime\r\n"
            b"Authorization: Bearer incoming-secret\r\n\r\n"
        )
        response = bytearray()
        while b"\r\n\r\n" not in response:
            response.extend(client.recv(4096))
        assert bytes(response).startswith(b"HTTP/1.1 101 Switching Protocols")

        client.sendall(b"client-payload")
        assert client.recv(4096) == b"upstream:client-payload"
    finally:
        client.close()
        proxy.shutdown()
        proxy.server_close()
        upstream.shutdown()
        upstream.server_close()

    headers = captured["headers"]
    assert captured["request_line"] == "GET /v1/live/rtc_test?mode=voice HTTP/1.1"
    assert headers["connection"].lower() == "upgrade"
    assert headers["upgrade"].lower() == "websocket"
    assert headers["sec-websocket-protocol"] == "realtime"
    assert headers["authorization"] == "Bearer provider-secret"
    assert captured["payload"] == b"client-payload"


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


def test_visible_catalog_allowlist_is_strict_for_cloud_and_local_models(tmp_path):
    body = json.dumps(
        {
            "models": [
                {
                    "slug": "gpt-5.6-sol",
                    "display_name": "Old Sol",
                    "visibility": "hide",
                    "model_messages": {},
                },
                {"slug": "grok-4.5", "display_name": "Grok"},
                {"slug": "local/gemma", "display_name": "Gemma"},
                {"slug": "local/stale", "display_name": "Stale local"},
            ]
        }
    ).encode("utf-8")

    filtered, hidden, visible, shape = filter_catalog_models(
        body,
        {"gpt-5.6-sol", "local/gemma"},
        set(),
        {"gpt-5.6-sol": "GPT 5.6 Sol"},
    )
    models = json.loads(filtered)["models"]

    assert [item["slug"] for item in models] == ["gpt-5.6-sol", "local/gemma"]
    assert models[0]["display_name"] == "GPT 5.6 Sol"
    assert models[0]["visibility"] == "list"
    assert models[1]["visibility"] == "list"
    assert models[0]["model_messages"] == {}
    assert hidden == 0
    assert visible == 2
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


def test_cloud_stream_shim_empty_response_retry_is_bounded_and_configurable():
    assert cloud_response_stream_shim_empty_retries({}) == 2
    assert cloud_response_stream_shim_empty_retries({"response_stream_shim_empty_retries": 0}) == 0
    assert cloud_response_stream_shim_empty_retries({"response_stream_shim_empty_retries": 99}) == 2
    assert response_has_meaningful_output({"output": []}) is False
    assert response_has_meaningful_output({"output": [{"type": "function_call"}]}) is True


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


def test_responses_json_to_sse_preserves_reasoning_function_calls_usage_and_status():
    upstream = {
        "id": "resp_upstream",
        "object": "response",
        "created_at": 123,
        "status": "completed",
        "model": "gemini-pro-agent",
        "output": [
            {
                "id": "rs_1",
                "type": "reasoning",
                "status": "completed",
                "summary": [{"type": "summary_text", "text": "plan"}],
                "encrypted_content": "opaque-value",
            },
            {
                "id": "fc_1",
                "type": "function_call",
                "status": "completed",
                "call_id": "call_1",
                "name": "read_file",
                "arguments": "{\"path\":\"README.md\"}",
            },
            {
                "id": "msg_1",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "done", "annotations": []}],
            },
        ],
        "usage": {"input_tokens": 17, "output_tokens": 9, "total_tokens": 26},
    }

    events = parse_sse_events(responses_sse_body_from_json(upstream, "fallback"))
    names = [name for name, _payload in events]
    completed = next(payload["response"] for name, payload in events if name == "response.completed")

    assert "response.reasoning_summary_text.delta" in names
    assert "response.function_call_arguments.delta" in names
    assert "response.output_text.delta" in names
    assert [item["type"] for item in completed["output"]] == ["reasoning", "function_call", "message"]
    assert completed["output"][0]["encrypted_content"] == "opaque-value"
    assert completed["output"][1]["call_id"] == "call_1"
    assert completed["usage"] == upstream["usage"]
    assert completed["status"] == "completed"


def test_chat_completion_tool_calls_are_converted_to_responses_items():
    upstream = {
        "id": "chatcmpl_1",
        "object": "chat.completion",
        "created": 456,
        "model": "gemini-pro-agent",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "reasoning_content": "inspect first",
                    "content": "I will inspect it.",
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "type": "function",
                            "function": {"name": "shell", "arguments": {"cmd": "pwd"}},
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
    }

    response = response_json_from_upstream(upstream, "fallback")
    events = parse_sse_events(responses_sse_body_from_json(upstream, "fallback"))
    names = [name for name, _payload in events]

    assert [item["type"] for item in response["output"]] == ["reasoning", "function_call", "message"]
    assert response["output"][1]["call_id"] == "call_abc"
    assert response["output"][1]["arguments"] == '{"cmd":"pwd"}'
    assert response["usage"]["input_tokens"] == 11
    assert response["usage"]["output_tokens"] == 7
    assert "response.function_call_arguments.done" in names
    assert "response.reasoning_summary_part.done" in names


def test_chat_completion_length_finish_reason_preserves_incomplete_status():
    upstream = {
        "model": "gemini-pro-agent",
        "choices": [{"finish_reason": "length", "message": {"role": "assistant", "content": "partial"}}],
    }

    events = parse_sse_events(responses_sse_body_from_json(upstream, "fallback"))
    terminal = next(payload for name, payload in events if name == "response.incomplete")

    assert terminal["response"]["status"] == "incomplete"
    assert terminal["response"]["output_text"] == "partial"


def test_429_retry_honors_retry_after_and_is_finite(monkeypatch):
    calls = []
    results = iter(
        [
            (429, {"Retry-After": "0.25"}, b'{"error":"busy"}'),
            (200, {"Content-Type": "application/json"}, b'{"ok":true}'),
        ]
    )

    def fake_read(*_args, **_kwargs):
        calls.append(1)
        return next(results)

    waited = []
    monkeypatch.setattr(hot_router, "read_upstream", fake_read)

    status, _headers, body, meta = read_upstream_with_429_retry(
        "https://example.test/v1/responses",
        "POST",
        {},
        data=b"{}",
        max_retries=2,
        max_retry_after_seconds=1,
        sleep=waited.append,
    )

    assert status == 200
    assert body == b'{"ok":true}'
    assert len(calls) == 2
    assert waited == [0.25]
    assert meta == {
        "upstream_retries": 1,
        "retry_wait_seconds": 0.25,
        "retry_after": ["0.25"],
    }


def test_stream_shim_retries_one_empty_200_and_preserves_followup_function_call(tmp_path, monkeypatch):
    config = config_for_hot_router(tmp_path)
    router = hot_router.HotRouter(config)
    handler = object.__new__(hot_router.HotRouterHandler)
    handler.router = router
    handler.path = "/v1/responses"
    handler.wfile = io.BytesIO()
    observed = {"statuses": [], "headers": []}
    handler.send_response = observed["statuses"].append
    handler.send_header = lambda name, value: observed["headers"].append((name, value))
    handler.end_headers = lambda: None
    responses = iter(
        [
            (
                200,
                {"Content-Type": "application/json"},
                json.dumps({"object": "response", "status": "completed", "output": []}).encode(),
                {"upstream_retries": 0, "retry_wait_seconds": 0.0, "retry_after": []},
            ),
            (
                200,
                {"Content-Type": "application/json"},
                json.dumps(
                    {
                        "object": "response",
                        "status": "completed",
                        "output": [
                            {
                                "type": "function_call",
                                "call_id": "call_1",
                                "name": "read_file",
                                "arguments": "{\"path\":\"README.md\"}",
                            }
                        ],
                    }
                ).encode(),
                {"upstream_retries": 0, "retry_wait_seconds": 0.0, "retry_after": []},
            ),
        ]
    )
    calls = []
    logs = []

    def fake_read(*_args, **_kwargs):
        calls.append(1)
        return next(responses)

    monkeypatch.setattr(hot_router, "read_upstream_with_429_retry", fake_read)
    monkeypatch.setattr(hot_router.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(hot_router, "log_event", lambda event, **fields: logs.append((event, fields)))

    handler.proxy_responses_stream_shim(
        "request-1",
        json.dumps({"model": "gemini-pro-agent", "stream": True}).encode(),
        "gemini-pro-agent",
        "https://example.test/v1",
        "cloud",
        {"id": "cloud", "response_stream_shim_empty_retries": 1},
        {"cloud_stream_shim": True},
    )

    body = handler.wfile.getvalue().decode("utf-8")
    assert len(calls) == 2
    assert observed["statuses"] == [200]
    assert "response.function_call_arguments.done" in body
    assert '"name": "read_file"' in body
    assert logs[-1][1]["empty_output_retries"] == 1
    assert logs[-1][1]["converted_output_items"] == 1
