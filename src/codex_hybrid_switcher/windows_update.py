from __future__ import annotations

import codecs
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .config import AppConfig, load_config
from .switcher import codex_is_running, protected_hashes


STATUS_HEALTHY = "healthy"
STATUS_REPAIR_REQUIRED = "repair_required"
STATUS_MANUAL_ACTION = "manual_action"

AUTO_REPAIR_ERROR_PREFIXES = (
    "Browser runtime has no CODEX_CLI_PATH",
    "Configured CODEX_CLI_PATH is missing companion programs:",
    "Configured CODEX_CLI_PATH is missing or not runnable.",
    "Configured CODEX_CLI_PATH does not match the current Codex app CLI.",
    "Configured CODEX_CLI_PATH uses an older managed version directory.",
)

MANAGED_CLI_BUNDLE_FILES = (
    "codex.exe",
    "rg.exe",
    "codex-windows-sandbox-setup.exe",
    "codex-command-runner.exe",
    "codex-code-mode-host.exe",
)
MANAGED_CLI_COMPANION_FILES = MANAGED_CLI_BUNDLE_FILES[1:]
BROWSER_PLUGIN_ID = "browser@openai-bundled"
CHROME_PLUGIN_ID = "chrome@openai-bundled"
BUNDLED_MARKETPLACE_NAME = "openai-bundled"
CODEX_STORE_PRODUCT_ID = "9PLM9XGG6VKS"
BUNDLED_PLUGIN_IDS = (BROWSER_PLUGIN_ID, CHROME_PLUGIN_ID)
BROWSER_POST_START_LOCK_SECONDS = 300
DEFAULT_APPX_SETTLE_CHECKS = 3
DEFAULT_APPX_SETTLE_POLL_SECONDS = 5.0
DEFAULT_APPX_SETTLE_TIMEOUT_SECONDS = 120.0
DEFAULT_APPX_SETTLE_TOTAL_TIMEOUT_SECONDS = 180.0
DEFAULT_MAX_REGISTRATION_PASSES = 2


@dataclass
class CliProbe:
    kind: str
    exists: bool
    runnable: bool
    version: str = ""
    sha256: str = ""
    size: int = 0
    bundle_complete: bool = True
    missing_bundle_files: list[str] = field(default_factory=list)


@dataclass
class PluginProbe:
    name: str
    source_version: str = "missing"
    cache_version: str = "missing"
    version_matches: bool = False
    installed: bool = False
    install_source: str = "missing"


@dataclass
class CliPluginState:
    plugin_id: str
    found: bool = False
    installed: bool = False
    enabled: bool = False
    install_policy: str = "missing"
    version: str = "missing"
    bucket: str = "missing"

    @property
    def available(self) -> bool:
        return self.install_policy.upper() == "AVAILABLE"

    @property
    def healthy(self) -> bool:
        return self.found and self.installed and self.enabled and self.available


@dataclass
class WindowsUpdateReport:
    status: str
    launch_safe: bool
    app_version: str = "missing"
    app_family: str = "missing"
    highest_staged_version: str = "missing"
    pending_registration: bool = False
    node_repl_registered: bool = False
    node_repl_mode: str = "missing"
    node_repl_runtime_exists: bool = False
    browser_runtime_version: str = "missing"
    configured_cli: CliProbe = field(default_factory=lambda: CliProbe("missing", False, False))
    source_cli: CliProbe = field(default_factory=lambda: CliProbe("missing", False, False))
    managed_cli: CliProbe = field(default_factory=lambda: CliProbe("missing", False, False))
    browser: PluginProbe = field(default_factory=lambda: PluginProbe("browser"))
    chrome: PluginProbe = field(default_factory=lambda: PluginProbe("chrome"))
    staging_count: int = 0
    low_memory_events_24h: int = 0
    top_memory_processes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def redacted_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AppxUpdateSnapshot:
    app_info: dict[str, str] | None
    current_version: str = "missing"
    highest_staged_version: str = "missing"
    pending_registration: bool = False

    @property
    def stability_key(self) -> tuple[str, str, bool]:
        return (
            self.current_version,
            self.highest_staged_version,
            self.pending_registration,
        )


def is_windows() -> bool:
    return sys.platform == "win32" or os.name == "nt"


