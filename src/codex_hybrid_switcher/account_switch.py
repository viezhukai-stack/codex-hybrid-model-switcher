from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

from .config import AppConfig, load_config
from .switcher import codex_is_running, file_hash
from .windows_update import (
    classify_cli_path,
    find_toml_section_key,
    inspect_windows_update,
    is_windows,
    managed_cli_path,
    probe_cli,
    read_utf8_text_preserving_bom,
    source_cli_path,
    user_environment_value,
    windows_codex_app_info,
)


ACCOUNT_BACKUP_FILES = (
    "auth.json",
    "config.toml",
    "models_cache.json",
    "state_5.sqlite",
    "state_5.sqlite-wal",
    "state_5.sqlite-shm",
)
ACCOUNT_BACKUP_DIRS = ("sessions", "archived_sessions")
NON_AUTH_FILES = ("config.toml", "models_cache.json", "state_5.sqlite")


def runtime_root() -> Path:
    return Path.home() / ".codex-hybrid-model-switcher"


def pending_transaction_path() -> Path:
    return runtime_root() / "account-switch-pending.json"


def hash_tree(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    try:
        files = sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: str(item.relative_to(path)))
        for item in files:
            relative = str(item.relative_to(path)).replace(os.sep, "/")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            with item.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def account_state_hashes(config: AppConfig) -> dict[str, str | None]:
    result = {name: file_hash(config.codex_home / name) for name in NON_AUTH_FILES}
    for name in ACCOUNT_BACKUP_DIRS:
        result[name] = hash_tree(config.codex_home / name)
    return result


def _copy_account_backup(config: AppConfig) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = config.codex_home / "backups" / f"account-switch-{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    # Restrict the parent before creating children so every copied file inherits
    # a usable ACL. Restricting recursively only after copy can strip inherited
    # ACEs from the children before the replacement grants reach them.
    _restrict_backup_acl(backup)
    for name in ACCOUNT_BACKUP_FILES:
        source = config.codex_home / name
        if source.exists():
            shutil.copy2(source, backup / name)
    for name in ACCOUNT_BACKUP_DIRS:
        source = config.codex_home / name
        if source.is_dir():
            shutil.copytree(source, backup / name, copy_function=shutil.copy2)
    for name in ACCOUNT_BACKUP_FILES:
        source = config.codex_home / name
        copied = backup / name
        if source.is_file() and file_hash(source) != file_hash(copied):
            raise OSError(f"account backup verification failed for {name}")
    return backup


def _restrict_backup_acl(path: Path) -> None:
    if is_windows():
        username = os.environ.get("USERNAME") or ""
        if not username:
            raise OSError("USERNAME is unavailable for backup ACL setup")
        identity = f"{os.environ.get('COMPUTERNAME')}\\{username}" if os.environ.get("COMPUTERNAME") else username
        proc = subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"{identity}:(OI)(CI)F",
                "SYSTEM:(OI)(CI)F",
                "/C",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if proc.returncode != 0:
            raise OSError("backup ACL setup failed")
    else:
        try:
            path.chmod(0o700)
        except OSError:
            pass


