from __future__ import annotations

from codex_hybrid_switcher.security import run_security_scan


def test_security_scan_accepts_clean_tree(tmp_path):
    (tmp_path / "README.md").write_text("placeholder endpoint and environment variable only\n", encoding="utf-8")

    assert run_security_scan(str(tmp_path)) == 0


def test_security_scan_rejects_private_lan_ip(tmp_path):
    private_ip = "10." + "0." + "0." + "177"
    (tmp_path / "notes.txt").write_text(f"private host {private_ip}\n", encoding="utf-8")

    assert run_security_scan(str(tmp_path)) == 1
