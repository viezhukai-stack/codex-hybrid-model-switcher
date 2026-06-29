from __future__ import annotations

import argparse
import socket
from pathlib import Path

from .config import expand_path, load_config
from .security import run_security_scan


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


def run_doctor(config_path: str | None = None, *, strict: bool = False) -> int:
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
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    return run_doctor(args.config, strict=args.strict)
