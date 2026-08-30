from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def test_installed_windows_launcher_uses_guarded_menu_script():
    text = (ROOT / "scripts" / "install-windows-launcher.ps1").read_text(encoding="utf-8")

    assert "windows-provider-menu.ps1" in text
    assert "windows-current-release-launcher.ps1" in text
    assert "windows-hot-router-mode.ps1" in text
    assert "Start Codex Hot Router.cmd" in text
    assert "Enable Codex Hot Router Mode.cmd" in text
    assert "Restore Codex 19030 Mode.cmd" in text
    assert "Repair Codex Browser and CLI.cmd" in text
    assert "Repair Codex Update and Plugins.cmd" in text
    assert "Repair Codex Live Audio.cmd" in text
    assert "Change Codex Account.cmd" in text
    assert "codex-hybrid-switcher menu" not in text
    assert "windows-current-release-launcher.ps1" in text
    assert "current-project.txt" in text
    assert "Start-Codex-Hot-Router.ps1" in text


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
    hot_router = (ROOT / "installer" / "windows" / "Start Codex Hot Router.cmd").read_text(encoding="utf-8")
    launcher = (ROOT / "installer" / "windows" / "Install Codex Hybrid.cmd").read_text(encoding="utf-8")
    diagnostics = (ROOT / "installer" / "windows" / "Codex Hybrid Diagnostics.cmd").read_text(encoding="utf-8")
    repair = (ROOT / "installer" / "windows" / "Repair Codex Browser and CLI.cmd").read_text(encoding="utf-8")
    orchestrate = (ROOT / "installer" / "windows" / "Repair Codex Update and Plugins.cmd").read_text(encoding="utf-8")
    orchestrator_script = (ROOT / "scripts" / "windows-update-orchestrate.ps1").read_text(encoding="utf-8")
    live_audio = (ROOT / "installer" / "windows" / "Repair Codex Live Audio.cmd").read_text(encoding="utf-8")
    account = (ROOT / "installer" / "windows" / "Change Codex Account.cmd").read_text(encoding="utf-8")
    restore = (ROOT / "installer" / "windows" / "Restore Official Codex.cmd").read_text(encoding="utf-8")
    readme = (ROOT / "installer" / "windows" / "README.txt").read_text(encoding="utf-8")
    readme_zh = (ROOT / "installer" / "windows" / "README.zh-CN.txt").read_text(encoding="utf-8")
    preset = (ROOT / "installer" / "windows" / "provider-preset.example.json").read_text(encoding="utf-8")

    assert "https://developers.openai.com/codex/app" in text
    assert "payload\\python" in text
    assert "Installed bundled portable Python" in text
    assert "Configured portable Python module path" in text
    assert "Python.Python.3.12" in text
    assert "winget install" in text
    assert "payload\\codex-hybrid-model-switcher" in text
    assert "Using bundled project payload" in text
    assert "provider-preset.json" in text
    assert "Codex Hybrid Installer Diagnostics" in text
    assert "configured_codex_cli_exists" in text
    assert "browser_bundled_version" in text
    assert "low_memory_events_24h" in text
    assert "codex-hybrid-installer-diagnostics.txt" in text
    assert "If Codex Desktop is fully closed and you want to apply now, type APPLY exactly." in text
    assert "archive/refs/tags/$ReleaseTag.zip" in text
    assert "api.github.com/repos/ggml-org/llama.cpp/releases/latest" in text
    assert "payload\\llama.cpp" in text
    assert "payload\\vcredist\\vc_redist.x64.exe" in text
    assert "payload\\models\\local-gemma" in text
    assert "$ModelRoot = Join-Path $InstallRoot \"models\"" in text
    assert "Show-DiskSpaceCheck" in text
    assert "Recommended free space for full local setup: 15-20 GB or more." in text
    assert "Copying about $sourceSizeGb GB of local model files. Please wait" in text
    assert "LocalSmokeTimeoutSeconds = 900" in text
    assert "Stop-ManagedBridgeOnPort" in text
    assert "Ensure-LlamaRuntimeRunnable" in text
    assert "Install-BundledVCRedist" in text
    assert "Start-Process -FilePath $ServerPath" in text
    assert "-RedirectStandardError $stderr" in text
    assert "Microsoft Visual C++ Runtime" in text
    assert "llama-server runtime check passed" in text
    assert '"--request-timeout", "$LocalSmokeTimeoutSeconds"' in text
    assert "Install-LocalModelSelection" in text
    assert "Bundled local model installed under local app data." in text
    assert "bundled_local_model" in text
    assert "installed_llama_cpp" in text
    assert "installed_local_model" in text
    assert "local_provider_enabled" in text
    assert "local_only_config" in text
    assert "install_drive_free_gb" in text
    assert "--skip-cloud" in text
    assert "No cloud base_url was provided. Continuing with local-only setup." in text
    assert "local-gemma" in text
    assert "LlamaServerPath" in text
    assert "Read-Host \"API key\" -AsSecureString" in text
    assert "SetEnvironmentVariable($Name, $plain, \"User\")" in text
    assert "OpenFileDialog" in text
    assert "local-smoke" in text
    assert "windows-provider-switch.ps1" in text
    assert "UnifyHistory" in text
    assert "history-status" in text
    assert "unify-history" in text
    assert "MIGRATE" in text
    assert "windows-portable-python-path.ps1" in text
    assert "-Apply" in text
    assert "install-windows-launcher.ps1" in text
    assert "INSTALLER DRY-RUN COMPLETE" in text
    assert "No real Codex switch was applied" in text
    assert "Remove-Item -LiteralPath $modelsCache" not in text
    assert "Remove-Item -LiteralPath $stateDb" not in text
    assert "Copy-Item -LiteralPath $modelsCache" not in text
    assert "Copy-Item -LiteralPath $stateDb" not in text
    assert "powershell -NoProfile -ExecutionPolicy Bypass" in launcher
    assert "windows-hot-router-start.ps1" in hot_router
    assert "VERSION.txt" in hot_router
    assert "pyproject.toml" in hot_router
    assert 'set "PACKAGE_VERSION=2.18.5"' not in hot_router
    assert "-DiagnosticsOnly" in diagnostics
    assert "windows-restore-official.ps1" in restore
    assert "VERSION.txt" in restore
    assert "pyproject.toml" in restore
    assert 'set "PACKAGE_VERSION=2.18.5"' not in restore
    assert "windows-update-repair.ps1" in repair
    assert "-Apply" in repair
    assert "windows-update-orchestrate.ps1" in orchestrate
    assert "-Apply" in orchestrate
    assert "windows-update-orchestrate.ps1" in orchestrate
    assert "SettleChecks" in orchestrator_script
    assert "SettleTotalTimeoutSeconds" in orchestrator_script
    assert "MaxRegistrationPasses" in orchestrator_script
    assert "windows-live-audio.ps1" in live_audio
    assert "-Action Doctor" in live_audio
    assert "-Action Repair -Confirm REPAIR" in live_audio
    assert "-Action Restore -Confirm RESTORE" in live_audio
    assert "windows-change-account.ps1" in account
    assert "-Apply" in account
    assert "Full local model packages may include payload\\models\\local-gemma" in readme
    assert "does not install CC Switch" in readme
    assert "网盘一键安装包" in readme_zh
    assert "不需要安装 Git" in readme_zh
    assert "恢复官方 Codex" in readme_zh
    assert "YOUR-OPENAI-COMPATIBLE-ENDPOINT.example" in preset
    assert "api_key_env" in preset


