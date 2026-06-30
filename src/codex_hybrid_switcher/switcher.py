from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import signal
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from .config import AppConfig, load_config

PROTECTED_CODEX_FILES = ("auth.json", "models_cache.json", "state_5.sqlite")
MANAGED_CUSTOM_PROVIDER_KEYS = {"name", "base_url", "wire_api", "requires_openai_auth"}
MANAGED_ROOT_KEYS = {"model_provider", "model", "review_model"}


def codex_config_path(config: AppConfig) -> Path:
    return config.codex_home / "config.toml"


def protected_codex_paths(config: AppConfig) -> list[Path]:
    return [config.codex_home / name for name in PROTECTED_CODEX_FILES]


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_hashes(config: AppConfig) -> dict[str, str | None]:
    return {path.name: file_hash(path) for path in protected_codex_paths(config)}


def provider_requires_bridge(provider: dict, config: AppConfig) -> bool:
    kind = provider.get("kind")
    if kind == "local":
        return True
    return kind == "cloud" and str(provider.get("route") or "direct") == "bridge"


def codex_base_url(provider: dict, config: AppConfig) -> str:
    if provider_requires_bridge(provider, config):
        return f"http://{config.bridge.host}:{config.bridge.port}/v1"
    return str(provider.get("base_url") or f"http://127.0.0.1:{config.bridge.port}/v1")


def missing_cloud_api_key_env(provider: dict) -> str | None:
    if provider.get("kind") != "cloud" or str(provider.get("route") or "direct") != "bridge":
        return None
    env_name = str(provider.get("api_key_env") or "")
    if not env_name or not os.environ.get(env_name):
        return env_name or "<missing>"
    return None


