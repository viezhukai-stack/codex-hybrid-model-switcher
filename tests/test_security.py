from __future__ import annotations

from codex_hybrid_switcher.security import run_security_scan


def test_security_scan_accepts_clean_tree(tmp_path):
    (tmp_path / "README.md").write_text("placeholder endpoint and environment variable only\n", encoding="utf-8")

    assert run_security_scan(str(tmp_path)) == 0


def test_security_scan_rejects_private_lan_ip(tmp_path):
    private_ip = "10." + "0." + "0." + "177"
    (tmp_path / "notes.txt").write_text(f"private host {private_ip}\n", encoding="utf-8")

    assert run_security_scan(str(tmp_path)) == 1


def test_security_scan_rejects_common_private_lan_ranges(tmp_path):
    private_ip = "192." + "168." + "1." + "5"
    (tmp_path / "notes.txt").write_text(f"private host {private_ip}\n", encoding="utf-8")

    assert run_security_scan(str(tmp_path)) == 1


def test_security_scan_rejects_unix_user_paths(tmp_path):
    private_path = "/Users/" + "mac" + "/.codex/config.toml"
    (tmp_path / "notes.txt").write_text(private_path, encoding="utf-8")

    assert run_security_scan(str(tmp_path)) == 1


def test_security_scan_rejects_windows_user_paths(tmp_path):
    private_path = "C:" + "\\Users\\" + "kevin" + "\\.codex\\config.toml"
    (tmp_path / "notes.txt").write_text(private_path, encoding="utf-8")

    assert run_security_scan(str(tmp_path)) == 1


def test_security_scan_rejects_token_key_and_password_assignments(tmp_path):
    sensitive_lines = [
        "api_" + "key = " + "sk-" + ("a" * 24),
        "access_" + "token = " + ("b" * 24),
        "password = " + "correct-horse-battery",
        "authorization = " + "Bearer " + ("c" * 24),
    ]
    (tmp_path / "notes.txt").write_text("\n".join(sensitive_lines), encoding="utf-8")

    assert run_security_scan(str(tmp_path)) == 1


def test_security_scan_rejects_internal_endpoint_hostnames(tmp_path):
    endpoint = "https://" + "provider" + ".internal/v1"
    (tmp_path / "notes.txt").write_text(endpoint, encoding="utf-8")

    assert run_security_scan(str(tmp_path)) == 1