def test_windows_restore_official_script_uses_guarded_openai_provider():
    text = (ROOT / "scripts" / "windows-restore-official.ps1").read_text(encoding="utf-8")
    launcher = (ROOT / "scripts" / "install-windows-launcher.ps1").read_text(encoding="utf-8")

    assert "openai-official" in text
    assert "windows-provider-switch.ps1" in text
    assert "auth.json" in text
    assert "models_cache.json" in text
    assert "state_5.sqlite" in text
    assert "APPLY" in text
    assert "Restore Official Codex.cmd" in launcher


def test_windows_package_builder_defaults_to_portable_python_with_no_python_escape_hatch():
    text = (ROOT / "scripts" / "build-windows-one-click-package.py").read_text(encoding="utf-8")

    assert "PYTHON_EMBED_URL" in text
    assert "PYTHON_EMBED_SHA256" in text
    assert "ensure_portable_python" in text
    assert "bundle_python: bool = True" in text
    assert "--no-python" in text
    assert "--include-model-dir" in text
    assert "MODEL_MANIFEST.json" in text
    assert "Apache-2.0" in text
    assert "Start Codex Hot Router.cmd" in text
    assert "windows-hot-router-start.ps1" in text
    assert "windows-update-repair.ps1" in text
    assert "windows-update-orchestrate.ps1" in text
    assert "Repair Codex Update and Plugins.cmd" in text
    assert "windows-live-audio.ps1" in text
    assert "Repair Codex Live Audio.cmd" in text
    assert "windows-browser-post-start.ps1" in text
    assert "windows-change-account.ps1" in text
    assert "windows-portable-python-path.ps1" in text


