from __future__ import annotations

import argparse
import platform
import time
from pathlib import Path

from .config import expand_path, load_config
from .private_config import validate_config
from .report import current_model_fields, newest_backup, read_config_toml


VERDICT_COMPLETE = "Complete"
VERDICT_PARTIAL = "Partially complete"
VERDICT_NOT_COMPLETE = "Not complete"
VERDICT_ROLLBACK = "Needs rollback"

REQUIRED_CANARY_CHECKS = {
    "Account information is visible": {"yes"},
    "Plugin entry points are visible": {"yes"},
    "MCP entry points are visible": {"yes", "na"},
    "Project list is visible": {"yes"},
    "A new test conversation responded": {"yes"},
    "Bridge health passed or is not required": {"yes", "na"},
    "Setup report was reviewed for secrets": {"yes"},
}

ROLLBACK_TRIGGER_CHECKS = {
    "Account information is visible",
    "Plugin entry points are visible",
    "MCP entry points are visible",
    "Project list is visible",
    "A new test conversation responded",
}


def _safe_reference(value: str | None) -> str:
    if not value:
        return "<not-provided>"
    return Path(value).name or "<provided>"


def _read_optional_report(path_value: str | None) -> tuple[str | None, str | None]:
    if not path_value:
        return None, "not provided"
    path = expand_path(path_value)
    if not path.exists():
        return None, "missing"
    return path.read_text(encoding="utf-8", errors="replace"), "present"


def _report_has_marker(text: str | None, marker: str) -> bool:
    return bool(text and marker in text)


def _canary_verdict(text: str | None) -> str | None:
    if not text:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- verdict:"):
            return stripped.split("`", 2)[1] if "`" in stripped else stripped
    return None


def _canary_statuses(text: str | None) -> dict[str, str]:
    statuses: dict[str, str] = {}
    if not text:
        return statuses
    for line in text.splitlines():
        stripped = line.strip()
        for label in REQUIRED_CANARY_CHECKS:
            if stripped.endswith(label):
                if "[x] yes" in stripped:
                    statuses[label] = "yes"
                elif "[-] not applicable" in stripped:
                    statuses[label] = "na"
                elif "[ ] no" in stripped:
                    statuses[label] = "no"
                elif "[ ] not recorded" in stripped:
                    statuses[label] = "not-recorded"
                else:
                    statuses[label] = "unknown"
    return statuses


def _canary_warnings_present(text: str | None) -> bool:
    return bool(text and "## Warnings" in text)


def _report_safety_marker_ok(text: str | None) -> bool:
    if not text:
        return False
    return (
        "does not include API keys" in text
        or "Do not attach `auth.json`" in text
        or "Forbidden Attachments" in text
    )


def _derive_verdict(*, config_errors: list[str], setup_ok: bool, canary_ok: bool, real_canary_ok: bool, statuses: dict[str, str], canary_verdict: str | None, warnings_present: bool) -> tuple[str, list[str]]:
    missing: list[str] = []
    rollback: list[str] = []

    if config_errors:
        missing.append("config validation failed")
    if not setup_ok:
        missing.append("setup report is missing or incomplete")
    if not canary_ok:
        missing.append("canary report is missing or incomplete")
    if not real_canary_ok:
        missing.append("real clean-machine canary template is missing or incomplete")

    for label, allowed in REQUIRED_CANARY_CHECKS.items():
        value = statuses.get(label, "not-recorded")
        if value == "no" and label in ROLLBACK_TRIGGER_CHECKS:
            rollback.append(label)
        if value not in allowed:
            missing.append(f"{label}: {value}")

    if canary_verdict != "complete":
        missing.append(f"canary verdict is {canary_verdict or 'missing'}")
    if warnings_present:
        missing.append("canary report contains warnings")

    if rollback:
        return VERDICT_ROLLBACK, rollback + missing
    if not config_errors and setup_ok and canary_ok and real_canary_ok and not missing:
        return VERDICT_COMPLETE, []
    if setup_ok or canary_ok or real_canary_ok or statuses:
        return VERDICT_PARTIAL, missing
    return VERDICT_NOT_COMPLETE, missing


