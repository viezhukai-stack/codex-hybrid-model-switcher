from __future__ import annotations

import json
import base64

from codex_hybrid_switcher import local_smoke
from codex_hybrid_switcher.smoke import output_matches, red_png_base64


def write_local_config(tmp_path, *, create_files: bool = True):
    paths = {
        "llama_server_path": tmp_path / "llama-server",
        "model_path": tmp_path / "model.gguf",
        "mmproj_path": tmp_path / "mmproj.gguf",
    }
    if create_files:
        for path in paths.values():
            path.write_text("placeholder", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "codex_home": str(tmp_path / "codex-home"),
                "bridge": {"host": "127.0.0.1", "port": 19030, "llama_port": 19031, "idle_seconds": 600},
                "providers": [{"id": "local-gemma", "kind": "local", "model": "local/gemma"}],
                "local_model": {
                    "id": "local/gemma",
                    "llama_server_path": str(paths["llama_server_path"]),
                    "model_path": str(paths["model_path"]),
                    "mmproj_path": str(paths["mmproj_path"]),
                },
            }
        ),
        encoding="utf-8",
    )
    return config_path


def test_output_matches_short_expected_words():
    assert output_matches("OK.", "OK")
    assert output_matches("The dominant color is red.", "red")
    assert not output_matches("blue", "red")


def test_red_png_base64_uses_non_tiny_png():
    data = base64.b64decode(red_png_base64())

    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(data) > 80


def test_local_smoke_stops_when_required_paths_are_missing(tmp_path, capsys):
    config_path = write_local_config(tmp_path, create_files=False)

    code = local_smoke.run_local_smoke(str(config_path))
    out = capsys.readouterr().out

    assert code == 1
    assert "MISSING llama_server_path" in out
    assert "Local smoke stopped before starting the bridge" in out


def test_local_smoke_refuses_existing_bridge_without_opt_in(tmp_path, monkeypatch, capsys):
    config_path = write_local_config(tmp_path)
    monkeypatch.setattr(local_smoke, "port_open", lambda _host, _port: True)

    code = local_smoke.run_local_smoke(str(config_path))
    out = capsys.readouterr().out

    assert code == 2
    assert "Bridge port already in use" in out


def test_local_smoke_starts_and_stops_managed_bridge(tmp_path, monkeypatch, capsys):
    config_path = write_local_config(tmp_path)
    calls = {"port": 0, "stopped": False, "smoke": False}

    class DummyProc:
        pid = 12345

        def poll(self):
            return None

    def fake_port_open(_host, _port):
        calls["port"] += 1
        return calls["port"] > 1

    def fake_stop(_proc):
        calls["stopped"] = True

    def fake_smoke(*_args, **_kwargs):
        calls["smoke"] = True
        return 0

    monkeypatch.setattr(local_smoke, "port_open", fake_port_open)
    monkeypatch.setattr(local_smoke, "start_bridge", lambda _config: DummyProc())
    monkeypatch.setattr(local_smoke, "stop_bridge", fake_stop)
    monkeypatch.setattr(local_smoke, "run_smoke", fake_smoke)

    code = local_smoke.run_local_smoke(str(config_path))
    out = capsys.readouterr().out

    assert code == 0
    assert calls["smoke"] is True
    assert calls["stopped"] is True
    assert "Started bridge" in out
    assert "Local smoke passed." in out
