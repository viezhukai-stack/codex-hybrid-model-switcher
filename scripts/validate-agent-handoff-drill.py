#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PROTECTED_FILES = ("auth.json", "models_cache.json", "state_5.sqlite")
REQUIRED_DOC_MARKERS = {
    "START_HERE.md": (
        "Copy This Prompt Into Codex",
        "bootstrap.py",
        "guarded-switch --dry-run",
        "setup-report",
        "canary-report",
        "FINAL_CHECK.md",
    ),
    "AGENTS.md": (
        "Never switch providers while Codex Desktop is running",
        "docs/canary-report.md",
        "Completion Criteria",
    ),
    "FINAL_CHECK.md": (
        "Complete",
        "Partially complete",
        "Needs rollback",
        "请不要修改任何文件",
    ),
}


def run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def run_expect_code(
    cmd: list[str], *, cwd: Path, env: dict[str, str], expected_code: int
) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != expected_code:
        raise SystemExit(f"expected exit code {expected_code}, got {proc.returncode}")
    return proc


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def protected_hashes(codex_home: Path) -> dict[str, str | None]:
    return {name: sha256(codex_home / name) for name in PROTECTED_FILES}


def write_stock_codex_home(codex_home: Path) -> None:
    codex_home.mkdir(parents=True)
    (codex_home / "config.toml").write_text(
        """model_provider = "openai"
model = "gpt-5.5"
review_model = "gpt-5.5"
model_reasoning_effort = "high"

[mcp_servers.example]
command = "example-mcp"

[plugins.example]
enabled = true

[projects."/example/project"]
trust_level = "trusted"

[features]
web_search = true
""",
        encoding="utf-8",
    )
    (codex_home / "auth.json").write_text('{"token":"stock-codex-placeholder"}', encoding="utf-8")
    (codex_home / "models_cache.json").write_text('{"models":[]}', encoding="utf-8")
    (codex_home / "state_5.sqlite").write_bytes(b"sqlite placeholder")
    sessions = codex_home / "sessions"
    sessions.mkdir()
    (sessions / "stock-session.jsonl").write_text("do not mutate session content", encoding="utf-8")
    rollouts = codex_home / "rollouts"
    rollouts.mkdir()
    (rollouts / "stock-rollout.log").write_text("do not mutate rollout content", encoding="utf-8")


def assert_docs_ready(repo: Path) -> None:
    for rel_path, markers in REQUIRED_DOC_MARKERS.items():
        text = (repo / rel_path).read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise SystemExit(f"{rel_path} missing handoff drill markers: {missing}")


def assert_not_leaked(text: str, work: Path) -> None:
    forbidden = (
        "example.test",
        str(work),
        "stock-codex-placeholder",
        "sqlite placeholder",
        "do not mutate",
        "test-provider-key",
    )
    leaked = [item for item in forbidden if item in text]
    if leaked:
        raise SystemExit(f"handoff drill report leaked private content: {leaked}")


