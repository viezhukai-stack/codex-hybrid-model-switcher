#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import signal
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PROTECTED_FILES = ("auth.json", "models_cache.json", "state_5.sqlite")
PRESERVED_CONFIG_MARKERS = (
    "[mcp_servers.example]",
    "[plugins.example]",
    "[projects.\"/tmp/example-project\"]",
    "[features]",
)


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            snapshot[path.relative_to(root).as_posix()] = sha256(path)
    return snapshot


def cleanup_bridge(temp_home: Path) -> None:
    pid_path = temp_home / ".codex-hybrid-model-switcher" / "bridge.pid"
    if not pid_path.exists():
        return
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return


def write_stock_codex_home(codex_home: Path) -> None:
    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "config.toml").write_text(
        """model_provider = "openai"
model = "gpt-5.5"
review_model = "gpt-5.5"
model_reasoning_effort = "high"

[mcp_servers.example]
command = "example-mcp"

[plugins.example]
enabled = true

[projects."/tmp/example-project"]
trust_level = "trusted"

[features]
web_search = true
""",
        encoding="utf-8",
    )
    (codex_home / "auth.json").write_text('{"account":"stock-codex-placeholder"}\n', encoding="utf-8")
    (codex_home / "models_cache.json").write_text('{"models":["gpt-5.5"]}\n', encoding="utf-8")
    (codex_home / "state_5.sqlite").write_bytes(b"sqlite placeholder for stock codex flow\n")
    sessions = codex_home / "sessions"
    sessions.mkdir()
    (sessions / "stock-session.jsonl").write_text(
        '{"model_provider":"openai","model":"gpt-5.5","text":"do not mutate"}\n',
        encoding="utf-8",
    )
    (codex_home / "rollouts").mkdir()
    (codex_home / "rollouts" / "rollout.log").write_text("do not mutate rollout logs\n", encoding="utf-8")


def assert_dry_run_unchanged(before: dict[str, str], codex_home: Path) -> None:
    after = snapshot_tree(codex_home)
    if after != before:
        raise SystemExit("bootstrap dry-run changed the simulated stock Codex home")


def assert_guarded_apply_scope(before: dict[str, str], codex_home: Path) -> None:
    after = snapshot_tree(codex_home)
    changed = sorted(path for path in before if before[path] != after.get(path))
    added = sorted(path for path in after if path not in before)
    removed = sorted(path for path in before if path not in after)

    if removed:
        raise SystemExit(f"guarded apply removed files unexpectedly: {removed}")
    if changed != ["config.toml"]:
        raise SystemExit(f"guarded apply changed unexpected files: {changed}")
    unexpected_added = [path for path in added if not path.startswith("config.toml.bak-codex-hybrid-")]
    if unexpected_added:
        raise SystemExit(f"guarded apply added unexpected files: {unexpected_added}")

    for protected in PROTECTED_FILES:
        if before[protected] != after[protected]:
            raise SystemExit(f"protected file changed unexpectedly: {protected}")
    if before["sessions/stock-session.jsonl"] != after["sessions/stock-session.jsonl"]:
        raise SystemExit("session history changed unexpectedly")
    if before["rollouts/rollout.log"] != after["rollouts/rollout.log"]:
        raise SystemExit("rollout log changed unexpectedly")

    config_text = (codex_home / "config.toml").read_text(encoding="utf-8")
    expected = [
        'model_provider = "custom"',
        'model = "provider-gpt-main"',
        'base_url = "https://example.test/v1"',
        "requires_openai_auth = true",
        'model_reasoning_effort = "high"',
    ]
    for item in expected:
        if item not in config_text:
            raise SystemExit(f"updated config missing expected content: {item}")
    for marker in PRESERVED_CONFIG_MARKERS:
        if marker not in config_text:
            raise SystemExit(f"updated config lost preserved block: {marker}")


def assert_report_is_redacted(report_path: Path, work: Path) -> None:
    text = report_path.read_text(encoding="utf-8")
    required = [
        "Codex Hybrid Setup Report",
        "config_validation: `passed`",
        "active_model_provider: `custom`",
        "active_model: `provider-gpt-main`",
        "`auth.json`: present sha256=",
        "`models_cache.json`: present sha256=",
        "`state_5.sqlite`: present sha256=",
        "`mcp`: present",
        "`plugins`: present",
        "`projects`: present",
    ]
    for item in required:
        if item not in text:
            raise SystemExit(f"setup report missing expected content: {item}")
    forbidden = [
        "example.test",
        str(work),
        "stock-codex-placeholder",
        "do not mutate",
        "sqlite placeholder",
        "rollout logs",
    ]
    for item in forbidden:
        if item in text:
            raise SystemExit(f"setup report leaked private content: {item}")


def validate_stock_flow(python: Path, repo: Path, work: Path) -> None:
    codex_home = work / "stock-codex-home"
    private_config = work / "private" / "config.json"
    temp_home = work / "home"
    temp_home.mkdir()
    write_stock_codex_home(codex_home)
    before_bootstrap = snapshot_tree(codex_home)

    env = os.environ.copy()
    env["HOME"] = str(temp_home)
    env["PYTHONPATH"] = str(repo / "src")
    env["OPENAI_COMPATIBLE_API_KEY"] = "test-provider-key"
    try:
        run(
            [
                str(python),
                "-I",
                "bootstrap.py",
                "--non-interactive",
                "--config",
                str(private_config),
                "--codex-home",
                str(codex_home),
                "--provider-id",
                "cloud-gpt-main",
                "--base-url",
                "https://example.test/v1",
                "--model",
                "provider-gpt-main",
                "--api-key-env",
                "OPENAI_COMPATIBLE_API_KEY",
                "--cloud-route",
                "direct",
            ],
            cwd=repo,
            env=env,
        )
        assert_dry_run_unchanged(before_bootstrap, codex_home)

        run(
            [
                str(python),
                "-m",
                "codex_hybrid_switcher",
                "guarded-switch",
                "cloud-gpt-main",
                "--config",
                str(private_config),
                "--force",
            ],
            cwd=repo,
            env=env,
        )
        assert_guarded_apply_scope(before_bootstrap, codex_home)
        report_path = work / "stock-flow-report.md"
        run(
            [
                str(python),
                "-m",
                "codex_hybrid_switcher",
                "setup-report",
                "--config",
                str(private_config),
                "--output",
                str(report_path),
            ],
            cwd=repo,
            env=env,
        )
        assert_report_is_redacted(report_path, work)
        print("stock Codex flow validation passed")
    finally:
        cleanup_bridge(temp_home)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate stock-Codex bootstrap-to-apply flow in a temporary profile.")
    parser.add_argument("--tmp-root", default=tempfile.gettempdir(), help="temporary root; defaults to the system temp directory")
    parser.add_argument("--keep", action="store_true", help="keep temporary validation directory")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    tmp_root = Path(args.tmp_root)
    if not tmp_root.exists():
        raise SystemExit(f"temporary root does not exist: {tmp_root}")
    work = Path(tempfile.mkdtemp(prefix="codex-hybrid-stock-flow-", dir=tmp_root))
    print(f"stock flow workspace: {work}")
    try:
        validate_stock_flow(Path(sys.executable), repo, work)
    finally:
        if args.keep:
            print(f"kept stock flow workspace: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
