#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER_ROOT = ROOT / "installer" / "windows"
PAYLOAD_PREFIX = Path("payload") / "codex-hybrid-model-switcher"

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("version not found in pyproject.toml")
    return match.group(1)


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    if path.name in {".DS_Store"}:
        return False
    return True


def git_tracked_files() -> list[Path]:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    files = []
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        rel = Path(raw.decode("utf-8"))
        if should_include(rel):
            files.append(rel)
    return files


def fallback_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if should_include(rel):
            files.append(rel)
    return files


def project_payload_files() -> list[Path]:
    files = git_tracked_files() or fallback_files()
    required = {
        Path("bootstrap.py"),
        Path("pyproject.toml"),
        Path("src/codex_hybrid_switcher/__init__.py"),
        Path("scripts/windows-provider-switch.ps1"),
        Path("scripts/install-windows-launcher.ps1"),
    }
    present = set(files)
    missing = sorted(str(path) for path in required if path not in present)
    if missing:
        raise SystemExit(f"project payload is missing required files: {', '.join(missing)}")
    return sorted(files)


def add_project_payload(archive: zipfile.ZipFile) -> None:
    for rel in project_payload_files():
        archive.write(ROOT / rel, PAYLOAD_PREFIX / rel)


def add_llama_payload(archive: zipfile.ZipFile, llama_dir: Path) -> None:
    if not llama_dir.exists():
        raise SystemExit(f"llama directory does not exist: {llama_dir}")
    server = next(llama_dir.rglob("llama-server.exe"), None)
    if server is None:
        raise SystemExit(f"llama-server.exe not found under: {llama_dir}")
    for path in llama_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(llama_dir)
        if should_include(rel):
            archive.write(path, Path("payload") / "llama.cpp" / rel)


def build(
    output: Path | None = None,
    *,
    thin: bool = False,
    llama_dir: Path | None = None,
) -> Path:
    version = project_version()
    output = output or (ROOT / "dist" / f"Codex-Hybrid-Windows-Netdisk-Setup-v{version}.zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    files = (
        INSTALLER_ROOT / "Install Codex Hybrid.cmd",
        INSTALLER_ROOT / "Install-CodexHybrid.ps1",
        INSTALLER_ROOT / "README.txt",
        INSTALLER_ROOT / "README.zh-CN.txt",
    )
    for file in files:
        if not file.exists():
            raise SystemExit(f"missing installer file: {file}")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.name)
        if not thin:
            add_project_payload(archive)
        if llama_dir is not None:
            add_llama_payload(archive, llama_dir)
    print(f"built {output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Windows netdisk one-click setup zip.")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--thin",
        action="store_true",
        help="build the old script-only package; the installer will download the project release from GitHub",
    )
    parser.add_argument(
        "--include-llama-dir",
        type=Path,
        help="optional llama.cpp runtime directory to bundle under payload/llama.cpp",
    )
    args = parser.parse_args()
    build(args.output, thin=args.thin, llama_dir=args.include_llama_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
