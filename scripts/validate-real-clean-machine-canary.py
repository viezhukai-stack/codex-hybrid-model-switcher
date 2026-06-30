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


REQUIRED_MARKERS = (
    "Real Clean Machine Canary",
    "stock Codex Desktop",
    "guarded-switch --dry-run",
    "config.toml.bak-codex-hybrid-*",
    "auth.json",
    "models_cache.json",
    "state_5.sqlite",
    "sessions/",
    "FINAL_CHECK.md",
    "A new test conversation responded",
)


def run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def write_private_config(path: Path, codex_home: Path, work: Path) -> None:
    path.parent.mkdir(parents=True)
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        """model_provider = "openai"
model = "gpt-5.5"

[mcp_servers.example]
command = "example"

[plugins.example]
enabled = true

[projects."/private/project"]
trust_level = "trusted"
""",
        encoding="utf-8",
    )
    (codex_home / "auth.json").write_text('{"token":"do-not-print"}', encoding="utf-8")
    (codex_home / "models_cache.json").write_text('{"models":[]}', encoding="utf-8")
    (codex_home / "state_5.sqlite").write_bytes(b"do-not-print-sqlite")
    (path).write_text(
        json.dumps(
            {
                "codex_home": str(codex_home),
                "providers": [
                    {
                        "id": "cloud-gpt-main",
                        "label": "Private Cloud",
                        "kind": "cloud",
                        "base_url": "https://private-provider.example/v1",
                        "api_key_env": "PRIVATE_PROVIDER_KEY",
                        "model": "private-model",
                        "wire_api": "responses",
                        "route": "bridge",
                    }
                ],
                "local_model": {
                    "id": "local/model",
                    "llama_server_path": str(work / "llama-server"),
                    "model_path": str(work / "private-model.gguf"),
                    "mmproj_path": str(work / "private-mmproj.gguf"),
                },
            }
        ),
        encoding="utf-8",
    )


def assert_not_leaked(text: str, work: Path) -> None:
    forbidden = (
        "private-provider.example",
        str(work),
        "do-not-print",
        "PRIVATE_PROVIDER_KEY=set",
    )
    leaked = [item for item in forbidden if item in text]
    if leaked:
        raise SystemExit(f"real canary template leaked private content: {leaked}")


def validate_template(python: Path, repo: Path, work: Path) -> None:
    config_path = work / "private" / "config.json"
    codex_home = work / "codex-home"
    output = work / "real-clean-machine-canary.md"
    write_private_config(config_path, codex_home, work)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PRIVATE_PROVIDER_KEY"] = "test-provider-key"

    run(
        [
            str(python),
            "-m",
            "codex_hybrid_switcher",
            "real-canary-template",
            "--config",
            str(config_path),
            "--provider-id",
            "cloud-gpt-main",
            "--setup-report",
            str(work / "codex-hybrid-setup-report.md"),
            "--canary-report",
            str(work / "codex-hybrid-canary-evidence.md"),
            "--output",
            str(output),
        ],
        cwd=repo,
        env=env,
    )
    text = output.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
    if missing:
        raise SystemExit(f"real canary template missing required markers: {missing}")
    assert_not_leaked(text, work)
    print(f"real clean machine canary template: {output}")
    print("real clean machine canary validation passed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the real clean-machine canary template generation.")
    parser.add_argument("--tmp-root", default=tempfile.gettempdir(), help="temporary root; defaults to system temp")
    parser.add_argument("--keep", action="store_true", help="keep temporary validation directory")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    tmp_root = Path(args.tmp_root)
    if not tmp_root.exists():
        raise SystemExit(f"temporary root does not exist: {tmp_root}")
    work = Path(tempfile.mkdtemp(prefix="codex-hybrid-real-canary-", dir=tmp_root))
    print(f"real canary validation workspace: {work}")
    try:
        validate_template(Path(sys.executable), repo, work)
    finally:
        if args.keep:
            print(f"kept real canary validation workspace: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
