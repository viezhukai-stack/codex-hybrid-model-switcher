#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "START_HERE.md",
    "AGENTS.md",
    "FINAL_CHECK.md",
    "README.md",
    "docs/user-success-criteria.md",
    "docs/bridge-health.md",
    "docs/canary-report.md",
    "docs/stock-codex-handoff-validation.md",
    "docs/release-checklist.md",
    "docs/validation-matrix.md",
    "scripts/validate-stock-codex-handoff.py",
    "scripts/validate-install.py",
)

DOC_REQUIREMENTS = {
    "START_HERE.md": (
        "Copy This Prompt Into Codex",
        "bootstrap.py",
        "bridge-health",
        "guarded-switch --dry-run",
        "setup-report",
        "canary-report",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
        "sessions/",
        "LaunchAgent",
        "KeepAlive",
    ),
    "AGENTS.md": (
        "Never switch providers while Codex Desktop is running",
        "docs/bridge-health.md",
        "docs/canary-report.md",
        "guarded-switch --dry-run",
        "config.toml.bak-codex-hybrid-*",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
        "sessions/",
    ),
    "FINAL_CHECK.md": (
        "Complete",
        "Partially complete",
        "Not complete",
        "Needs rollback",
        "bridge-health",
        "canary-report",
        "请不要修改任何文件",
    ),
    "docs/canary-report.md": (
        "canary-report",
        "account-visible",
        "plugins-visible",
        "mcp-visible",
        "project-list-visible",
        "test-chat-responded",
        "bridge-health-passed",
        "setup-report-reviewed",
        "verdict complete",
        "does not include API keys",
    ),
    "docs/user-success-criteria.md": (
        "Account information is still visible",
        "Plugin and MCP entry points are still visible",
        "project list is still visible",
        "A new test conversation responds",
        "bridge-health",
        "canary-report",
        "not complete yet",
    ),
    "docs/bridge-health.md": (
        "read-only",
        "/v1/health",
        "/v1/models",
        "api_key_env",
        "does not edit",
        "does not start the bridge",
    ),
    "docs/stock-codex-handoff-validation.md": (
        "default `bridge` bootstrap dry-run",
        "clean repository copy",
        "canary evidence",
        "does not start a real bridge service",
        "stock Codex handoff validation passed",
    ),
    "docs/release-checklist.md": (
        "python scripts/validate-release-acceptance.py",
        "python scripts/validate-stock-codex-handoff.py",
        "canary-report",
        "security-scan",
        "GitHub Actions passes",
    ),
    "docs/validation-matrix.md": (
        "Stock Codex handoff",
        "Bridge health diagnostic",
        "Canary evidence report",
        "default bridge dry-run",
    ),
}


def run(cmd: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def check_required_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        raise SystemExit(f"missing release acceptance files: {missing}")
    print("OK required files are present")


def check_docs() -> None:
    for rel_path, required_items in DOC_REQUIREMENTS.items():
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        missing = [item for item in required_items if item not in text]
        if missing:
            raise SystemExit(f"{rel_path} missing required release acceptance text: {missing}")
    print("OK release acceptance documentation markers are present")


def check_version_consistency() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    init = (ROOT / "src" / "codex_hybrid_switcher" / "__init__.py").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version_line = next((line for line in pyproject.splitlines() if line.startswith("version = ")), "")
    if not version_line:
        raise SystemExit("pyproject.toml missing project version")
    version = version_line.split("=", 1)[1].strip().strip('"')
    if f'__version__ = "{version}"' not in init:
        raise SystemExit(f"__init__.py version does not match pyproject version {version}")
    if f"## v{version}" not in changelog:
        raise SystemExit(f"CHANGELOG.md missing entry for v{version}")
    print(f"OK version is consistent: {version}")


def run_acceptance(*, quick: bool = False, tmp_root: str | None = None) -> int:
    check_required_files()
    check_docs()
    check_version_consistency()

    run([sys.executable, "-m", "compileall", "-q", "bootstrap.py", "src", "tests", "scripts"])
    run([sys.executable, "-m", "codex_hybrid_switcher", "security-scan", "."])

    if quick:
        print("release acceptance quick validation passed")
        return 0

    handoff_cmd = [sys.executable, "scripts/validate-stock-codex-handoff.py"]
    if tmp_root:
        handoff_cmd.extend(["--tmp-root", tmp_root])
    run(handoff_cmd)
    print("release acceptance validation passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate release acceptance evidence for stock Codex handoff.")
    parser.add_argument("--quick", action="store_true", help="skip the heavier clean-copy handoff validation")
    parser.add_argument("--tmp-root", help="temporary root passed to validate-stock-codex-handoff.py")
    args = parser.parse_args(argv)
    return run_acceptance(quick=args.quick, tmp_root=args.tmp_root)


if __name__ == "__main__":
    raise SystemExit(main())
