from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from codex_hybrid_switcher.config import load_config
from codex_hybrid_switcher import windows_update


def write_config(tmp_path: Path) -> tuple[Path, Path]:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"codex_home": str(codex_home), "providers": [{"id": "official", "kind": "official"}]}),
        encoding="utf-8",
    )
    for name in ("auth.json", "models_cache.json", "state_5.sqlite"):
        (codex_home / name).write_text(name, encoding="utf-8")
    return config_path, codex_home


def app_fixture(tmp_path: Path, version: str = "26.715.9999.0") -> tuple[dict[str, str], Path]:
    app = tmp_path / "WindowsApps" / "OpenAI.Codex"
    source = app / "app" / "resources" / "codex.exe"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"current-codex-cli")
    for name in windows_update.MANAGED_CLI_COMPANION_FILES:
        (source.parent / name).write_bytes(("current-" + name).encode("utf-8"))
    for plugin in ("browser", "chrome"):
        manifest = app / "app" / "resources" / "plugins" / "openai-bundled" / "plugins" / plugin / ".codex-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": plugin, "version": "26.715.9000"}), encoding="utf-8")
    return {"Version": version, "PackageFamilyName": "OpenAI.Codex_family", "InstallLocation": str(app)}, source


def copy_cli_bundle(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    for name, source_path in windows_update.cli_bundle_paths(source).items():
        (destination.parent / name).write_bytes(source_path.read_bytes())


def add_plugin_cache(codex_home: Path, version: str = "26.715.9000") -> None:
    for plugin in ("browser", "chrome"):
        manifest = codex_home / "plugins" / "cache" / "openai-bundled" / plugin / version / ".codex-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": plugin, "version": version}), encoding="utf-8")


def cli_plugin_state(
    *,
    installed: bool,
    enabled: bool,
    policy: str = "AVAILABLE",
) -> windows_update.CliPluginState:
    return windows_update.CliPluginState(
        plugin_id=windows_update.BROWSER_PLUGIN_ID,
        found=True,
        installed=installed,
        enabled=enabled,
        install_policy=policy,
        version="26.715.9000",
        bucket="installed" if installed else "available",
    )


def test_parse_cli_plugin_catalog_distinguishes_installed_and_available():
    states = windows_update.parse_cli_plugin_catalog(
        {
            "installed": [
                {
                    "pluginId": "browser@openai-bundled",
                    "version": "26.715.9000",
                    "installed": True,
                    "enabled": True,
                    "installPolicy": "AVAILABLE",
                }
            ],
            "available": [
                {
                    "pluginId": "chrome@openai-bundled",
                    "version": "26.715.9000",
                    "installed": False,
                    "enabled": False,
                    "installPolicy": "AVAILABLE",
                }
            ],
        }
    )

    assert states["browser@openai-bundled"].healthy is True
    assert states["chrome@openai-bundled"].available is True
    assert states["chrome@openai-bundled"].installed is False


def test_orchestrator_plugin_verification_accepts_prestart_feature_gate(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, source = app_fixture(tmp_path)
    add_plugin_cache(codex_home)
    (codex_home / "config.toml").write_text(
        '[plugins."browser@openai-bundled"]\nenabled = true\n'
        '[plugins."chrome@openai-bundled"]\nenabled = true\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        windows_update,
        "query_codex_plugin_catalog",
        lambda _cli: (
            {
                plugin_id: windows_update.CliPluginState(
                    plugin_id=plugin_id,
                    found=True,
                    installed=True,
                    enabled=True,
                    install_policy="PENDING",
                    version="26.715.9000",
                    bucket="installed",
                )
                for plugin_id in windows_update.BUNDLED_PLUGIN_IDS
            },
            None,
        ),
    )

    ok, detail = windows_update.verify_official_bundled_plugins(config, app, source)

    assert ok is True
    assert "post-start" in detail


def test_plugin_probe_accepts_new_bundled_marketplace_layout(tmp_path):
    _config_path, codex_home = write_config(tmp_path)
    app, _source = app_fixture(tmp_path)
    manifest = (
        codex_home
        / ".tmp"
        / "bundled-marketplaces"
        / "openai-bundled"
        / "plugins"
        / "browser"
        / ".codex-plugin"
        / "plugin.json"
    )
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "browser", "version": "26.715.9000"}), encoding="utf-8")
    config_text = '[plugins."browser@openai-bundled"]\nenabled = true\n'

    probe = windows_update.plugin_probe("browser", app, codex_home, config_text)

    assert probe.installed is True
    assert probe.install_source == "bundled-marketplace"
    assert probe.cache_version == "26.715.9000"
    assert probe.version_matches is True


def add_official_runtime(tmp_path: Path, codex_home: Path, version: str = "26.715.9000") -> Path:
    runtime = tmp_path / "OpenAI" / "Codex" / "runtimes" / "cua_node" / "hash" / "bin" / "node_repl.exe"
    runtime.parent.mkdir(parents=True)
    runtime.write_bytes(b"official-node-repl")
    (codex_home / "config.toml").write_text(
        "[mcp_servers.node_repl]\n"
        f"command = '{runtime}'\n\n"
        "[mcp_servers.node_repl.env]\n"
        f"BROWSER_USE_CODEX_APP_VERSION = \"{version}\"\n",
        encoding="utf-8",
    )
    return runtime


def test_toml_cli_path_supports_single_and_double_quotes():
    single = "[mcp_servers.node_repl.env]\nCODEX_CLI_PATH = 'C:\\OpenAI\\codex.exe'\n"
    double = '[mcp_servers.node_repl.env]\nCODEX_CLI_PATH = "C:\\\\OpenAI\\\\codex.exe"\n'

    assert windows_update.find_toml_section_key(single, "[mcp_servers.node_repl.env]", "CODEX_CLI_PATH")[0] == "C:\\OpenAI\\codex.exe"
    assert windows_update.find_toml_section_key(double, "[mcp_servers.node_repl.env]", "CODEX_CLI_PATH")[0] == "C:\\OpenAI\\codex.exe"


def test_all_user_appx_probe_parses_single_staged_package(monkeypatch):
    payload = {
        "Name": "OpenAI.Codex",
        "Version": "26.721.4979.0",
        "Status": "Ok",
        "UserInstallStates": [{"user": "S-1-5-18", "state": "Staged"}],
    }
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(
        windows_update,
        "_run_powershell",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["powershell"], 0, json.dumps(payload), ""
        ),
    )

    packages = windows_update.windows_codex_all_user_packages()

    assert packages == [payload]
    assert windows_update.package_is_staged(packages[0]) is True


def test_pending_registration_compares_current_and_staged_appx_versions():
    app = {"Version": "26.721.3996.0"}
    packages = [
        {
            "Version": "26.721.4979.0",
            "UserInstallStates": [{"state": "Staged"}],
        },
        {
            "Version": "26.721.3996.0",
            "UserInstallStates": [{"state": "Installed"}],
        },
    ]

    highest, pending = windows_update.pending_codex_registration(app, packages)

    assert highest == "26.721.4979.0"
    assert pending is True


