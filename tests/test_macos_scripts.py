from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_installed_macos_launcher_uses_guarded_menu_script():
    text = read("scripts/install-macos-launcher.sh")

    assert "macos-provider-menu.sh" in text
    assert "macos-hot-router-start.sh" in text
    assert "Start Codex Hybrid 2.0.command" in text
    assert "Enable Codex Hybrid 2.0.command" in text
    assert "Restore Codex 19030 Mode.command" in text
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
    common = read("scripts/macos-app-common.sh")

    assert "guarded-switch" in text
    assert "--dry-run" in text
    assert "validate-config" in text
    assert ".codex-hybrid-model-switcher/env.sh" in text
    assert "macos-app-common.sh" in text
    assert "ps -ww -axo args=" in common
    assert "(ChatGPT|Codex)\\.app" in common
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


def test_macos_one_click_installer_has_safe_beginner_boundaries():
    text = read("installer/macos/Install-CodexHybrid.sh")
    launcher = read("installer/macos/Install Codex Hybrid.command")
    diagnostics = read("installer/macos/Codex Hybrid Diagnostics.command")
    restore = read("installer/macos/Restore Official Codex.command")
    readme = read("installer/macos/README.txt")
    readme_zh = read("installer/macos/README.zh-CN.txt")
    preset = read("installer/macos/provider-preset.example.json")

    assert "https://developers.openai.com/codex/app" in text
    assert "payload/codex-hybrid-model-switcher" in text
    assert "provider-preset.json" in text
    assert 'env_file="${runtime_root}/env.sh"' in text
    assert "os.chmod(path, 0o600)" in text
    assert "read -r -s -p \"API key:" in text
    assert "validate-config" in text
    assert "bridge-health" in text
    assert "--skip-cloud" in text
    assert "--skip-local-smoke" in text
    assert "--local-smoke-timeout" in text
    assert "--llama-backend" in text
    assert "--unify-history" in text
    assert "--skip-history-unify" in text
    assert "history-status" in text
    assert "unify-history" in text
    assert "MIGRATE" in text
    assert "History unification status" in text
    assert "payload/python" in text
    assert "/Applications/ChatGPT.app" in text
    assert "/Applications/Codex.app" in text
    assert text.index("mdfind") < text.index('"/Applications/ChatGPT.app"')
    assert "pyproject.toml" in text
    assert "package_version:-2.18.0" not in text
    assert "CFBundleIdentifier" in text
    assert "CFBundleShortVersionString" in text
    assert "codex_app_bundle_id=" in text
    assert "codex_app_version=" in text
    assert "codex_cli_version=" in text
    assert "Python 3.10 or newer is required" in text
    assert "https://www.python.org/downloads/macos/" in text
    assert "python_version=" in text
    assert "python_min_version_ok=" in text
    assert "bundled_python_present=" in text
    assert "payload/models/local-gemma" in text
    assert "payload/llama.cpp" in text
    assert "Copying about $(format_size_gb" in text
    assert "stop_managed_bridge_on_port 19030" in text
    assert "codex_hybrid_switcher bridge" in text
    assert "The installer will not stop an existing bridge while Codex is open." in text
    assert "local-smoke" in text
    assert "local-gemma" in text
    assert "No cloud base_url was provided. Continuing with local-only setup." in text
    assert "macos-provider-switch.sh" in text
    assert "install-macos-launcher.sh" in text
    assert "open -a ChatGPT" in text
    assert "open -a Codex" in text
    assert "open -b com.openai.codex" in text
    assert "Start Codex Hybrid 2.0.command" in text
    assert "Opening Codex Desktop" in text
    assert "INSTALLER DRY-RUN COMPLETE" in text
    assert "No real Codex switch was applied" in text
    assert "APPLY" in text
    assert "Codex Hybrid macOS Installer Diagnostics" in text
    assert "codex-hybrid-macos-installer-diagnostics.txt" in text
    assert "Remove-Item" not in text
    assert "rm -rf \"${HOME}/.codex\"" not in text
    assert "models_cache.json" not in text
    assert "bash \"${script_dir}/Install-CodexHybrid.sh\"" in launcher
    assert "--diagnostics-only" in diagnostics
    assert "macos-restore-official.sh" in restore
    assert "The distributed full local macOS package includes payload/models/local-gemma" in readme
    assert "No macOS package includes CC Switch, API keys, or ChatGPT/Codex Desktop." in readme
    assert "Python 3.10 or newer is required" in readme
    assert "MIGRATE" in readme
    assert "macOS 小白安装说明" in readme_zh
    assert "完整本地 macOS 包" in readme_zh
    assert "不会修改" in readme_zh
    assert "Python 3.10" in readme_zh
    assert "MIGRATE" in readme_zh
    assert "YOUR-OPENAI-COMPATIBLE-ENDPOINT.example" in preset
    assert "api_key_env" in preset


def test_macos_restore_official_script_uses_guarded_openai_provider():
    text = read("scripts/macos-restore-official.sh")
    launcher = read("scripts/install-macos-launcher.sh")

    assert "openai-official" in text
    assert "macos-provider-switch.sh" in text
    assert "auth.json" in text
    assert "models_cache.json" in text
    assert "state_5.sqlite" in text
    assert "APPLY" in text
    assert ".codex-hybrid-model-switcher/env.sh" in launcher


