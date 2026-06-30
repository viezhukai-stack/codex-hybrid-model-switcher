from __future__ import annotations

import argparse
import sys

from .bridge import run_bridge
from .bridge_health import run_bridge_health
from .doctor import run_doctor
from .env_help import run_env_help
from .local_smoke import run_local_smoke
from .private_config import init_config, run_validate_config
from .report import run_setup_report
from .security import run_security_scan
from .setup_wizard import run_setup_wizard
from .smoke import run_smoke
from .switcher import guarded_switch_provider, interactive_menu, switch_provider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codex-hybrid-switcher")
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_config(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--config", dest="sub_config")
        return parser

    add_config(sub.add_parser("bridge"))
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
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--config", dest="sub_config")
    doctor.add_argument("--strict", action="store_true")
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
    add_config(sub.add_parser("status"))

    args = parser.parse_args(argv)
    config_path = getattr(args, "sub_config", None) or args.config
    if args.command == "bridge":
        return run_bridge(config_path)
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
        )
    if args.command == "doctor":
        return run_doctor(config_path, strict=args.strict)
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
    if args.command == "status":
        return run_doctor(config_path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
