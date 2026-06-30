#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codex_hybrid_switcher.config import DEFAULT_CONFIG, expand_path, load_config  # noqa: E402
from codex_hybrid_switcher.private_config import run_validate_config  # noqa: E402
from codex_hybrid_switcher.setup_wizard import DEFAULT_PROVIDER_ID, run_setup_wizard  # noqa: E402
from codex_hybrid_switcher.switcher import guarded_switch_provider, protected_hashes  # noqa: E402


def default_platform() -> str:
    return "windows" if os.name == "nt" else "macos"


def print_header() -> None:
    print("Codex Hybrid Model Switcher bootstrap")
    print("=====================================")
    print("This script runs from the repository without installing the package first.")
    print("Default mode creates a private config, validates it, and runs dry-run only.")
    print()


def print_preflight(config_path: Path) -> None:
    print("Preflight")
    print(f"  platform: {platform.system() or sys.platform}")
    print(f"  python: {sys.version.split()[0]}")
    print(f"  repository: {ROOT}")
    print(f"  private config: {config_path}")
    print()


def run_validate_and_dry_run(config_path: Path, provider_id: str, *, skip_dry_run: bool) -> int:
    validate_code = run_validate_config(str(config_path))
    if validate_code != 0:
        return validate_code

    if skip_dry_run:
        print()
        print("Skipped guarded dry-run by request. No Codex files were changed.")
        return 0

    print()
    print("Guarded dry-run")
    print("No files will be changed in this step.")
    print()
    return guarded_switch_provider(provider_id, str(config_path), dry_run=True)


def print_apply_instructions(config_path: Path, provider_id: str) -> None:
    print()
    print("Next step for a real switch")
    print("  1. Review the dry-run above.")
    print("  2. Quit Codex Desktop completely.")
    print("  3. From this repository, run:")
    if os.name == "nt":
        print(f"     set PYTHONPATH={SRC} && py -3 -m codex_hybrid_switcher guarded-switch {provider_id} --config {config_path}")
    else:
        print(f"     PYTHONPATH={SRC} python3 -m codex_hybrid_switcher guarded-switch {provider_id} --config {config_path}")
    print()
    print("If you already installed the package, the shorter command is:")
    if os.name == "nt":
        print(f"     py -3 -m codex_hybrid_switcher guarded-switch {provider_id} --config {config_path}")
    else:
        print(f"     python3 -m codex_hybrid_switcher guarded-switch {provider_id} --config {config_path}")
    print()
    print("Do not edit auth.json, models_cache.json, state_5.sqlite, or sessions.")
    print()
    print("If validate-config shows api_key_env(...unset), print safe setup instructions with:")
    if os.name == "nt":
        print(f"     set PYTHONPATH={SRC} && py -3 -m codex_hybrid_switcher env-help --config {config_path}")
    else:
        print(f"     PYTHONPATH={SRC} python3 -m codex_hybrid_switcher env-help --config {config_path}")
    print()
    print("For bridge-routed providers, check the bridge entry point with:")
    if os.name == "nt":
        print(f"     set PYTHONPATH={SRC} && py -3 -m codex_hybrid_switcher bridge-health --config {config_path}")
    else:
        print(f"     PYTHONPATH={SRC} python3 -m codex_hybrid_switcher bridge-health --config {config_path}")
    print()
    print("After applying, generate a redacted setup report with:")
    if os.name == "nt":
        print(
            f"     set PYTHONPATH={SRC} && py -3 -m codex_hybrid_switcher setup-report "
            f"--config {config_path} --output %USERPROFILE%\\Desktop\\codex-hybrid-setup-report.md"
        )
    else:
        print(
            f"     PYTHONPATH={SRC} python3 -m codex_hybrid_switcher setup-report "
            f"--config {config_path} --output ~/Desktop/codex-hybrid-setup-report.md"
        )
    print()
    print("After Codex Desktop opens, account/plugins/MCP/project list are visible, and a test chat responds, record final canary evidence with:")
    if os.name == "nt":
        print(
            f"     set PYTHONPATH={SRC} && py -3 -m codex_hybrid_switcher canary-report "
            f"--config {config_path} --provider-id {provider_id} --setup-report %USERPROFILE%\\Desktop\\codex-hybrid-setup-report.md "
            "--account-visible yes --plugins-visible yes --mcp-visible yes --project-list-visible yes "
            "--test-chat-responded yes --bridge-health-passed yes --setup-report-reviewed yes --verdict complete "
            "--output %USERPROFILE%\\Desktop\\codex-hybrid-canary-evidence.md"
        )
    else:
        print(
            f"     PYTHONPATH={SRC} python3 -m codex_hybrid_switcher canary-report "
            f"--config {config_path} --provider-id {provider_id} --setup-report ~/Desktop/codex-hybrid-setup-report.md "
            "--account-visible yes --plugins-visible yes --mcp-visible yes --project-list-visible yes "
            "--test-chat-responded yes --bridge-health-passed yes --setup-report-reviewed yes --verdict complete "
            "--output ~/Desktop/codex-hybrid-canary-evidence.md"
        )
    print()
    print("For a real clean-machine canary, create the final field checklist with:")
    if os.name == "nt":
        print(
            f"     set PYTHONPATH={SRC} && py -3 -m codex_hybrid_switcher real-canary-template "
            f"--config {config_path} --provider-id {provider_id} "
            "--setup-report %USERPROFILE%\\Desktop\\codex-hybrid-setup-report.md "
            "--canary-report %USERPROFILE%\\Desktop\\codex-hybrid-canary-evidence.md "
            "--output %USERPROFILE%\\Desktop\\codex-hybrid-real-clean-machine-canary.md"
        )
    else:
        print(
            f"     PYTHONPATH={SRC} python3 -m codex_hybrid_switcher real-canary-template "
            f"--config {config_path} --provider-id {provider_id} "
            "--setup-report ~/Desktop/codex-hybrid-setup-report.md "
            "--canary-report ~/Desktop/codex-hybrid-canary-evidence.md "
            "--output ~/Desktop/codex-hybrid-real-clean-machine-canary.md"
        )
    print()
    print("Then generate the read-only final check with:")
    if os.name == "nt":
        print(
            f"     set PYTHONPATH={SRC} && py -3 -m codex_hybrid_switcher final-check "
            f"--config {config_path} "
            "--setup-report %USERPROFILE%\\Desktop\\codex-hybrid-setup-report.md "
            "--canary-report %USERPROFILE%\\Desktop\\codex-hybrid-canary-evidence.md "
            "--real-canary-template %USERPROFILE%\\Desktop\\codex-hybrid-real-clean-machine-canary.md "
            "--output %USERPROFILE%\\Desktop\\codex-hybrid-final-check.md"
        )
    else:
        print(
            f"     PYTHONPATH={SRC} python3 -m codex_hybrid_switcher final-check "
            f"--config {config_path} "
            "--setup-report ~/Desktop/codex-hybrid-setup-report.md "
            "--canary-report ~/Desktop/codex-hybrid-canary-evidence.md "
            "--real-canary-template ~/Desktop/codex-hybrid-real-clean-machine-canary.md "
            "--output ~/Desktop/codex-hybrid-final-check.md"
        )
    print()
    print("Use FINAL_CHECK.md to review the final Complete / Partially complete / Not complete / Needs rollback verdict.")