def test_appx_stability_requires_three_identical_observations():
    app_v1 = {"Version": "26.803.8161.0"}
    app_v2 = {"Version": "26.803.10989.0"}
    observations = iter(
        (
            windows_update.AppxUpdateSnapshot(app_v1, app_v1["Version"], "26.803.9000.0", True),
            windows_update.AppxUpdateSnapshot(app_v1, app_v1["Version"], app_v2["Version"], True),
            windows_update.AppxUpdateSnapshot(app_v1, app_v1["Version"], app_v2["Version"], True),
            windows_update.AppxUpdateSnapshot(app_v1, app_v1["Version"], app_v2["Version"], True),
        )
    )

    stable = windows_update.wait_for_codex_appx_stability(
        consecutive_checks=3,
        poll_seconds=0,
        timeout_seconds=1,
        probe=lambda: next(observations),
        sleeper=lambda _seconds: None,
        clock=lambda: 0,
    )

    assert stable is not None
    assert stable.highest_staged_version == "26.803.10989.0"
    assert stable.pending_registration is True


def test_bundled_marketplace_path_comes_from_current_appx(tmp_path):
    app, _source = app_fixture(tmp_path, version="26.727.6591.0")

    marketplace = windows_update.bundled_marketplace_path(app)

    assert marketplace == (
        Path(app["InstallLocation"])
        / "app"
        / "resources"
        / "plugins"
        / "openai-bundled"
    )


def test_winget_registration_command_uses_official_store_product(monkeypatch, tmp_path):
    winget = tmp_path / "winget.exe"
    winget.write_bytes(b"winget")
    observed: dict[str, object] = {}
    monkeypatch.setattr(windows_update, "winget_path", lambda: winget)
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)

    def fake_run(arguments, **kwargs):
        observed["arguments"] = arguments
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(arguments, 0, "ok", "")

    monkeypatch.setattr(windows_update.subprocess, "run", fake_run)

    result = windows_update._run_winget_codex_registration(timeout=12)

    assert result.returncode == 0
    arguments = observed["arguments"]
    assert arguments[:3] == [str(winget), "install", "--id"]
    assert windows_update.CODEX_STORE_PRODUCT_ID in arguments
    assert ["--source", "msstore"] == arguments[5:7]
    assert "--force" in arguments
    assert "--silent" in arguments
    assert "--disable-interactivity" in arguments
    assert observed["kwargs"]["encoding"] == "utf-8"
    assert observed["kwargs"]["errors"] == "replace"


def test_staged_package_registration_prefers_exact_official_target():
    packages = [
        {
            "Name": "OpenAI.Codex",
            "Version": "26.814.5517.0",
            "InstallLocation": "C:/WindowsApps/Codex-5517",
            "UserInstallStates": [{"state": "Staged"}],
        },
        {
            "Name": "OpenAI.Codex",
            "Version": "26.815.1000.0",
            "InstallLocation": "C:/WindowsApps/Codex-1000",
            "UserInstallStates": [{"state": "Staged"}],
        },
    ]

    selected = windows_update.staged_codex_package_for_registration(
        "26.814.5517.0",
        packages,
    )

    assert selected is packages[0]


def test_local_staged_registration_uses_official_manifest(tmp_path, monkeypatch):
    install = tmp_path / "OpenAI.Codex_26.814.5517.0"
    install.mkdir()
    (install / "AppxManifest.xml").write_text("<Package />", encoding="utf-8")
    observed: dict[str, object] = {}

    def fake_powershell(script, *, timeout=20):
        observed["script"] = script
        observed["timeout"] = timeout
        return subprocess.CompletedProcess(["powershell"], 0, "", "")

    monkeypatch.setattr(windows_update, "_run_powershell", fake_powershell)
    result = windows_update._run_local_staged_codex_registration(
        {"InstallLocation": str(install)},
        timeout=45,
    )

    assert result.returncode == 0
    assert "Add-AppxPackage -Register" in observed["script"]
    assert "-DisableDevelopmentMode" in observed["script"]
    assert str(install / "AppxManifest.xml") in observed["script"]
    assert observed["timeout"] == 45


def test_appx_registration_falls_back_to_downloaded_official_package(tmp_path, monkeypatch):
    old_app, _source = app_fixture(tmp_path, version="26.810.7004.0")
    new_app = dict(old_app, Version="26.814.5517.0")
    staged = {
        "Name": "OpenAI.Codex",
        "Version": new_app["Version"],
        "InstallLocation": new_app["InstallLocation"],
        "UserInstallStates": [{"state": "Staged"}],
    }
    local_calls: list[dict[str, object]] = []
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    monkeypatch.setattr(windows_update, "windows_codex_all_user_packages", lambda: [staged])
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: new_app)
    monkeypatch.setattr(windows_update.time, "sleep", lambda _seconds: None)

    result = windows_update.run_windows_appx_registration(
        old_app,
        apply=True,
        target_version=new_app["Version"],
        timeout_seconds=1,
        poll_seconds=0.1,
        runner=lambda: subprocess.CompletedProcess(["winget"], 1, "", "0x80072efd"),
        local_runner=lambda package: (
            local_calls.append(package)
            or subprocess.CompletedProcess(["powershell"], 0, "", "")
        ),
    )

    assert result == 0
    assert local_calls == [staged]


def test_appx_registration_does_not_fallback_without_staged_official_package(tmp_path, monkeypatch):
    old_app, _source = app_fixture(tmp_path, version="26.810.7004.0")
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    monkeypatch.setattr(windows_update, "windows_codex_all_user_packages", lambda: [])

    result = windows_update.run_windows_appx_registration(
        old_app,
        apply=True,
        target_version="26.814.5517.0",
        runner=lambda: subprocess.CompletedProcess(["winget"], 1, "", "offline"),
        local_runner=lambda _package: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert result == 20


def test_appx_registration_apply_waits_until_target_is_registered(tmp_path, monkeypatch):
    old_app, _source = app_fixture(tmp_path, version="26.721.3996.0")
    new_app = dict(old_app, Version="26.727.6591.0")
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: new_app)
    monkeypatch.setattr(
        windows_update,
        "windows_codex_all_user_packages",
        lambda: [{"Version": "26.727.6591.0", "UserInstallStates": [{"state": "Staged"}]}],
    )
    monkeypatch.setattr(windows_update.time, "sleep", lambda _seconds: None)

    result = windows_update.run_windows_appx_registration(
        old_app,
        apply=True,
        timeout_seconds=1,
        poll_seconds=0.1,
        runner=lambda: subprocess.CompletedProcess(["winget"], 0, "ok", ""),
    )

    assert result == 0


def test_appx_registration_returns_after_target_even_if_newer_build_is_staged(tmp_path, monkeypatch):
    old_app, _source = app_fixture(tmp_path, version="26.803.8161.0")
    registered_app = dict(old_app, Version="26.803.9000.0")
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: registered_app)
    monkeypatch.setattr(
        windows_update,
        "windows_codex_all_user_packages",
        lambda: [
            {
                "Version": "26.803.10989.0",
                "UserInstallStates": [{"state": "Staged"}],
            }
        ],
    )

    result = windows_update.run_windows_appx_registration(
        old_app,
        apply=True,
        target_version="26.803.9000.0",
        timeout_seconds=1,
        poll_seconds=0.1,
        runner=lambda: subprocess.CompletedProcess(["winget"], 0, "ok", ""),
    )

    assert result == 0


