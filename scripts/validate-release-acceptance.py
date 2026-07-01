#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "HANDOFF_TO_CODEX.md",
    "START_HERE.md",
    "AGENTS.md",
    "FINAL_CHECK.md",
    "README.md",
    "docs/user-success-criteria.md",
    "docs/bridge-health.md",
    "docs/agent-handoff-drill.md",
    "docs/canary-report.md",
    "docs/real-clean-machine-canary.md",
    "docs/windows-hyperv-clean-vm-canary.md",
    "docs/supervised-handoff-drill.md",
    "docs/windows-one-click-installer.md",
    "docs/final-check.md",
    "docs/stock-codex-handoff-validation.md",
    "docs/release-checklist.md",
    "docs/validation-matrix.md",
    "scripts/validate-stock-codex-handoff.py",
    "scripts/validate-github-entrypoint.py",
    "scripts/validate-agent-handoff-drill.py",
    "scripts/validate-real-clean-machine-canary.py",
    "scripts/validate-install.py",
    "scripts/bootstrap-windows.ps1",
    "scripts/build-windows-one-click-package.py",
    "installer/windows/Install Codex Hybrid.cmd",
    "installer/windows/Install-CodexHybrid.ps1",
    "installer/windows/README.txt",
    "installer/windows/README.zh-CN.txt",
    ".github/ISSUE_TEMPLATE/real_clean_machine_canary.yml",
)

