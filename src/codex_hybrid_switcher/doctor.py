from __future__ import annotations

import argparse
import socket
from pathlib import Path

from .config import expand_path, load_config


def port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def check_path(label: str, path: Path) -> bool:
    ok = path.exists()
    print(f"{'OK' if ok else 'MISSING'} {label}: {path}")
    return ok


def run_doctor(config_path: str | None = None) -> int:
    config = load_config(config_path)
    ok = True
    ok &= check_path("Codex home", config.codex_home)
    ok &= check_path("config file", config.path)
    local = config.local_model
    for key in ("llama_server_path", "model_path", "mmproj_path"):
        if key in local:
            ok &= check_path(key, expand_path(local[key]))
    bridge = config.bridge
    print(f"{'OPEN' if port_open(bridge.host, bridge.port) else 'CLOSED'} bridge port: {bridge.host}:{bridge.port}")
    print(f"{'OPEN' if port_open(bridge.host, bridge.llama_port) else 'CLOSED'} llama port: {bridge.host}:{bridge.llama_port}")
    print("Providers:")
    for provider in config.providers:
        print(f"  - {provider.get('id')} ({provider.get('kind')}) -> {provider.get('model')}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args(argv)
    return run_doctor(args.config)