def test_windows_hot_router_launcher_checks_bridge_before_router_and_opens_codex():
    text = (ROOT / "scripts" / "windows-hot-router-start.ps1").read_text(encoding="utf-8")
    cmd = (ROOT / "scripts" / "Start Codex Hot Router.cmd").read_text(encoding="utf-8")

    assert text.index("ensure-bridge") < text.index('@("hot-router"')
    assert text.index("windows-update-orchestrate.ps1") < text.index("ensure-bridge")
    assert "-Apply" in text
    assert "-Automatic" in text
    assert text.index("Repair-PortablePythonPath") < text.index("windows-update-orchestrate.ps1")
    assert '$ProgressPreference = "SilentlyContinue"' in text
    assert "windows-portable-python-path.ps1" in text
    assert "Repair Codex Update and Plugins.cmd" in text
    assert "Start-BrowserPostStartCheck" in text
    assert "windows-browser-post-start.ps1" in text
    assert "127.0.0.1:19030" in text
    assert "$RouterHost`:$Port" in text
    assert "privateConfig.hot_router" in text
    assert "Get-StartApps" in text
    assert "Get-AppxPackageManifest" in text
    assert "Enable-HotRouterMode" in text
    assert "windows-hot-router-mode.ps1" in text
    assert "ChatGPT*" in text
    assert "OpenAI.Codex_2p2nqsd0c76g0!App" in text
    assert "Register-ScheduledTask" not in text
    assert "New-Service" not in text
    assert "Start-Service" not in text
    assert "windows-hot-router-start.ps1" in cmd


def test_windows_stable_launcher_selects_latest_installed_release_without_services():
    text = (ROOT / "scripts" / "windows-current-release-launcher.ps1").read_text(encoding="utf-8")
    installed = (ROOT / "scripts" / "install-windows-launcher.ps1").read_text(encoding="utf-8")
    package = (ROOT / "installer" / "windows" / "Start Codex Hot Router.cmd").read_text(encoding="utf-8")

    assert "current-project.txt" in text
    assert "Installed-Projects" in text
    assert "Project-Version" in text
    assert "windows-hot-router-start.ps1" in text
    assert "| Out-Host" in text
    assert "return $LASTEXITCODE" not in text
    assert "exit $LASTEXITCODE" in text
    assert "Start-Codex-Hot-Router.ps1" in installed
    assert "Start-Codex-Hot-Router.ps1" in package
    for source in (text, installed, package):
        assert "Register-ScheduledTask" not in source
        assert "New-Service" not in source


def test_windows_maintenance_wrappers_stream_output_without_polluting_exit_code():
    for name in (
        "windows-update-orchestrate.ps1",
        "windows-update-repair.ps1",
        "windows-change-account.ps1",
    ):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert text.count("| Out-Host") >= 4
        assert "return $LASTEXITCODE" in text
    assert "Register-ScheduledTask" not in text
    assert "Restart-Computer" not in text