def _run_powershell(script: str, *, timeout: float = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def windows_codex_app_info() -> dict[str, str] | None:
    if not is_windows():
        return None
    script = (
        "$p=Get-AppxPackage OpenAI.Codex | Select-Object -First 1 "
        "Name,Version,PackageFamilyName,InstallLocation;"
        "if($p){$p|ConvertTo-Json -Compress}"
    )
    try:
        proc = _run_powershell(script)
        data = json.loads(proc.stdout.strip() or "null")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return {str(key): str(value) for key, value in data.items() if value is not None}


def windows_codex_all_user_packages() -> list[dict[str, Any]]:
    if not is_windows():
        return []
    script = (
        "$items=@(Get-AppxPackage -AllUsers -Name OpenAI.Codex -ErrorAction SilentlyContinue | ForEach-Object {"
        "$states=@($_.PackageUserInformation | ForEach-Object {"
        "[pscustomobject]@{user=[string]$_.UserSecurityId;state=[string]$_.InstallState}"
        "});"
        "[pscustomobject]@{Name=[string]$_.Name;Version=[string]$_.Version;"
        "PackageFullName=[string]$_.PackageFullName;PackageFamilyName=[string]$_.PackageFamilyName;"
        "InstallLocation=[string]$_.InstallLocation;Status=[string]$_.Status;UserInstallStates=$states}"
        "});"
        "$items|ConvertTo-Json -Compress -Depth 6"
    )
    try:
        proc = _run_powershell(script, timeout=30)
        data = json.loads(proc.stdout.strip() or "[]")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def windows_version_key(value: str | None) -> tuple[int, ...]:
    numbers = [int(part) for part in re.findall(r"\d+", value or "")]
    return tuple((numbers + [0, 0, 0, 0])[:4])


def package_is_staged(package: dict[str, Any]) -> bool:
    candidates: list[str] = [
        str(package.get("Status") or ""),
        str(package.get("InstallState") or ""),
    ]
    states = package.get("UserInstallStates") or package.get("PackageUserInformation")
    if isinstance(states, list):
        for state in states:
            if isinstance(state, dict):
                candidates.append(str(state.get("state") or state.get("InstallState") or ""))
            else:
                candidates.append(str(state))
    elif states is not None:
        candidates.append(str(states))
    return any("staged" in value.lower() for value in candidates)


def pending_codex_registration(
    app_info: dict[str, str],
    packages: list[dict[str, Any]] | None = None,
) -> tuple[str, bool]:
    packages = windows_codex_all_user_packages() if packages is None else packages
    staged_versions = [
        str(package.get("Version") or "")
        for package in packages
        if package_is_staged(package) and package.get("Version")
    ]
    if not staged_versions:
        return "missing", False
    highest = max(staged_versions, key=windows_version_key)
    current = str(app_info.get("Version") or "")
    return highest, windows_version_key(highest) > windows_version_key(current)


def codex_appx_update_snapshot() -> AppxUpdateSnapshot:
    """Read one current-user/staged Codex AppX update observation."""

    app = windows_codex_app_info()
    if not app:
        return AppxUpdateSnapshot(app_info=None)
    highest, pending = pending_codex_registration(app)
    return AppxUpdateSnapshot(
        app_info=app,
        current_version=str(app.get("Version") or "missing"),
        highest_staged_version=highest,
        pending_registration=pending,
    )


def wait_for_codex_appx_stability(
    *,
    consecutive_checks: int = DEFAULT_APPX_SETTLE_CHECKS,
    poll_seconds: float = DEFAULT_APPX_SETTLE_POLL_SECONDS,
    timeout_seconds: float = DEFAULT_APPX_SETTLE_TIMEOUT_SECONDS,
    probe: Callable[[], AppxUpdateSnapshot] | None = None,
    sleeper: Callable[[float], None] | None = None,
    clock: Callable[[], float] | None = None,
) -> AppxUpdateSnapshot | None:
    """Wait until the registered/staged AppX view is unchanged repeatedly.

    Microsoft Store can stage a second Codex build immediately after the first
    registration finishes.  A single snapshot therefore is not a safe launch
    gate.  This bounded helper requires the complete observation tuple to stay
    unchanged for ``consecutive_checks`` probes.  It never starts Codex and it
    does not modify Store, Codex, or user state.
    """

    checks_required = max(1, int(consecutive_checks))
    interval = max(0.0, float(poll_seconds))
    timeout = max(0.0, float(timeout_seconds))
    probe = probe or codex_appx_update_snapshot
    sleeper = sleeper or time.sleep
    clock = clock or time.monotonic
    deadline = clock() + timeout
    last_key: tuple[str, str, bool] | None = None
    stable_checks = 0

    while True:
        snapshot = probe()
        if snapshot.app_info is None:
            print("OpenAI.Codex AppX package disappeared while waiting for Store stability.")
            return None
        if snapshot.stability_key == last_key:
            stable_checks += 1
        else:
            last_key = snapshot.stability_key
            stable_checks = 1
        print(
            "Codex Store stability check "
            f"{stable_checks}/{checks_required}: current={snapshot.current_version} "
            f"staged={snapshot.highest_staged_version} "
            f"pending={'yes' if snapshot.pending_registration else 'no'}"
        )
        if stable_checks >= checks_required:
            return snapshot
        remaining = deadline - clock()
        if remaining <= 0:
            print("Codex Store versions did not become stable before the bounded wait expired.")
            return None
        sleeper(min(interval, remaining))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_cli(
    path: Path | None,
    kind: str,
    *,
    execute: bool = True,
    required_siblings: tuple[str, ...] = (),
) -> CliProbe:
    if not path or not path.is_file():
        return CliProbe(
            kind=kind,
            exists=False,
            runnable=False,
            bundle_complete=not required_siblings,
            missing_bundle_files=list(required_siblings),
        )
    missing_bundle_files = [
        name for name in required_siblings if not (path.parent / name).is_file()
    ]
    bundle_complete = not missing_bundle_files
    try:
        size = path.stat().st_size
        digest = sha256_file(path)
    except OSError:
        return CliProbe(
            kind=kind,
            exists=True,
            runnable=False,
            bundle_complete=bundle_complete,
            missing_bundle_files=missing_bundle_files,
        )
    if not execute:
        return CliProbe(
            kind=kind,
            exists=True,
            runnable=size > 0 and bundle_complete,
            sha256=digest,
            size=size,
            bundle_complete=bundle_complete,
            missing_bundle_files=missing_bundle_files,
        )
    try:
        proc = subprocess.run(
            [str(path), "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
            check=False,
        )
        output = proc.stdout.strip().splitlines()
        version = output[0] if output else ""
        runnable = proc.returncode == 0 and "codex-cli" in version.lower() and bundle_complete
    except (OSError, subprocess.TimeoutExpired):
        runnable = False
        version = ""
    return CliProbe(
        kind=kind,
        exists=True,
        runnable=runnable,
        version=version,
        sha256=digest,
        size=size,
        bundle_complete=bundle_complete,
        missing_bundle_files=missing_bundle_files,
    )


def cli_bundle_paths(cli_path: Path | None) -> dict[str, Path]:
    if not cli_path:
        return {}
    return {name: cli_path.parent / name for name in MANAGED_CLI_BUNDLE_FILES}


def cli_bundle_hashes(cli_path: Path | None) -> dict[str, str] | None:
    paths = cli_bundle_paths(cli_path)
    if not paths or any(not path.is_file() for path in paths.values()):
        return None
    try:
        return {name: sha256_file(path) for name, path in paths.items()}
    except OSError:
        return None


def source_cli_path(app_info: dict[str, str] | None) -> Path | None:
    if not app_info:
        return None
    root = Path(app_info.get("InstallLocation") or "")
    candidates = [root / "app" / "resources" / "codex.exe", root / "resources" / "codex.exe"]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def bundled_marketplace_path(app_info: dict[str, str] | None) -> Path | None:
    """Return the marketplace shipped by the currently registered Codex AppX.

    Windows Codex has used both ``app/resources`` and ``resources`` layouts
    across releases.  The path is resolved from the live AppX package rather
    than from a surviving ``.tmp`` copy, so plugin refreshes cannot silently
    install an older Browser/Chrome bundle.
    """

    if not app_info:
        return None
    root = Path(app_info.get("InstallLocation") or "")
    candidates = (
        root / "app" / "resources" / "plugins" / BUNDLED_MARKETPLACE_NAME,
        root / "resources" / "plugins" / BUNDLED_MARKETPLACE_NAME,
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def winget_path() -> Path | None:
    """Find the official Windows Package Manager executable without a shell."""

    for name in ("winget.exe", "winget"):
        found = shutil.which(name)
        if found:
            return Path(found)
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    candidate = local / "Microsoft" / "WindowsApps" / "winget.exe"
    return candidate if candidate.is_file() else None


def _run_winget_codex_registration(
    *,
    product_id: str = CODEX_STORE_PRODUCT_ID,
    timeout: float = 300,
) -> subprocess.CompletedProcess[str]:
    executable = winget_path()
    if executable is None:
        return subprocess.CompletedProcess(
            ["winget.exe"],
            127,
            "",
            "winget.exe was not found",
        )
    arguments = [
        str(executable),
        "install",
        "--id",
        product_id,
        "-e",
        "--source",
        "msstore",
        "--force",
        "--accept-source-agreements",
        "--accept-package-agreements",
        "--silent",
        "--disable-interactivity",
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if is_windows() else 0
    try:
        return subprocess.run(
            arguments,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            creationflags=creationflags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(arguments, 1, "", f"{type(exc).__name__}")


def _registration_target_reached(target_version: str) -> tuple[bool, dict[str, str] | None]:
    app = windows_codex_app_info()
    if not app:
        return False, None
    current = str(app.get("Version") or "")
    return windows_version_key(current) >= windows_version_key(target_version), app


def run_windows_appx_registration(
    app_info: dict[str, str] | None = None,
    *,
    apply: bool = False,
    target_version: str | None = None,
    timeout_seconds: float = 300,
    poll_seconds: float = 3,
    runner: Callable[[], subprocess.CompletedProcess[str]] | None = None,
) -> int:
    """Complete a staged Store update for the current Codex user.

    The dry-run path never invokes winget.  The apply path only runs while
    Codex is fully closed and uses the official Microsoft Store product ID;
    it does not log in, change the provider, or touch Codex databases.
    """

    if not is_windows():
        print("Codex AppX registration is available only on Windows.")
        return 20
    app = app_info or windows_codex_app_info()
    if not app:
        print("OpenAI.Codex AppX package was not found.")
        return 20
    highest, pending = pending_codex_registration(app)
    target = target_version or highest
    current_version = str(app.get("Version") or "")
    if target_version and windows_version_key(current_version) >= windows_version_key(target):
        print(f"Codex AppX registration target is already current: {current_version}.")
        return 0
    if not pending and not target_version:
        print("Codex AppX registration is already current.")
        return 0
    print(
        "Codex AppX registration is pending: "
        f"current={app.get('Version') or 'missing'} target={target} "
        f"highest_staged={highest}."
    )
    print(f"store_product_id: {CODEX_STORE_PRODUCT_ID}")
    print("planned: winget install from the Microsoft Store with accepted agreements and no interaction")
    if not apply:
        print("DRY-RUN COMPLETE. No Store registration was started.")
        return 0
    if codex_is_running():
        print("Codex/ChatGPT is running. Quit it completely before registering the update.")
        return 20
    result = runner() if runner is not None else _run_winget_codex_registration(timeout=timeout_seconds)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        suffix = f" Detail: {detail[-1]}" if detail else ""
        print(f"Official Codex Store registration failed (exit {result.returncode}).{suffix}")
        return 20

    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while True:
        reached, current = _registration_target_reached(target)
        if reached:
            print(f"Codex AppX registration complete: {current.get('Version') or 'unknown'}.")
            return 0
        if time.monotonic() >= deadline:
            print(
                "The Store command finished, but Windows did not register the requested "
                f"Codex version {target} before the bounded wait expired."
            )
            return 20
        time.sleep(min(max(0.1, poll_seconds), max(0.1, deadline - time.monotonic())))


def managed_cli_path(app_info: dict[str, str] | None) -> Path | None:
    if not app_info:
        return None
    version = re.sub(r"[^0-9A-Za-z._-]+", "-", app_info.get("Version") or "unknown")
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return local / "CodexHybridModelSwitcher" / "codex-cli" / version / "codex.exe"


def paths_equivalent(left: Path | None, right: Path | None) -> bool:
    if left is None or right is None:
        return left is right
    return os.path.normcase(os.path.abspath(os.fspath(left))) == os.path.normcase(
        os.path.abspath(os.fspath(right))
    )


def user_environment_value(name: str) -> str | None:
    if os.name != "nt":
        value = os.environ.get(name)
        return value.strip() if value and value.strip() else None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _kind = winreg.QueryValueEx(key, name)
    except (ImportError, FileNotFoundError, OSError):
        value = os.environ.get(name)
    return value.strip() if isinstance(value, str) and value.strip() else None


def set_user_environment_value(name: str, value: str | None) -> None:
    if os.name != "nt":
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
        return
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        if value is None:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        import ctypes

        result = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF,
            0x001A,
            0,
            "Environment",
            0x0002,
            5000,
            ctypes.byref(result),
        )
    except (AttributeError, OSError):
        pass


def _decode_toml_string(raw: str) -> str | None:
    value = raw.strip()
    if len(value) < 2:
        return None
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.startswith('"') and value.endswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, str) else None
    return None


def find_toml_section_key(text: str, section: str, key: str) -> tuple[str | None, int | None]:
    current = ""
    wanted = section.strip()
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*(?:#.*)?$")
    for index, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped
            continue
        if current != wanted:
            continue
        match = pattern.match(line)
        if match:
            return _decode_toml_string(match.group(1)), index
    return None, None


def node_repl_registered(text: str) -> bool:
    return bool(re.search(r"(?m)^\s*\[mcp_servers\.node_repl(?:\]|\.)", text))


def official_node_repl_runtime(text: str) -> tuple[Path | None, bool, str]:
    command, _ = find_toml_section_key(text, "[mcp_servers.node_repl]", "command")
    runtime_version, _ = find_toml_section_key(
        text,
        "[mcp_servers.node_repl.env]",
        "BROWSER_USE_CODEX_APP_VERSION",
    )
    runtime = Path(command) if command else None
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    official_root = local / "OpenAI" / "Codex" / "runtimes" / "cua_node"
    try:
        official_path = bool(
            runtime
            and runtime.resolve(strict=False).is_relative_to(official_root.resolve(strict=False))
        )
        exists = bool(
            official_path
            and runtime_version
            and runtime.is_file()
            and runtime.stat().st_size > 0
        )
    except OSError:
        exists = False
    return runtime, exists, runtime_version or "missing"


def render_cli_path_update(text: str, path: Path) -> str:
    section = "[mcp_servers.node_repl.env]"
    lines = text.splitlines()
    trailing_newline = text.endswith(("\n", "\r"))
    replacement = f"CODEX_CLI_PATH = {json.dumps(str(path))}"
    current = ""
    section_index: int | None = None
    next_section_index: int | None = None
    key_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current == section and next_section_index is None:
                next_section_index = index
            current = stripped
            if current == section:
                section_index = index
            continue
        if current == section and re.match(r"^\s*CODEX_CLI_PATH\s*=", line):
            key_index = index
    if key_index is not None:
        lines[key_index] = replacement
    elif section_index is not None:
        insert_at = next_section_index if next_section_index is not None else len(lines)
        lines.insert(insert_at, replacement)
    elif node_repl_registered(text):
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([section, replacement])
    else:
        raise ValueError("mcp_servers.node_repl is not registered")
    newline = "\r\n" if "\r\n" in text else "\n"
    updated = newline.join(lines)
    if trailing_newline:
        updated += newline
    return updated


def read_utf8_text_preserving_bom(path: Path) -> tuple[str, bool]:
    data = path.read_bytes()
    has_bom = data.startswith(codecs.BOM_UTF8)
    return data.decode("utf-8-sig"), has_bom


def write_utf8_text_atomic(path: Path, text: str, *, bom: bool) -> None:
    stamp = f"{os.getpid()}-{int(time.time())}"
    temp = path.with_name(f"{path.name}.tmp-codex-update-{stamp}")
    payload = text.encode("utf-8")
    if bom:
        payload = codecs.BOM_UTF8 + payload
    temp.write_bytes(payload)
    os.replace(temp, path)


def config_guard_text(text: str) -> str:
    """Normalize config text for the update transaction invariant.

    Official plugin/marketplace refreshes are allowed to rewrite their own
    sections and the Browser node-repl block.  Provider routing, user MCP
    entries, permissions, and all other Codex settings remain protected.
    ``CODEX_CLI_PATH`` is also normalized because the guarded CLI repair may
    intentionally update that one path.
    """

    current = ""
    kept: list[str] = []
    skip = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped
            lower = current.lower()
            skip = (
                lower.startswith("[plugins")
                or lower.startswith("[plugin")
                or lower.startswith("[marketplace")
            )
        if skip:
            continue
        if current.lower().startswith("[mcp_servers.node_repl"):
            if re.match(r"^\s*(command|CODEX_CLI_PATH|BROWSER_USE_CODEX_APP_VERSION)\s*=", line):
                kept.append("<managed-browser-runtime-setting>")
            else:
                kept.append(line.rstrip())
            continue
        if re.match(r"^\s*CODEX_CLI_PATH\s*=", line):
            kept.append("CODEX_CLI_PATH = <managed-by-codex-hybrid>")
        else:
            kept.append(line.rstrip())
    return "\n".join(kept).strip() + "\n"


def config_guard_hash(text: str) -> str:
    return hashlib.sha256(config_guard_text(text).encode("utf-8")).hexdigest()


def _update_backup_root() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return local / "CodexHybridModelSwitcher" / "backups"


def _restrict_update_backup_acl(path: Path) -> None:
    """Restrict update backups to the current user on Windows."""

    if is_windows():
        username = os.environ.get("USERNAME") or ""
        if not username:
            raise OSError("USERNAME is unavailable for update backup ACL setup")
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
            raise OSError("update backup ACL setup failed")
    else:
        try:
            path.chmod(0o700)
        except OSError:
            pass


def backup_windows_update_state(config: AppConfig) -> Path:
    """Create a private, timestamped update backup without changing Codex state."""

    root = _update_backup_root()
    root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = root / f"update-orchestrate-{stamp}"
    backup.mkdir(parents=False, exist_ok=False)
    _restrict_update_backup_acl(backup)
    names = (
        "config.toml",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
        "state_5.sqlite-wal",
        "state_5.sqlite-shm",
    )
    hashes: dict[str, str | None] = {}
    for name in names:
        source = config.codex_home / name
        target = backup / name
        if source.is_file():
            shutil.copy2(source, target)
            hashes[name] = sha256_file(target)
        else:
            hashes[name] = None
    manifest = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "codex_home": str(config.codex_home),
        "files": hashes,
        "note": "Private backup for Windows Codex AppX registration and plugin refresh.",
    }
    (backup / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return backup


def _restore_config_from_backup(backup: Path, config: AppConfig) -> bool:
    source = backup / "config.toml"
    target = config.codex_home / "config.toml"
    if not source.is_file():
        return False
    temp = target.with_name(f"{target.name}.tmp-codex-update-restore-{os.getpid()}")
    try:
        shutil.copy2(source, temp)
        os.replace(temp, target)
    except OSError:
        try:
            temp.unlink()
        except OSError:
            pass
        return False
    return sha256_file(source) == sha256_file(target)


def classify_cli_path(path: Path | None) -> str:
    if not path:
        return "missing"
    value = str(path).lower()
    local = str(Path(os.environ.get("LOCALAPPDATA") or "")).lower()
    if local and value.startswith(str(Path(local) / "codexhybridmodelswitcher").lower()):
        return "hybrid-cache"
    if local and value.startswith(str(Path(local) / "openai" / "codex" / "bin").lower()):
        return "openai-relocated"
    if "windowsapps" in value:
        return "appx-source"
    return "other"


def manifest_version(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return "missing"
    value = data.get("version") if isinstance(data, dict) else None
    return str(value) if value else "missing"


def plugin_probe(
    name: str,
    app_info: dict[str, str] | None,
    codex_home: Path,
    config_text: str = "",
) -> PluginProbe:
    source = Path("__missing__")
    if app_info:
        source = (
            Path(app_info.get("InstallLocation") or "")
            / "app"
            / "resources"
            / "plugins"
            / "openai-bundled"
            / "plugins"
            / name
            / ".codex-plugin"
            / "plugin.json"
        )
    source_version = manifest_version(source)
    selector = f'[plugins."{name}@openai-bundled"]'
    installed = selector in config_text and bool(
        re.search(
            rf"(?ms)^\s*{re.escape(selector)}\s*$.*?^\s*enabled\s*=\s*true\s*$",
            config_text,
        )
    )
    cache_root = codex_home / "plugins" / "cache" / "openai-bundled" / name
    cache_versions: list[tuple[str, Path]] = []
    if cache_root.is_dir():
        for child in cache_root.iterdir():
            if not child.is_dir() or child.name.lower() == "latest":
                continue
            version = manifest_version(child / ".codex-plugin" / "plugin.json")
            if version != "missing":
                cache_versions.append((version, child))
    marketplace_plugin = (
        codex_home
        / ".tmp"
        / "bundled-marketplaces"
        / "openai-bundled"
        / "plugins"
        / name
    )
    marketplace_version = manifest_version(
        marketplace_plugin / ".codex-plugin" / "plugin.json"
    )
    if marketplace_version != "missing":
        cache_versions.append((marketplace_version, marketplace_plugin))
    cache_version = source_version if any(version == source_version for version, _ in cache_versions) else (
        sorted((version for version, _ in cache_versions), reverse=True)[0] if cache_versions else "missing"
    )
    install_source = "missing"
    if installed:
        if marketplace_version == cache_version:
            install_source = "bundled-marketplace"
        elif cache_versions:
            install_source = "plugin-cache"
    return PluginProbe(
        name=name,
        source_version=source_version,
        cache_version=cache_version,
        version_matches=source_version != "missing" and source_version == cache_version,
        installed=installed,
        install_source=install_source,
    )


def parse_cli_plugin_catalog(payload: dict[str, Any]) -> dict[str, CliPluginState]:
    states: dict[str, CliPluginState] = {}
    for bucket in ("installed", "available"):
        items = payload.get(bucket) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            plugin_id = str(item.get("pluginId") or "").strip()
            if not plugin_id:
                continue
            states[plugin_id] = CliPluginState(
                plugin_id=plugin_id,
                found=True,
                installed=bool(item.get("installed", bucket == "installed")),
                enabled=bool(item.get("enabled", False)),
                install_policy=str(item.get("installPolicy") or "missing"),
                version=str(item.get("version") or "missing"),
                bucket=bucket,
            )
    return states


def _json_object_from_output(output: str) -> dict[str, Any] | None:
    start = output.find("{")
    end = output.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        payload = json.loads(output[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _run_codex_plugin_command(
    cli_path: Path,
    arguments: list[str],
    *,
    timeout: float = 60,
) -> subprocess.CompletedProcess[str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if is_windows() else 0
    return subprocess.run(
        [str(cli_path), "plugin", *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        creationflags=creationflags,
    )


def _plugin_command_output(process: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(
        part.strip()
        for part in (process.stdout or "", process.stderr or "")
        if part and part.strip()
    )


def _marketplace_remove_is_already_absent(process: subprocess.CompletedProcess[str]) -> bool:
    if process.returncode == 0:
        return True
    text = _plugin_command_output(process).lower()
    return any(
        marker in text
        for marker in (
            "not found",
            "does not exist",
            "no marketplace",
            "unknown marketplace",
        )
    )


def refresh_official_bundled_plugins(
    cli_path: Path,
    app_info: dict[str, str],
    *,
    apply: bool = False,
    plugin_ids: tuple[str, ...] = BUNDLED_PLUGIN_IDS,
) -> int:
    """Refresh the marketplace and official Browser/Chrome through Codex CLI.

    The old plugin cache is deliberately not copied or deleted.  Removing and
    re-adding only the named marketplace makes the official CLI resolve the
    source shipped by the currently registered AppX package.  Individual old
    plugin cache directories are left in place because Windows may expose a
    ``latest`` reparse link that cannot be removed reliably.
    """

    marketplace = bundled_marketplace_path(app_info)
    if marketplace is None:
        print("The current Codex AppX bundled marketplace was not found.")
        return 20
    if not cli_path.is_file():
        print("The current Codex CLI was not found; marketplace refresh stopped.")
        return 20

    commands = [
        ["marketplace", "remove", BUNDLED_MARKETPLACE_NAME, "--json"],
        ["marketplace", "add", str(marketplace), "--json"],
        *[["add", plugin_id, "--json"] for plugin_id in plugin_ids],
    ]
    print(f"official_marketplace: {marketplace}")
    print("planned_plugin_operations: " + "; ".join("plugin " + " ".join(command) for command in commands))
    if not apply:
        print("DRY-RUN COMPLETE. No marketplace or plugin files were changed.")
        return 0

    for index, command in enumerate(commands):
        try:
            result = _run_codex_plugin_command(cli_path, command)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"Official Codex plugin command failed: {type(exc).__name__}.")
            return 20
        if index == 0 and _marketplace_remove_is_already_absent(result):
            continue
        if result.returncode != 0:
            detail = _plugin_command_output(result).splitlines()
            suffix = f" Detail: {detail[-1]}" if detail else ""
            print(f"Official Codex plugin command exited with code {result.returncode}.{suffix}")
            return 20
    print("Official bundled marketplace and Browser/Chrome refresh complete.")
    return 0


def query_codex_plugin_catalog(
    cli_path: Path,
) -> tuple[dict[str, CliPluginState], str | None]:
    try:
        proc = _run_codex_plugin_command(cli_path, ["list", "--json"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {}, type(exc).__name__
    if proc.returncode != 0:
        return {}, f"plugin list exited with code {proc.returncode}"
    payload = _json_object_from_output(proc.stdout)
    if payload is None:
        return {}, "plugin list did not return valid JSON"
    return parse_cli_plugin_catalog(payload), None


def current_codex_cli_for_plugins(
    config: AppConfig,
    app_info: dict[str, str],
) -> Path | None:
    source = source_cli_path(app_info)
    source_hashes = cli_bundle_hashes(source)
    try:
        config_text, _ = read_utf8_text_preserving_bom(config.codex_home / "config.toml")
    except OSError:
        config_text = ""
    config_value, _ = find_toml_section_key(
        config_text,
        "[mcp_servers.node_repl.env]",
        "CODEX_CLI_PATH",
    )
    environment_value = user_environment_value("CODEX_CLI_PATH")
    configured = Path(config_value or environment_value) if (config_value or environment_value) else None
    candidates = (managed_cli_path(app_info), configured, source)
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        probe = probe_cli(
            candidate,
            classify_cli_path(candidate),
            execute=False,
            required_siblings=MANAGED_CLI_COMPANION_FILES,
        )
        if not probe.exists or not probe.bundle_complete:
            continue
        candidate_hashes = cli_bundle_hashes(candidate)
        if source_hashes is not None and candidate_hashes != source_hashes:
            continue
        return candidate
    return None


def _browser_config_ready(
    config: AppConfig,
    app_info: dict[str, str],
) -> bool:
    try:
        config_text, _ = read_utf8_text_preserving_bom(config.codex_home / "config.toml")
    except OSError:
        return False
    probe = plugin_probe("browser", app_info, config.codex_home, config_text)
    return probe.installed and probe.version_matches


def _acquire_browser_post_start_lock(path: Path) -> int | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.exists() and time.time() - path.stat().st_mtime > BROWSER_POST_START_LOCK_SECONDS:
            path.unlink()
    except OSError:
        return None
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None
    os.write(descriptor, f"pid={os.getpid()}\ntime={int(time.time())}\n".encode("ascii"))
    return descriptor


def _release_browser_post_start_lock(path: Path, descriptor: int) -> None:
    try:
        os.close(descriptor)
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def count_staging_paths(codex_home: Path) -> int:
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    roots = [local / "OpenAI" / "Codex" / "bin", codex_home / "plugins" / "cache"]
    count = 0
    for root in roots:
        if not root.is_dir():
            continue
        try:
            count += sum(1 for path in root.rglob("*") if path.name.lower().startswith(".staging-"))
        except OSError:
            continue
    return count


def windows_resource_snapshot() -> tuple[int, list[dict[str, Any]]]:
    if not is_windows():
        return 0, []
    script = (
        "$since=(Get-Date).AddHours(-24);"
        "$events=@(Get-WinEvent -FilterHashtable @{LogName='System';Id=2004;StartTime=$since} "
        "-MaxEvents 50 -ErrorAction SilentlyContinue).Count;"
        "$top=@(Get-Process -ErrorAction SilentlyContinue|Sort-Object PrivateMemorySize64 -Descending|"
        "Select-Object -First 5 @{n='name';e={$_.ProcessName}},@{n='pid';e={$_.Id}},"
        "@{n='private_mb';e={[math]::Round($_.PrivateMemorySize64/1MB,1)}},"
        "@{n='working_set_mb';e={[math]::Round($_.WorkingSet64/1MB,1)}});"
        "@{events=$events;top=$top}|ConvertTo-Json -Compress -Depth 3"
    )
    try:
        proc = _run_powershell(script, timeout=30)
        data = json.loads(proc.stdout.strip() or "{}")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return 0, []
    events = int(data.get("events") or 0) if isinstance(data, dict) else 0
    top = data.get("top") or [] if isinstance(data, dict) else []
    if isinstance(top, dict):
        top = [top]
    cleaned = []
    for item in top if isinstance(top, list) else []:
        if not isinstance(item, dict):
            continue
        cleaned.append(
            {
                "name": str(item.get("name") or "unknown"),
                "pid": int(item.get("pid") or 0),
                "private_mb": float(item.get("private_mb") or 0),
                "working_set_mb": float(item.get("working_set_mb") or 0),
            }
        )
    return events, cleaned


def inspect_windows_update(
    config: AppConfig,
    *,
    execute_cli: bool = True,
    include_resources: bool = True,
    app_info: dict[str, str] | None = None,
    all_user_packages: list[dict[str, Any]] | None = None,
) -> WindowsUpdateReport:
    if not is_windows() and app_info is None:
        return WindowsUpdateReport(
            status=STATUS_MANUAL_ACTION,
            launch_safe=False,
            errors=["Windows Codex update checks are available only on Windows."],
        )
    app = app_info if app_info is not None else windows_codex_app_info()
    if not app:
        return WindowsUpdateReport(
            status=STATUS_MANUAL_ACTION,
            launch_safe=False,
            errors=["OpenAI.Codex AppX package was not found."],
        )
    if all_user_packages is None:
        all_user_packages = windows_codex_all_user_packages() if is_windows() else []
    highest_staged_version, pending_registration = pending_codex_registration(
        app,
        all_user_packages,
    )
    config_path = config.codex_home / "config.toml"
    try:
        text, _ = read_utf8_text_preserving_bom(config_path)
    except OSError:
        text = ""
    config_cli_value, _ = find_toml_section_key(
        text,
        "[mcp_servers.node_repl.env]",
        "CODEX_CLI_PATH",
    )
    environment_cli_value = user_environment_value("CODEX_CLI_PATH")
    configured_value = config_cli_value or environment_cli_value
    configured_path = Path(configured_value) if configured_value else None
    source_path = source_cli_path(app)
    managed_path = managed_cli_path(app)
    configured_probe = probe_cli(
        configured_path,
        classify_cli_path(configured_path),
        execute=execute_cli,
        required_siblings=MANAGED_CLI_COMPANION_FILES,
    )
    source_probe = probe_cli(
        source_path,
        "appx-source",
        execute=execute_cli,
        required_siblings=MANAGED_CLI_COMPANION_FILES,
    )
    managed_probe = probe_cli(
        managed_path,
        "hybrid-cache",
        execute=execute_cli,
        required_siblings=MANAGED_CLI_COMPANION_FILES,
    )
    browser = plugin_probe("browser", app, config.codex_home, text)
    chrome = plugin_probe("chrome", app, config.codex_home, text)
    staging_count = count_staging_paths(config.codex_home)
    events, top = windows_resource_snapshot() if include_resources else (0, [])
    registered = node_repl_registered(text)
    _runtime_path, runtime_exists, browser_runtime_version = official_node_repl_runtime(text)
    node_repl_mode = "missing"
    warnings: list[str] = []
    errors: list[str] = []
    launch_safe = True
    status = STATUS_HEALTHY

    browser_expected = browser.source_version != "missing" or browser.cache_version != "missing"
    if browser_expected and not browser.installed:
        warnings.append("Browser is bundled but not installed in Codex plugin config.")
    if browser_expected and not registered:
        warnings.append("Browser is present, but mcp_servers.node_repl is not registered.")
    if registered:
        if config_cli_value:
            node_repl_mode = "managed-cli-config"
        elif environment_cli_value:
            node_repl_mode = "managed-cli-environment"
        elif runtime_exists:
            node_repl_mode = "official-cua-runtime-missing-cli"
        else:
            node_repl_mode = "incomplete"
        if not configured_value:
            launch_safe = False
            status = STATUS_REPAIR_REQUIRED if source_probe.exists else STATUS_MANUAL_ACTION
            errors.append(
                "Browser runtime has no CODEX_CLI_PATH, so privileged Browser requests cannot start codex app-server."
            )
        elif not configured_probe.exists or not configured_probe.runnable:
            launch_safe = False
            status = STATUS_REPAIR_REQUIRED if source_probe.exists else STATUS_MANUAL_ACTION
            if configured_probe.missing_bundle_files:
                errors.append(
                    "Configured CODEX_CLI_PATH is missing companion programs: "
                    + ", ".join(configured_probe.missing_bundle_files)
                )
            else:
                errors.append("Configured CODEX_CLI_PATH is missing or not runnable.")
        elif source_probe.exists and configured_probe.sha256 != source_probe.sha256:
            launch_safe = False
            status = STATUS_REPAIR_REQUIRED
            errors.append("Configured CODEX_CLI_PATH does not match the current Codex app CLI.")
        if (
            configured_probe.kind == "hybrid-cache"
            and managed_path is not None
            and not paths_equivalent(configured_path, managed_path)
        ):
            launch_safe = False
            status = STATUS_REPAIR_REQUIRED
            errors.append("Configured CODEX_CLI_PATH uses an older managed version directory.")
    if source_probe.exists and not source_probe.runnable:
        warnings.append("The AppX CLI could not be executed in this process context; file integrity was still checked.")
    for plugin in (browser, chrome):
        if plugin.source_version != "missing" and not plugin.version_matches:
            warnings.append(
                f"{plugin.name} cache version {plugin.cache_version} does not match bundled version {plugin.source_version}."
            )
    if staging_count:
        warnings.append(f"Found {staging_count} Codex staging path(s); official cache files were not modified.")
    if pending_registration:
        launch_safe = False
        status = STATUS_MANUAL_ACTION
        errors.append(
            "A newer Codex AppX package "
            f"{highest_staged_version} is staged, but the current user is still registered to "
            f"{app.get('Version') or 'missing'}. Complete the Codex update registration before launching."
        )
    if events:
        warnings.append(f"Windows recorded {events} low-memory event(s) in the last 24 hours.")
    return WindowsUpdateReport(
        status=status,
        launch_safe=launch_safe,
        app_version=str(app.get("Version") or "missing"),
        app_family=str(app.get("PackageFamilyName") or "missing"),
        highest_staged_version=highest_staged_version,
        pending_registration=pending_registration,
        node_repl_registered=registered,
        node_repl_mode=node_repl_mode,
        node_repl_runtime_exists=runtime_exists,
        browser_runtime_version=browser_runtime_version,
        configured_cli=configured_probe,
        source_cli=source_probe,
        managed_cli=managed_probe,
        browser=browser,
        chrome=chrome,
        staging_count=staging_count,
        low_memory_events_24h=events,
        top_memory_processes=top,
        warnings=warnings,
        errors=errors,
    )


def _print_report(report: WindowsUpdateReport) -> None:
    print("Windows Codex update check")
    print(f"status: {report.status}")
    print(f"launch_safe: {'yes' if report.launch_safe else 'no'}")
    print(f"codex_app_version: {report.app_version}")
    print(f"highest_staged_version: {report.highest_staged_version}")
    print(f"pending_registration: {'yes' if report.pending_registration else 'no'}")
    print(
        "node_repl: "
        f"mode={report.node_repl_mode} "
        f"runtime_exists={'yes' if report.node_repl_runtime_exists else 'no'} "
        f"browser_version={report.browser_runtime_version}"
    )
    print(
        "configured_cli: "
        f"{report.configured_cli.kind} "
        f"exists={'yes' if report.configured_cli.exists else 'no'} "
        f"runnable={'yes' if report.configured_cli.runnable else 'no'} "
        f"bundle_complete={'yes' if report.configured_cli.bundle_complete else 'no'} "
        f"version={report.configured_cli.version or '<unknown>'}"
    )
    if report.configured_cli.missing_bundle_files:
        print("configured_cli_missing: " + ", ".join(report.configured_cli.missing_bundle_files))
    print(
        f"browser: installed={'yes' if report.browser.installed else 'no'} "
        f"source={report.browser.install_source} "
        f"bundled={report.browser.source_version} cache={report.browser.cache_version}"
    )
    print(
        f"chrome: installed={'yes' if report.chrome.installed else 'no'} "
        f"source={report.chrome.install_source} "
        f"bundled={report.chrome.source_version} cache={report.chrome.cache_version}"
    )
    print(f"staging_paths: {report.staging_count}")
    print(f"low_memory_events_24h: {report.low_memory_events_24h}")
    if report.top_memory_processes:
        print("top_memory_processes:")
        for item in report.top_memory_processes:
            print(
                f"  - {item['name']} pid={item['pid']} "
                f"private_mb={item['private_mb']} working_set_mb={item['working_set_mb']}"
            )
    for warning in report.warnings:
        print(f"WARN {warning}")
    for error in report.errors:
        print(f"ERROR {error}")


def run_windows_update_doctor(
    config_path: str | None = None,
    *,
    json_output: bool = False,
    launch_gate: bool = False,
    include_resources: bool = True,
) -> int:
    config = load_config(config_path)
    report = inspect_windows_update(config, include_resources=include_resources)
    if json_output:
        print(json.dumps(report.redacted_dict(), ensure_ascii=False, sort_keys=True))
    else:
        _print_report(report)
    if launch_gate:
        return 0 if report.launch_safe else 10
    if report.status == STATUS_HEALTHY:
        return 0
    return 10 if report.status == STATUS_REPAIR_REQUIRED else 20


def _backup_update_config(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak-codex-update-{stamp}")
    shutil.copy2(path, backup)
    return backup


def _backup_cli_environment(root: Path, previous: str | None) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = root / f"CODEX_CLI_PATH.bak-{stamp}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(
        json.dumps({"CODEX_CLI_PATH": previous}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return backup


def _install_cli_bundle_atomically(
    source: Path,
    destination: Path,
    source_hashes: dict[str, str],
) -> tuple[bool, Path | None, Path | None]:
    """Stage and swap the complete managed CLI directory as one rename."""

    destination_dir = destination.parent
    bundle_root = destination_dir.parent
    bundle_root.mkdir(parents=True, exist_ok=True)
    staging_dir = bundle_root / f".staging-{os.getpid()}-{int(time.time())}-codex-cli"
    previous_dir = bundle_root / f".previous-{os.getpid()}-{int(time.time())}-codex-cli"
    staging_dir.mkdir(parents=False, exist_ok=False)
    try:
        for name, source_path in cli_bundle_paths(source).items():
            shutil.copy2(source_path, staging_dir / name)
        staged_cli = staging_dir / "codex.exe"
        copied = probe_cli(
            staged_cli,
            "hybrid-cache",
            execute=True,
            required_siblings=MANAGED_CLI_COMPANION_FILES,
        )
        if not copied.runnable or not copied.bundle_complete or cli_bundle_hashes(staged_cli) != source_hashes:
            return False, staging_dir, None

        if destination_dir.exists():
            os.replace(destination_dir, previous_dir)
        os.replace(staging_dir, destination_dir)
        installed = probe_cli(
            destination,
            "hybrid-cache",
            execute=True,
            required_siblings=MANAGED_CLI_COMPANION_FILES,
        )
        if not installed.runnable or cli_bundle_hashes(destination) != source_hashes:
            # Do not leave a mixed directory behind if post-swap validation
            # fails. The old directory is retained until this point.
            if destination_dir.exists():
                shutil.rmtree(destination_dir, ignore_errors=True)
            if previous_dir.exists():
                os.replace(previous_dir, destination_dir)
            return False, None, None
        return True, None, previous_dir if previous_dir.exists() else None
    except Exception:
        if destination_dir.exists() and previous_dir.exists():
            shutil.rmtree(destination_dir, ignore_errors=True)
            try:
                os.replace(previous_dir, destination_dir)
            except OSError:
                pass
        raise
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


def run_windows_update_repair(
    config_path: str | None = None,
    *,
    apply: bool = False,
    confirm: Callable[[str], str] = input,
) -> int:
    config = load_config(config_path)
    if not is_windows():
        print("Windows Codex update repair is available only on Windows.")
        return 20
    app = windows_codex_app_info()
    if not app:
        print("OpenAI.Codex AppX package was not found.")
        return 20
    highest_staged_version, pending_registration = pending_codex_registration(app)
    if pending_registration:
        print(
            "A newer Codex AppX package is waiting for registration: "
            f"current={app.get('Version') or 'missing'} staged={highest_staged_version}."
        )
        print(
            "Run the closed-app windows-update-orchestrate path to complete "
            "official Store registration before the CLI repair."
        )
        return 20
    codex_config = config.codex_home / "config.toml"
    try:
        existing, bom = read_utf8_text_preserving_bom(codex_config)
    except OSError as exc:
        print(f"Codex config could not be read: {type(exc).__name__}")
        return 20
    if not node_repl_registered(existing):
        print("Browser node_repl is not registered. Install or refresh Browser in Codex first.")
        return 20
    config_value, _ = find_toml_section_key(
        existing,
        "[mcp_servers.node_repl.env]",
        "CODEX_CLI_PATH",
    )
    environment_value = user_environment_value("CODEX_CLI_PATH")
    current_value = config_value or environment_value
    source = source_cli_path(app)
    destination = managed_cli_path(app)
    source_probe = probe_cli(
        source,
        "appx-source",
        execute=False,
        required_siblings=MANAGED_CLI_COMPANION_FILES,
    )
    source_hashes = cli_bundle_hashes(source)
    if (
        not source
        or not source_probe.exists
        or source_probe.size <= 0
        or not source_probe.bundle_complete
        or source_hashes is None
    ):
        missing = ", ".join(source_probe.missing_bundle_files)
        suffix = f" Missing: {missing}." if missing else ""
        print("The current Codex app CLI bundle was not found or is incomplete." + suffix)
        return 20
    update_config = config_value is not None
    updated = render_cli_path_update(existing, destination) if update_config else existing
    current_path = Path(current_value) if current_value else None
    current_probe = probe_cli(
        current_path,
        classify_cli_path(current_path),
        execute=False,
        required_siblings=MANAGED_CLI_COMPANION_FILES,
    )
    destination_probe = probe_cli(
        destination,
        "hybrid-cache",
        execute=True,
        required_siblings=MANAGED_CLI_COMPANION_FILES,
    )
    destination_hashes = cli_bundle_hashes(destination)
    already_current = (
        Path(environment_value or "") == destination
        and (not update_config or Path(config_value or "") == destination)
        and destination_probe.runnable
        and destination_probe.bundle_complete
        and destination_hashes == source_hashes
    )
    print("Windows Codex CLI repair")
    print(f"codex_app_version: {app.get('Version') or 'unknown'}")
    print(f"current_cli: {current_probe.kind} exists={'yes' if current_probe.exists else 'no'}")
    print("target_cli: hybrid-cache complete bundle")
    print("user_environment_change: CODEX_CLI_PATH only")
    print(
        "config_change: update existing [mcp_servers.node_repl.env].CODEX_CLI_PATH"
        if update_config
        else "config_change: none (Codex may regenerate the Browser block)"
    )
    if already_current:
        print("No repair is needed.")
        return 0
    if not apply:
        print("DRY-RUN COMPLETE. No files were changed.")
        print("Run again with --apply and type REPAIR to perform the guarded repair.")
        return 0
    if codex_is_running():
        print("Codex/ChatGPT is running. Quit it completely before repair.")
        return 20
    if confirm("Type REPAIR to continue: ") != "REPAIR":
        print("Cancelled. No files were changed.")
        return 0
    before = protected_hashes(config)
    previous_environment = environment_value
    environment_backup: Path | None = None
    config_backup: Path | None = None
    destination_dir = destination.parent
    destination_dir.parent.mkdir(parents=True, exist_ok=True)
    previous_bundle_dir: Path | None = None
    try:
        installed_ok, _staging_dir, previous_bundle_dir = _install_cli_bundle_atomically(
            source,
            destination,
            source_hashes,
        )
        if not installed_ok:
            print("Copied CLI bundle failed validation. Codex config was not changed.")
            return 20
        environment_backup = _backup_cli_environment(destination_dir.parent, previous_environment)
        set_user_environment_value("CODEX_CLI_PATH", str(destination))
        if update_config:
            config_backup = _backup_update_config(codex_config)
            write_utf8_text_atomic(codex_config, updated, bom=bom)
    except Exception:
        if environment_backup is not None:
            set_user_environment_value("CODEX_CLI_PATH", previous_environment)
        if config_backup is not None:
            shutil.copy2(config_backup, codex_config)
        raise
    finally:
        # The previous versioned directory is intentionally retained as a
        # private rollback copy. It is never selected by CODEX_CLI_PATH.
        pass
    after = protected_hashes(config)
    changed = [name for name in before if before[name] != after[name]]
    if changed:
        set_user_environment_value("CODEX_CLI_PATH", previous_environment)
        if config_backup is not None:
            shutil.copy2(config_backup, codex_config)
        print("Protected Codex files changed unexpectedly: " + ", ".join(changed))
        print("The previous CLI environment and config were restored.")
        return 20
    final_environment = user_environment_value("CODEX_CLI_PATH")
    final_config_value, _ = find_toml_section_key(
        read_utf8_text_preserving_bom(codex_config)[0],
        "[mcp_servers.node_repl.env]",
        "CODEX_CLI_PATH",
    )
    if Path(final_environment or "") != destination or (
        update_config and Path(final_config_value or "") != destination
    ):
        set_user_environment_value("CODEX_CLI_PATH", previous_environment)
        if config_backup is not None:
            shutil.copy2(config_backup, codex_config)
        print("CLI path verification failed. The previous environment and config were restored.")
        return 20
    if environment_backup is not None:
        print(f"Environment backup created: {environment_backup.name}")
    if config_backup is not None:
        print(f"Config backup created: {config_backup.name}")
    print("Repair complete. Protected Codex files were unchanged.")
    return 0


def auto_repair_eligible(report: WindowsUpdateReport) -> bool:
    """Limit launcher automation to the known Browser CLI refresh cases."""

    return bool(
        report.status == STATUS_REPAIR_REQUIRED
        and not report.launch_safe
        and not report.pending_registration
        and report.node_repl_registered
        and report.source_cli.exists
        and report.source_cli.bundle_complete
        and report.source_cli.sha256
        and report.errors
        and all(
            any(error.startswith(prefix) for prefix in AUTO_REPAIR_ERROR_PREFIXES)
            for error in report.errors
        )
    )


def run_windows_update_ensure(config_path: str | None = None) -> int:
    """Refresh a stale AppX CLI bundle before the daily launcher opens Codex."""

    config = load_config(config_path)
    report = inspect_windows_update(config, include_resources=False)
    if report.launch_safe:
        print("Codex Browser/CLI compatibility is current.")
        return 0
    if report.pending_registration:
        _print_report(report)
        print(
            "Codex has downloaded a newer app version but Windows has not registered it for this user yet. "
            "Keep Codex closed and run windows-update-orchestrate or Repair Codex Update and Plugins.cmd."
        )
        return 20
    if not auto_repair_eligible(report):
        _print_report(report)
        print("Automatic CLI refresh stopped because this is not a supported version-only repair.")
        return 20
    if codex_is_running():
        print("Codex/ChatGPT is running. Quit it completely before automatic CLI refresh.")
        return 20

    print(
        "Codex app update detected. Refreshing the guarded Browser CLI bundle "
        f"for app version {report.app_version}."
    )
    try:
        repaired = run_windows_update_repair(
            config_path,
            apply=True,
            confirm=lambda _prompt: "REPAIR",
        )
    except Exception as exc:
        print(f"Automatic CLI refresh failed: {type(exc).__name__}.")
        return 20
    if repaired != 0:
        print("Automatic CLI refresh did not complete. Use the manual repair entry.")
        return repaired

    final = inspect_windows_update(config, include_resources=False)
    if not final.launch_safe:
        _print_report(final)
        print("Automatic CLI refresh finished, but the launch gate is still not healthy.")
        return 20
    print("Automatic CLI refresh complete. Protected Codex files were unchanged.")
    return 0


def official_plugins_need_refresh(config: AppConfig, app_info: dict[str, str]) -> bool:
    """Return whether either official bundled plugin is missing or stale."""

    try:
        text, _ = read_utf8_text_preserving_bom(config.codex_home / "config.toml")
    except OSError:
        return True
    probes = [plugin_probe(name, app_info, config.codex_home, text) for name in ("browser", "chrome")]
    return any(not probe.installed or not probe.version_matches for probe in probes)


def verify_official_bundled_plugins(
    config: AppConfig,
    app_info: dict[str, str],
    cli_path: Path,
) -> tuple[bool, str]:
    """Verify both plugin files and the official CLI catalog after refresh."""

    try:
        text, _ = read_utf8_text_preserving_bom(config.codex_home / "config.toml")
    except OSError as exc:
        return False, f"config read failed: {type(exc).__name__}"
    for name in ("browser", "chrome"):
        probe = plugin_probe(name, app_info, config.codex_home, text)
        if not probe.installed or not probe.version_matches:
            return False, (
                f"{name} is not installed with the current AppX version "
                f"(bundled={probe.source_version}, cache={probe.cache_version})"
            )
    states, error = query_codex_plugin_catalog(cli_path)
    if error:
        return False, error
    awaiting_feature_gate: list[str] = []
    for plugin_id in BUNDLED_PLUGIN_IDS:
        state = states.get(plugin_id)
        if state is None or not state.installed or not state.enabled:
            return False, f"{plugin_id} is not installed and enabled in the official CLI catalog"
        if not state.available:
            awaiting_feature_gate.append(plugin_id)
    if awaiting_feature_gate:
        return True, (
            "Browser/Chrome are installed and enabled; Codex post-start verification will wait for AVAILABLE: "
            + ", ".join(awaiting_feature_gate)
        )
    return True, "Browser and Chrome are installed, enabled, and version-aligned"


def run_windows_update_orchestrate(
    config_path: str | None = None,
    *,
    apply: bool = False,
    automatic: bool = False,
    registration_timeout_seconds: float = 300,
    registration_poll_seconds: float = 3,
    settle_checks: int = DEFAULT_APPX_SETTLE_CHECKS,
    settle_poll_seconds: float = DEFAULT_APPX_SETTLE_POLL_SECONDS,
    settle_timeout_seconds: float = DEFAULT_APPX_SETTLE_TIMEOUT_SECONDS,
    settle_total_timeout_seconds: float = DEFAULT_APPX_SETTLE_TOTAL_TIMEOUT_SECONDS,
    max_registration_passes: int = DEFAULT_MAX_REGISTRATION_PASSES,
    confirm: Callable[[str], str] = input,
) -> int:
    """Run the complete closed-app Windows update transaction.

    The order is deliberately fixed: observe and back up, wait for the Store
    view to become stable, register up to two staged AppX versions if needed,
    refresh the matching CLI bundle, then refresh the current AppX marketplace
    and official Browser/Chrome entries.  Registration is followed by another
    stability wait so a second Store build cannot be missed.  Codex is opened
    only by the outer desktop launcher after this command succeeds.
    """

    config = load_config(config_path)
    if not is_windows():
        print("Windows Codex update orchestration is available only on Windows.")
        return 20
    if codex_is_running():
        print("Codex/ChatGPT is running. Quit it completely before the update transaction.")
        return 20
    app = windows_codex_app_info()
    if not app:
        print("OpenAI.Codex AppX package was not found.")
        return 20

    report = inspect_windows_update(config, include_resources=False, app_info=app)
    initial_plugins_need_refresh = official_plugins_need_refresh(config, app)
    print("Windows Codex update orchestration")
    print(f"codex_app_version: {report.app_version}")
    print(f"pending_registration: {'yes' if report.pending_registration else 'no'}")
    print(f"cli_launch_gate: {'ready' if report.launch_safe else 'repair-needed'}")
    print(f"plugins_need_refresh: {'yes' if initial_plugins_need_refresh else 'no'}")
    if not apply:
        if report.pending_registration:
            print(
                "planned: require "
                f"{max(1, int(settle_checks))} stable Store observations, register at most "
                f"{max(1, int(max_registration_passes))} versions, and settle again before launch"
            )
        if not report.launch_safe:
            print("planned: refresh the current AppX CLI bundle and CODEX_CLI_PATH")
        if initial_plugins_need_refresh:
            cli = current_codex_cli_for_plugins(config, app)
            if cli:
                refresh_official_bundled_plugins(cli, app, apply=False)
            else:
                print("planned: refresh Browser/Chrome after a matching CLI becomes available")
        print("DRY-RUN COMPLETE. No Store, config, plugin, or Codex state was changed.")
        return 0

    if not automatic and confirm("Type APPLY to continue: ") != "APPLY":
        print("Cancelled. No Windows update or plugin changes were made.")
        return 3

    initial_snapshot = codex_appx_update_snapshot()
    if initial_snapshot.app_info is None:
        print("OpenAI.Codex AppX package disappeared before the update transaction started.")
        return 20
    force_plugin_refresh = False
    if (
        report.launch_safe
        and not report.pending_registration
        and not initial_snapshot.pending_registration
        and not initial_plugins_need_refresh
    ):
        quick_cli = current_codex_cli_for_plugins(config, initial_snapshot.app_info)
        if quick_cli is not None:
            quick_ok, quick_detail = verify_official_bundled_plugins(
                config,
                initial_snapshot.app_info,
                quick_cli,
            )
            if quick_ok:
                print("Healthy fast path: " + quick_detail)
                print("No Store registration, backup, CLI copy, or plugin refresh was needed.")
                return 0
            force_plugin_refresh = True
            print("Fast-path plugin verification needs repair: " + quick_detail)

    before_hashes = protected_hashes(config)
    try:
        before_config, before_bom = read_utf8_text_preserving_bom(config.codex_home / "config.toml")
    except OSError as exc:
        print(f"Codex config could not be read: {type(exc).__name__}")
        return 20
    before_guard = config_guard_hash(before_config)
    try:
        backup = backup_windows_update_state(config)
    except OSError as exc:
        print(f"Update backup preparation failed: {type(exc).__name__}. Codex remains closed.")
        return 20
    print(f"Update backup created: {backup}")

    def transaction_invariants_hold(stage: str, *, restore_backup: bool = False) -> bool:
        current_hashes = protected_hashes(config)
        changed = [
            name
            for name in before_hashes
            if before_hashes[name] != current_hashes[name]
        ]
        if changed:
            print(f"Protected Codex files changed during {stage}: " + ", ".join(changed))
            print(f"Codex remains closed. Update backup: {backup}")
            return False
        try:
            current_config, _ = read_utf8_text_preserving_bom(config.codex_home / "config.toml")
        except OSError as exc:
            print(f"Codex config verification failed during {stage}: {type(exc).__name__}")
            return False
        if config_guard_hash(current_config) != before_guard:
            if restore_backup:
                _restore_config_from_backup(backup, config)
            else:
                _restore_config_from_text(config.codex_home / "config.toml", before_config, before_bom)
            print(
                f"A protected Codex configuration block changed during {stage}; "
                "the original config was restored."
            )
            return False
        return True

    registration_passes = 0
    alignment_retries = 0
    plugins_refreshed = False
    settle_deadline = time.monotonic() + max(0.0, float(settle_total_timeout_seconds))

    def wait_for_stable_store_view() -> AppxUpdateSnapshot | None:
        remaining = settle_deadline - time.monotonic()
        if remaining <= 0:
            print("The total Codex Store stability wait reached its bounded limit.")
            return None
        return wait_for_codex_appx_stability(
            consecutive_checks=settle_checks,
            poll_seconds=settle_poll_seconds,
            timeout_seconds=min(max(0.0, float(settle_timeout_seconds)), remaining),
        )

    snapshot = initial_snapshot
    snapshot_is_stable = False

    while True:
        while snapshot.pending_registration:
            if not snapshot_is_stable:
                stable = wait_for_stable_store_view()
                if stable is None:
                    print("Codex remains closed because the Store update view did not stabilize.")
                    return 20
                snapshot = stable
                snapshot_is_stable = True
            if not snapshot.pending_registration:
                break
            if registration_passes >= max(1, int(max_registration_passes)):
                print(
                    "A newer Codex build is still pending after the bounded registration passes. "
                    "Codex remains closed; retry the same daily entry after the Store finishes staging."
                )
                return 20
            target = snapshot.highest_staged_version
            registration_passes += 1
            print(
                f"Codex Store registration pass {registration_passes}/"
                f"{max(1, int(max_registration_passes))}: target={target}"
            )
            registration = run_windows_appx_registration(
                snapshot.app_info,
                apply=True,
                target_version=target,
                timeout_seconds=registration_timeout_seconds,
                poll_seconds=registration_poll_seconds,
            )
            if registration != 0:
                print(
                    "Codex remains closed. Resolve the official Store registration, "
                    "then retry the daily entry."
                )
                return registration
            if not transaction_invariants_hold(
                f"Store registration pass {registration_passes}",
                restore_backup=True,
            ):
                return 20
            stable = wait_for_stable_store_view()
            if stable is None:
                print("Codex remains closed because the post-registration Store view did not stabilize.")
                return 20
            snapshot = stable
            snapshot_is_stable = True

        app = snapshot.app_info
        if app is None:
            print("Codex AppX disappeared before CLI alignment. Codex remains closed.")
            return 20

        # The existing ensure path remains the single source of truth for the
        # versioned, hash-checked CLI bundle.  It is a no-op when aligned.
        ensure = run_windows_update_ensure(config_path)
        if ensure != 0:
            late_snapshot = codex_appx_update_snapshot()
            if late_snapshot.app_info is not None and late_snapshot.pending_registration:
                print("A newer Codex build appeared during CLI alignment; returning to the Store gate.")
                snapshot = late_snapshot
                snapshot_is_stable = False
                continue
            print("Codex remains closed because the matching CLI bundle was not verified.")
            return ensure

        app = windows_codex_app_info() or app
        cli = current_codex_cli_for_plugins(config, app)
        if cli is None:
            print("The current hash-matched Codex CLI was not found for official plugin refresh.")
            return 20

        if force_plugin_refresh or official_plugins_need_refresh(config, app):
            try:
                plugin_config_before, plugin_bom = read_utf8_text_preserving_bom(
                    config.codex_home / "config.toml"
                )
            except OSError as exc:
                print(f"Codex config could not be read before plugin refresh: {type(exc).__name__}")
                return 20
            refresh = refresh_official_bundled_plugins(cli, app, apply=True)
            if refresh != 0:
                # Keep any validated CLI repair, but do not leave a half-written
                # marketplace/config transaction behind.
                _restore_config_from_text(
                    config.codex_home / "config.toml",
                    plugin_config_before,
                    plugin_bom,
                )
                print("Browser/Chrome refresh failed. The previous config was restored and Codex remains closed.")
                return refresh
            plugins_refreshed = True
            force_plugin_refresh = False

        if not transaction_invariants_hold("CLI and Browser/Chrome alignment"):
            return 20

        final_snapshot = codex_appx_update_snapshot()
        if final_snapshot.app_info is None:
            print("OpenAI.Codex AppX package disappeared during final verification.")
            return 20
        aligned_version = str(app.get("Version") or "missing")
        if final_snapshot.pending_registration:
            print("A newer Codex build appeared during final verification; returning to the Store gate.")
            snapshot = final_snapshot
            snapshot_is_stable = False
            continue
        if final_snapshot.current_version != aligned_version:
            alignment_retries += 1
            if alignment_retries > max(1, int(max_registration_passes)):
                print(
                    "The registered Codex version kept changing during final alignment. "
                    "Codex remains closed; retry after Microsoft Store activity settles."
                )
                return 20
            print(
                "Windows registered another Codex build during CLI/plugin alignment; "
                "rechecking the final AppX once more."
            )
            snapshot = final_snapshot
            snapshot_is_stable = False
            continue
        snapshot = final_snapshot
        break

    final_report = inspect_windows_update(
        config,
        include_resources=False,
        app_info=snapshot.app_info,
    )
    if final_report.pending_registration or not final_report.launch_safe:
        _print_report(final_report)
        print("The final AppX/CLI launch gate is not healthy. Codex remains closed.")
        return 20
    final_cli = current_codex_cli_for_plugins(config, snapshot.app_info or {})
    if final_cli is None:
        print("The final current-AppX CLI could not be verified. Codex remains closed.")
        return 20
    ok, detail = verify_official_bundled_plugins(config, snapshot.app_info or {}, final_cli)
    if not ok:
        print("Official Browser/Chrome verification failed: " + detail)
        print(f"Codex remains closed. Update backup: {backup}")
        return 20
    print("Official Browser/Chrome verification: " + detail)
    if not plugins_refreshed:
        print("Browser/Chrome were already aligned with the final AppX marketplace.")
    if not transaction_invariants_hold("final update verification"):
        return 20
    print(
        "Windows update orchestration complete. Account, model catalog, MCP, "
        "projects, and protected state were preserved. "
        f"Store registration passes: {registration_passes}."
    )
    return 0


def _restore_config_from_text(path: Path, text: str, bom: bool) -> None:
    try:
        write_utf8_text_atomic(path, text, bom=bom)
    except OSError:
        pass


def run_windows_browser_ensure(
    config_path: str | None = None,
    *,
    wait_seconds: float = 90,
    settle_seconds: float = 15,
    poll_seconds: float = 3,
    verify_seconds: float = 30,
) -> int:
    """Install Browser once, after the desktop feature gates have settled."""

    if not is_windows():
        print("Windows Browser post-start repair is available only on Windows.")
        return 20
    config = load_config(config_path)
    lock_path = config.path.parent / ".windows-browser-post-start.lock"
    lock_descriptor = _acquire_browser_post_start_lock(lock_path)
    if lock_descriptor is None:
        print("A Browser post-start check is already running; this duplicate check will exit.")
        return 0
    try:
        app = windows_codex_app_info()
        if not app:
            print("OpenAI.Codex AppX package was not found.")
            return 20
        cli_path = current_codex_cli_for_plugins(config, app)
        if cli_path is None:
            print("The current hash-matched Codex CLI bundle was not found.")
            print("Run 'Repair Codex Browser and CLI.cmd' while Codex is fully closed.")
            return 20

        wait_seconds = max(0.0, float(wait_seconds))
        settle_seconds = max(0.0, float(settle_seconds))
        poll_seconds = max(0.1, float(poll_seconds))
        verify_seconds = max(0.0, float(verify_seconds))
        start_deadline = time.monotonic() + wait_seconds
        while not codex_is_running():
            if time.monotonic() >= start_deadline:
                print("Codex did not start before the Browser post-start timeout.")
                return 20
            time.sleep(min(poll_seconds, max(0.0, start_deadline - time.monotonic())))

        if settle_seconds:
            time.sleep(settle_seconds)
        if not codex_is_running():
            print("Codex closed before the Browser post-start check could finish.")
            return 20

        print("Checking Browser after Codex feature initialization...")
        last_error: str | None = None
        feature_deadline = time.monotonic() + wait_seconds
        while True:
            states, last_error = query_codex_plugin_catalog(cli_path)
            browser = states.get(BROWSER_PLUGIN_ID)
            if browser and browser.healthy and _browser_config_ready(config, app):
                print(f"Browser is installed, enabled, and available (version {browser.version}).")
                return 0
            if browser and browser.available:
                break
            if time.monotonic() >= feature_deadline:
                detail = f" Last check: {last_error}." if last_error else ""
                print("Browser did not become available after Codex feature initialization." + detail)
                return 20
            time.sleep(min(poll_seconds, max(0.0, feature_deadline - time.monotonic())))

        print("Browser is available but missing or stale. Installing it through the official Codex CLI...")
        try:
            install = _run_codex_plugin_command(
                cli_path,
                ["add", BROWSER_PLUGIN_ID, "--json"],
                timeout=max(60.0, verify_seconds),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"Browser installation failed: {type(exc).__name__}.")
            return 20
        if install.returncode != 0:
            print(f"Browser installation exited with code {install.returncode}.")
            return 20

        verify_deadline = time.monotonic() + verify_seconds
        while True:
            states, last_error = query_codex_plugin_catalog(cli_path)
            browser = states.get(BROWSER_PLUGIN_ID)
            if browser and browser.healthy and _browser_config_ready(config, app):
                print(f"Browser repair complete (version {browser.version}).")
                print("No Codex restart was requested by the repair.")
                return 0
            if time.monotonic() >= verify_deadline:
                detail = f" Last check: {last_error}." if last_error else ""
                print("Browser installation did not reach a stable enabled state." + detail)
                return 20
            time.sleep(min(poll_seconds, max(0.0, verify_deadline - time.monotonic())))
    finally:
        _release_browser_post_start_lock(lock_path, lock_descriptor)
