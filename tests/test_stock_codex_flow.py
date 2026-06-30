from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_stock_codex_flow_validation_script(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-stock-codex-flow.py"),
            "--tmp-root",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout
    assert "stock Codex flow validation passed" in proc.stdout
    assert "Protected Codex files unchanged" in proc.stdout


def test_stock_codex_handoff_validation_script(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-stock-codex-handoff.py"),
            "--tmp-root",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout
    assert "stock Codex handoff validation passed" in proc.stdout
    assert "default bridge handoff dry-run validation passed" in proc.stdout
    assert "bridge-health" in proc.stdout
    assert "Guarded dry-run" in proc.stdout
    assert "Protected Codex files unchanged" in proc.stdout
