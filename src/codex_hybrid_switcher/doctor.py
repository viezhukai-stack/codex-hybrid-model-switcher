from __future__ import annotations

import argparse
import json
import os
import plistlib
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import expand_path, load_config
from .security import run_security_scan
from .switcher import protected_hashes


def port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def check_path(label: str, path: Path, *, required: bool = True) -> bool:
    ok = path.exists()
    if ok:
        status = "OK"
    else:
        status = "MISSING" if required else "WARN"
    print(f"{status} {label}: {path}")
    return ok


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def macos_codex_app_paths() -> list[Path]:
    candidates: list[Path] = []
    try:
        proc = subprocess.run(
            ["mdfind", "kMDItemCFBundleIdentifier == 'com.openai.codex'"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        candidates.extend(Path(line.strip()) for line in proc.stdout.splitlines() if line.strip().endswith(".app"))
    except OSError:
        pass
    candidates.extend(
        [
            Path("/Applications/ChatGPT.app"),
            Path.home() / "Applications/ChatGPT.app",
            Path("/Applications/Codex.app"),
            Path.home() / "Applications/Codex.app",
        ]
    )
    result: list[Path] = []
    for candidate in candidates:
        if candidate.is_dir() and candidate not in result:
            result.append(candidate)
    return result


def windows_codex_app_info() -> dict[str, str] | None:
    script = (
        "$p=Get-AppxPackage OpenAI.Codex | Select-Object -First 1 Name,Version,PackageFamilyName,InstallLocation;"
        "if($p){$p|ConvertTo-Json -Compress}"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        data = json.loads(proc.stdout or "null")
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return {str(key): str(value) for key, value in data.items() if value is not None}


def native_codex_app_info() -> dict[str, str] | None:
    if sys.platform == "darwin":
        for app in macos_codex_app_paths():
            plist = app / "Contents/Info.plist"
            try:
                with plist.open("rb") as handle:
                    data = plistlib.load(handle)
            except (OSError, plistlib.InvalidFileException):
                continue
            return {
                "name": app.stem,
                "path": str(app),
                "bundle_id": str(data.get("CFBundleIdentifier") or ""),
                "version": str(data.get("CFBundleShortVersionString") or data.get("CFBundleVersion") or ""),
            }
        return None
    if os.name == "nt":
        data = windows_codex_app_info()
        if not data:
            return None
        return {
            "name": data.get("Name", "OpenAI.Codex"),
            "path": data.get("InstallLocation", ""),
            "bundle_id": data.get("PackageFamilyName", ""),
            "version": data.get("Version", ""),
        }
    return None


def native_codex_cli_path(app_info: dict[str, str] | None) -> Path | None:
    if not app_info:
        return None
    root = Path(app_info.get("path") or "")
    candidates = (
        [root / "Contents/Resources/codex"]
        if sys.platform == "darwin"
        else [root / "app/resources/codex.exe", root / "resources/codex.exe"]
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def catalog_model_ids(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        items = payload.get("models") or payload.get("data") or []
    else:
        items = payload
    if not isinstance(items, list):
        return []
    ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get("slug") or item.get("id") or item.get("model")
        if isinstance(value, str) and value and value not in ids:
            ids.append(value)
    return ids


def run_native_command(args: list[str], *, merge_stderr: bool = False) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
    try:
        proc = subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if merge_stderr else subprocess.DEVNULL,
            check=False,
        )
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return proc, None


def run_native_codex_checks(config) -> bool:
    app_info = native_codex_app_info()
    if not app_info:
        print("WARN native Codex app: not found")
        return False
    print(f"OK native Codex app: {app_info['name']} {app_info['version']} ({app_info['bundle_id']})")
    cli = native_codex_cli_path(app_info)
    if not cli:
        print("WARN bundled Codex CLI: not found")
        return False

    hashes_ok = True
    try:
        before = protected_hashes(config)
    except OSError as exc:
        before = None
        hashes_ok = False
        print(f"WARN native diagnostics could not hash protected Codex files before checks: {type(exc).__name__}")

    version, version_error = run_native_command([str(cli), "--version"], merge_stderr=True)
    version_ok = version is not None and version.returncode == 0
    version_output = version.stdout.strip() if version is not None else version_error
    print(f"{'OK' if version_ok else 'WARN'} bundled Codex CLI: {version_output or '<no version>'}")

    doctor, doctor_error = run_native_command([str(cli), "doctor", "--json"])
    try:
        doctor_payload = json.loads(doctor.stdout or "{}") if doctor is not None else {}
        doctor_json = isinstance(doctor_payload, dict)
    except json.JSONDecodeError:
        doctor_payload = {}
        doctor_json = False
    doctor_status = str(
        doctor_payload.get("overallStatus")
        or (doctor_error if doctor is None else ("ok" if doctor.returncode == 0 else "warn"))
    )
    failed_checks = [
        str(check_id)
        for check_id, check in (doctor_payload.get("checks") or {}).items()
        if isinstance(check, dict) and str(check.get("status") or "").lower() not in {"ok", "pass"}
    ]
    doctor_ok = (
        doctor is not None
        and doctor.returncode == 0
        and doctor_json
        and doctor_status.lower() not in {"fail", "error"}
    )
    print(f"{'OK' if doctor_ok else 'WARN'} native codex doctor --json: {doctor_status}")
    if failed_checks:
        print("  - non-passing checks: " + ", ".join(failed_checks))

    models, models_error = run_native_command([str(cli), "debug", "models", "--bundled"])
    try:
        model_ids = catalog_model_ids(json.loads(models.stdout or "{}")) if models is not None else []
    except json.JSONDecodeError:
        model_ids = []
    models_ok = models is not None and models.returncode == 0 and bool(model_ids)
    model_status = f"{len(model_ids)} models" if models is not None else str(models_error or "unavailable")
    print(f"{'OK' if models_ok else 'WARN'} bundled model catalog: {model_status}")
    if model_ids:
        print("  - " + ", ".join(model_ids))

    try:
        after = protected_hashes(config)
    except OSError as exc:
        after = None
        hashes_ok = False
        print(f"WARN native diagnostics could not hash protected Codex files after checks: {type(exc).__name__}")
    if before is not None and after is not None:
        changed = [name for name in before if before[name] != after[name]]
        if changed:
            print("ERROR native diagnostics changed protected Codex files: " + ", ".join(changed))
            return False
        print("OK native diagnostics left protected Codex files unchanged")
    else:
        print("WARN protected-file comparison was incomplete")
    return version_ok and doctor_ok and models_ok and hashes_ok


def run_doctor(config_path: str | None = None, *, strict: bool = False, native_codex: bool = False) -> int:
    config = load_config(config_path)
    ok = True
    ok &= check_path("config file", config.path)
    codex_home_ok = check_path("Codex home", config.codex_home, required=strict)
    ok &= codex_home_ok if strict else True
    local = config.local_model
    for key in ("llama_server_path", "model_path", "mmproj_path"):
        if key in local:
            path_ok = check_path(key, expand_path(local[key]), required=strict)
            ok &= path_ok if strict else True
    bridge = config.bridge
    bridge_open = port_open(bridge.host, bridge.port)
    llama_open = port_open(bridge.host, bridge.llama_port)
    print(f"{'OPEN' if bridge_open else 'CLOSED'} bridge port: {bridge.host}:{bridge.port}")
    print(f"{'OPEN' if llama_open else 'CLOSED'} llama port: {bridge.host}:{bridge.llama_port}")
    print("Providers:")
    for provider in config.providers:
        print(f"  - {provider.get('id')} ({provider.get('kind')}) -> {provider.get('model')}")
    if strict:
        print("Security scan:")
        ok &= run_security_scan(str(repo_root())) == 0
    if native_codex:
        print("Native Codex diagnostics:")
        ok &= run_native_codex_checks(config)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--native-codex", action="store_true")
    args = parser.parse_args(argv)
    return run_doctor(args.config, strict=args.strict, native_codex=args.native_codex)
