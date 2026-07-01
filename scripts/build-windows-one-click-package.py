#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER_ROOT = ROOT / "installer" / "windows"


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("version not found in pyproject.toml")
    return match.group(1)


def build(output: Path | None = None) -> Path:
    version = project_version()
    output = output or (ROOT / "dist" / f"Codex-Hybrid-Windows-Setup-v{version}.zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    files = (
        INSTALLER_ROOT / "Install Codex Hybrid.cmd",
        INSTALLER_ROOT / "Install-CodexHybrid.ps1",
        INSTALLER_ROOT / "README.txt",
    )
    for file in files:
        if not file.exists():
            raise SystemExit(f"missing installer file: {file}")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.name)
    print(f"built {output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Windows one-click setup zip.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
