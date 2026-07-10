from __future__ import annotations

import json
import subprocess

from codex_hybrid_switcher import doctor
from codex_hybrid_switcher.config import AppConfig


def test_catalog_model_ids_supports_latest_models_shape():
    payload = {
        "models": [
            {"slug": "gpt-5.6-sol"},
            {"id": "future-model-2027"},
            {"slug": "gpt-5.6-sol"},
        ]
    }

    assert doctor.catalog_model_ids(payload) == ["gpt-5.6-sol", "future-model-2027"]


def test_macos_codex_app_discovery_prefers_bundle_id_results(tmp_path, monkeypatch):
    bundle_app = tmp_path / "BundleLocated.app"
    bundle_app.mkdir()

    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=str(bundle_app) + "\n",
        ),
    )

    assert doctor.macos_codex_app_paths()[0] == bundle_app


def test_native_codex_checks_are_redacted_and_hash_guarded(tmp_path, monkeypatch, capsys):
    cli = tmp_path / "codex"
    cli.write_text("placeholder", encoding="utf-8")
    config = AppConfig(tmp_path / "config.json", {"codex_home": str(tmp_path / ".codex"), "providers": []})

    monkeypatch.setattr(
        doctor,
        "native_codex_app_info",
        lambda: {
            "name": "ChatGPT",
            "path": "/Applications/ChatGPT.app",
            "bundle_id": "com.openai.codex",
            "version": "26.707.31428",
        },
    )
    monkeypatch.setattr(doctor, "native_codex_cli_path", lambda _info: cli)
    monkeypatch.setattr(doctor, "protected_hashes", lambda _config: {"auth.json": "same"})

    def fake_run(args, **_kwargs):
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="codex-cli 0.144.0\n")
        if args[-2:] == ["doctor", "--json"]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"overallStatus": "ok", "checks": {"state.paths": {"status": "ok"}}}),
            )
        if args[-3:] == ["debug", "models", "--bundled"]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"models": [{"slug": "gpt-5.6-sol"}]}),
            )
        raise AssertionError(args)

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)

    assert doctor.run_native_codex_checks(config) is True
    out = capsys.readouterr().out
    assert "ChatGPT" in out
    assert "gpt-5.6-sol" in out
    assert "protected Codex files unchanged" in out


def test_native_codex_checks_warn_when_windowsapps_cli_is_not_executable(tmp_path, monkeypatch, capsys):
    cli = tmp_path / "codex.exe"
    cli.write_text("placeholder", encoding="utf-8")
    config = AppConfig(tmp_path / "config.json", {"codex_home": str(tmp_path / ".codex"), "providers": []})

    monkeypatch.setattr(
        doctor,
        "native_codex_app_info",
        lambda: {
            "name": "OpenAI.Codex",
            "path": "C:/Program Files/WindowsApps/OpenAI.Codex/app",
            "bundle_id": "OpenAI.Codex_family",
            "version": "26.707.3748.0",
        },
    )
    monkeypatch.setattr(doctor, "native_codex_cli_path", lambda _info: cli)
    monkeypatch.setattr(doctor, "protected_hashes", lambda _config: {"auth.json": "same"})
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError(5, "Access is denied")),
    )

    assert doctor.run_native_codex_checks(config) is False
    out = capsys.readouterr().out
    assert "WARN bundled Codex CLI: PermissionError" in out
    assert "WARN native codex doctor --json: PermissionError" in out
    assert "WARN bundled model catalog: PermissionError" in out
    assert "protected Codex files unchanged" in out


def test_native_codex_checks_warn_when_protected_file_is_locked(tmp_path, monkeypatch, capsys):
    cli = tmp_path / "codex"
    cli.write_text("placeholder", encoding="utf-8")
    config = AppConfig(tmp_path / "config.json", {"codex_home": str(tmp_path / ".codex"), "providers": []})

    monkeypatch.setattr(
        doctor,
        "native_codex_app_info",
        lambda: {
            "name": "ChatGPT",
            "path": "/Applications/ChatGPT.app",
            "bundle_id": "com.openai.codex",
            "version": "26.707.31428",
        },
    )
    monkeypatch.setattr(doctor, "native_codex_cli_path", lambda _info: cli)
    monkeypatch.setattr(doctor, "protected_hashes", lambda _config: (_ for _ in ()).throw(PermissionError("locked")))

    def fake_run(args, **_kwargs):
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="codex-cli 0.144.0\n")
        if args[-2:] == ["doctor", "--json"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps({"overallStatus": "ok", "checks": {}}))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps({"models": [{"slug": "gpt-5.6-sol"}]}))

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)

    assert doctor.run_native_codex_checks(config) is False
    out = capsys.readouterr().out
    assert "could not hash protected Codex files before checks" in out
    assert "could not hash protected Codex files after checks" in out
    assert "protected-file comparison was incomplete" in out
