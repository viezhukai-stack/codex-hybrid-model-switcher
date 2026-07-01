from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_installed_windows_launcher_uses_guarded_menu_script():
    text = (ROOT / "scripts" / "install-windows-launcher.ps1").read_text(encoding="utf-8")

    assert "windows-provider-menu.ps1" in text
    assert "codex-hybrid-switcher menu" not in text


def test_repository_windows_launcher_uses_guarded_menu_script():
    text = (ROOT / "scripts" / "Codex Model Switcher.cmd").read_text(encoding="utf-8")

    assert "windows-provider-menu.ps1" in text
    assert "codex-hybrid-switcher menu" not in text


def test_windows_menu_delegates_to_guarded_switch_wrapper():
    text = (ROOT / "scripts" / "windows-provider-menu.ps1").read_text(encoding="utf-8")

    assert "windows-provider-switch.ps1" in text
    assert "-AllowLocal" in text
    assert "-Apply" in text
    assert "APPLY" in text
    assert "codex-hybrid-switcher menu" not in text


def test_windows_bootstrap_handles_beginner_stock_machine_path():
    text = (ROOT / "scripts" / "bootstrap-windows.ps1").read_text(encoding="utf-8")

    assert "Python.Python.3.12" in text
    assert "winget install" in text
    assert "archive/refs/tags/$ReleaseTag.zip" in text
    assert "bootstrap.py" in text
    assert "validate-config" in text
    assert "env-help" in text
    assert "bridge-health" in text
    assert "guarded-switch" in text
    assert "--dry-run" in text
    assert "Invoke-Python -PythonCommand $python -Arguments" in text
    assert "does not read, print, or store API keys" in text