def test_refresh_official_plugins_uses_current_marketplace_and_both_plugins(tmp_path, monkeypatch):
    app, source = app_fixture(tmp_path)
    commands: list[list[str]] = []

    def fake_command(_cli, arguments, **_kwargs):
        commands.append(arguments)
        return subprocess.CompletedProcess(["codex", *arguments], 0, "{}", "")

    monkeypatch.setattr(windows_update, "_run_codex_plugin_command", fake_command)

    result = windows_update.refresh_official_bundled_plugins(source, app, apply=True)

    assert result == 0
    assert commands == [
        ["marketplace", "remove", "openai-bundled", "--json"],
        [
            "marketplace",
            "add",
            str(Path(app["InstallLocation"]) / "app" / "resources" / "plugins" / "openai-bundled"),
            "--json",
        ],
        ["add", "browser@openai-bundled", "--json"],
        ["add", "chrome@openai-bundled", "--json"],
    ]


def test_reserved_bundled_marketplace_is_detected_as_app_managed(tmp_path, monkeypatch):
    _app, source = app_fixture(tmp_path)
    monkeypatch.setattr(windows_update, "_cli_version_tuple", lambda _cli: (0, 149, 0))

    assert windows_update.bundled_marketplace_is_app_managed(source) is True


def test_cli_version_tuple_parses_alpha_version_output(tmp_path, monkeypatch):
    _app, source = app_fixture(tmp_path)
    monkeypatch.setattr(
        windows_update.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [str(source), "--version"],
            0,
            "codex-cli 0.149.0-alpha.18\n",
            "",
        ),
    )

    assert windows_update._cli_version_tuple(source) == (0, 149, 0)


def test_reserved_bundled_marketplace_ignores_stale_cached_listing(tmp_path, monkeypatch):
    _app, source = app_fixture(tmp_path)
    monkeypatch.setattr(windows_update, "_cli_version_tuple", lambda _cli: (0, 149, 0))

    assert windows_update.bundled_marketplace_is_app_managed(source) is True


def test_legacy_cli_keeps_explicit_bundled_marketplace_refresh(tmp_path, monkeypatch):
    _app, source = app_fixture(tmp_path)
    monkeypatch.setattr(windows_update, "_cli_version_tuple", lambda _cli: (0, 148, 9))

    assert windows_update.bundled_marketplace_is_app_managed(source) is False


def test_reserved_bundled_marketplace_refresh_is_deferred(tmp_path, monkeypatch):
    app, source = app_fixture(tmp_path)
    commands: list[list[str]] = []
    monkeypatch.setattr(windows_update, "bundled_marketplace_is_app_managed", lambda _cli: True)

    def fake_command(_cli, arguments, **_kwargs):
        commands.append(arguments)
        return subprocess.CompletedProcess(["codex", *arguments], 0, "{}", "")

    monkeypatch.setattr(windows_update, "_run_codex_plugin_command", fake_command)

    assert windows_update.refresh_official_bundled_plugins(source, app, apply=True) == 0
    assert commands == []