def codex_is_running() -> bool:
    try:
        if sys.platform == "win32":
            proc = subprocess.run(["tasklist"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
            if proc.returncode != 0:
                return True
            return "Codex" in proc.stdout
        proc = subprocess.run(["ps", "-axo", "command"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        if proc.returncode != 0:
            return True
        return "Codex.app" in proc.stdout or "codex app-server" in proc.stdout
    except OSError:
        return True


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak-codex-hybrid-{stamp}")
    shutil.copy2(path, backup)
    return backup


def runtime_dir(config: AppConfig) -> Path:
    path = Path.home() / ".codex-hybrid-model-switcher"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bridge_pid_file(config: AppConfig) -> Path:
    return runtime_dir(config) / "bridge.pid"


def bridge_log_file(config: AppConfig) -> Path:
    return runtime_dir(config) / "bridge.log"


def port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def process_alive(pid: int) -> bool:
    if sys.platform == "win32":
        proc = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return str(pid) in proc.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_bridge_pid(config: AppConfig) -> int | None:
    path = bridge_pid_file(config)
    if not path.exists():
        return None
    try:
        pid = int(path.read_text().strip())
    except ValueError:
        return None
    return pid if process_alive(pid) else None


def start_bridge(config: AppConfig) -> None:
    bridge = config.bridge
    if port_open(bridge.host, bridge.port):
        return
    cmd = [sys.executable, "-m", "codex_hybrid_switcher", "bridge", "--config", str(config.path)]
    creationflags = 0
    if sys.platform == "win32":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
        )
    log_path = bridge_log_file(config)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("ab")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
    finally:
        log_handle.close()
    bridge_pid_file(config).write_text(str(proc.pid), encoding="utf-8")
    for _ in range(30):
        time.sleep(1)
        if port_open(bridge.host, bridge.port):
            return
        if proc.poll() is not None:
            raise RuntimeError("bridge process exited before becoming healthy")
    raise RuntimeError("bridge did not become healthy within 30 seconds")


def stop_bridge(config: AppConfig) -> None:
    pid = read_bridge_pid(config)
    if not pid:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return
    os.kill(pid, signal.SIGTERM if hasattr(signal, "SIGTERM") else signal.SIGINT)
    for _ in range(20):
        if not process_alive(pid):
            break
        time.sleep(0.5)
    if process_alive(pid):
        os.kill(pid, signal.SIGKILL if hasattr(signal, "SIGKILL") else signal.SIGTERM)


def render_config(provider: dict, config: AppConfig, *, root_extras: str = "", custom_provider_extras: str = "") -> str:
    model = str(provider.get("model") or "gpt-5.5")
    root = root_extras.strip()
    if provider.get("kind") == "official":
        text = f'model_provider = "openai"\nmodel = "{model}"\nreview_model = "{model}"\n'
        if root:
            text += f"\n{root}\n"
        return text

    provider_id = "custom"
    base_url = codex_base_url(provider, config)
    wire_api = str(provider.get("wire_api") or "responses")
    text = (
        f'model_provider = "{provider_id}"\n'
        f'model = "{model}"\n'
        f'review_model = "{model}"\n'
    )
    if root:
        text += f"\n{root}\n"
    text += (
        "\n"
        f"[model_providers.{provider_id}]\n"
        f'name = "{provider.get("label") or provider.get("id")}"\n'
        f'base_url = "{base_url}"\n'
        f'wire_api = "{wire_api}"\n'
        "requires_openai_auth = true\n"
    )
    extras = custom_provider_extras.strip()
    if extras:
        text += f"\n{extras}\n"
    return text


def build_config_text(existing: str, provider: dict, config: AppConfig) -> str:
    root_preserved, section_preserved = split_preserved_config(existing)
    managed = render_config(
        provider,
        config,
        root_extras=root_preserved,
        custom_provider_extras=extract_custom_provider_extras(existing),
    ).rstrip()
    preserved = section_preserved.strip()
    if preserved:
        return f"{managed}\n\n{preserved}\n"
    return f"{managed}\n"


def extract_custom_provider_extras(existing: str) -> str:
    lines = existing.splitlines()
    extras: list[str] = []
    in_managed_provider = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped == "[model_providers.custom]":
                in_managed_provider = True
                continue
            if in_managed_provider:
                break

        if not in_managed_provider:
            continue

        if not stripped or stripped.startswith("#"):
            extras.append(line)
            continue

        key = stripped.split("=", 1)[0].strip().lower()
        if key in MANAGED_CUSTOM_PROVIDER_KEYS:
            continue
        extras.append(line)

    text = "\n".join(extras).strip()
    return text


def strip_managed_config(existing: str) -> str:
    root_preserved, section_preserved = split_preserved_config(existing)
    text = "\n\n".join(part.strip() for part in (root_preserved, section_preserved) if part.strip())
    return text + ("\n\n" if text else "")


def split_preserved_config(existing: str) -> tuple[str, str]:
    lines = existing.splitlines()
    root_kept: list[str] = []
    section_kept: list[str] = []
    in_managed_provider = False
    in_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = True
            if stripped == "[model_providers.custom]":
                in_managed_provider = True
                continue
            in_managed_provider = False

        if in_managed_provider:
            continue

        if not in_section:
            key = stripped.split("=", 1)[0].strip().lower()
            if key in MANAGED_ROOT_KEYS:
                continue
            root_kept.append(line)
            continue

        section_kept.append(line)

    return "\n".join(root_kept).strip(), "\n".join(section_kept).strip()


def unified_diff(path: Path, before: str, after: str) -> str:
    before_lines = [redact_config_line(line) for line in before.splitlines(keepends=True)]
    after_lines = [redact_config_line(line) for line in after.splitlines(keepends=True)]
    return "".join(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"{path.name} (current)",
            tofile=f"{path.name} (planned)",
        )
    )


def redact_config_line(line: str) -> str:
    key = line.lstrip("+- ").split("=", 1)[0].strip().lower()
    private_keys = {
        "base_url",
        "name",
        "experimental_bearer_token",
        "bearer_token",
        "api_key",
        "access" + "_token",
        "refresh" + "_token",
        "id" + "_token",
        "password",
    }
    if key not in private_keys:
        return line
    prefix = line[: len(line) - len(line.lstrip("+- "))]
    newline = "\n" if line.endswith("\n") else ""
    return f'{prefix}{key} = "<redacted>"{newline}'


def switch_provider(provider_id: str, config_path: str | None = None, *, force: bool = False, dry_run: bool = False) -> int:
    config = load_config(config_path)
    provider = config.provider(provider_id)
    path = codex_config_path(config)
    existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    text = build_config_text(existing, provider, config)
    if dry_run:
        print("Dry run: no files changed, no backup created, bridge not started or stopped.")
        if provider_requires_bridge(provider, config):
            print(f"Bridge route selected: Codex will point to http://{config.bridge.host}:{config.bridge.port}/v1 on apply.")
            missing_env = missing_cloud_api_key_env(provider)
            if missing_env:
                print(f"Note: API key environment variable is not set for this shell: {missing_env}")
        diff = unified_diff(path, existing, text)
        print(diff if diff else "No config changes required.")
        return 0
    missing_env = missing_cloud_api_key_env(provider)
    if missing_env:
        print(f"Cloud bridge route requires API key environment variable to be set: {missing_env}")
        print("Set it in your shell or OS environment, then rerun guarded-switch.")
        return 2
    if codex_is_running() and not force:
        print("Codex Desktop appears to be running. Quit Codex completely, then rerun the switch.")
        return 2
    requires_bridge = provider_requires_bridge(provider, config)
    if requires_bridge:
        start_bridge(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = backup_file(path)
    path.write_text(text, encoding="utf-8")
    if not requires_bridge:
        stop_bridge(config)
    if backup:
        print(f"Backed up previous config: {backup}")
    print(f"Switched Codex provider to {provider_id}")
    return 0


def guarded_switch_provider(
    provider_id: str,
    config_path: str | None = None,
    *,
    force: bool = False,
    dry_run: bool = False,
    allow_local: bool = False,
    skip_local_smoke: bool = False,
) -> int:
    config = load_config(config_path)
    provider = config.provider(provider_id)
    if provider.get("kind") == "local":
        if not allow_local:
            print("Guarded switch refuses local providers unless --allow-local is explicit.")
            print("Run local-smoke first, then rerun guarded-switch with --allow-local.")
            return 2
        if dry_run:
            print("Local provider selected. Dry-run will not start bridge or llama.cpp.")
        elif not skip_local_smoke:
            print("Running local smoke before switching to the local provider.")
            from .local_smoke import run_local_smoke

            smoke_code = run_local_smoke(str(config.path))
            if smoke_code != 0:
                print("Local smoke failed; guarded switch stopped before writing Codex config.")
                return smoke_code
        else:
            print("Skipping local smoke because --skip-local-smoke was provided.")
    before = protected_hashes(config)
    print("Protected file hashes before switch:")
    for name, digest in before.items():
        print(f"  - {name}: {'missing' if digest is None else digest[:12]}")
    code = switch_provider(provider_id, str(config.path), force=force, dry_run=dry_run)
    if code != 0 or dry_run:
        return code
    after = protected_hashes(config)
    changed = [name for name in before if before[name] != after[name]]
    print("Protected file hashes after switch:")
    for name, digest in after.items():
        print(f"  - {name}: {'missing' if digest is None else digest[:12]}")
    if changed:
        print("Protected Codex files changed unexpectedly:")
        for name in changed:
            print(f"  - {name}")
        print("Stop and restore from backup before continuing.")
        return 1
    print("Protected Codex files unchanged.")
    return 0


def interactive_menu(config_path: str | None = None, *, force: bool = False, dry_run: bool = False) -> int:
    config = load_config(config_path)
    print("Codex Hybrid Model Switcher")
    print()
    for idx, provider in enumerate(config.providers, 1):
        print(f"{idx}. {provider.get('label') or provider.get('id')} [{provider.get('kind')}]")
    print()
    choice = input("Choose provider number: ").strip()
    try:
        provider = config.providers[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return 2
    return switch_provider(str(provider["id"]), str(config.path), force=force, dry_run=dry_run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("provider_id", nargs="?")
    parser.add_argument("--config")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not args.provider_id:
        return interactive_menu(args.config, force=args.force, dry_run=args.dry_run)
    return switch_provider(args.provider_id, args.config, force=args.force, dry_run=args.dry_run)
