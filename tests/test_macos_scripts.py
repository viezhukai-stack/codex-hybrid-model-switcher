from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_installed_macos_launcher_uses_guarded_menu_script():
    text = read("scripts/install-macos-launcher.sh")

    assert "macos-provider-menu.sh" in text
    assert "codex-hybrid-switcher menu" not in text


def test_macos_menu_delegates_to_guarded_switch_wrapper():
    text = read("scripts/macos-provider-menu.sh")

    assert "macos-provider-switch.sh" in text
    assert "--allow-local" in text
    assert "--apply" in text
    assert "APPLY" in text
    assert "codex-hybrid-switcher menu" not in text


def test_macos_switch_wrapper_uses_guarded_switch_and_refuses_running_codex():
    text = read("scripts/macos-provider-switch.sh")

    assert "guarded-switch" in text
    assert "--dry-run" in text
    assert "validate-config" in text
    assert "pgrep" in text
    assert "Codex appears to be running" in text
    assert "auth.json" not in text
    assert "state_5.sqlite" not in text


def test_bootstrap_launchers_call_bootstrap_without_apply():
    mac_text = read("scripts/Codex Hybrid Bootstrap.command")
    win_text = read("scripts/Codex Hybrid Bootstrap.cmd")

    assert "bootstrap.py" in mac_text
    assert "bootstrap.py" in win_text
    assert "guarded-switch" not in mac_text
    assert "guarded-switch" not in win_text
    assert "--apply" not in mac_text.lower()
    assert "--apply" not in win_text.lower()
