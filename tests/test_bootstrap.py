from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_noninteractive_creates_private_config_and_dry_runs(tmp_path):
    config = tmp_path / "private" / "config.json"
    codex_home = tmp_path / "codex-home"
    proc = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "bootstrap.py"),
            "--non-interactive",
            "--config",
            str(config),
            "--codex-home",
            str(codex_home),
            "--provider-id",
            "cloud-main",
            "--base-url",
            "https://example.test/v1",
            "--model",
            "provider-model",
            "--api-key-env",
            "OPENAI_COMPATIBLE_API_KEY",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout
    assert config.exists()
    assert not (codex_home / "config.toml").exists()
    data = json.loads(config.read_text(encoding="utf-8"))
    assert data["providers"][1]["id"] == "cloud-main"
    assert data["providers"][1]["model"] == "provider-model"
    assert "Guarded dry-run" in proc.stdout
    assert "No files will be changed" in proc.stdout
    assert "PYTHONPATH=" in proc.stdout
    assert "state_5.sqlite" in proc.stdout
    assert "env-help" in proc.stdout


def test_bootstrap_requires_base_url_for_noninteractive_new_config(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "bootstrap.py"),
            "--non-interactive",
            "--config",
            str(tmp_path / "config.json"),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert proc.returncode == 2
    assert "--base-url is required" in proc.stdout


def test_bootstrap_uses_existing_private_config_without_regenerating(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "codex_home": str(tmp_path / "codex-home"),
                "providers": [
                    {
                        "id": "cloud-gpt-main",
                        "label": "Cloud GPT Main",
                        "kind": "cloud",
                        "base_url": "https://example.test/v1",
                        "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
                        "model": "provider-gpt-main",
                        "wire_api": "responses",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "-I", str(ROOT / "bootstrap.py"), "--config", str(config), "--skip-dry-run"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout
    assert "Private config already exists" in proc.stdout
    assert "Skipped guarded dry-run" in proc.stdout
