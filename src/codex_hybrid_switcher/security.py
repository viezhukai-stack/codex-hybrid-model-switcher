from __future__ import annotations

import argparse
import re
from pathlib import Path


PATTERNS = [
    r"id_token",
    r"refresh_token",
    r"access_token",
    r"Bearer\s+[A-Za-z0-9_.-]{20,}",
    r"password\s*[:=]",
    r"api[_-]?key\s*[:=]\s*[A-Za-z0-9_.-]{12,}",
    r"10\.0\.0\.\d+",
    r"/Users/mac",
    r"C:\\Users\\hl",
]

ALLOWLIST_SUBSTRINGS = [
    "PATTERNS =",
    "api_key_env",
    "replace-with-your-provider-key",
    "r\"id_token\"",
    "r\"refresh_token\"",
    "r\"access_token\"",
    "r\"/Users/mac\"",
]


SKIP_DIRS = {".git", ".venv", ".pytest_cache", "__pycache__", "dist", "build"}


def run_security_scan(root: str = ".") -> int:
    compiled = [re.compile(p, re.IGNORECASE) for p in PATTERNS]
    findings: list[str] = []
    base = Path(root)
    for path in base.rglob("*"):
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.name == "security.py":
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(allowed in line for allowed in ALLOWLIST_SUBSTRINGS):
                continue
            if any(pattern.search(line) for pattern in compiled):
                findings.append(f"{path}:{line_no}: {line[:160]}")
    if findings:
        print("Sensitive-looking content found:")
        print("\n".join(findings))
        return 1
    print("No sensitive-looking content found.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    return run_security_scan(args.root)
