from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import zipfile


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


def test_windows_one_click_installer_has_safe_beginner_boundaries():
    text = (ROOT / "installer" / "windows" / "Install-CodexHybrid.ps1").read_text(encoding="utf-8")
    launcher = (ROOT / "installer" / "windows" / "Install Codex Hybrid.cmd").read_text(encoding="utf-8")
    readme = (ROOT / "installer" / "windows" / "README.txt").read_text(encoding="utf-8")
    readme_zh = (ROOT / "installer" / "windows" / "README.zh-CN.txt").read_text(encoding="utf-8")

    assert "https://developers.openai.com/codex/app" in text
    assert "Python.Python.3.12" in text
    assert "winget install" in text
    assert "payload\\codex-hybrid-model-switcher" in text
    assert "Using bundled project payload" in text
    assert "archive/refs/tags/$ReleaseTag.zip" in text
    assert "api.github.com/repos/ggml-org/llama.cpp/releases/latest" in text
    assert "payload\\llama.cpp" in text
    assert "LlamaServerPath" in text
    assert "Read-Host \"API key\" -AsSecureString" in text
    assert "SetEnvironmentVariable($Name, $plain, \"User\")" in text
    assert "OpenFileDialog" in text
    assert "local-smoke" in text
    assert "windows-provider-switch.ps1" in text
    assert "-Apply" in text
    assert "install-windows-launcher.ps1" in text
    assert "INSTALLER DRY-RUN COMPLETE" in text
    assert "No real Codex switch was applied" in text
    assert "Set-Content" not in text
    assert "models_cache.json" not in text
    assert "state_5.sqlite" not in text
    assert "powershell -NoProfile -ExecutionPolicy Bypass" in launcher
    assert "This package does not include model files" in readme
    assert "网盘一键安装包" in readme_zh
    assert "不需要安装 Git" in readme_zh


def test_windows_one_click_package_builder_creates_expected_zip(tmp_path):
    output = tmp_path / "setup.zip"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-windows-one-click-package.py"), "--output", str(output)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert output.exists()
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert "Install Codex Hybrid.cmd" in names
    assert "Install-CodexHybrid.ps1" in names
    assert "README.txt" in names
    assert "README.zh-CN.txt" in names
    assert "payload/codex-hybrid-model-switcher/bootstrap.py" in names
    assert "payload/codex-hybrid-model-switcher/src/codex_hybrid_switcher/__init__.py" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-provider-switch.ps1" in names
    assert not any(name.startswith(".git/") for name in names)
    assert not any(name.startswith(".venv/") for name in names)
    assert not any(name.startswith("dist/") for name in names)
