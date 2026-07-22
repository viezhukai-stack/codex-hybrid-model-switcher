from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from codex_hybrid_switcher import account_switch


def write_account_fixture(tmp_path: Path) -> tuple[Path, Path]:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    for name, content in (
        ("auth.json", "old-auth"),
        ("config.toml", "[mcp_servers.node_repl]\n[mcp_servers.node_repl.env]\nCODEX_CLI_PATH='cli'\n"),
        ("models_cache.json", "models"),
        ("state_5.sqlite", "state"),
    ):
        (codex_home / name).write_text(content, encoding="utf-8")
    sessions = codex_home / "sessions"
    sessions.mkdir()
    (sessions / "task.jsonl").write_text("task", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "codex_home": str(codex_home),
                "account_switch": {"proxy_url": "http://127.0.0.1:7897"},
                "providers": [{"id": "official", "kind": "official"}],
            }
        ),
        encoding="utf-8",
    )
    return config_path, codex_home


def patch_account_environment(monkeypatch, tmp_path: Path, cli: Path) -> None:
    monkeypatch.setattr(account_switch, "is_windows", lambda: True)
    monkeypatch.setattr(account_switch, "codex_is_running", lambda: False)
    monkeypatch.setattr(account_switch, "current_codex_cli", lambda _config: cli)
    monkeypatch.setattr(account_switch, "_login_is_active", lambda _cli: True)
    monkeypatch.setattr(account_switch, "_restrict_backup_acl", lambda _path: None)
    monkeypatch.setattr(account_switch, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        account_switch,
        "inspect_windows_update",
        lambda _config, include_resources=False: SimpleNamespace(status="healthy", launch_safe=True),
    )


def test_change_account_default_is_zero_write_dry_run(tmp_path, monkeypatch, capsys):
    config_path, codex_home = write_account_fixture(tmp_path)
    cli = tmp_path / "codex.exe"
    cli.write_text("cli", encoding="utf-8")
    patch_account_environment(monkeypatch, tmp_path, cli)
    before = {path.name: path.read_bytes() for path in codex_home.iterdir() if path.is_file()}

    assert account_switch.run_change_account(str(config_path)) == 0

    after = {path.name: path.read_bytes() for path in codex_home.iterdir() if path.is_file()}
    assert before == after
    assert "DRY-RUN COMPLETE" in capsys.readouterr().out
    assert not account_switch.pending_transaction_path().exists()


def test_change_account_cancel_does_not_create_backup(tmp_path, monkeypatch):
    config_path, codex_home = write_account_fixture(tmp_path)
    cli = tmp_path / "codex.exe"
    cli.write_text("cli", encoding="utf-8")
    patch_account_environment(monkeypatch, tmp_path, cli)

    assert account_switch.run_change_account(str(config_path), apply=True, confirm=lambda _prompt: "CANCEL") == 3
    assert not (codex_home / "backups").exists()
    assert (codex_home / "auth.json").read_text(encoding="utf-8") == "old-auth"


