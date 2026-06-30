from __future__ import annotations

import json

from codex_hybrid_switcher.config import load_config
from codex_hybrid_switcher.private_config import init_config, run_validate_config, validate_config


def write_private_config(tmp_path, *, cloud_base_url="https://private.example/v1", local_path="/private/model.gguf"):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "codex_home": str(tmp_path / "codex-home"),
                "providers": [
                    {
                        "id": "cloud-main",
                        "kind": "cloud",
                        "base_url": cloud_base_url,
                        "api_key_env": "PRIVATE_PROVIDER_KEY",
                        "model": "private-model",
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
                    "llama_server_path": str(tmp_path / "llama-server"),
                    "model_path": local_path,
                    "mmproj_path": str(tmp_path / "mmproj.gguf"),
                },
            }
        ),
        encoding="utf-8",
    )
    return config_path


def test_init_config_copies_template_and_refuses_overwrite(tmp_path):
    template = tmp_path / "template.json"
    template.write_text('{"providers": []}', encoding="utf-8")
    output = tmp_path / "private" / "config.json"

    assert init_config(output=str(output), template=str(template)) == 0
    assert output.read_text(encoding="utf-8") == '{"providers": []}'
    assert init_config(output=str(output), template=str(template)) == 2


def test_validate_config_accepts_complete_private_config(tmp_path):
    config = load_config(str(write_private_config(tmp_path)))

    assert validate_config(config) == []


def test_validate_config_reports_missing_cloud_fields(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"providers": [{"id": "cloud-main", "kind": "cloud", "model": "private-model"}]}),
        encoding="utf-8",
    )

    errors = validate_config(load_config(str(config_path)))

    assert "cloud-main: base_url is required" in errors
    assert "cloud-main: api_key_env is required" in errors


def test_validate_config_reports_unknown_cloud_route(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "id": "cloud-main",
                        "kind": "cloud",
                        "base_url": "https://private.example/v1",
                        "api_key_env": "PRIVATE_PROVIDER_KEY",
                        "model": "private-model",
                        "route": "sideways",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    errors = validate_config(load_config(str(config_path)))

    assert "cloud-main: route must be direct or bridge" in errors


def test_run_validate_config_redacts_private_endpoint_and_paths(tmp_path, capsys):
    host = "private-" + "endpoint.example"
    private_path = "/private/" + "models/model.gguf"
    config_path = write_private_config(tmp_path, cloud_base_url=f"https://{host}/v1", local_path=private_path)

    assert run_validate_config(str(config_path)) == 0
    out = capsys.readouterr().out

    assert host not in out
    assert private_path not in out
    assert "route=bridge" in out
    assert "https://<redacted>/v1" in out
    assert "model_path: configured" in out
