from __future__ import annotations

import argparse
import platform
import time
from pathlib import Path

from .config import AppConfig, expand_path, load_config
from .private_config import validate_config
from .report import (
    current_model_fields,
    newest_backup,
    protected_file_lines,
    provider_lines,
    read_config_toml,
    section_presence,
)


STATUS_VALUES = ("yes", "no", "na", "not-recorded")
CLI_STATUS_VALUES = ("yes", "no", "na")
VERDICT_VALUES = ("complete", "partial", "failed", "rollback-needed")

CHECKS = (
    ("account_visible", "Account information is visible"),
    ("plugins_visible", "Plugin entry points are visible"),
    ("mcp_visible", "MCP entry points are visible"),
    ("project_list_visible", "Project list is visible"),
    ("test_chat_responded", "A new test conversation responded"),
    ("bridge_health_passed", "Bridge health passed or is not required"),
    ("setup_report_reviewed", "Setup report was reviewed for secrets"),
)


def _status_label(value: str) -> str:
    if value == "yes":
        return "[x] yes"
    if value == "no":
        return "[ ] no"
    if value == "na":
        return "[-] not applicable"
    return "[ ] not recorded"


def _safe_setup_report_reference(value: str | None) -> str:
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


def _warnings(verdict: str, evidence: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    required = (
        "account_visible",
        "plugins_visible",
        "mcp_visible",
        "project_list_visible",
        "test_chat_responded",
        "setup_report_reviewed",
    )
    missing = [name for name in required if evidence.get(name) != "yes"]
    if verdict == "complete" and missing:
        warnings.append("verdict is complete but one or more required UI evidence checks are not yes")
    failed = [name for name, value in evidence.items() if value == "no"]
    if failed:
        warnings.append("one or more evidence checks are marked no")
    return warnings


def render_canary_report(
    config_path: str | None = None,
    *,
    provider_id: str | None = None,
    setup_report: str | None = None,
    verdict: str = "partial",
    evidence: dict[str, str] | None = None,
) -> str:
    if verdict not in VERDICT_VALUES:
        raise ValueError(f"invalid verdict: {verdict}")

    evidence = evidence or {}
    for key, value in evidence.items():
        if value not in STATUS_VALUES:
            raise ValueError(f"invalid status for {key}: {value}")

    config = load_config(config_path)
    config_text = read_config_toml(config)
    fields = current_model_fields(config_text)
    sections = section_presence(config_text)
    errors = validate_config(config)
    warnings = _warnings(verdict, evidence)

    lines = [
        "# Codex Hybrid Canary Evidence",
        "",
        "## Summary",
        "",
        f"- generated_at: `{time.strftime('%Y-%m-%d %H:%M:%S %z')}`",
        f"- platform: `{platform.system() or 'unknown'}`",
        f"- verdict: `{verdict}`",
        f"- config_validation: `{'passed' if not errors else 'failed'}`",
        f"- tested_provider: `{_provider_summary(config, provider_id)}`",
        f"- active_model_provider: `{fields.get('model_provider', '<missing>')}`",
        f"- active_model: `{fields.get('model', '<missing>')}`",
        f"- newest_config_backup: `{newest_backup(config)}`",
        f"- setup_report_reference: `{_safe_setup_report_reference(setup_report)}`",
        "",
        "## Manual UI Evidence",
        "",
    ]
    for key, label in CHECKS:
        lines.append(f"- {_status_label(evidence.get(key, 'not-recorded'))} {label}")

    lines.extend(
        [
            "",
            "## Providers",
            "",
            *provider_lines(config),
            "",
            "## Protected Codex Files",
            "",
            *protected_file_lines(config),
            "",
            "## Preserved Config Sections",
            "",
        ]
    )
    for name, present in sections.items():
        lines.append(f"- `{name}`: {'present' if present else 'missing'}")

    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    if errors:
        lines.extend(["", "## Validation Errors", ""])
        lines.extend(f"- {error}" for error in errors)

    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- This evidence report is a redacted support artifact.",
            "- It records manual UI confirmations, but it does not prove account identity.",
            "- It does not include API keys, account tokens, session content, or database content.",
            "- Do not attach `auth.json`, `models_cache.json`, `state_5.sqlite`, `sessions/`, or `rollouts/`.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_canary_report(
    config_path: str | None = None,
    *,
    output: str | None = None,
    provider_id: str | None = None,
    setup_report: str | None = None,
    verdict: str = "partial",
    evidence: dict[str, str] | None = None,
) -> int:
    report = render_canary_report(
        config_path,
        provider_id=provider_id,
        setup_report=setup_report,
        verdict=verdict,
        evidence=evidence,
    )
    if output:
        path = expand_path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        print(f"Wrote canary evidence: {path}")
    else:
        print(report, end="")
    return 0


def add_canary_report_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", dest="sub_config")
    parser.add_argument("--output")
    parser.add_argument("--provider-id")
    parser.add_argument("--setup-report")
    parser.add_argument("--verdict", choices=VERDICT_VALUES, default="partial")
    for key, label in CHECKS:
        parser.add_argument(f"--{key.replace('_', '-')}", choices=CLI_STATUS_VALUES, help=label)


def evidence_from_args(args: argparse.Namespace) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for key, _label in CHECKS:
        value = getattr(args, key, None)
        if value:
            evidence[key] = value
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    add_canary_report_args(parser)
    args = parser.parse_args(argv)
    return run_canary_report(
        args.sub_config,
        output=args.output,
        provider_id=args.provider_id,
        setup_report=args.setup_report,
        verdict=args.verdict,
        evidence=evidence_from_args(args),
    )


if __name__ == "__main__":
    raise SystemExit(main())