def test_change_account_success_keeps_non_auth_state_and_completes_transaction(tmp_path, monkeypatch):
    config_path, codex_home = write_account_fixture(tmp_path)
    cli = tmp_path / "codex.exe"
    cli.write_text("cli", encoding="utf-8")
    patch_account_environment(monkeypatch, tmp_path, cli)

    def fake_cli(_cli, *args):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="Logged in using ChatGPT")

    monkeypatch.setattr(account_switch, "_run_cli_capture", fake_cli)
    monkeypatch.setattr(account_switch, "_run_device_login", lambda _cli, _proxy: 0)
    before = account_switch.account_state_hashes(account_switch.load_config(str(config_path)))

    assert account_switch.run_change_account(str(config_path), apply=True, confirm=lambda _prompt: "SWITCH") == 0

    after = account_switch.account_state_hashes(account_switch.load_config(str(config_path)))
    assert before == after
    assert (codex_home / "auth.json").read_text(encoding="utf-8") == "old-auth"
    backups = list((codex_home / "backups").glob("account-switch-*"))
    assert len(backups) == 1
    manifest = json.loads((backups[0] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "complete"
    assert not account_switch.pending_transaction_path().exists()


def test_failed_device_login_restores_previous_auth(tmp_path, monkeypatch):
    config_path, codex_home = write_account_fixture(tmp_path)
    cli = tmp_path / "codex.exe"
    cli.write_text("cli", encoding="utf-8")
    patch_account_environment(monkeypatch, tmp_path, cli)

    def fake_cli(_cli, *args):
        if args == ("logout",):
            (codex_home / "auth.json").unlink()
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="")

    monkeypatch.setattr(account_switch, "_run_cli_capture", fake_cli)
    monkeypatch.setattr(account_switch, "_run_device_login", lambda _cli, _proxy: 1)

    assert account_switch.run_change_account(str(config_path), apply=True, confirm=lambda _prompt: "SWITCH") == 20
    assert (codex_home / "auth.json").read_text(encoding="utf-8") == "old-auth"
    assert not account_switch.pending_transaction_path().exists()
    manifest_path = next((codex_home / "backups").glob("account-switch-*/manifest.json"))
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["state"] == "rolled_back"


def test_account_backup_restricts_parent_before_copying_children(tmp_path, monkeypatch):
    config_path, codex_home = write_account_fixture(tmp_path)
    config = account_switch.load_config(str(config_path))
    observed = []

    def record_acl(path):
        observed.append((path, list(path.iterdir())))

    monkeypatch.setattr(account_switch, "_restrict_backup_acl", record_acl)

    backup = account_switch._copy_account_backup(config)

    assert observed == [(backup, [])]
    assert (backup / "auth.json").read_text(encoding="utf-8") == "old-auth"


def test_restore_auth_repairs_backup_acl_after_permission_error(tmp_path, monkeypatch):
    config_path, codex_home = write_account_fixture(tmp_path)
    config = account_switch.load_config(str(config_path))
    backup = codex_home / "backups" / "account-switch-test"
    backup.mkdir(parents=True)
    (backup / "auth.json").write_text("backup-auth", encoding="utf-8")
    (codex_home / "auth.json").unlink()
    real_copy2 = account_switch.shutil.copy2
    calls = {"copy": 0, "repair": 0}

    def flaky_copy(source, target):
        calls["copy"] += 1
        if calls["copy"] == 1:
            raise PermissionError("simulated ACL regression")
        return real_copy2(source, target)

    monkeypatch.setattr(account_switch.shutil, "copy2", flaky_copy)
    monkeypatch.setattr(
        account_switch,
        "_repair_backup_acl",
        lambda _path: calls.__setitem__("repair", calls["repair"] + 1),
    )

    assert account_switch._restore_auth(config, backup) is True
    assert calls == {"copy": 2, "repair": 1}
    assert (codex_home / "auth.json").read_text(encoding="utf-8") == "backup-auth"


def test_recover_last_restores_interrupted_account_transaction(tmp_path, monkeypatch):
    config_path, codex_home = write_account_fixture(tmp_path)
    cli = tmp_path / "codex.exe"
    cli.write_text("cli", encoding="utf-8")
    patch_account_environment(monkeypatch, tmp_path, cli)
    backup = codex_home / "backups" / "account-switch-test"
    backup.mkdir(parents=True)
    (backup / "auth.json").write_text("backup-auth", encoding="utf-8")
    (codex_home / "auth.json").unlink()
    transaction = {"state": "logged_out", "backup": str(backup)}
    account_switch._write_json_atomic(account_switch.pending_transaction_path(), transaction)

    assert account_switch.run_change_account(str(config_path), recover_last=True) == 0
    assert (codex_home / "auth.json").read_text(encoding="utf-8") == "backup-auth"
    assert not account_switch.pending_transaction_path().exists()
