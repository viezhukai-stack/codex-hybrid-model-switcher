#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER_ROOT = ROOT / "installer" / "macos"
PAYLOAD_PREFIX = Path("payload") / "codex-hybrid-model-switcher"
DEFAULT_MODEL_SOURCE_URL = "https://huggingface.co/llmfan46/gemma-4-E4B-it-ultra-uncensored-heretic-GGUF"
DEFAULT_MODEL_LICENSE = "Apache-2.0"
LLAMA_VERSION = "b9860"
LLAMA_MACOS_ASSETS = {
    "macos-x64": {
        "name": f"llama-{LLAMA_VERSION}-bin-macos-x64.tar.gz",
        "url": f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_VERSION}/llama-{LLAMA_VERSION}-bin-macos-x64.tar.gz",
    },
    "macos-arm64": {
        "name": f"llama-{LLAMA_VERSION}-bin-macos-arm64.tar.gz",
        "url": f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_VERSION}/llama-{LLAMA_VERSION}-bin-macos-arm64.tar.gz",
    },
}

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    ".package-cache",
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


def git_worktree_files() -> list[Path]:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
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
    files = git_worktree_files() or fallback_files()
    required = {
        Path("bootstrap.py"),
        Path("pyproject.toml"),
        Path("src/codex_hybrid_switcher/__init__.py"),
        Path("src/codex_hybrid_switcher/history.py"),
        Path("scripts/macos-provider-switch.sh"),
        Path("scripts/macos-provider-menu.sh"),
        Path("scripts/macos-restore-official.sh"),
        Path("scripts/install-macos-launcher.sh"),
    }
    present = set(files)
    missing = sorted(str(path) for path in required if path not in present)
    if missing:
        raise SystemExit(f"project payload is missing required files: {', '.join(missing)}")
    return sorted(files)


def write_file(archive: zipfile.ZipFile, source: Path, target: Path) -> None:
    archive.write(source, target)
    info = archive.getinfo(str(target))
    if source.stat().st_mode & 0o111:
        info.external_attr = (0o100755 & 0xFFFF) << 16


def add_project_payload(archive: zipfile.ZipFile) -> None:
    for rel in project_payload_files():
        write_file(archive, ROOT / rel, PAYLOAD_PREFIX / rel)


def add_directory_payload(archive: zipfile.ZipFile, source_dir: Path, archive_prefix: Path) -> None:
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source_dir)
        if should_include(rel):
            write_file(archive, path, archive_prefix / rel)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_payload_files(model_dir: Path) -> tuple[Path, Path, list[Path]]:
    if not model_dir.exists():
        raise SystemExit(f"model directory does not exist: {model_dir}")
    ggufs = sorted((path for path in model_dir.glob("*.gguf") if path.is_file()), key=lambda p: p.name.lower())
    model = next((path for path in ggufs if "mmproj" not in path.name.lower()), None)
    mmproj = next((path for path in ggufs if "mmproj" in path.name.lower()), None)
    if model is None:
        raise SystemExit(f"GGUF model file not found under: {model_dir}")
    if mmproj is None:
        raise SystemExit(f"mmproj GGUF file not found under: {model_dir}")
    extras = [
        path
        for path in model_dir.iterdir()
        if path.is_file()
        and path not in {model, mmproj}
        and path.name != ".DS_Store"
        and path.name not in {"MODEL_MANIFEST.json", "NOTICE.txt"}
        and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".txt", ".md", ".json", ".license"}
    ]
    return model, mmproj, sorted(extras, key=lambda p: p.name.lower())


def add_model_payload(
    archive: zipfile.ZipFile,
    model_dir: Path,
    *,
    source_url: str = DEFAULT_MODEL_SOURCE_URL,
    license_name: str = DEFAULT_MODEL_LICENSE,
    payload_name: str = "local-gemma",
) -> None:
    model, mmproj, extras = model_payload_files(model_dir)
    prefix = Path("payload") / "models" / payload_name
    files = [model, mmproj, *extras]
    manifest_files = []
    for file in files:
        archive.write(
            file,
            prefix / file.name,
            compress_type=zipfile.ZIP_STORED if file.suffix.lower() == ".gguf" else zipfile.ZIP_DEFLATED,
        )
        manifest_files.append(
            {
                "name": file.name,
                "size": file.stat().st_size,
                "sha256": sha256(file),
            }
        )
    manifest = {
        "payload": payload_name,
        "model_id": "local/gemma",
        "display_name": "Local Gemma 4 E4B",
        "source_url": source_url,
        "license": license_name,
        "files": manifest_files,
    }
    archive.writestr(str(prefix / "MODEL_MANIFEST.json"), json.dumps(manifest, indent=2) + "\n")
    archive.writestr(
        str(prefix / "NOTICE.txt"),
        "\n".join(
            [
                "Codex Hybrid Local Model Payload",
                "",
                f"Source: {source_url}",
                f"License: {license_name}",
                "",
                "This package includes model files for private netdisk distribution.",
                "Do not commit these model files to the Git repository.",
                "",
            ]
        ),
    )


