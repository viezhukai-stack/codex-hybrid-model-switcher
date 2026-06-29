#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def write_simulated_codex_config(path: Path) -> str:
    text = """model_provider = "openai"
model = "gpt-5.5"
review_model = "gpt-5.5"

[model_providers.custom]
name = "Old Provider"
base_url = "http://127.0.0.1:1/v1"
wire_api = "responses"

[mcp_servers.example]
command = "example-mcp"

[plugins.example]
enabled = true

[features]
web_search = true
"""
    path.write_text(text, encoding="utf-8")
    return text


def write_validation_config(path: Path, codex_home: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "codex_home": str(codex_home),
                "cc_switch_home": str(path.parent / "cc-switch-home"),
                "bridge": {"host": "127.0.0.1", "port": 19030, "llama_port": 19031, "idle_seconds": 600},
                "providers": [
                    {
                        "id": "cloud-gpt-main",
                        "label": "Cloud GPT Main",
                        "kind": "cloud",
                        "base_url": "https://example.test/v1",
                        "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
                        "model": "provider-gpt-main",
                        "wire_api": "responses",
                    },
                    {
                        "id": "local-gemma",
                        "label": "Local Gemma",
                        "kind": "local",
                        "base_url": "http://127.0.0.1:19030/v1",
                        "model": "local/gemma",
                        "wire_api": "responses",
                    },
                ],
                "local_model": {
                    "id": "local/gemma",
                    "llama_server_path": str(path.parent / "missing-llama-server"),
                    "model_path": str(path.parent / "missing-model.gguf"),
                    "mmproj_path": str(path.parent / "missing-mmproj.gguf"),
                },
            }
        ),
        encoding="utf-8",
    )


def validate_dry_run(python: Path, repo: Path, work: Path) -> None:
    codex_home = work / "codex-home"
    codex_home.mkdir()
    config_toml = codex_home / "config.toml"
    before = write_simulated_codex_config(config_toml)
    config_json = work / "config.json"
    write_validation_config(config_json, codex_home)

    proc = run(
        [
            str(python),
            "-m",
            "codex_hybrid_switcher",
            "switch",
            "cloud-gpt-main",
            "--dry-run",
            "--config",
            str(config_json),
        ],
        cwd=repo,
    )
    after = config_toml.read_text(encoding="utf-8")
    if after != before:
        raise SystemExit("dry-run changed the simulated config.toml")
    required_stdout = [
        'model_provider = "custom"',
        'base_url = "<redacted>"',
    ]
    missing = [item for item in required_stdout if item not in proc.stdout]
    if missing:
        raise SystemExit(f"dry-run output missing expected content: {missing}")
    required_preserved = ["[mcp_servers.example]", "[plugins.example]", "[features]"]
    missing_preserved = [item for item in required_preserved if item not in after]
    if missing_preserved:
        raise SystemExit(f"simulated config lost preserved blocks: {missing_preserved}")

    proc = run(
        [
            str(python),
            "-m",
            "codex_hybrid_switcher",
            "guarded-switch",
            "cloud-gpt-main",
            "--dry-run",
            "--config",
            str(config_json),
        ],
        cwd=repo,
    )
    if config_toml.read_text(encoding="utf-8") != before:
        raise SystemExit("guarded dry-run changed the simulated config.toml")
    if "Protected file hashes before switch" not in proc.stdout:
        raise SystemExit("guarded dry-run did not print protected hash preflight")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run isolated install validation without touching real Codex state.")
    parser.add_argument("--tmp-root", default="/private/tmp", help="temporary root; defaults to /private/tmp")
    parser.add_argument("--keep", action="store_true", help="keep temporary validation directory")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    tmp_root = Path(args.tmp_root)
    if not tmp_root.exists():
        raise SystemExit(f"temporary root does not exist: {tmp_root}")
    work = Path(tempfile.mkdtemp(prefix="codex-hybrid-install-", dir=tmp_root))
    print(f"validation workspace: {work}")
    try:
        venv = work / ".venv"
        run([sys.executable, "-m", "venv", str(venv)], cwd=repo)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python), "-m", "pip", "install", "-e", ".[dev]"], cwd=repo)
        run([str(python), "-m", "compileall", "-q", "src", "tests"], cwd=repo)
        run([str(python), "-m", "pytest"], cwd=repo)
        run([str(python), "-m", "codex_hybrid_switcher", "security-scan", "."], cwd=repo)
        for platform in ("macos", "windows"):
            generated_config = work / f"generated-private-{platform}" / "config.json"
            run(
                [
                    str(python),
                    "-m",
                    "codex_hybrid_switcher",
                    "init-config",
                    "--platform",
                    platform,
                    "--output",
                    str(generated_config),
                ],
                cwd=repo,
            )
            run([str(python), "-m", "codex_hybrid_switcher", "validate-config", "--config", str(generated_config)], cwd=repo)
        validation_config = work / "doctor-config.json"
        codex_home = work / "doctor-codex-home"
        codex_home.mkdir()
        write_validation_config(validation_config, codex_home)
        run([str(python), "-m", "codex_hybrid_switcher", "doctor", "--config", str(validation_config)], cwd=repo)
        validate_dry_run(python, repo, work)
        print("install validation passed")
    finally:
        if args.keep:
            print(f"kept validation workspace: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
