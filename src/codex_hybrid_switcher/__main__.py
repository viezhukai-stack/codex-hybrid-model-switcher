from __future__ import annotations

import argparse
import sys

from .account_switch import run_change_account
from .bridge import run_bridge
from .bridge_health import run_bridge_health
from .canary_report import add_canary_report_args, evidence_from_args, run_canary_report
from .doctor import run_doctor
from .env_help import run_env_help
from .final_check import add_final_check_args, run_final_check
from .history import run_history_status, run_restore_history_backup, run_unify_history
from .hot_router import run_hot_router
from .hot_router_mode import run_hot_router_mode
from .local_smoke import run_local_smoke
from .private_config import init_config, run_validate_config
from .real_canary import add_real_canary_template_args, run_real_canary_template
from .report import run_setup_report
from .security import run_security_scan
from .setup_wizard import run_setup_wizard
from .smoke import run_smoke
from .switcher import guarded_switch_provider, interactive_menu, run_ensure_bridge, switch_provider
from .windows_update import (
    run_windows_browser_ensure,
    run_windows_update_doctor,
    run_windows_update_ensure,
    run_windows_update_repair,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codex-hybrid-switcher")
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_config(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--config", dest="sub_config")
        return parser

    add_config(sub.add_parser("bridge"))
    ensure_bridge = sub.add_parser("ensure-bridge")
    ensure_bridge.add_argument("--config", dest="sub_config")
    hot_router = sub.add_parser("hot-router")
    hot_router.add_argument("--config", dest="sub_config")
    hot_router.add_argument("--host")
    hot_router.add_argument("--port", type=int)
    hot_router_mode = sub.add_parser("hot-router-mode")
    hot_router_mode.add_argument("mode_command", choices=["enable", "restore", "status"])
    hot_router_mode.add_argument("--config", dest="sub_config")
    hot_router_mode.add_argument("--router-url")
    hot_router_mode.add_argument("--allow-codex-running", action="store_true")
    bridge_health = sub.add_parser("bridge-health")
    bridge_health.add_argument("--config", dest="sub_config")
    bridge_health.add_argument("--strict", action="store_true")
    bridge_health.add_argument("--timeout", type=float, default=2.0)
    local_smoke = sub.add_parser("local-smoke")
    local_smoke.add_argument("--config", dest="sub_config")
    local_smoke.add_argument("--use-existing-bridge", action="store_true")
    local_smoke.add_argument("--keep-bridge", action="store_true")
    local_smoke.add_argument("--skip-vision", action="store_true")
    local_smoke.add_argument("--expect-text", default="OK")
    local_smoke.add_argument("--expect-vision", default="red")
    local_smoke.add_argument("--request-timeout", type=float, default=180)
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--config", dest="sub_config")
    doctor.add_argument("--strict", action="store_true")
    doctor.add_argument("--native-codex", action="store_true")
    windows_update_doctor = sub.add_parser("windows-update-doctor")
    windows_update_doctor.add_argument("--config", dest="sub_config")
    windows_update_doctor.add_argument("--json", action="store_true")
    windows_update_doctor.add_argument("--launch-gate", action="store_true")
    windows_update_doctor.add_argument("--skip-resource-check", action="store_true")
    windows_update_repair = sub.add_parser("windows-update-repair")
    windows_update_repair.add_argument("--config", dest="sub_config")
    windows_update_repair.add_argument("--apply", action="store_true")
    windows_update_ensure = sub.add_parser("windows-update-ensure")
    windows_update_ensure.add_argument("--config", dest="sub_config")
    windows_browser_ensure = sub.add_parser("windows-browser-ensure")
    windows_browser_ensure.add_argument("--config", dest="sub_config")
    windows_browser_ensure.add_argument("--wait-seconds", type=float, default=90)
    windows_browser_ensure.add_argument("--settle-seconds", type=float, default=15)
    windows_browser_ensure.add_argument("--poll-seconds", type=float, default=3)
    change_account = sub.add_parser("change-account")
    change_account.add_argument("--config", dest="sub_config")
    change_account.add_argument("--apply", action="store_true")
    change_account.add_argument("--recover-last", action="store_true")
    change_account.add_argument("--proxy-url")
    add_config(sub.add_parser("smoke"))
    init_config_parser = sub.add_parser("init-config")
    init_config_parser.add_argument("--output")
    init_config_parser.add_argument("--platform", choices=["macos", "windows"])
    init_config_parser.add_argument("--template")
    init_config_parser.add_argument("--force", action="store_true")
    sub.add_parser("security-scan").add_argument("root", nargs="?", default=".")
    validate_config = sub.add_parser("validate-config")
    validate_config.add_argument("--config", dest="sub_config")
    validate_config.add_argument("--check-paths", action="store_true")
    setup_report = sub.add_parser("setup-report")
    setup_report.add_argument("--config", dest="sub_config")
    setup_report.add_argument("--output")
    canary_report = sub.add_parser("canary-report")
    add_canary_report_args(canary_report)
    real_canary_template = sub.add_parser("real-canary-template")
    add_real_canary_template_args(real_canary_template)
    final_check = sub.add_parser("final-check")
    add_final_check_args(final_check)
    env_help = sub.add_parser("env-help")
    env_help.add_argument("--config", dest="sub_config")
    env_help.add_argument("--platform", choices=["macos", "windows"])
    env_help.add_argument("--name")
    setup = sub.add_parser("setup")
    setup.add_argument("--output")
    setup.add_argument("--platform", choices=["macos", "windows"])
    setup.add_argument("--codex-home")
    setup.add_argument("--provider-id")
    setup.add_argument("--provider-label")
    setup.add_argument("--base-url")
    setup.add_argument("--model")
    setup.add_argument("--api-key-env")
    setup.add_argument("--wire-api")
    setup.add_argument("--cloud-route", choices=["bridge", "direct"])
    setup.add_argument("--skip-cloud", action="store_true")
    setup.add_argument("--include-local", action="store_true")
    setup.add_argument("--llama-server-path")
    setup.add_argument("--model-path")
    setup.add_argument("--mmproj-path")
    setup.add_argument("--non-interactive", action="store_true")
    setup.add_argument("--force", action="store_true")
    menu = sub.add_parser("menu")
    menu.add_argument("--config", dest="sub_config")
    menu.add_argument("--force", action="store_true")
    menu.add_argument("--dry-run", action="store_true")
    switch = sub.add_parser("switch")
    switch.add_argument("provider_id")
    switch.add_argument("--config", dest="sub_config")
    switch.add_argument("--force", action="store_true")
    switch.add_argument("--dry-run", action="store_true")
    guarded_switch = sub.add_parser("guarded-switch")
    guarded_switch.add_argument("provider_id")
    guarded_switch.add_argument("--config", dest="sub_config")
    guarded_switch.add_argument("--force", action="store_true")
    guarded_switch.add_argument("--dry-run", action="store_true")
    guarded_switch.add_argument("--allow-local", action="store_true")
    guarded_switch.add_argument("--skip-local-smoke", action="store_true")
    history_status = sub.add_parser("history-status")
    history_status.add_argument("--config", dest="sub_config")
    unify_history = sub.add_parser("unify-history")
    unify_history.add_argument("--config", dest="sub_config")
    unify_history.add_argument("--from-provider", default="openai")
    unify_history.add_argument("--to-provider", default="custom")
    unify_history.add_argument("--from-model")
    unify_history.add_argument("--to-model")
    unify_history.add_argument("--dry-run", action="store_true")
    unify_history.add_argument("--apply", action="store_true")
    restore_history = sub.add_parser("restore-history-backup")
    restore_history.add_argument("--config", dest="sub_config")
    restore_history.add_argument("--backup", required=True)
    add_config(sub.add_parser("status"))

    args = parser.parse_args(argv)
    config_path = getattr(args, "sub_config", None) or args.config
    if args.command == "bridge":
        return run_bridge(config_path)
    if args.command == "ensure-bridge":
        return run_ensure_bridge(config_path)
    if args.command == "hot-router":
        return run_hot_router(config_path, host=args.host, port=args.port)
    if args.command == "hot-router-mode":
        return run_hot_router_mode(
            args.mode_command,
            config_path,
            router_url=args.router_url,
            allow_codex_running=args.allow_codex_running,
        )
    if args.command == "bridge-health":
        return run_bridge_health(config_path, strict=args.strict, timeout=args.timeout)
    if args.command == "local-smoke":
        return run_local_smoke(
            config_path,
            use_existing_bridge=args.use_existing_bridge,
            keep_bridge=args.keep_bridge,
            skip_vision=args.skip_vision,
            expect_text=args.expect_text,
            expect_vision=args.expect_vision,
            request_timeout=args.request_timeout,
        )
    if args.command == "doctor":
        return run_doctor(config_path, strict=args.strict, native_codex=args.native_codex)
    if args.command == "windows-update-doctor":
        return run_windows_update_doctor(
            config_path,
            json_output=args.json,
            launch_gate=args.launch_gate,
            include_resources=not args.skip_resource_check,
        )
    if args.command == "windows-update-repair":
        return run_windows_update_repair(config_path, apply=args.apply)
    if args.command == "windows-update-ensure":
        return run_windows_update_ensure(config_path)
    if args.command == "windows-browser-ensure":
        return run_windows_browser_ensure(
            config_path,
            wait_seconds=args.wait_seconds,
            settle_seconds=args.settle_seconds,
            poll_seconds=args.poll_seconds,
        )
    if args.command == "change-account":
        return run_change_account(
            config_path,
            apply=args.apply,
            recover_last=args.recover_last,
            proxy_url=args.proxy_url,
        )
    if args.command == "smoke":
        return run_smoke(config_path)
    if args.command == "init-config":
        return init_config(output=args.output, platform=args.platform, template=args.template, force=args.force)
    if args.command == "security-scan":
        return run_security_scan(args.root)
    if args.command == "validate-config":
        return run_validate_config(config_path, check_paths=args.check_paths)
    if args.command == "setup-report":
        return run_setup_report(config_path, output=args.output)
    if args.command == "canary-report":
        return run_canary_report(
            config_path,
            output=args.output,
            provider_id=args.provider_id,
            setup_report=args.setup_report,
            verdict=args.verdict,
            evidence=evidence_from_args(args),
        )
    if args.command == "real-canary-template":
        return run_real_canary_template(
            config_path,
            output=args.output,
            provider_id=args.provider_id,
            setup_report=args.setup_report,
            canary_report=args.canary_report,
        )
    if args.command == "final-check":
        return run_final_check(
            config_path,
            setup_report=args.setup_report,
            canary_report=args.canary_report,
            real_canary_template=args.real_canary_template,
            output=args.output,
        )
    if args.command == "env-help":
        return run_env_help(config_path, platform=args.platform, name=args.name)
    if args.command == "setup":
        return run_setup_wizard(
            output=args.output,
            platform=args.platform,
            codex_home=args.codex_home,
            provider_id=args.provider_id,
            provider_label=args.provider_label,
            base_url=args.base_url,
            model=args.model,
            api_key_env=args.api_key_env,
            wire_api=args.wire_api,
            cloud_route=args.cloud_route,
            include_cloud=not args.skip_cloud,
            include_local=args.include_local,
            llama_server_path=args.llama_server_path,
            model_path=args.model_path,
            mmproj_path=args.mmproj_path,
            non_interactive=args.non_interactive,
            force=args.force,
        )
    if args.command == "menu":
        return interactive_menu(config_path, force=args.force, dry_run=args.dry_run)
    if args.command == "switch":
        return switch_provider(args.provider_id, config_path, force=args.force, dry_run=args.dry_run)
    if args.command == "guarded-switch":
        return guarded_switch_provider(
            args.provider_id,
            config_path,
            force=args.force,
            dry_run=args.dry_run,
            allow_local=args.allow_local,
            skip_local_smoke=args.skip_local_smoke,
        )
    if args.command == "history-status":
        return run_history_status(config_path)
    if args.command == "unify-history":
        return run_unify_history(
            config_path,
            from_provider=args.from_provider,
            to_provider=args.to_provider,
            from_model=args.from_model,
            to_model=args.to_model,
            dry_run=args.dry_run or not args.apply,
            apply=args.apply,
        )
    if args.command == "restore-history-backup":
        return run_restore_history_backup(config_path, backup=args.backup)
    if args.command == "status":
        return run_doctor(config_path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
