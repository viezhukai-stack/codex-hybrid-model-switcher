from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from .config import AppConfig, expand_path, load_config
from .smoke import run_smoke


def port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def required_local_paths(config: AppConfig) -> list[tuple[str, Path | None]]:
    local = config.local_model
    return [
        ("llama_server_path", expand_path(local["llama_server_path"]) if local.get("llama_server_path") else None),
        ("model_path", expand_path(local["model_path"]) if local.get("model_path") else None),
        ("mmproj_path", expand_path(local["mmproj_path"]) if local.get("mmproj_path") else None),
    ]


def validate_local_paths(config: AppConfig) -> int:
    ok = True
    for label, path in required_local_paths(config):
        exists = bool(path and path.exists())
        print(f"{'OK' if exists else 'MISSING'} {label}: {path if path else '<not configured>'}")
        ok = ok and exists
    return 0 if ok else 1


def wait_for_bridge(config: AppConfig, *, timeout_seconds: int = 30) -> bool:
    bridge = config.bridge
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if port_open(bridge.host, bridge.port):
            return True
        time.sleep(0.5)
    return False


def start_bridge(config: AppConfig) -> subprocess.Popen[str]:
    cmd = [sys.executable, "-m", "codex_hybrid_switcher", "bridge", "--config", str(config.path)]
    env = os.environ.copy()
    repo_src = str(Path(__file__).resolve().parents[1])
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = repo_src if not existing else repo_src + os.pathsep + existing
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)


def stop_bridge(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def run_local_smoke(
    config_path: str | None = None,
    *,
    use_existing_bridge: bool = False,
    keep_bridge: bool = False,
    skip_vision: bool = False,
    expect_text: str = "OK",
    expect_vision: str = "red",
) -> int:
    config = load_config(config_path)
    if validate_local_paths(config) != 0:
        print("Local smoke stopped before starting the bridge because required files are missing.")
        return 1

    bridge = config.bridge
    existing_bridge = port_open(bridge.host, bridge.port)
    if existing_bridge and not use_existing_bridge:
        print(f"Bridge port already in use: {bridge.host}:{bridge.port}")
        print("Stop the existing service or rerun with --use-existing-bridge.")
        return 2

    proc: subprocess.Popen[str] | None = None
    try:
        if existing_bridge:
            print(f"Using existing bridge on {bridge.host}:{bridge.port}.")
        else:
            proc = start_bridge(config)
            if not wait_for_bridge(config):
                print("Bridge did not become ready within 30 seconds.")
                return 1
            print(f"Started bridge on {bridge.host}:{bridge.port}.")

        code = run_smoke(config_path, skip_vision=skip_vision, expect_text=expect_text, expect_vision=expect_vision)
        if code == 0:
            print("Local smoke passed.")
        else:
            print("Local smoke failed.")
        return code
    finally:
        if proc and not keep_bridge:
            stop_bridge(proc)
            print("Stopped managed bridge.")
        elif proc and keep_bridge:
            print(f"Managed bridge left running with PID {proc.pid}.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--use-existing-bridge", action="store_true")
    parser.add_argument("--keep-bridge", action="store_true")
    parser.add_argument("--skip-vision", action="store_true")
    parser.add_argument("--expect-text", default="OK")
    parser.add_argument("--expect-vision", default="red")
    args = parser.parse_args(argv)
    return run_local_smoke(
        args.config,
        use_existing_bridge=args.use_existing_bridge,
        keep_bridge=args.keep_bridge,
        skip_vision=args.skip_vision,
        expect_text=args.expect_text,
        expect_vision=args.expect_vision,
    )


if __name__ == "__main__":
    raise SystemExit(main())