def test_macos_provider_switch_detects_new_chatgpt_desktop_processes():
    text = read("scripts/macos-app-common.sh")

    assert "(ChatGPT|Codex)\\.app" in text
    assert "codex( .*)? app-server" in text
    assert "codex-command-runner" in text
    assert "codex-code-mode-host" in text
    assert "com.openai.codex" in text
    assert text.index("mdfind") < text.index('"/Applications/ChatGPT.app"')
    assert 'wait "${cli_pid}"' in text


def test_macos_hot_router_launcher_uses_config_and_native_app_discovery():
    text = read("scripts/macos-hot-router-start.sh")

    assert "ensure-bridge" in text
    assert "hot-router --config" in text
    assert "hot-router-mode enable" in text
    assert "macos-app-common.sh" in text
    assert "open_codex_desktop" in text
    assert "LaunchAgent" not in text
    assert "KeepAlive" not in text


def test_macos_one_click_package_builder_creates_expected_zip(tmp_path):
    output = tmp_path / "macos-setup.zip"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-macos-one-click-package.py"), "--output", str(output)],
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
        command_mode = archive.getinfo("Install Codex Hybrid.command").external_attr >> 16
    assert "Install Codex Hybrid.command" in names
    assert "Start Codex Hybrid 2.0.command" in names
    assert "Enable Codex Hybrid 2.0.command" in names
    assert "Restore Codex 19030 Mode.command" in names
    assert "VERSION.txt" in names
    assert "Codex Hybrid Diagnostics.command" in names
    assert "Restore Official Codex.command" in names
    assert "Install-CodexHybrid.sh" in names
    assert "README.txt" in names
    assert "README.zh-CN.txt" in names
    assert "先看我-安装说明.txt" in names
    assert "SHA256校验.txt" in names
    assert "provider-preset.example.json" in names
    assert "payload/codex-hybrid-model-switcher/bootstrap.py" in names
    assert "payload/codex-hybrid-model-switcher/src/codex_hybrid_switcher/__init__.py" in names
    assert "payload/codex-hybrid-model-switcher/src/codex_hybrid_switcher/history.py" in names
    assert "payload/codex-hybrid-model-switcher/scripts/macos-provider-switch.sh" in names
    assert "payload/codex-hybrid-model-switcher/scripts/macos-provider-menu.sh" in names
    assert "payload/codex-hybrid-model-switcher/scripts/macos-app-common.sh" in names
    assert "payload/codex-hybrid-model-switcher/scripts/macos-hot-router-start.sh" in names
    assert "payload/codex-hybrid-model-switcher/scripts/macos-hot-router-mode.sh" in names
    assert "payload/codex-hybrid-model-switcher/scripts/macos-restore-official.sh" in names
    assert "payload/codex-hybrid-model-switcher/scripts/install-macos-launcher.sh" in names
    assert command_mode & 0o111
    assert not any(name.startswith(".git/") for name in names)
    assert not any(name.startswith(".venv/") for name in names)
    assert not any(name.startswith("dist/") for name in names)
    assert not any(name.startswith(".package-cache/") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/.github/") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/docs/") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/tests/") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/scripts/validate-") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/小白一键配置包codex混合配置2.0版/") for name in names)


def test_macos_package_builder_can_bundle_full_local_payload(tmp_path):
    model_dir = tmp_path / "model"
    llama_x64 = tmp_path / "llama-x64"
    llama_arm64 = tmp_path / "llama-arm64"
    model_dir.mkdir()
    llama_x64.mkdir()
    llama_arm64.mkdir()
    (model_dir / "gemma-Q4_K_M.gguf").write_bytes(b"fake-model")
    (model_dir / "gemma-mmproj-BF16.gguf").write_bytes(b"fake-mmproj")
    (model_dir / "test_red_square.png").write_bytes(b"png")
    (llama_x64 / "llama-server").write_text("placeholder", encoding="utf-8")
    (llama_arm64 / "llama-server").write_text("placeholder", encoding="utf-8")
    (llama_x64 / "llama-server").chmod(0o755)
    (llama_arm64 / "llama-server").chmod(0o755)
    output = tmp_path / "macos-full-local.zip"

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build-macos-one-click-package.py"),
            "--output",
            str(output),
            "--full-local",
            "--include-model-dir",
            str(model_dir),
            "--include-llama-macos-x64",
            str(llama_x64),
            "--include-llama-macos-arm64",
            str(llama_arm64),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("payload/models/local-gemma/MODEL_MANIFEST.json").decode("utf-8"))
    assert "payload/llama.cpp/macos-x64/llama-server" in names
    assert "payload/llama.cpp/macos-arm64/llama-server" in names
    assert "payload/models/local-gemma/gemma-Q4_K_M.gguf" in names
    assert "payload/models/local-gemma/gemma-mmproj-BF16.gguf" in names
    assert "payload/models/local-gemma/test_red_square.png" in names
    assert "payload/models/local-gemma/NOTICE.txt" in names
    assert manifest["license"] == "Apache-2.0"
    assert {item["name"] for item in manifest["files"]} >= {"gemma-Q4_K_M.gguf", "gemma-mmproj-BF16.gguf"}


def test_macos_package_builder_can_optionally_bundle_python_payload(tmp_path):
    python_dir = tmp_path / "python-runtime"
    (python_dir / "bin").mkdir(parents=True)
    (python_dir / "bin" / "python3").write_text("#!/bin/sh\n", encoding="utf-8")
    (python_dir / "bin" / "python3").chmod(0o755)
    output = tmp_path / "macos-with-python.zip"

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build-macos-one-click-package.py"),
            "--output",
            str(output),
            "--include-python-dir",
            str(python_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert "payload/python/bin/python3" in names
