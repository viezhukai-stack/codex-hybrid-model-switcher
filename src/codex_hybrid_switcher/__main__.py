from __future__ import annotations

import argparse
import sys

from .bridge import run_bridge
from .doctor import run_doctor
from .private_config import init_config, run_validate_config
from .security import run_security_scan
from .smoke import run_smoke
from .switcher import interactive_menu, switch_provider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codex-hybrid-switcher")
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_config(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--config", dest="sub_config")
        return parser

    add_config(sub.add_parser("bridge"))
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
    menu = sub.add_parser("menu")
    menu.add_argument("--config", dest="sub_config")
    menu.add_argument("--force", action="store_true")
    menu.add_argument("--dry-run", action="store_true")
    switch = sub.add_parser("switch")
    switch.add_argument("provider_id")
    switch.add_argument("--config", dest="sub_config")
    switch.add_argument("--force", action="store_true")
    switch.add_argument("--dry-run", action="store_true")
    add_config(sub.add_parser("status"))

    args = parser.parse_args(argv)
    config_path = getattr(args, "sub_config", None) or args.config
    if args.command == "bridge":
        return run_bridge(config_path)
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
    if args.command == "menu":
        return interactive_menu(config_path, force=args.force, dry_run=args.dry_run)
    if args.command == "switch":
        return switch_provider(args.provider_id, config_path, force=args.force, dry_run=args.dry_run)
    if args.command == "status":
        return run_doctor(config_path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