def test_reserved_bundled_marketplace_accepts_stale_cache_before_desktop_launch(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, source = app_fixture(tmp_path)
    add_plugin_cache(codex_home, version="26.715.1000")
    (codex_home / "config.toml").write_text(
        '[plugins."browser@openai-bundled"]\nenabled = true\n'
        '[plugins."chrome@openai-bundled"]\nenabled = true\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(windows_update, "bundled_marketplace_is_app_managed", lambda _cli: True)

    ok, detail = windows_update.verify_official_bundled_plugins(config, app, source)

    assert ok is True
    assert "Codex Desktop" in detail


def test_config_guard_ignores_plugin_node_repl_and_cli_path_but_preserves_other_mcp():
    before = """model_provider = "custom"

[model_providers.custom]
base_url = "http://127.0.0.1:19032/v1"

[mcp_servers.node_repl]
command = "old"

[mcp_servers.obsidian]
command = "obsidian"

[plugins."browser@openai-bundled"]
enabled = true
"""
    after = before.replace("old", "new") + "\n[plugins.\"chrome@openai-bundled\"]\nenabled = true\n"

    assert windows_update.config_guard_hash(before) == windows_update.config_guard_hash(after)
    changed = before.replace('base_url = "http://127.0.0.1:19032/v1"', 'base_url = "http://bad"')
    assert windows_update.config_guard_hash(before) != windows_update.config_guard_hash(changed)
    node_repl_changed = before.replace('command = "old"', 'timeout = 999')
    assert windows_update.config_guard_hash(before) != windows_update.config_guard_hash(node_repl_changed)


def test_update_orchestrator_dry_run_never_registers_or_creates_backup(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app, source = app_fixture(tmp_path)
    add_plugin_cache(codex_home)
    (codex_home / "config.toml").write_text(
        f"model_provider = 'custom'\n[mcp_servers.node_repl]\ncommand='node'\n"
        f"[mcp_servers.node_repl.env]\nCODEX_CLI_PATH='{source}'\n"
        "[plugins.\"browser@openai-bundled\"]\nenabled = true\n"
        "[plugins.\"chrome@openai-bundled\"]\nenabled = true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)
    monkeypatch.setattr(windows_update, "windows_codex_all_user_packages", lambda: [])
    monkeypatch.setattr(
        windows_update,
        "inspect_windows_update",
        lambda *_args, **_kwargs: windows_update.WindowsUpdateReport(
            status=windows_update.STATUS_HEALTHY,
            launch_safe=True,
            app_version=app["Version"],
        ),
    )
    monkeypatch.setattr(windows_update, "official_plugins_need_refresh", lambda *_args: False)
    monkeypatch.setattr(
        windows_update,
        "run_windows_appx_registration",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("registration should not run")),
    )
    monkeypatch.setattr(
        windows_update,
        "refresh_official_bundled_plugins",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("refresh should not run")),
    )

    before = {name: (codex_home / name).read_bytes() for name in ("auth.json", "models_cache.json", "state_5.sqlite")}
    assert windows_update.run_windows_update_orchestrate(str(config_path), apply=False) == 0
    assert {name: (codex_home / name).read_bytes() for name in before} == before
    assert not (tmp_path / "CodexHybridModelSwitcher").exists()


def test_update_orchestrator_apply_refreshes_plugins_after_cli_gate(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app, source = app_fixture(tmp_path)
    config_toml = codex_home / "config.toml"
    config_toml.write_text(
        "model_provider = 'custom'\n\n[model_providers.custom]\nbase_url = 'http://127.0.0.1:19032/v1'\n"
        "\n[mcp_servers.obsidian]\ncommand = 'obsidian'\n",
        encoding="utf-8",
    )
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "config.toml").write_bytes(config_toml.read_bytes())
    observed: dict[str, object] = {}
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)
    monkeypatch.setattr(windows_update, "inspect_windows_update", lambda *_args, **_kwargs: windows_update.WindowsUpdateReport(
        status=windows_update.STATUS_HEALTHY,
        launch_safe=True,
        app_version=app["Version"],
    ))
    monkeypatch.setattr(windows_update, "official_plugins_need_refresh", lambda *_args: True)
    monkeypatch.setattr(
        windows_update,
        "backup_windows_update_state",
        lambda _config: backup,
    )
    def fake_ensure(_path):
        observed["ensure"] = True
        return 0

    monkeypatch.setattr(windows_update, "run_windows_update_ensure", fake_ensure)
    monkeypatch.setattr(windows_update, "current_codex_cli_for_plugins", lambda *_args: source)
    def fake_refresh(_cli, _app, *, apply=False):
        observed["refresh"] = apply
        return 0

    monkeypatch.setattr(windows_update, "refresh_official_bundled_plugins", fake_refresh)
    monkeypatch.setattr(
        windows_update,
        "verify_official_bundled_plugins",
        lambda *_args: (True, "ok"),
    )

    assert windows_update.run_windows_update_orchestrate(
        str(config_path),
        apply=True,
        automatic=True,
    ) == 0
    assert observed == {"ensure": True, "refresh": True}


def test_update_orchestrator_registers_two_consecutive_store_builds(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app0, source = app_fixture(tmp_path, version="26.803.8161.0")
    app1 = dict(app0, Version="26.803.9000.0")
    app2 = dict(app0, Version="26.803.10989.0")
    (codex_home / "config.toml").write_text(
        "model_provider='custom'\n[model_providers.custom]\nbase_url='http://127.0.0.1:19032/v1'\n",
        encoding="utf-8",
    )
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "config.toml").write_bytes((codex_home / "config.toml").read_bytes())
    current_app = {"value": app0}
    initial = windows_update.AppxUpdateSnapshot(app0, app0["Version"], app1["Version"], True)
    final = windows_update.AppxUpdateSnapshot(app2, app2["Version"], "missing", False)
    direct_snapshots = iter((initial, final))
    stable_snapshots = iter(
        (
            initial,
            windows_update.AppxUpdateSnapshot(app1, app1["Version"], app2["Version"], True),
            final,
        )
    )
    inspect_calls = {"count": 0}
    targets: list[str] = []

    def fake_inspect(*_args, **_kwargs):
        inspect_calls["count"] += 1
        if inspect_calls["count"] == 1:
            return windows_update.WindowsUpdateReport(
                status=windows_update.STATUS_MANUAL_ACTION,
                launch_safe=False,
                app_version=app0["Version"],
                highest_staged_version=app1["Version"],
                pending_registration=True,
            )
        return windows_update.WindowsUpdateReport(
            status=windows_update.STATUS_HEALTHY,
            launch_safe=True,
            app_version=app2["Version"],
        )

    def fake_registration(_app, *, target_version=None, **_kwargs):
        assert target_version is not None
        targets.append(target_version)
        current_app["value"] = app1 if target_version == app1["Version"] else app2
        return 0

    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: current_app["value"])
    monkeypatch.setattr(windows_update, "inspect_windows_update", fake_inspect)
    monkeypatch.setattr(windows_update, "official_plugins_need_refresh", lambda *_args: False)
    monkeypatch.setattr(windows_update, "backup_windows_update_state", lambda _config: backup)
    monkeypatch.setattr(windows_update, "codex_appx_update_snapshot", lambda: next(direct_snapshots))
    monkeypatch.setattr(windows_update, "wait_for_codex_appx_stability", lambda **_kwargs: next(stable_snapshots))
    monkeypatch.setattr(windows_update, "run_windows_appx_registration", fake_registration)
    monkeypatch.setattr(windows_update, "run_windows_update_ensure", lambda _path: 0)
    monkeypatch.setattr(windows_update, "current_codex_cli_for_plugins", lambda *_args: source)
    monkeypatch.setattr(windows_update, "verify_official_bundled_plugins", lambda *_args: (True, "ok"))

    protected_before = {
        name: (codex_home / name).read_bytes()
        for name in ("auth.json", "models_cache.json", "state_5.sqlite")
    }
    assert windows_update.run_windows_update_orchestrate(
        str(config_path),
        apply=True,
        automatic=True,
        settle_checks=3,
        settle_poll_seconds=0,
        max_registration_passes=2,
    ) == 0
    assert targets == [app1["Version"], app2["Version"]]
    assert {
        name: (codex_home / name).read_bytes()
        for name in protected_before
    } == protected_before


def test_update_orchestrator_stays_closed_when_third_build_is_still_pending(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app0, _source = app_fixture(tmp_path, version="26.803.8161.0")
    app1 = dict(app0, Version="26.803.9000.0")
    app2 = dict(app0, Version="26.803.10989.0")
    app3 = dict(app0, Version="26.803.12000.0")
    (codex_home / "config.toml").write_text("model_provider='custom'\n", encoding="utf-8")
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "config.toml").write_bytes((codex_home / "config.toml").read_bytes())
    initial = windows_update.AppxUpdateSnapshot(app0, app0["Version"], app1["Version"], True)
    stable_snapshots = iter(
        (
            initial,
            windows_update.AppxUpdateSnapshot(app1, app1["Version"], app2["Version"], True),
            windows_update.AppxUpdateSnapshot(app2, app2["Version"], app3["Version"], True),
        )
    )
    targets: list[str] = []

    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app0)
    monkeypatch.setattr(
        windows_update,
        "inspect_windows_update",
        lambda *_args, **_kwargs: windows_update.WindowsUpdateReport(
            status=windows_update.STATUS_MANUAL_ACTION,
            launch_safe=False,
            app_version=app0["Version"],
            highest_staged_version=app1["Version"],
            pending_registration=True,
        ),
    )
    monkeypatch.setattr(windows_update, "official_plugins_need_refresh", lambda *_args: False)
    monkeypatch.setattr(windows_update, "backup_windows_update_state", lambda _config: backup)
    monkeypatch.setattr(windows_update, "codex_appx_update_snapshot", lambda: initial)
    monkeypatch.setattr(windows_update, "wait_for_codex_appx_stability", lambda **_kwargs: next(stable_snapshots))

    def fake_registration(_app, *, target_version=None, **_kwargs):
        targets.append(str(target_version))
        return 0

    monkeypatch.setattr(windows_update, "run_windows_appx_registration", fake_registration)
    monkeypatch.setattr(
        windows_update,
        "run_windows_update_ensure",
        lambda _path: (_ for _ in ()).throw(AssertionError("CLI alignment must not start")),
    )

    assert windows_update.run_windows_update_orchestrate(
        str(config_path),
        apply=True,
        automatic=True,
        settle_poll_seconds=0,
        max_registration_passes=2,
    ) == 20
    assert targets == [app1["Version"], app2["Version"]]


