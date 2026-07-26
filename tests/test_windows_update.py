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