def ensure_macos_llama_runtime(backend: str) -> Path:
    if backend not in LLAMA_MACOS_ASSETS:
        raise SystemExit(f"unknown macOS llama backend: {backend}")
    asset = LLAMA_MACOS_ASSETS[backend]
    cache = ROOT / ".package-cache" / "llama.cpp"
    archive_path = cache / str(asset["name"])
    extract_dir = cache / f"{LLAMA_VERSION}-{backend}"
    cache.mkdir(parents=True, exist_ok=True)
    if not archive_path.exists():
        print(f"downloading llama.cpp {LLAMA_VERSION} {backend}")
        subprocess.run(["curl", "-L", str(asset["url"]), "-o", str(archive_path)], check=True)
    if not next(extract_dir.rglob("llama-server"), None) if extract_dir.exists() else True:
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)
        subprocess.run(["tar", "-xzf", str(archive_path), "-C", str(extract_dir)], check=True)
    server = next(extract_dir.rglob("llama-server"), None)
    if server is None:
        raise SystemExit(f"llama-server not found after extracting {archive_path}")
    server.chmod(server.stat().st_mode | 0o755)
    return extract_dir


def add_llama_payload(archive: zipfile.ZipFile, backend: str, source_dir: Path) -> None:
    if not source_dir.exists():
        raise SystemExit(f"llama directory does not exist: {source_dir}")
    server = next(source_dir.rglob("llama-server"), None)
    if server is None:
        raise SystemExit(f"llama-server not found under: {source_dir}")
    add_directory_payload(archive, source_dir, Path("payload") / "llama.cpp" / backend)


def add_python_payload(archive: zipfile.ZipFile, source_dir: Path) -> None:
    if not source_dir.exists():
        raise SystemExit(f"python directory does not exist: {source_dir}")
    candidates = [source_dir / "bin" / "python3", source_dir / "python3"]
    if not any(candidate.exists() for candidate in candidates):
        raise SystemExit(f"python3 runtime not found under: {source_dir}")
    add_directory_payload(archive, source_dir, Path("payload") / "python")


def build(
    output: Path | None = None,
    *,
    thin: bool = False,
    full_local: bool = False,
    model_dir: Path | None = None,
    llama_macos_x64: Path | None = None,
    llama_macos_arm64: Path | None = None,
    python_dir: Path | None = None,
    model_source_url: str = DEFAULT_MODEL_SOURCE_URL,
    model_license: str = DEFAULT_MODEL_LICENSE,
) -> Path:
    version = project_version()
    output = output or (
        ROOT
        / "dist"
        / (
            f"Codex-Hybrid-macOS-Full-Local-Setup-v{version}.zip"
            if full_local
            else f"Codex-Hybrid-macOS-Netdisk-Setup-v{version}.zip"
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_name(f"{output.name}.tmp")
    if temp_output.exists():
        temp_output.unlink()
    files = (
        INSTALLER_ROOT / "Install Codex Hybrid.command",
        INSTALLER_ROOT / "Codex Hybrid Diagnostics.command",
        INSTALLER_ROOT / "Restore Official Codex.command",
        INSTALLER_ROOT / "Install-CodexHybrid.sh",
        INSTALLER_ROOT / "README.txt",
        INSTALLER_ROOT / "README.zh-CN.txt",
        INSTALLER_ROOT / "先看我-安装说明.txt",
        INSTALLER_ROOT / "SHA256校验.txt",
        INSTALLER_ROOT / "provider-preset.example.json",
    )
    for file in files:
        if not file.exists():
            raise SystemExit(f"missing installer file: {file}")
    with zipfile.ZipFile(temp_output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            write_file(archive, file, Path(file.name))
        if not thin:
            add_project_payload(archive)
        if full_local:
            if model_dir is None:
                model_dir = ROOT / ".package-cache" / "models" / "local-gemma"
            if llama_macos_x64 is None:
                llama_macos_x64 = ensure_macos_llama_runtime("macos-x64")
            if llama_macos_arm64 is None:
                llama_macos_arm64 = ensure_macos_llama_runtime("macos-arm64")
            add_llama_payload(archive, "macos-x64", llama_macos_x64)
            add_llama_payload(archive, "macos-arm64", llama_macos_arm64)
            add_model_payload(archive, model_dir, source_url=model_source_url, license_name=model_license)
        if python_dir is not None:
            add_python_payload(archive, python_dir)
    shutil.move(str(temp_output), output)
    print(f"built {output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the macOS netdisk one-click setup zip.")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--thin",
        action="store_true",
        help="build a script-only package without the bundled project payload",
    )
    parser.add_argument("--full-local", action="store_true", help="bundle local model and macOS llama.cpp runtimes")
    parser.add_argument("--include-model-dir", type=Path, help="local model directory to bundle under payload/models/local-gemma")
    parser.add_argument("--include-llama-macos-x64", type=Path, help="macOS x64 llama.cpp runtime directory")
    parser.add_argument("--include-llama-macos-arm64", type=Path, help="macOS arm64 llama.cpp runtime directory")
    parser.add_argument("--include-python-dir", type=Path, help="optional tested macOS Python runtime directory to bundle under payload/python")
    parser.add_argument(
        "--model-source-url",
        default=DEFAULT_MODEL_SOURCE_URL,
        help="source URL recorded in MODEL_MANIFEST.json when --full-local is used",
    )
    parser.add_argument(
        "--model-license",
        default=DEFAULT_MODEL_LICENSE,
        help="license recorded in MODEL_MANIFEST.json when --full-local is used",
    )
    args = parser.parse_args()
    build(
        args.output,
        thin=args.thin,
        full_local=args.full_local,
        model_dir=args.include_model_dir,
        llama_macos_x64=args.include_llama_macos_x64,
        llama_macos_arm64=args.include_llama_macos_arm64,
        python_dir=args.include_python_dir,
        model_source_url=args.model_source_url,
        model_license=args.model_license,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