def test_update_orchestrator_no_pending_update_uses_fast_path(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app, source = app_fixture(tmp_path, version="26.803.10989.0")
    (codex_home / "config.toml").write_text("model_provider='custom'\n", encoding="utf-8")
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "config.toml").write_bytes((codex_home / "config.toml").read_bytes())
    snapshot = windows_update.AppxUpdateSnapshot(app, app["Version"], "missing", False)

    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)
    monkeypatch.setattr(
        windows_update,
        "inspect_windows_update",
        lambda *_args, **_kwargs: windows_update.WindowsUpdateReport(
            status=windows_update.STATUS_HEALTHY,
            launch_safe=True,
            app_version=app["Version"],
        ),
    )
    monkeypatch.setattr(windows_update, "official_plugins_need_refresh", lambda *_args: False)
    monkeypatch.setattr(
        windows_update,
        "backup_windows_update_state",
        lambda _config: (_ for _ in ()).throw(AssertionError("healthy fast path must not create a backup")),
    )
    monkeypatch.setattr(windows_update, "codex_appx_update_snapshot", lambda: snapshot)
    monkeypatch.setattr(
        windows_update,
        "wait_for_codex_appx_stability",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("stable wait should not run")),
    )
    monkeypatch.setattr(
        windows_update,
        "run_windows_appx_registration",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("registration should not run")),
    )
    monkeypatch.setattr(windows_update, "run_windows_update_ensure", lambda _path: 0)
    monkeypatch.setattr(windows_update, "current_codex_cli_for_plugins", lambda *_args: source)
    monkeypatch.setattr(windows_update, "verify_official_bundled_plugins", lambda *_args: (True, "ok"))

    assert windows_update.run_windows_update_orchestrate(
        str(config_path),
        apply=True,
        automatic=True,
    ) == 0


def test_render_cli_path_update_preserves_other_mcp_and_plugin_config(tmp_path):
    existing = """model_provider = "custom"

[mcp_servers.node_repl]
command = "node"

[mcp_servers.node_repl.env]
CODEX_CLI_PATH = 'C:\\old\\codex.exe'

[plugins."browser@openai-bundled"]
enabled = true
"""
    target = tmp_path / "managed" / "codex.exe"

    updated = windows_update.render_cli_path_update(existing, target)

    assert "C:\\old\\codex.exe" not in updated
    assert str(target).replace("\\", "\\\\") in updated
    assert '[plugins."browser@openai-bundled"]' in updated
    assert 'command = "node"' in updated