DOC_REQUIREMENTS = {
    "HANDOFF_TO_CODEX.md": (
        "https://github.com/viezhukai-stack/codex-hybrid-model-switcher",
        "stock Codex Desktop",
        "base_url",
        "api_key_env",
        "cloud_route: bridge",
        "validate-agent-handoff-drill.py",
        "guarded-switch --dry-run",
        "real-canary-template",
        "final-check",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
    ),
    "START_HERE.md": (
        "HANDOFF_TO_CODEX.md",
        "Copy This Prompt Into Codex",
        "bootstrap.py",
        "bootstrap-windows.ps1",
        "bridge-health",
        "guarded-switch --dry-run",
        "setup-report",
        "canary-report",
        "real-canary-template",
        "final-check",
        "validate-agent-handoff-drill.py",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
        "sessions/",
        "LaunchAgent",
        "KeepAlive",
    ),
    "AGENTS.md": (
        "HANDOFF_TO_CODEX.md",
        "Never switch providers while Codex Desktop is running",
        "docs/bridge-health.md",
        "docs/agent-handoff-drill.md",
        "docs/real-clean-machine-canary.md",
        "docs/windows-hyperv-clean-vm-canary.md",
        "docs/supervised-handoff-drill.md",
        "docs/final-check.md",
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
        "final-check",
        "请不要修改任何文件",
    ),
    "docs/agent-handoff-drill.md": (
        "stock Codex Desktop",
        "bootstrap.py",
        "Guarded dry-run",
        "setup-report",
        "canary-report",
        "FINAL_CHECK.md",
        "agent handoff drill validation passed",
    ),
    "docs/real-clean-machine-canary.md": (
        "stock Codex Desktop",
        "guarded-switch --dry-run",
        "real-canary-template",
        "FINAL_CHECK.md",
        "docs/windows-hyperv-clean-vm-canary.md",
        "stock-codex-baseline",
        "v2.12.2",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
    ),
    "docs/windows-hyperv-clean-vm-canary.md": (
        "Hyper-V",
        "Windows 11",
        "stock Codex Desktop",
        "stock-codex-baseline",
        "v2.12.2",
        "scripts/bootstrap-windows.ps1",
        "HANDOFF_TO_CODEX.md",
        "cloud_route=bridge",
        "validate-agent-handoff-drill.py",
        "validate-config",
        "bridge-health",
        "guarded-switch --dry-run",
        "config.toml.bak-codex-hybrid-*",
        "codex-hybrid-setup-report.md",
        "codex-hybrid-canary-evidence.md",
        "codex-hybrid-real-clean-machine-canary.md",
        "codex-hybrid-final-check.md",
        "final-check",
        "Complete",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
        "sessions/",
        "rollout logs",
        "local llama.cpp",
    ),
    "docs/supervised-handoff-drill.md": (
        "Supervised Handoff Drill",
        "fixed release zip",
        "scripts/bootstrap-windows.ps1",
        "Python is missing",
        "validate-agent-handoff-drill.py",
        "bootstrap.py",
        "validate-config",
        "env-help",
        "bridge-health",
        "guarded-switch --dry-run",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
        "sessions/",
    ),
    "docs/windows-one-click-installer.md": (
        "Codex-Hybrid-Windows-Netdisk-Setup-v2.13.2.zip",
        "Install Codex Hybrid.cmd",
        "Codex Hybrid Diagnostics.cmd",
        "Install-CodexHybrid.ps1",
        "provider-preset.example.json",
        "payload/codex-hybrid-model-switcher",
        "portable Python",
        "https://developers.openai.com/codex/app",
        "Python 3.12",
        "winget",
        "Git is not required",
        "bundled llama.cpp",
        "APPLY",
        "diagnostics report",
        "GGUF",
        "mmproj",
        "https://github.com/ggml-org/llama.cpp/releases",
        "validate-config",
        "bridge-health",
        "local-smoke",
        "guarded",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
        "sessions/",
        "-Apply",
    ),
    "docs/final-check.md": (
        "final-check",
        "read-only",
        "Complete",
        "Partially complete",
        "Not complete",
        "Needs rollback",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
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
        "final-check",
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
        "python scripts/validate-github-entrypoint.py",
        "python scripts/validate-stock-codex-handoff.py",
        "python scripts/validate-agent-handoff-drill.py",
        "python scripts/validate-real-clean-machine-canary.py",
        "docs/windows-hyperv-clean-vm-canary.md",
        "docs/supervised-handoff-drill.md",
        "stock-codex-baseline",
        "v2.12.2",
        "cloud_route=bridge",
        "codex-hybrid-final-check.md",
        "canary-report",
        "security-scan",
        "GitHub Actions passes",
    ),
    "docs/validation-matrix.md": (
        "GitHub handoff entrypoint",
        "Stock Codex handoff",
        "Agent handoff drill",
        "Real clean-machine canary template",
        "Windows Hyper-V clean VM canary",
        "Supervised handoff drill",
        "Bridge health diagnostic",
        "Canary evidence report",
        "Final check report",
        "stock-codex-baseline",
        "v2.12.2",
        "cloud_route=bridge",
        "default bridge dry-run",
    ),
    ".github/ISSUE_TEMPLATE/real_clean_machine_canary.yml": (
        "Real clean-machine canary",
        "Stock Codex Desktop",
        "HANDOFF_TO_CODEX.md",
        "validate-agent-handoff-drill.py",
        "docs/windows-hyperv-clean-vm-canary.md",
        "Hyper-V",
        "stock-codex-baseline",
        "v2.12.2",
        "cloud_route=bridge",
        "guarded-switch --dry-run",
        "final-check",
        "auth.json",
        "models_cache.json",
        "state_5.sqlite",
        "sessions/",
        "FINAL_CHECK.md",
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
    run([sys.executable, "scripts/validate-github-entrypoint.py"])

    if quick:
        print("release acceptance quick validation passed")
        return 0

    handoff_cmd = [sys.executable, "scripts/validate-stock-codex-handoff.py"]
    if tmp_root:
        handoff_cmd.extend(["--tmp-root", tmp_root])
    run(handoff_cmd)
    drill_cmd = [sys.executable, "scripts/validate-agent-handoff-drill.py"]
    if tmp_root:
        drill_cmd.extend(["--tmp-root", tmp_root])
    run(drill_cmd)
    real_canary_cmd = [sys.executable, "scripts/validate-real-clean-machine-canary.py"]
    if tmp_root:
        real_canary_cmd.extend(["--tmp-root", tmp_root])
    run(real_canary_cmd)
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
