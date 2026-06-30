from __future__ import annotations

import argparse
import platform
import time
from pathlib import Path

from .config import AppConfig, expand_path, load_config
from .private_config import validate_config


def _safe_reference(value: str | None) -> str:
    if not value:
        return "<not-provided>"
    return Path(value).name or "<provided>"


def _provider_summary(config: AppConfig, provider_id: str | None) -> str:
    if not provider_id:
        return "<not-provided>"
    try:
        provider = config.provider(provider_id)
    except KeyError:
        return f"{provider_id} (not found in config)"
    kind = provider.get("kind") or "<missing>"
    model = provider.get("model") or "<missing>"
    route = provider.get("route") or "direct"
    return f"{provider_id} kind={kind} model={model} route={route}"


def render_real_canary_template(
    config_path: str | None = None,
    *,
    provider_id: str | None = None,
    setup_report: str | None = None,
    canary_report: str | None = None,
) -> str:
    config = load_config(config_path)
    errors = validate_config(config)

    lines = [
        "# Real Clean Machine Canary",
        "",
        "Use this checklist for a real user who starts with stock Codex Desktop and hands this repository to Codex.",
        "Do not paste secrets, screenshots with tokens, raw Codex state files, or full local paths into this report.",
        "",
        "## Scope",
        "",
        f"- generated_at: `{time.strftime('%Y-%m-%d %H:%M:%S %z')}`",
        f"- platform_running_template: `{platform.system() or 'unknown'}`",
        f"- config_validation: `{'passed' if not errors else 'failed'}`",
        f"- provider_under_test: `{_provider_summary(config, provider_id)}`",
        f"- setup_report_reference: `{_safe_reference(setup_report)}`",
        f"- canary_report_reference: `{_safe_reference(canary_report)}`",
        "- canary_type: `real clean machine`",
        "",
        "## Tester Intake",
        "",
        "- [ ] The machine had stock Codex Desktop before this repository was used.",
        "- [ ] The tester used a fresh clone or downloaded copy of this repository.",
        "- [ ] The tester did not copy another machine's `.codex` directory.",
        "- [ ] The provider endpoint and model id came from the tester's own provider account.",
        "- [ ] The API key was stored in an environment variable, not in repository files.",
        "",
        "## Agent Handoff Evidence",
        "",
        "- [ ] Codex read `START_HERE.md` and `AGENTS.md` before making changes.",
        "- [ ] Codex ran `bootstrap.py` or `codex-hybrid-switcher setup` first.",
        "- [ ] Codex ran `guarded-switch --dry-run` before any real switch.",
        "- [ ] The dry-run showed only provider/model changes to `config.toml`.",
        "- [ ] Codex asked the user to quit Codex Desktop before the real switch.",
        "- [ ] The real switch created a `config.toml.bak-codex-hybrid-*` backup.",
        "- [ ] `auth.json`, `models_cache.json`, and `state_5.sqlite` hashes stayed unchanged.",
        "- [ ] Codex did not edit `sessions/` or rollout logs.",
        "",
        "## Visible Codex Checks",
        "",
        "- [ ] Codex Desktop reopened without an error page.",
        "- [ ] Account information is visible.",
        "- [ ] Plugin entry points are visible.",
        "- [ ] MCP entry points are visible, or the tester confirms MCP is not used on this machine.",
        "- [ ] The project list is visible.",
        "- [ ] A new test conversation responded using the selected provider.",
        "- [ ] If a bridge-routed provider was used, `bridge-health` passed or was marked not applicable with a reason.",
        "",
        "## Required Artifacts",
        "",
        "- [ ] Redacted `setup-report` generated and reviewed.",
        "- [ ] Redacted `canary-report` generated with the visible checks recorded.",
        "- [ ] `FINAL_CHECK.md` verdict was `Complete`, or the remaining gaps are listed below.",
        "",
        "## Gaps Or Follow-up",
        "",
        "- result: `<complete | partial | failed | rollback-needed>`",
        "- notes: `<short redacted notes only>`",
        "",
        "## Forbidden Attachments",
        "",
        "- Do not attach `auth.json`.",
        "- Do not attach `models_cache.json`.",
        "- Do not attach `state_5.sqlite`.",
        "- Do not attach `sessions/`.",
        "- Do not attach rollout logs.",
        "- Do not attach API keys, account tokens, provider dashboards, or unredacted screenshots.",
    ]
    if errors:
        lines.extend(["", "## Config Validation Errors", ""])
        lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines) + "\n"


def run_real_canary_template(
    config_path: str | None = None,
    *,
    output: str | None = None,
    provider_id: str | None = None,
    setup_report: str | None = None,
    canary_report: str | None = None,
) -> int:
    report = render_real_canary_template(
        config_path,
        provider_id=provider_id,
        setup_report=setup_report,
        canary_report=canary_report,
    )
    if output:
        path = expand_path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        print(f"Wrote real clean machine canary template: {path}")
    else:
        print(report, end="")
    return 0


def add_real_canary_template_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", dest="sub_config")
    parser.add_argument("--output")
    parser.add_argument("--provider-id")
    parser.add_argument("--setup-report")
    parser.add_argument("--canary-report")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    add_real_canary_template_args(parser)
    args = parser.parse_args(argv)
    return run_real_canary_template(
        args.sub_config,
        output=args.output,
        provider_id=args.provider_id,
        setup_report=args.setup_report,
        canary_report=args.canary_report,
    )


if __name__ == "__main__":
    raise SystemExit(main())