def test_inspect_windows_update_detects_healthy_and_stale_cli(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, source = app_fixture(tmp_path)
    add_plugin_cache(codex_home)
    configured = tmp_path / "OpenAI" / "Codex" / "bin" / "hash" / "codex.exe"
    copy_cli_bundle(source, configured)
    (codex_home / "config.toml").write_text(
        f"[mcp_servers.node_repl]\ncommand = 'node'\n\n[mcp_servers.node_repl.env]\nCODEX_CLI_PATH = '{configured}'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    healthy = windows_update.inspect_windows_update(
        config,
        execute_cli=False,
        include_resources=False,
        app_info=app,
    )
    assert healthy.status == windows_update.STATUS_HEALTHY
    assert healthy.launch_safe is True
    assert healthy.browser.version_matches is True

    configured.write_bytes(b"old-cli")
    stale = windows_update.inspect_windows_update(
        config,
        execute_cli=False,
        include_resources=False,
        app_info=app,
    )
    assert stale.status == windows_update.STATUS_REPAIR_REQUIRED
    assert stale.launch_safe is False


def test_inspect_windows_update_detects_stale_cli_companion(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, source = app_fixture(tmp_path)
    add_plugin_cache(codex_home)
    configured = tmp_path / "OpenAI" / "Codex" / "bin" / "hash" / "codex.exe"
    copy_cli_bundle(source, configured)
    (configured.parent / "codex-code-mode-host.exe").write_bytes(b"stale-companion")
    (codex_home / "config.toml").write_text(
        f"[mcp_servers.node_repl]\ncommand = 'node'\n\n"
        f"[mcp_servers.node_repl.env]\nCODEX_CLI_PATH = '{configured}'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    report = windows_update.inspect_windows_update(
        config,
        execute_cli=False,
        include_resources=False,
        app_info=app,
    )

    assert report.configured_cli.sha256 == report.source_cli.sha256
    assert report.status == windows_update.STATUS_REPAIR_REQUIRED
    assert report.launch_safe is False
    assert "Configured CODEX_CLI_PATH does not match the current Codex app CLI bundle." in report.errors
    assert windows_update.auto_repair_eligible(report) is True


def test_inspect_windows_update_repairs_matching_cli_in_older_managed_directory(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, source = app_fixture(tmp_path, version="26.727.6591.0")
    add_plugin_cache(codex_home)
    configured = (
        tmp_path
        / "CodexHybridModelSwitcher"
        / "codex-cli"
        / "26.727.4816.0"
        / "codex.exe"
    )
    copy_cli_bundle(source, configured)
    (codex_home / "config.toml").write_text(
        f"[mcp_servers.node_repl]\ncommand='node'\n"
        f"[mcp_servers.node_repl.env]\nCODEX_CLI_PATH='{configured}'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    report = windows_update.inspect_windows_update(
        config,
        execute_cli=False,
        include_resources=False,
        app_info=app,
    )

    assert report.configured_cli.sha256 == report.source_cli.sha256
    assert report.status == windows_update.STATUS_REPAIR_REQUIRED
    assert report.launch_safe is False
    assert "Configured CODEX_CLI_PATH uses an older managed version directory." in report.errors
    assert windows_update.auto_repair_eligible(report) is True


def test_inspect_blocks_launch_when_newer_appx_is_staged(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, source = app_fixture(tmp_path, version="26.721.3996.0")
    add_plugin_cache(codex_home)
    configured = tmp_path / "OpenAI" / "Codex" / "bin" / "hash" / "codex.exe"
    copy_cli_bundle(source, configured)
    (codex_home / "config.toml").write_text(
        f"[mcp_servers.node_repl]\ncommand='node'\n[mcp_servers.node_repl.env]\nCODEX_CLI_PATH='{configured}'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    report = windows_update.inspect_windows_update(
        config,
        execute_cli=False,
        include_resources=False,
        app_info=app,
        all_user_packages=[
            {
                "Version": "26.721.4979.0",
                "UserInstallStates": [{"user": "S-1-5-18", "state": "Staged"}],
            }
        ],
    )

    assert report.status == windows_update.STATUS_MANUAL_ACTION
    assert report.launch_safe is False
    assert report.highest_staged_version == "26.721.4979.0"
    assert report.pending_registration is True
    assert any("Complete the Codex update registration" in error for error in report.errors)


def test_official_cua_runtime_without_codex_cli_path_requires_repair(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, _source = app_fixture(tmp_path)
    add_plugin_cache(codex_home)
    runtime = add_official_runtime(tmp_path, codex_home)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("CODEX_CLI_PATH", raising=False)

    report = windows_update.inspect_windows_update(
        config,
        execute_cli=False,
        include_resources=False,
        app_info=app,
    )

    assert runtime.is_file()
    assert report.status == windows_update.STATUS_REPAIR_REQUIRED
    assert report.launch_safe is False
    assert report.node_repl_mode == "official-cua-runtime-missing-cli"
    assert report.node_repl_runtime_exists is True
    assert report.browser_runtime_version == "26.715.9000"
    assert report.configured_cli.exists is False
    assert any("cannot start codex app-server" in error for error in report.errors)


def test_missing_official_runtime_and_cli_path_still_requires_repair(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, _source = app_fixture(tmp_path)
    (codex_home / "config.toml").write_text(
        "[mcp_servers.node_repl]\ncommand = 'missing-node-repl.exe'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("CODEX_CLI_PATH", raising=False)

    report = windows_update.inspect_windows_update(
        config,
        execute_cli=False,
        include_resources=False,
        app_info=app,
    )

    assert report.status == windows_update.STATUS_REPAIR_REQUIRED
    assert report.launch_safe is False
    assert report.node_repl_mode == "incomplete"


def test_configured_cli_missing_companion_programs_requires_repair(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, source = app_fixture(tmp_path)
    add_plugin_cache(codex_home)
    configured = tmp_path / "managed" / "codex.exe"
    configured.parent.mkdir(parents=True)
    configured.write_bytes(source.read_bytes())
    (codex_home / "config.toml").write_text(
        "[mcp_servers.node_repl]\ncommand='node'\n"
        f"[mcp_servers.node_repl.env]\nCODEX_CLI_PATH='{configured}'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    report = windows_update.inspect_windows_update(
        config,
        execute_cli=False,
        include_resources=False,
        app_info=app,
    )

    assert report.status == windows_update.STATUS_REPAIR_REQUIRED
    assert report.launch_safe is False
    assert set(report.configured_cli.missing_bundle_files) == set(
        windows_update.MANAGED_CLI_COMPANION_FILES
    )
    assert any("missing companion programs" in error for error in report.errors)


def test_repair_dry_run_for_official_cua_runtime_preserves_config(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app, _source = app_fixture(tmp_path)
    add_official_runtime(tmp_path, codex_home)
    before = (codex_home / "config.toml").read_bytes()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("CODEX_CLI_PATH", raising=False)
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)

    assert windows_update.run_windows_update_repair(str(config_path), apply=False) == 0
    assert (codex_home / "config.toml").read_bytes() == before
    assert not list(codex_home.glob("config.toml.bak-codex-update-*"))


def test_plugin_mismatch_and_staging_are_reported_without_rewriting_cache(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    config = load_config(str(config_path))
    app, source = app_fixture(tmp_path)
    add_plugin_cache(codex_home, version="26.715.1000")
    configured = tmp_path / "OpenAI" / "Codex" / "bin" / "hash" / "codex.exe"
    copy_cli_bundle(source, configured)
    (codex_home / "config.toml").write_text(
        f"[mcp_servers.node_repl]\ncommand='node'\n[mcp_servers.node_repl.env]\nCODEX_CLI_PATH = '{configured}'\n",
        encoding="utf-8",
    )
    staging = codex_home / "plugins" / "cache" / ".staging-test"
    staging.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    report = windows_update.inspect_windows_update(config, execute_cli=False, include_resources=False, app_info=app)

    assert report.launch_safe is True
    assert report.staging_count == 1
    assert any("browser cache version" in warning for warning in report.warnings)
    assert staging.exists()


def test_guarded_repair_updates_only_cli_key_and_preserves_bom(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app, source = app_fixture(tmp_path)
    configured = tmp_path / "OpenAI" / "Codex" / "bin" / "old" / "codex.exe"
    configured.parent.mkdir(parents=True)
    configured.write_bytes(b"old-cli")
    config_toml = codex_home / "config.toml"
    text = (
        "model_provider = \"custom\"\r\n"
        "[mcp_servers.node_repl]\r\ncommand = \"node\"\r\n"
        "[mcp_servers.node_repl.env]\r\n"
        f"CODEX_CLI_PATH = '{configured}'\r\n"
        "[plugins.\"browser@openai-bundled\"]\r\nenabled = true\r\n"
    )
    config_toml.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    user_environment: dict[str, str | None] = {"CODEX_CLI_PATH": None}
    monkeypatch.setattr(
        windows_update,
        "user_environment_value",
        lambda name: user_environment.get(name),
    )
    monkeypatch.setattr(
        windows_update,
        "set_user_environment_value",
        lambda name, value: user_environment.__setitem__(name, value),
    )

    def fake_probe(path, kind, *, execute=True, required_siblings=()):
        path = Path(path) if path else None
        if not path or not path.is_file():
            return windows_update.CliProbe(
                kind,
                False,
                False,
                bundle_complete=not required_siblings,
                missing_bundle_files=list(required_siblings),
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        missing = [name for name in required_siblings if not (path.parent / name).is_file()]
        return windows_update.CliProbe(
            kind,
            True,
            not missing,
            "codex-cli test",
            digest,
            path.stat().st_size,
            bundle_complete=not missing,
            missing_bundle_files=missing,
        )

    monkeypatch.setattr(windows_update, "probe_cli", fake_probe)

    assert windows_update.run_windows_update_repair(str(config_path), apply=True, confirm=lambda _prompt: "REPAIR") == 0

    updated = config_toml.read_bytes()
    assert updated.startswith(b"\xef\xbb\xbf")
    decoded = updated.decode("utf-8-sig")
    assert '[plugins."browser@openai-bundled"]' in decoded
    value, _ = windows_update.find_toml_section_key(decoded, "[mcp_servers.node_repl.env]", "CODEX_CLI_PATH")
    assert value and "CodexHybridModelSwitcher" in value
    managed = windows_update.managed_cli_path(app)
    assert managed is not None
    assert windows_update.cli_bundle_hashes(managed) == windows_update.cli_bundle_hashes(source)
    assert all((managed.parent / name).is_file() for name in windows_update.MANAGED_CLI_BUNDLE_FILES)
    assert user_environment["CODEX_CLI_PATH"] == str(managed)
    assert (codex_home / "auth.json").read_text(encoding="utf-8") == "auth.json"
    assert list(codex_home.glob("config.toml.bak-codex-update-*"))


def test_guarded_repair_uses_user_environment_when_config_key_is_absent(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app, source = app_fixture(tmp_path)
    add_official_runtime(tmp_path, codex_home)
    before_config = (codex_home / "config.toml").read_bytes()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    user_environment: dict[str, str | None] = {"CODEX_CLI_PATH": None}
    monkeypatch.setattr(
        windows_update,
        "user_environment_value",
        lambda name: user_environment.get(name),
    )
    monkeypatch.setattr(
        windows_update,
        "set_user_environment_value",
        lambda name, value: user_environment.__setitem__(name, value),
    )

    def fake_probe(path, kind, *, execute=True, required_siblings=()):
        path = Path(path) if path else None
        if not path or not path.is_file():
            return windows_update.CliProbe(
                kind,
                False,
                False,
                bundle_complete=not required_siblings,
                missing_bundle_files=list(required_siblings),
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        missing = [name for name in required_siblings if not (path.parent / name).is_file()]
        return windows_update.CliProbe(
            kind,
            True,
            not missing,
            "codex-cli test",
            digest,
            path.stat().st_size,
            bundle_complete=not missing,
            missing_bundle_files=missing,
        )

    monkeypatch.setattr(windows_update, "probe_cli", fake_probe)

    assert windows_update.run_windows_update_repair(
        str(config_path),
        apply=True,
        confirm=lambda _prompt: "REPAIR",
    ) == 0

    managed = windows_update.managed_cli_path(app)
    assert managed is not None
    assert user_environment["CODEX_CLI_PATH"] == str(managed)
    assert windows_update.cli_bundle_hashes(managed) == windows_update.cli_bundle_hashes(source)
    assert (codex_home / "config.toml").read_bytes() == before_config
    assert not list(codex_home.glob("config.toml.bak-codex-update-*"))


def test_replace_with_permission_retry_handles_transient_windows_scanner_lock(tmp_path, monkeypatch):
    source = tmp_path / "staging"
    destination = tmp_path / "installed"
    source.mkdir()
    (source / "codex.exe").write_bytes(b"cli")
    real_replace = windows_update.os.replace
    calls = 0
    sleeps: list[float] = []

    def flaky_replace(left, right):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise PermissionError("scanner still holds the staged directory")
        return real_replace(left, right)

    monkeypatch.setattr(windows_update.os, "replace", flaky_replace)
    monkeypatch.setattr(windows_update.time, "sleep", sleeps.append)

    windows_update._replace_with_permission_retry(source, destination)

    assert calls == 3
    assert sleeps == [0.25, 0.25]
    assert (destination / "codex.exe").read_bytes() == b"cli"


def test_cli_bundle_is_only_executed_after_staging_directory_swap(tmp_path, monkeypatch):
    _app, source = app_fixture(tmp_path)
    destination = tmp_path / "managed" / "26.818.5345.0" / "codex.exe"
    source_hashes = windows_update.cli_bundle_hashes(source)
    assert source_hashes is not None
    probes: list[tuple[Path, bool]] = []

    def fake_probe(path, kind, *, execute=True, required_siblings=()):
        path = Path(path)
        probes.append((path, execute))
        missing = [name for name in required_siblings if not (path.parent / name).is_file()]
        return windows_update.CliProbe(
            kind=kind,
            exists=path.is_file(),
            runnable=path.is_file() and not missing,
            version="codex-cli test" if execute else "",
            size=path.stat().st_size if path.is_file() else 0,
            bundle_complete=not missing,
            missing_bundle_files=missing,
        )

    monkeypatch.setattr(windows_update, "probe_cli", fake_probe)

    installed, staging, previous = windows_update._install_cli_bundle_atomically(
        source,
        destination,
        source_hashes,
    )

    assert installed is True
    assert staging is None
    assert previous is None
    assert probes[0][1] is False
    assert probes[0][0].parent.name.startswith(".staging-")
    assert probes[1] == (destination, True)
    assert windows_update.cli_bundle_hashes(destination) == source_hashes


def test_cli_bundle_swap_restores_previous_directory_when_staging_rename_fails(tmp_path, monkeypatch):
    _app, source = app_fixture(tmp_path)
    destination = tmp_path / "managed" / "26.818.5345.0" / "codex.exe"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"previous-cli")
    for name in windows_update.MANAGED_CLI_COMPANION_FILES:
        (destination.parent / name).write_bytes(("previous-" + name).encode("utf-8"))
    previous_hashes = windows_update.cli_bundle_hashes(destination)
    source_hashes = windows_update.cli_bundle_hashes(source)
    assert previous_hashes is not None
    assert source_hashes is not None
    real_replace = windows_update.os.replace

    def fail_staging_swap(left, right):
        left_path = Path(left)
        if left_path.name.startswith(".staging-"):
            raise PermissionError("persistent scanner lock")
        return real_replace(left, right)

    monkeypatch.setattr(windows_update.os, "replace", fail_staging_swap)
    monkeypatch.setattr(windows_update.time, "sleep", lambda _seconds: None)

    try:
        windows_update._install_cli_bundle_atomically(source, destination, source_hashes)
    except PermissionError:
        pass
    else:
        raise AssertionError("the simulated staging swap should fail")

    assert windows_update.cli_bundle_hashes(destination) == previous_hashes
    assert not list(destination.parent.parent.glob(".previous-*-codex-cli"))


def test_restore_config_from_text_reports_verified_success_and_write_failure(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    path.write_text("old\n", encoding="utf-8")

    assert windows_update._restore_config_from_text(path, "model_provider = 'custom'\n", False) is True
    assert path.read_text(encoding="utf-8") == "model_provider = 'custom'\n"

    monkeypatch.setattr(
        windows_update,
        "write_utf8_text_atomic",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("locked")),
    )
    assert windows_update._restore_config_from_text(path, "replacement\n", False) is False


def automatic_report(*, healthy: bool, error: str = "") -> windows_update.WindowsUpdateReport:
    source = windows_update.CliProbe(
        "appx-source",
        exists=True,
        runnable=False,
        sha256="source-hash",
        size=123,
        bundle_complete=True,
    )
    return windows_update.WindowsUpdateReport(
        status=windows_update.STATUS_HEALTHY if healthy else windows_update.STATUS_REPAIR_REQUIRED,
        launch_safe=healthy,
        app_version="26.715.10079.0",
        node_repl_registered=True,
        source_cli=source,
        errors=[] if healthy else [error],
    )


def test_update_ensure_is_zero_write_when_launch_is_already_safe(tmp_path, monkeypatch):
    config_path, _codex_home = write_config(tmp_path)
    report = automatic_report(healthy=True)
    monkeypatch.setattr(windows_update, "inspect_windows_update", lambda *_args, **_kwargs: report)
    monkeypatch.setattr(
        windows_update,
        "run_windows_update_repair",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("repair should not run")),
    )

    assert windows_update.run_windows_update_ensure(str(config_path)) == 0


def test_update_ensure_repairs_only_supported_cli_version_drift(tmp_path, monkeypatch):
    config_path, _codex_home = write_config(tmp_path)
    stale = automatic_report(
        healthy=False,
        error="Configured CODEX_CLI_PATH does not match the current Codex app CLI.",
    )
    healthy = automatic_report(healthy=True)
    reports = iter((stale, healthy))
    monkeypatch.setattr(windows_update, "inspect_windows_update", lambda *_args, **_kwargs: next(reports))
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: False)
    observed: dict[str, object] = {}

    def fake_repair(path, *, apply=False, confirm=input):
        observed.update(path=path, apply=apply, confirmation=confirm("prompt"))
        return 0

    monkeypatch.setattr(windows_update, "run_windows_update_repair", fake_repair)

    assert windows_update.run_windows_update_ensure(str(config_path)) == 0
    assert observed == {
        "path": str(config_path),
        "apply": True,
        "confirmation": "REPAIR",
    }


def test_update_ensure_stops_for_unsupported_update_failures(tmp_path, monkeypatch):
    config_path, _codex_home = write_config(tmp_path)
    report = automatic_report(healthy=False, error="Unexpected Browser configuration failure.")
    monkeypatch.setattr(windows_update, "inspect_windows_update", lambda *_args, **_kwargs: report)
    monkeypatch.setattr(
        windows_update,
        "run_windows_update_repair",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("repair should not run")),
    )

    assert windows_update.run_windows_update_ensure(str(config_path)) == 20


def test_update_ensure_stops_before_repair_for_pending_appx_registration(tmp_path, monkeypatch):
    config_path, _codex_home = write_config(tmp_path)
    report = automatic_report(healthy=False)
    report.status = windows_update.STATUS_MANUAL_ACTION
    report.highest_staged_version = "26.721.4979.0"
    report.pending_registration = True
    monkeypatch.setattr(windows_update, "inspect_windows_update", lambda *_args, **_kwargs: report)
    monkeypatch.setattr(
        windows_update,
        "run_windows_update_repair",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("repair should not run")),
    )

    assert windows_update.run_windows_update_ensure(str(config_path)) == 20


def test_update_ensure_stops_when_codex_is_running(tmp_path, monkeypatch):
    config_path, _codex_home = write_config(tmp_path)
    report = automatic_report(
        healthy=False,
        error="Configured CODEX_CLI_PATH does not match the current Codex app CLI.",
    )
    monkeypatch.setattr(windows_update, "inspect_windows_update", lambda *_args, **_kwargs: report)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: True)

    assert windows_update.run_windows_update_ensure(str(config_path)) == 20


def test_browser_ensure_is_zero_write_when_browser_is_already_healthy(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app, _source = app_fixture(tmp_path)
    cli_path = tmp_path / "managed" / "codex.exe"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_bytes(b"cli")
    (codex_home / "config.toml").write_text(
        '[plugins."browser@openai-bundled"]\nenabled = true\n',
        encoding="utf-8",
    )
    before = {name: (codex_home / name).read_bytes() for name in ("auth.json", "models_cache.json", "state_5.sqlite")}
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)
    monkeypatch.setattr(windows_update, "current_codex_cli_for_plugins", lambda *_args: cli_path)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: True)
    monkeypatch.setattr(
        windows_update,
        "query_codex_plugin_catalog",
        lambda _path: ({windows_update.BROWSER_PLUGIN_ID: cli_plugin_state(installed=True, enabled=True)}, None),
    )
    monkeypatch.setattr(windows_update, "_browser_config_ready", lambda *_args: True)
    monkeypatch.setattr(
        windows_update,
        "_run_codex_plugin_command",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("plugin add should not run")),
    )

    assert windows_update.run_windows_browser_ensure(
        str(config_path),
        wait_seconds=0,
        settle_seconds=0,
        poll_seconds=0.1,
        verify_seconds=0,
    ) == 0
    assert {name: (codex_home / name).read_bytes() for name in before} == before
    assert not (config_path.parent / ".windows-browser-post-start.lock").exists()


def test_browser_ensure_defers_reserved_marketplace_to_desktop(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app, _source = app_fixture(tmp_path)
    cli_path = tmp_path / "managed" / "codex.exe"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_bytes(b"cli")
    (codex_home / "config.toml").write_text(
        '[plugins."browser@openai-bundled"]\nenabled = true\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)
    monkeypatch.setattr(windows_update, "current_codex_cli_for_plugins", lambda *_args: cli_path)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: True)
    monkeypatch.setattr(windows_update, "bundled_marketplace_is_app_managed", lambda _cli: True)
    monkeypatch.setattr(windows_update, "_browser_config_ready", lambda *_args: False)
    monkeypatch.setattr(
        windows_update,
        "query_codex_plugin_catalog",
        lambda *_args: (_ for _ in ()).throw(AssertionError("reserved marketplace must not be queried")),
    )
    monkeypatch.setattr(
        windows_update,
        "_run_codex_plugin_command",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("reserved marketplace must not be rewritten")),
    )

    assert windows_update.run_windows_browser_ensure(
        str(config_path),
        wait_seconds=0,
        settle_seconds=0,
        poll_seconds=0.1,
        verify_seconds=0,
    ) == 0
    assert not (config_path.parent / ".windows-browser-post-start.lock").exists()


def test_browser_ensure_installs_only_after_plugin_becomes_available(tmp_path, monkeypatch):
    config_path, codex_home = write_config(tmp_path)
    app, _source = app_fixture(tmp_path)
    cli_path = tmp_path / "managed" / "codex.exe"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_bytes(b"cli")
    (codex_home / "config.toml").write_text("model_provider = 'custom'\n", encoding="utf-8")
    before = {name: (codex_home / name).read_bytes() for name in ("auth.json", "models_cache.json", "state_5.sqlite")}
    installed = {"value": False}
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)
    monkeypatch.setattr(windows_update, "current_codex_cli_for_plugins", lambda *_args: cli_path)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: True)

    def fake_catalog(_path):
        return (
            {
                windows_update.BROWSER_PLUGIN_ID: cli_plugin_state(
                    installed=installed["value"],
                    enabled=installed["value"],
                )
            },
            None,
        )

    def fake_command(_path, arguments, **_kwargs):
        assert arguments == ["add", windows_update.BROWSER_PLUGIN_ID, "--json"]
        installed["value"] = True
        return subprocess.CompletedProcess([str(_path), *arguments], 0, "{}", "")

    monkeypatch.setattr(windows_update, "query_codex_plugin_catalog", fake_catalog)
    monkeypatch.setattr(windows_update, "_run_codex_plugin_command", fake_command)
    monkeypatch.setattr(windows_update, "_browser_config_ready", lambda *_args: installed["value"])

    assert windows_update.run_windows_browser_ensure(
        str(config_path),
        wait_seconds=0,
        settle_seconds=0,
        poll_seconds=0.1,
        verify_seconds=0,
    ) == 0
    assert installed["value"] is True
    assert {name: (codex_home / name).read_bytes() for name in before} == before


def test_browser_ensure_does_not_install_before_feature_gate_is_available(tmp_path, monkeypatch):
    config_path, _codex_home = write_config(tmp_path)
    app, _source = app_fixture(tmp_path)
    cli_path = tmp_path / "managed" / "codex.exe"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_bytes(b"cli")
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(windows_update, "windows_codex_app_info", lambda: app)
    monkeypatch.setattr(windows_update, "current_codex_cli_for_plugins", lambda *_args: cli_path)
    monkeypatch.setattr(windows_update, "codex_is_running", lambda: True)
    monkeypatch.setattr(windows_update, "query_codex_plugin_catalog", lambda _path: ({}, None))
    monkeypatch.setattr(
        windows_update,
        "_run_codex_plugin_command",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("plugin add should not run")),
    )

    assert windows_update.run_windows_browser_ensure(
        str(config_path),
        wait_seconds=0,
        settle_seconds=0,
        poll_seconds=0.1,
        verify_seconds=0,
    ) == 20


def test_browser_ensure_deduplicates_concurrent_launcher_checks(tmp_path, monkeypatch):
    config_path, _codex_home = write_config(tmp_path)
    lock = config_path.parent / ".windows-browser-post-start.lock"
    lock.write_text("active", encoding="utf-8")
    monkeypatch.setattr(windows_update, "is_windows", lambda: True)
    monkeypatch.setattr(
        windows_update,
        "windows_codex_app_info",
        lambda: (_ for _ in ()).throw(AssertionError("duplicate should exit before probing")),
    )

    assert windows_update.run_windows_browser_ensure(str(config_path)) == 0
    assert lock.exists()
