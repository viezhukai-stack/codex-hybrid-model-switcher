#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER_ROOT = ROOT / "installer" / "windows"
PAYLOAD_PREFIX = Path("payload") / "codex-hybrid-model-switcher"
PYTHON_EMBED_VERSION = "3.12.10"
PYTHON_EMBED_NAME = f"python-{PYTHON_EMBED_VERSION}-embed-amd64.zip"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_EMBED_VERSION}/{PYTHON_EMBED_NAME}"
PYTHON_EMBED_SHA256 = "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"

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
        Path("scripts/windows-restore-official.ps1"),
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


def add_directory_payload(archive: zipfile.ZipFile, source_dir: Path, archive_prefix: Path) -> None:
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source_dir)
        if should_include(rel):
            archive.write(path, archive_prefix / rel)


def add_llama_payload(archive: zipfile.ZipFile, llama_dir: Path) -> None:
    if not llama_dir.exists():
        raise SystemExit(f"llama directory does not exist: {llama_dir}")
    server = next(llama_dir.rglob("llama-server.exe"), None)
    if server is None:
        raise SystemExit(f"llama-server.exe not found under: {llama_dir}")
    add_directory_payload(archive, llama_dir, Path("payload") / "llama.cpp")


def add_python_payload(archive: zipfile.ZipFile, python_dir: Path) -> None:
    if not python_dir.exists():
        raise SystemExit(f"python directory does not exist: {python_dir}")
    python_exe = next(python_dir.rglob("python.exe"), None)
    if python_exe is None:
        raise SystemExit(f"python.exe not found under: {python_dir}")
    add_directory_payload(archive, python_dir, Path("payload") / "python")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_portable_python() -> Path:
    cache = ROOT / ".package-cache"
    zip_path = cache / PYTHON_EMBED_NAME
    extract_dir = cache / f"python-{PYTHON_EMBED_VERSION}-embed-amd64"
    cache.mkdir(parents=True, exist_ok=True)
    if not zip_path.exists():
        print(f"downloading portable Python {PYTHON_EMBED_VERSION} from python.org")
        try:
            urllib.request.urlretrieve(PYTHON_EMBED_URL, zip_path)
        except Exception:
            subprocess.run(["curl", "-L", PYTHON_EMBED_URL, "-o", str(zip_path)], check=True)
    actual = sha256(zip_path)
    if actual != PYTHON_EMBED_SHA256:
        raise SystemExit(f"portable Python sha256 mismatch: expected {PYTHON_EMBED_SHA256}, got {actual}")
    if not (extract_dir / "python.exe").exists():
        if extract_dir.exists():
            for path in sorted(extract_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            extract_dir.rmdir()
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
    return extract_dir


def build(
    output: Path | None = None,
    *,
    thin: bool = False,
    llama_dir: Path | None = None,
    python_dir: Path | None = None,
    bundle_python: bool = True,
) -> Path:
    version = project_version()
    output = output or (ROOT / "dist" / f"Codex-Hybrid-Windows-Netdisk-Setup-v{version}.zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_name(f"{output.name}.tmp")
    if temp_output.exists():
        temp_output.unlink()
    files = (
        INSTALLER_ROOT / "Install Codex Hybrid.cmd",
        INSTALLER_ROOT / "Codex Hybrid Diagnostics.cmd",
        INSTALLER_ROOT / "Restore Official Codex.cmd",
        INSTALLER_ROOT / "Install-CodexHybrid.ps1",
        INSTALLER_ROOT / "README.txt",
        INSTALLER_ROOT / "README.zh-CN.txt",
        INSTALLER_ROOT / "provider-preset.example.json",
    )
    for file in files:
        if not file.exists():
            raise SystemExit(f"missing installer file: {file}")
    with zipfile.ZipFile(temp_output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.name)
        if not thin:
            add_project_payload(archive)
        if llama_dir is not None:
            add_llama_payload(archive, llama_dir)
        if python_dir is None and bundle_python and not thin:
            python_dir = ensure_portable_python()
        if python_dir is not None:
            add_python_payload(archive, python_dir)
    shutil.move(str(temp_output), output)
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
    parser.add_argument(
        "--include-python-dir",
        type=Path,
        help="optional portable Python directory to bundle under payload/python",
    )
    parser.add_argument(
        "--no-python",
        action="store_true",
        help="do not bundle portable Python; the installer will use system Python or winget instead",
    )
    args = parser.parse_args()
    build(
        args.output,
        thin=args.thin,
        llama_dir=args.include_llama_dir,
        python_dir=args.include_python_dir,
        bundle_python=not args.no_python,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