def test_windows_browser_post_start_helper_is_bounded_and_one_shot():
    text = (ROOT / "scripts" / "windows-browser-post-start.ps1").read_text(encoding="utf-8")

    assert "windows-browser-ensure" in text
    assert "--wait-seconds" in text
    assert "browser-post-start.log" in text
    assert "windows-portable-python-path.ps1" in text
    assert "Register-ScheduledTask" not in text
    assert "New-Service" not in text
    assert "Restart-Computer" not in text
    assert "Stop-Process" not in text


def test_windows_live_audio_repair_is_explicit_backup_first_and_user_scoped():
    text = (ROOT / "scripts" / "windows-live-audio.ps1").read_text(encoding="utf-8")
    launcher = (ROOT / "scripts" / "Repair Codex Live Audio.cmd").read_text(encoding="utf-8")

    assert 'ValidateSet("Doctor", "Repair", "Restore")' in text
    assert '$Confirm -cne "REPAIR"' in text
    assert '$Confirm -cne "RESTORE"' in text
    assert "Test-CodexDesktopRunning" in text
    assert "Get-CimInstance Win32_Process" in text
    assert 'CommandLine -match "app-server"' in text
    assert "Get-StableProtectedHashes" in text
    assert "New-LiveAudioBackup" in text
    assert text.index("New-LiveAudioBackup") < text.index("Set-CodexMicrophoneConsent")
    assert "CapabilityAccessManager\\ConsentStore\\microphone" in text
    assert "SetEndpointVisibility" in text
    assert "SetDefaultEndpoint" in text
    assert "Get-ProtectedHashes" in text
    assert '".codex\\auth.json"' in text
    assert '".codex\\models_cache.json"' in text
    assert '".codex\\state_5.sqlite"' in text
    assert "Set-ItemProperty -Path $script:CaptureRegistryRoot" not in text
    assert "Stop-Process" not in text
    assert "Register-ScheduledTask" not in text
    assert "New-Service" not in text
    assert "Restart-Computer" not in text
    assert "REPAIR" in launcher
    assert "RESTORE" in launcher
    assert "-Action Doctor" in launcher


def test_windows_download_scripts_disable_progress_rendering():
    paths = (
        ROOT / "scripts" / "windows-hot-router-start.ps1",
        ROOT / "scripts" / "bootstrap-windows.ps1",
        ROOT / "installer" / "windows" / "Install-CodexHybrid.ps1",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "Invoke-WebRequest" in text
        assert '$ProgressPreference = "SilentlyContinue"' in text


def test_windows_portable_python_path_helper_replaces_old_release_src_atomically():
    helper = (ROOT / "scripts" / "windows-portable-python-path.ps1").read_text(encoding="utf-8")

    assert "python*._pth" in helper
    assert "codexhybridmodelswitcher/releases/*/project/src" in helper
    assert '$updated.Add($src)' in helper
    assert "Move-Item -LiteralPath $temporary" in helper
    assert "Register-ScheduledTask" not in helper
    assert "New-Service" not in helper


def test_windows_hot_router_mode_launcher_only_delegates_base_url_toggle():
    text = (ROOT / "scripts" / "windows-hot-router-mode.ps1").read_text(encoding="utf-8")
    enable = (ROOT / "scripts" / "Enable Codex Hot Router Mode.cmd").read_text(encoding="utf-8")
    restore = (ROOT / "scripts" / "Restore Codex 19030 Mode.cmd").read_text(encoding="utf-8")

    assert "hot-router-mode" in text
    assert "RouterUrl" in text
    assert "--router-url" in text
    assert "models_cache.json" not in text
    assert "state_5.sqlite" not in text
    assert "auth.json" not in text
    assert "windows-hot-router-mode.ps1" in enable
    assert "-Action enable" in enable
    assert "-Action restore" in restore


def test_windows_one_click_package_builder_creates_expected_zip(tmp_path):
    output = tmp_path / "setup.zip"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-windows-one-click-package.py"), "--output", str(output), "--no-python"],
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
    assert "VERSION.txt" in names
    assert "Start Codex Hot Router.cmd" in names
    assert "Codex Hybrid Diagnostics.cmd" in names
    assert "Repair Codex Update and Plugins.cmd" in names
    assert "Repair Codex Browser and CLI.cmd" in names
    assert "Repair Codex Live Audio.cmd" in names
    assert "Change Codex Account.cmd" in names
    assert "Restore Official Codex.cmd" in names
    assert "Install-CodexHybrid.ps1" in names
    assert "README.txt" in names
    assert "README.zh-CN.txt" in names
    assert "provider-preset.example.json" in names
    assert "payload/codex-hybrid-model-switcher/bootstrap.py" in names
    assert "payload/codex-hybrid-model-switcher/src/codex_hybrid_switcher/__init__.py" in names
    assert "payload/codex-hybrid-model-switcher/src/codex_hybrid_switcher/history.py" in names
    assert "payload/codex-hybrid-model-switcher/src/codex_hybrid_switcher/hot_router.py" in names
    assert "payload/codex-hybrid-model-switcher/src/codex_hybrid_switcher/hot_router_mode.py" in names
    assert "payload/codex-hybrid-model-switcher/src/codex_hybrid_switcher/windows_update.py" in names
    assert "payload/codex-hybrid-model-switcher/src/codex_hybrid_switcher/account_switch.py" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-hot-router-start.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-current-release-launcher.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-browser-post-start.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-update-orchestrate.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-hot-router-mode.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-portable-python-path.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/Start Codex Hot Router.cmd" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-provider-switch.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-restore-official.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-update-repair.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/Repair Codex Update and Plugins.cmd" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-live-audio.ps1" in names
    assert "payload/codex-hybrid-model-switcher/scripts/Repair Codex Live Audio.cmd" in names
    assert "payload/codex-hybrid-model-switcher/scripts/windows-change-account.ps1" in names
    assert not any(name.startswith(".git/") for name in names)
    assert not any(name.startswith(".venv/") for name in names)
    assert not any(name.startswith("dist/") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/.github/") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/docs/") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/dist-materials/") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/tests/") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/scripts/validate-") for name in names)
    assert not any(name.startswith("payload/codex-hybrid-model-switcher/小白一键配置包codex混合配置2.0版/") for name in names)