def write_drill_report(
    path: Path,
    *,
    setup_report: Path,
    canary_report: Path,
    before_hashes: dict[str, str | None],
    after_hashes: dict[str, str | None],
) -> None:
    lines = [
        "# Agent Handoff Drill Report",
        "",
        "## Verdict",
        "",
        "- drill_result: `passed`",
        "- simulated_user: `stock Codex Desktop user`",
        "- final_verdict: `Complete`",
        "",
        "## Evidence Chain",
        "",
        "- [x] Handoff docs include the copy-paste prompt and stop conditions.",
        "- [x] Bootstrap created private config outside the repository.",
        "- [x] Guarded dry-run changed no simulated Codex files.",
        "- [x] API-key help was available without printing a key value.",
        "- [x] Bridge health reported closed-port diagnostics without leaking upstream hostnames.",
        "- [x] Guarded apply changed only `config.toml` and created a backup.",
        "- [x] Protected Codex file hashes stayed unchanged.",
        "- [x] Redacted setup report was generated.",
        "- [x] Canary evidence report recorded visible UI confirmations.",
        "- [x] Final verdict path uses `FINAL_CHECK.md`.",
        "",
        "## Protected File Hash Prefixes",
        "",
    ]
    for name in PROTECTED_FILES:
        before = before_hashes[name]
        after = after_hashes[name]
        lines.append(f"- `{name}`: before=`{before[:12] if before else 'missing'}` after=`{after[:12] if after else 'missing'}`")
    lines.extend(
        [
            "",
            "## Generated Artifacts",
            "",
            f"- setup_report: `{setup_report.name}`",
            f"- canary_report: `{canary_report.name}`",
            "",
            "## Safety Boundary",
            "",
            "- This drill used only a temporary simulated Codex home.",
            "- It did not read or write a real user profile.",
            "- It did not include API keys, account tokens, session content, or database content.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_drill(python: Path, repo: Path, work: Path) -> None:
    assert_docs_ready(repo)
    codex_home = work / "stock-codex-home"
    private_config = work / "private" / "config.json"
    setup_report = work / "codex-hybrid-setup-report.md"
    canary_report = work / "codex-hybrid-canary-evidence.md"
    drill_report = work / "agent-handoff-drill-report.md"
    write_stock_codex_home(codex_home)
    before_hashes = protected_hashes(codex_home)

    env = os.environ.copy()
    env["HOME"] = str(work / "home")
    env["PYTHONPATH"] = str(repo / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["OPENAI_COMPATIBLE_API_KEY"] = "test-provider-key"

    bootstrap = run(
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
    for marker in ("Guarded dry-run", "No files will be changed", "setup-report", "canary-report", "FINAL_CHECK.md"):
        if marker not in bootstrap.stdout:
            raise SystemExit(f"bootstrap output missing drill marker: {marker}")
    if not private_config.exists():
        raise SystemExit("bootstrap did not create private config")

    env_without_key = env.copy()
    env_without_key.pop("OPENAI_COMPATIBLE_API_KEY", None)
    env_help = run(
        [str(python), "-m", "codex_hybrid_switcher", "env-help", "--platform", "macos", "--config", str(private_config)],
        cwd=repo,
        env=env_without_key,
    )
    for marker in ("API key environment help", "does not read, print, or store API keys", "OPENAI_COMPATIBLE_API_KEY"):
        if marker not in env_help.stdout:
            raise SystemExit(f"env-help output missing drill marker: {marker}")
    if "test-provider-key" in env_help.stdout:
        raise SystemExit("env-help leaked the simulated API key value")

    bridge_health_config = work / "private" / "bridge-health-config.json"
    bridge_health_config.write_text(private_config.read_text(encoding="utf-8"), encoding="utf-8")
    import json

    data = json.loads(bridge_health_config.read_text(encoding="utf-8"))
    data["bridge"]["port"] = 9
    data["bridge"]["llama_port"] = 10
    data["providers"][1]["route"] = "bridge"
    bridge_health_config.write_text(json.dumps(data), encoding="utf-8")
    bridge_health = run_expect_code(
        [str(python), "-m", "codex_hybrid_switcher", "bridge-health", "--config", str(bridge_health_config)],
        cwd=repo,
        env=env_without_key,
        expected_code=1,
    )
    for marker in ("CLOSED bridge TCP port", "OPENAI_COMPATIBLE_API_KEY (unset)", "env-help"):
        if marker not in bridge_health.stdout:
            raise SystemExit(f"bridge-health output missing drill marker: {marker}")
    if "example.test" in bridge_health.stdout:
        raise SystemExit("bridge-health leaked upstream hostname")

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
    after_hashes = protected_hashes(codex_home)
    if before_hashes != after_hashes:
        raise SystemExit("protected Codex hashes changed during handoff drill")
    if not list(codex_home.glob("config.toml.bak-codex-hybrid-*")):
        raise SystemExit("guarded apply did not create a config backup")

    run(
        [
            str(python),
            "-m",
            "codex_hybrid_switcher",
            "setup-report",
            "--config",
            str(private_config),
            "--output",
            str(setup_report),
        ],
        cwd=repo,
        env=env,
    )
    run(
        [
            str(python),
            "-m",
            "codex_hybrid_switcher",
            "canary-report",
            "--config",
            str(private_config),
            "--provider-id",
            "cloud-gpt-main",
            "--setup-report",
            str(setup_report),
            "--account-visible",
            "yes",
            "--plugins-visible",
            "yes",
            "--mcp-visible",
            "yes",
            "--project-list-visible",
            "yes",
            "--test-chat-responded",
            "yes",
            "--bridge-health-passed",
            "yes",
            "--setup-report-reviewed",
            "yes",
            "--verdict",
            "complete",
            "--output",
            str(canary_report),
        ],
        cwd=repo,
        env=env,
    )
    for report in (setup_report, canary_report):
        assert_not_leaked(report.read_text(encoding="utf-8"), work)
    if "verdict: `complete`" not in canary_report.read_text(encoding="utf-8"):
        raise SystemExit("canary report did not record complete verdict")

    write_drill_report(
        drill_report,
        setup_report=setup_report,
        canary_report=canary_report,
        before_hashes=before_hashes,
        after_hashes=after_hashes,
    )
    text = drill_report.read_text(encoding="utf-8")
    assert_not_leaked(text, work)
    for marker in ("drill_result: `passed`", "final_verdict: `Complete`", "Protected Codex file hashes stayed unchanged"):
        if marker not in text:
            raise SystemExit(f"drill report missing marker: {marker}")
    print(f"agent handoff drill report: {drill_report}")
    print("agent handoff drill validation passed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a simulated stock Codex agent handoff drill.")
    parser.add_argument("--tmp-root", default=tempfile.gettempdir(), help="temporary root; defaults to system temp")
    parser.add_argument("--keep", action="store_true", help="keep temporary drill directory")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    tmp_root = Path(args.tmp_root)
    if not tmp_root.exists():
        raise SystemExit(f"temporary root does not exist: {tmp_root}")
    work = Path(tempfile.mkdtemp(prefix="codex-hybrid-agent-drill-", dir=tmp_root))
    print(f"agent handoff drill workspace: {work}")
    try:
        validate_drill(Path(sys.executable), repo, work)
    finally:
        if args.keep:
            print(f"kept agent handoff drill workspace: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