def run_bootstrap(args: argparse.Namespace) -> int:
    config_path = expand_path(args.config or DEFAULT_CONFIG)
    provider_id = args.provider_id or DEFAULT_PROVIDER_ID
    print_header()
    print_preflight(config_path)

    if config_path.exists() and not args.force_config:
        print("Private config already exists; using it.")
        print("Use --force-config to regenerate it.")
    else:
        setup_code = run_setup_wizard(
            output=str(config_path),
            platform=args.platform or default_platform(),
            codex_home=args.codex_home,
            provider_id=provider_id,
            provider_label=args.provider_label,
            base_url=args.base_url,
            model=args.model,
            api_key_env=args.api_key_env,
            cloud_route=args.cloud_route,
            include_local=args.include_local,
            llama_server_path=args.llama_server_path,
            model_path=args.model_path,
            mmproj_path=args.mmproj_path,
            non_interactive=args.non_interactive,
            force=args.force_config,
        )
        if setup_code != 0:
            return setup_code

    config = load_config(str(config_path))
    if args.show_hashes:
        print()
        print("Protected Codex file hashes")
        for name, digest in protected_hashes(config).items():
            print(f"  - {name}: {'missing' if digest is None else digest[:12]}")

    code = run_validate_and_dry_run(config_path, provider_id, skip_dry_run=args.skip_dry_run)
    if code == 0:
        print_apply_instructions(config_path, provider_id)
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe first-run bootstrap for Codex Hybrid Model Switcher.")
    parser.add_argument("--config", help="private config path; defaults to ~/.codex-hybrid-model-switcher/config.json")
    parser.add_argument("--platform", choices=["macos", "windows"], help="target platform for generated config")
    parser.add_argument("--codex-home", help="Codex home path for generated config")
    parser.add_argument("--provider-id", default=DEFAULT_PROVIDER_ID)
    parser.add_argument("--provider-label")
    parser.add_argument("--base-url")
    parser.add_argument("--model")
    parser.add_argument("--api-key-env")
    parser.add_argument("--cloud-route", choices=["bridge", "direct"], help="cloud provider route; bridge uses the local bridge and api_key_env, direct writes provider base_url into Codex config")
    parser.add_argument("--include-local", action="store_true", help="include local llama.cpp provider in generated config")
    parser.add_argument("--llama-server-path")
    parser.add_argument("--model-path")
    parser.add_argument("--mmproj-path")
    parser.add_argument("--non-interactive", action="store_true", help="do not prompt; requires --base-url for new configs")
    parser.add_argument("--force-config", action="store_true", help="replace existing private config")
    parser.add_argument("--skip-dry-run", action="store_true", help="validate only; do not run guarded dry-run")
    parser.add_argument("--show-hashes", action="store_true", help="print protected Codex file hash prefixes")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_bootstrap(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
