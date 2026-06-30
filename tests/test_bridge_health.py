from __future__ import annotations

import json

from codex_hybrid_switcher import bridge_health
from codex_hybrid_switcher.bridge_health import JsonResult


def write_config(tmp_path, *, route: str = "bridge", include_local: bool = False):
    providers = [
        {
            "id": "cloud-gpt-main",
            "label": "Cloud GPT Main",
            "kind": "cloud",
            "base_url": "https://example.test/v1",
            "api_key_env": "PRIVATE_PROVIDER_KEY",
            "model": "provider-gpt-main",
            "wire_api": "responses",
            "route": route,
        }
    ]
    if include_local:
        providers.append(
            {
                "id": "local-gemma",
                "label": "Local Gemma",
                "kind": "local",
                "model": "local/gemma",
                "wire_api": "responses",
            }
        )
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "codex_home": str(tmp_path / "codex-home"),
                "bridge": {"host": "127.0.0.1", "port": 19030, "llama_port": 19031, "idle_seconds": 600},
                "providers": providers,
                "local_model": {"id": "local/gemma"},
            }
        ),
        encoding="utf-8",
    )
    return config_path


def test_bridge_health_closed_port_reports_next_steps(tmp_path, monkeypatch, capsys):
    config_path = write_config(tmp_path)
    monkeypatch.delenv("PRIVATE_PROVIDER_KEY", raising=False)
    monkeypatch.setattr(bridge_health, "port_open", lambda _host, _port: False)
    monkeypatch.setattr(
        bridge_health,
        "fetch_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not fetch when port is closed")),
    )

    code = bridge_health.run_bridge_health(str(config_path))

    out = capsys.readouterr().out
    assert code == 1
    assert "CLOSED bridge TCP port" in out
    assert "PRIVATE_PROVIDER_KEY (unset)" in out
    assert "env-help" in out
    assert "codex_hybrid_switcher bridge" in out
    assert "example.test" not in out


def test_bridge_health_passes_when_bridge_models_and_env_are_available(tmp_path, monkeypatch, capsys):
    config_path = write_config(tmp_path)
    monkeypatch.setenv("PRIVATE_PROVIDER_KEY", "secret-value-not-printed")
    monkeypatch.setattr(bridge_health, "port_open", lambda _host, _port: True)

    def fake_fetch(url: str, *, timeout: float = 2.0) -> JsonResult:
        if url.endswith("/health"):
            return JsonResult(True, 200, {"ok": True, "models": ["provider-gpt-main"], "port": 19030})
        if url.endswith("/models"):
            return JsonResult(True, 200, {"object": "list", "data": [{"id": "provider-gpt-main", "object": "model"}]})
        raise AssertionError(url)

    monkeypatch.setattr(bridge_health, "fetch_json", fake_fetch)

    code = bridge_health.run_bridge_health(str(config_path))

    out = capsys.readouterr().out
    assert code == 0
    assert "OK /v1/health: HTTP 200" in out
    assert "OK /v1/models: HTTP 200" in out
    assert "provider-gpt-main" in out
    assert "secret-value-not-printed" not in out
    assert "Bridge health passed." in out


def test_bridge_health_fails_when_running_bridge_has_stale_model_list(tmp_path, monkeypatch, capsys):
    config_path = write_config(tmp_path, include_local=True)
    monkeypatch.setenv("PRIVATE_PROVIDER_KEY", "secret-value-not-printed")
    monkeypatch.setattr(bridge_health, "port_open", lambda _host, _port: True)

    def fake_fetch(url: str, *, timeout: float = 2.0) -> JsonResult:
        if url.endswith("/health"):
            return JsonResult(True, 200, {"ok": True, "models": ["old-model"], "port": 19030})
        if url.endswith("/models"):
            return JsonResult(True, 200, {"object": "list", "data": [{"id": "old-model", "object": "model"}]})
        raise AssertionError(url)

    monkeypatch.setattr(bridge_health, "fetch_json", fake_fetch)

    code = bridge_health.run_bridge_health(str(config_path))

    out = capsys.readouterr().out
    assert code == 1
    assert "Missing expected bridge models:" in out
    assert "provider-gpt-main" in out
    assert "local/gemma" in out
    assert "Restart the bridge" in out


def test_bridge_health_does_not_require_closed_bridge_for_direct_cloud_only(tmp_path, monkeypatch, capsys):
    config_path = write_config(tmp_path, route="direct")
    monkeypatch.delenv("PRIVATE_PROVIDER_KEY", raising=False)
    monkeypatch.setattr(bridge_health, "port_open", lambda _host, _port: False)

    code = bridge_health.run_bridge_health(str(config_path))

    out = capsys.readouterr().out
    assert code == 0
    assert "required by: no bridge-routed providers" in out
    assert "CLOSED bridge TCP port" in out