def test_windows_one_click_package_builder_can_bundle_optional_runtime_dirs(tmp_path):
    python_dir = tmp_path / "python-portable"
    llama_dir = tmp_path / "llama"
    vcredist = tmp_path / "vc_redist.x64.exe"
    python_dir.mkdir()
    llama_dir.mkdir()
    (python_dir / "python.exe").write_text("placeholder", encoding="utf-8")
    (llama_dir / "llama-server.exe").write_text("placeholder", encoding="utf-8")
    vcredist.write_text("placeholder", encoding="utf-8")
    output = tmp_path / "setup-with-runtimes.zip"

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build-windows-one-click-package.py"),
            "--output",
            str(output),
            "--include-python-dir",
            str(python_dir),
            "--include-llama-dir",
            str(llama_dir),
            "--include-vcredist-file",
            str(vcredist),
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
    assert "payload/python/python.exe" in names
    assert "payload/llama.cpp/llama-server.exe" in names
    assert "payload/vcredist/vc_redist.x64.exe" in names


def test_windows_one_click_package_builder_can_bundle_local_model_payload(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "gemma-Q4_K_M.gguf").write_bytes(b"fake-model")
    (model_dir / "gemma-mmproj-BF16.gguf").write_bytes(b"fake-mmproj")
    (model_dir / "test_red_square.png").write_bytes(b"png")
    output = tmp_path / "setup-with-model.zip"

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build-windows-one-click-package.py"),
            "--output",
            str(output),
            "--no-python",
            "--include-model-dir",
            str(model_dir),
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
    assert "payload/models/local-gemma/gemma-Q4_K_M.gguf" in names
    assert "payload/models/local-gemma/gemma-mmproj-BF16.gguf" in names
    assert "payload/models/local-gemma/test_red_square.png" in names
    assert "payload/models/local-gemma/NOTICE.txt" in names
    assert manifest["license"] == "Apache-2.0"
    assert {item["name"] for item in manifest["files"]} >= {"gemma-Q4_K_M.gguf", "gemma-mmproj-BF16.gguf"}
