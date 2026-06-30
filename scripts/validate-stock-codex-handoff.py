#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_HANDOFF_FILES = (
    "START_HERE.md",
    "AGENTS.md",
    "README.md",
    "bootstrap.py",
    "src/codex_hybrid_switcher/__main__.py",
    "scripts/validate-stock-codex-flow.py",
)

REPO_IGNORE_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
}


def run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def run_expect_code(cmd: list[str], *, cwd: Path, env: dict[str, str], expected_code: int) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != expected_code:
        raise SystemExit(f"expected exit code {expected_code}, got {proc.returncode}")
    return proc


def load_stock_flow_module(repo: Path):
    script_path = repo / "scripts" / "validate-stock-codex-flow.py"
    spec = importlib.util.spec_from_file_location("stock_flow_validation", script_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load stock flow helper: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ignore_repo_entries(_dir: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in REPO_IGNORE_DIRS or name.endswith(".egg-info"):
            ignored.add(name)
    return ignored


def copy_clean_repo(source_repo: Path, target_repo: Path) -> None:
    shutil.copytree(source_repo, target_repo, ignore=ignore_repo_entries)
    for required in REQUIRED_HANDOFF_FILES:
        if not (target_repo / required).exists():
            raise SystemExit(f"clean handoff copy is missing required file: {required}")


def assert_handoff_docs(repo: Path) -> None:
    start = (repo / "START_HERE.md").read_text(encoding="utf-8")
    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    readme = (repo / "README.md").read_text(encoding="utf-8")

    required_start = [
        "Copy This Prompt Into Codex",
        "bootstrap.py",
        "guarded-switch --dry-run",
        "setup-report",
        "不要填 API key 原文",
        "config.toml.bak-codex-hybrid-*",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
        "sessions/",
        "rollout",
        "LaunchAgent",
        "KeepAlive",
    ]
    for item in required_start:
        if item not in start:
            raise SystemExit(f"START_HERE.md missing expected handoff guidance: {item}")
    if "START_HERE.md" not in agents:
        raise SystemExit("AGENTS.md does not point agents to START_HERE.md")
    if "START_HERE.md" not in readme:
        raise SystemExit("README.md does not point users to START_HERE.md")


def validate_default_bridge_handoff(
    *,
    python: Path,
    clean_repo: Path,
    private_config: Path,
    codex_home: Path,
    before_repo: dict[str, str],
    before_codex: dict[str, str],
    env: dict[str, str],
    stock_flow,
) -> None:
    bridge_env = env.copy()
    bridge_env.pop("OPENAI_COMPATIBLE_API_KEY", None)
    proc = run(
        [
            str(python),
            "-B",
            "-I",
            "bootstrap.py",
            "--non-interactive",
            "--config",
            str(private_config),
            "--codex-home",
            str(codex_home),
            "--provider-id",
            "cloud-gpt-main",
            "--base-url",
            "https://example.test/v1",
            "--model",
            "provider-gpt-main",
            "--api-key-env",
            "OPENAI_COMPATIBLE_API_KEY",
        ],
        cwd=clean_repo,
        env=bridge_env,
    )
    required = [
        "route=bridge",
        "api_key_env=OPENAI_COMPATIBLE_API_KEY(unset)",
        "Bridge route selected",
        "bridge-health",
        "No files will be changed",
    ]
    missing = [item for item in required if item not in proc.stdout]
    if missing:
        raise SystemExit(f"default bridge bootstrap output missing expected text: {missing}")
    if not private_config.exists():
        raise SystemExit("default bridge bootstrap did not create private config")
    if clean_repo in private_config.parents:
        raise SystemExit("default bridge private config was created inside the repository")
    if stock_flow.snapshot_tree(clean_repo) != before_repo:
        raise SystemExit("default bridge bootstrap polluted the clean handoff repository")
    stock_flow.assert_dry_run_unchanged(before_codex, codex_home)

    data = json.loads(private_config.read_text(encoding="utf-8"))
    data["bridge"]["port"] = 9
    data["bridge"]["llama_port"] = 10
    private_config.write_text(json.dumps(data), encoding="utf-8")
    health = run_expect_code(
        [
            str(python),
            "-B",
            "-m",
            "codex_hybrid_switcher",
            "bridge-health",
            "--config",
            str(private_config),
        ],
        cwd=clean_repo,
        env=bridge_env,
        expected_code=1,
    )
    required_health = [
        "CLOSED bridge TCP port",
        "OPENAI_COMPATIBLE_API_KEY (unset)",
        "env-help",
        "codex_hybrid_switcher bridge",
    ]
    missing_health = [item for item in required_health if item not in health.stdout]
    if missing_health:
        raise SystemExit(f"default bridge-health output missing expected text: {missing_health}")
    if "example.test" in health.stdout:
        raise SystemExit("default bridge-health leaked private upstream hostname")
    print("default bridge handoff dry-run validation passed")


def validate_handoff(python: Path, source_repo: Path, work: Path) -> None:
    clean_repo = work / "downloaded-repo"
    bridge_private_config = work / "private-bridge" / "config.json"
    direct_private_config = work / "private-direct" / "config.json"
    codex_home = work / "stock-codex-home"
    temp_home = work / "home"
    report_path = work / "handoff-report.md"

    copy_clean_repo(source_repo, clean_repo)
    assert_handoff_docs(clean_repo)

    stock_flow = load_stock_flow_module(clean_repo)
    temp_home.mkdir()
    stock_flow.write_stock_codex_home(codex_home)
    before_repo = stock_flow.snapshot_tree(clean_repo)
    before_codex = stock_flow.snapshot_tree(codex_home)

    env = os.environ.copy()
    env["HOME"] = str(temp_home)
    env["PYTHONPATH"] = str(clean_repo / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    try:
        validate_default_bridge_handoff(
            python=python,
            clean_repo=clean_repo,
            private_config=bridge_private_config,
            codex_home=codex_home,
            before_repo=before_repo,
            before_codex=before_codex,
            env=env,
            stock_flow=stock_flow,
        )

        env["OPENAI_COMPATIBLE_API_KEY"] = "test-provider-key"
        proc = run(
            [
                str(python),
                "-B",
                "-I",
                "bootstrap.py",
                "--non-interactive",
                "--config",
                str(direct_private_config),
                "--codex-home",
                str(codex_home),
                "--provider-id",
                "cloud-gpt-main",
                "--base-url",
                "https://example.test/v1",
                "--model",
                "provider-gpt-main",
                "--api-key-env",
                "OPENAI_COMPATIBLE_API_KEY",
                "--cloud-route",
                "direct",
            ],
            cwd=clean_repo,
            env=env,
        )
        for expected in ("Guarded dry-run", "No files will be changed", "setup-report"):
            if expected not in proc.stdout:
                raise SystemExit(f"bootstrap output missing expected handoff text: {expected}")
        if not direct_private_config.exists():
            raise SystemExit("bootstrap did not create private config")
        if clean_repo in direct_private_config.parents:
            raise SystemExit("private config was created inside the repository")
        if stock_flow.snapshot_tree(clean_repo) != before_repo:
            raise SystemExit("bootstrap polluted the clean handoff repository")
        stock_flow.assert_dry_run_unchanged(before_codex, codex_home)

        run(
            [
                str(python),
                "-B",
                "-m",
                "codex_hybrid_switcher",
                "guarded-switch",
                "cloud-gpt-main",
                "--config",
                str(direct_private_config),
                "--force",
            ],
            cwd=clean_repo,
            env=env,
        )
        stock_flow.assert_guarded_apply_scope(before_codex, codex_home)

        run(
            [
                str(python),
                "-B",
                "-m",
                "codex_hybrid_switcher",
                "setup-report",
                "--config",
                str(direct_private_config),
                "--output",
                str(report_path),
            ],
            cwd=clean_repo,
            env=env,
        )
        stock_flow.assert_report_is_redacted(report_path, work)
        print("stock Codex handoff validation passed")
    finally:
        stock_flow.cleanup_bridge(temp_home)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the START_HERE handoff flow from a clean repository copy.")
    parser.add_argument("--tmp-root", default=tempfile.gettempdir(), help="temporary root; defaults to the system temp directory")
    parser.add_argument("--keep", action="store_true", help="keep temporary validation directory")
    args = parser.parse_args(argv)

    source_repo = Path(__file__).resolve().parents[1]
    tmp_root = Path(args.tmp_root)
    if not tmp_root.exists():
        raise SystemExit(f"temporary root does not exist: {tmp_root}")
    work = Path(tempfile.mkdtemp(prefix="codex-hybrid-handoff-", dir=tmp_root))
    print(f"handoff workspace: {work}")
    try:
        validate_handoff(Path(sys.executable), source_repo, work)
    finally:
        if args.keep:
            print(f"kept handoff workspace: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