def _repair_backup_acl(path: Path) -> None:
    _restrict_backup_acl(path)
    if not is_windows():
        return
    proc = subprocess.run(
        [
            "icacls",
            str(path / "*"),
            "/inheritance:e",
            "/T",
            "/C",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if proc.returncode != 0:
        raise OSError("backup child ACL recovery failed")


def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _load_pending() -> dict | None:
    path = pending_transaction_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _restore_auth(config: AppConfig, backup: Path) -> bool:
    source = backup / "auth.json"
    target = config.codex_home / "auth.json"
    if not source.is_file():
        return False
    temp = target.with_name(f"{target.name}.tmp-account-restore-{os.getpid()}")
    try:
        shutil.copy2(source, temp)
    except PermissionError:
        _repair_backup_acl(backup)
        shutil.copy2(source, temp)
    os.replace(temp, target)
    return file_hash(source) == file_hash(target)


def _mark_transaction(manifest: Path, transaction: dict, state: str, **extra: object) -> None:
    transaction["state"] = state
    transaction["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    transaction.update(extra)
    _write_json_atomic(manifest, transaction)


def _configured_cli_path(config: AppConfig) -> Path | None:
    config_path = config.codex_home / "config.toml"
    try:
        text, _ = read_utf8_text_preserving_bom(config_path)
    except OSError:
        return None
    value, _ = find_toml_section_key(text, "[mcp_servers.node_repl.env]", "CODEX_CLI_PATH")
    return Path(value) if value else None


def current_codex_cli(config: AppConfig) -> Path | None:
    app = windows_codex_app_info()
    source = source_cli_path(app)
    source_probe = probe_cli(source, "appx-source", execute=False)
    configured = _configured_cli_path(config)
    candidates: list[Path] = []
    if configured:
        candidates.append(configured)
    environment_cli = user_environment_value("CODEX_CLI_PATH")
    if environment_cli:
        candidates.append(Path(environment_cli))
    managed = managed_cli_path(app)
    if managed:
        candidates.append(managed)
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    bin_root = local / "OpenAI" / "Codex" / "bin"
    if bin_root.is_dir():
        candidates.extend(
            sorted(
                bin_root.glob("*/codex.exe"),
                key=lambda path: path.stat().st_mtime if path.exists() else 0,
                reverse=True,
            )
        )
    if source:
        candidates.append(source)
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        probe = probe_cli(candidate, classify_cli_path(candidate), execute=True)
        if not probe.runnable:
            continue
        if source_probe.sha256 and probe.sha256 != source_probe.sha256:
            continue
        return candidate
    return None


def _run_cli_capture(cli: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(cli), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _login_is_active(cli: Path) -> bool:
    try:
        proc = _run_cli_capture(cli, "login", "status")
    except OSError:
        return False
    return proc.returncode == 0 and "logged in" in proc.stdout.lower()


def _effective_proxy(config: AppConfig, override: str | None) -> str | None:
    if override:
        return override
    value = config.raw.get("account_switch") or {}
    if isinstance(value, dict) and value.get("proxy_url"):
        return str(value["proxy_url"])
    return None


def _run_device_login(cli: Path, proxy_url: str | None) -> int:
    old = {name: os.environ.get(name) for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")}
    if proxy_url:
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["ALL_PROXY"] = proxy_url
        os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    try:
        return subprocess.run([str(cli), "login", "--device-auth"], check=False).returncode
    finally:
        for name, value in old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _rollback_account(config: AppConfig, backup: Path, manifest: Path, transaction: dict, reason: str) -> bool:
    restored = _restore_auth(config, backup)
    _mark_transaction(manifest, transaction, "rolled_back", reason=reason, auth_restored=restored)
    pending_transaction_path().unlink(missing_ok=True)
    return restored


def run_change_account(
    config_path: str | None = None,
    *,
    apply: bool = False,
    recover_last: bool = False,
    proxy_url: str | None = None,
    confirm: Callable[[str], str] = input,
) -> int:
    config = load_config(config_path)
    if not is_windows():
        print("Codex account switching is available only on Windows in this release.")
        return 20
    if recover_last:
        if codex_is_running():
            print("Codex/ChatGPT is running. Quit it completely before account recovery.")
            return 20
        pending = _load_pending()
        if not pending:
            print("No interrupted account switch was found.")
            return 0
        backup = Path(str(pending.get("backup") or ""))
        manifest = backup / "manifest.json"
        if not backup.is_dir() or not _restore_auth(config, backup):
            print("The previous account backup could not be restored.")
            return 20
        pending["state"] = "recovered"
        pending["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        _write_json_atomic(manifest, pending)
        pending_transaction_path().unlink(missing_ok=True)
        print("Previous Codex account state was restored.")
        return 0

    report = inspect_windows_update(config, include_resources=False)
    cli = current_codex_cli(config)
    effective_proxy = _effective_proxy(config, proxy_url)
    pending = _load_pending()
    print("Codex account switch")
    print(f"update_check: {report.status}")
    print(f"cli: {'ready' if cli else 'missing'}")
    print(f"current_login: {'yes' if cli and _login_is_active(cli) else 'no'}")
    print(f"proxy: {'configured' if effective_proxy else 'system/default'}")
    print(f"hot_router_launcher: {'present' if (Path.home() / 'Desktop' / 'Start Codex Hot Router.cmd').exists() else 'missing'}")
    print(f"interrupted_transaction: {'yes' if pending else 'no'}")
    print("preserved: config.toml, models_cache.json, state_5.sqlite, sessions, plugins, MCP, projects")
    if pending:
        print("Run change-account --recover-last before starting another account switch.")
        return 20
    if not report.launch_safe or not cli:
        print("Run Windows Codex update repair before changing accounts.")
        return 20
    if not apply:
        print("DRY-RUN COMPLETE. The current account was not changed.")
        print("Run again with --apply and type SWITCH to start device-code login.")
        return 0
    if codex_is_running():
        print("Codex/ChatGPT is running. Quit it completely before changing accounts.")
        return 20
    if confirm("Type SWITCH to continue: ") != "SWITCH":
        print("Cancelled. The current account was not changed.")
        return 3

    before = account_state_hashes(config)
    try:
        backup = _copy_account_backup(config)
    except OSError as exc:
        print(f"Account backup preparation failed: {type(exc).__name__}. The current login was not changed.")
        return 20
    transaction = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "state": "prepared",
        "backup": str(backup),
        "non_auth_hashes": before,
        "auth_present": (config.codex_home / "auth.json").is_file(),
    }
    manifest = backup / "manifest.json"
    _write_json_atomic(manifest, transaction)
    _write_json_atomic(pending_transaction_path(), transaction)
    try:
        logout = _run_cli_capture(cli, "logout")
    except OSError as exc:
        _rollback_account(config, backup, manifest, transaction, f"logout_{type(exc).__name__}")
        print("Codex logout failed. The previous account state was restored.")
        return 20
    if logout.returncode != 0:
        _rollback_account(config, backup, manifest, transaction, f"logout_exit_{logout.returncode}")
        print("Codex logout failed. The previous account state was restored.")
        return 20
    _mark_transaction(manifest, transaction, "logged_out")
    _write_json_atomic(pending_transaction_path(), transaction)
    try:
        login_code = _run_device_login(cli, effective_proxy)
    except (OSError, KeyboardInterrupt) as exc:
        _rollback_account(config, backup, manifest, transaction, f"login_{type(exc).__name__}")
        print("Device login stopped. The previous account state was restored.")
        return 20
    if login_code != 0 or not _login_is_active(cli):
        restored = _rollback_account(config, backup, manifest, transaction, f"login_exit_{login_code}")
        print(
            "Device login did not complete. "
            + ("The previous account state was restored." if restored else "Use --recover-last to restore the previous account.")
        )
        return 20
    after = account_state_hashes(config)
    changed = [name for name in before if before[name] != after[name]]
    if changed:
        restored = _rollback_account(config, backup, manifest, transaction, "non_auth_state_changed")
        print("Non-account Codex state changed unexpectedly: " + ", ".join(changed))
        if restored:
            print("The previous account was restored. Other state remains available in the backup.")
        return 20
    _mark_transaction(manifest, transaction, "complete", non_auth_unchanged=True)
    pending_transaction_path().unlink(missing_ok=True)
    print(f"Account switch complete. Backup: {backup}")
    print("Projects, plugins, MCP, configuration, model cache, and sessions were unchanged.")
    return 0