def render_final_check(
    config_path: str | None = None,
    *,
    setup_report: str | None = None,
    canary_report: str | None = None,
    real_canary_template: str | None = None,
) -> str:
    config = load_config(config_path)
    config_text = read_config_toml(config)
    fields = current_model_fields(config_text)
    config_errors = validate_config(config)

    setup_text, setup_status = _read_optional_report(setup_report)
    canary_text, canary_status = _read_optional_report(canary_report)
    real_text, real_status = _read_optional_report(real_canary_template)

    setup_ok = _report_has_marker(setup_text, "Codex Hybrid Setup Report") and _report_safety_marker_ok(setup_text)
    canary_ok = _report_has_marker(canary_text, "Codex Hybrid Canary Evidence") and _report_safety_marker_ok(canary_text)
    real_canary_ok = _report_has_marker(real_text, "Real Clean Machine Canary") and _report_safety_marker_ok(real_text)
    statuses = _canary_statuses(canary_text)
    canary_verdict = _canary_verdict(canary_text)
    warnings_present = _canary_warnings_present(canary_text)
    verdict, blockers = _derive_verdict(
        config_errors=config_errors,
        setup_ok=setup_ok,
        canary_ok=canary_ok,
        real_canary_ok=real_canary_ok,
        statuses=statuses,
        canary_verdict=canary_verdict,
        warnings_present=warnings_present,
    )

    lines = [
        "# Codex Hybrid Final Check",
        "",
        "## Verdict",
        "",
        f"- final_verdict: `{verdict}`",
        f"- generated_at: `{time.strftime('%Y-%m-%d %H:%M:%S %z')}`",
        f"- platform: `{platform.system() or 'unknown'}`",
        f"- config_file: `<private-config>`",
        f"- config_validation: `{'passed' if not config_errors else 'failed'}`",
        f"- active_model_provider: `{fields.get('model_provider', '<missing>')}`",
        f"- active_model: `{fields.get('model', '<missing>')}`",
        f"- newest_config_backup: `{newest_backup(config)}`",
        "",
        "## Inputs",
        "",
        f"- setup_report: `{_safe_reference(setup_report)}` status=`{setup_status}`",
        f"- canary_report: `{_safe_reference(canary_report)}` status=`{canary_status}`",
        f"- real_canary_template: `{_safe_reference(real_canary_template)}` status=`{real_status}`",
        "",
        "## Canary Evidence",
        "",
        f"- canary_verdict: `{canary_verdict or '<missing>'}`",
        f"- canary_warnings: `{'present' if warnings_present else 'none'}`",
    ]
    for label in REQUIRED_CANARY_CHECKS:
        lines.append(f"- `{label}`: `{statuses.get(label, 'not-recorded')}`")

    if config_errors:
        lines.extend(["", "## Config Validation Errors", ""])
        lines.extend(f"- {error}" for error in config_errors)
    if blockers:
        lines.extend(["", "## Missing Or Failed Evidence", ""])
        lines.extend(f"- {item}" for item in blockers)

    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            "- This final check is read-only.",
            "- It does not edit Codex config, account files, model cache, history database, sessions, or rollout logs.",
            "- It uses report filenames only and does not include API keys, account tokens, session content, database content, provider hostnames, or full local paths.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_final_check(
    config_path: str | None = None,
    *,
    setup_report: str | None = None,
    canary_report: str | None = None,
    real_canary_template: str | None = None,
    output: str | None = None,
) -> int:
    report = render_final_check(
        config_path,
        setup_report=setup_report,
        canary_report=canary_report,
        real_canary_template=real_canary_template,
    )
    if output:
        path = expand_path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        print(f"Wrote final check: {path}")
    else:
        print(report, end="")
    return 0


def add_final_check_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", dest="sub_config")
    parser.add_argument("--setup-report")
    parser.add_argument("--canary-report")
    parser.add_argument("--real-canary-template")
    parser.add_argument("--output")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    add_final_check_args(parser)
    args = parser.parse_args(argv)
    return run_final_check(
        args.sub_config,
        setup_report=args.setup_report,
        canary_report=args.canary_report,
        real_canary_template=args.real_canary_template,
        output=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
