from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Callable

from .config import DEFAULT_CONFIG, expand_path, load_config
from .private_config import run_validate_config, validate_config


DEFAULT_PROVIDER_ID = "cloud-gpt-main"
DEFAULT_PROVIDER_LABEL = "Cloud GPT Main"
DEFAULT_API_KEY_ENV = "OPENAI_COMPATIBLE_API_KEY"
DEFAULT_MODEL = "provider-gpt-main"
DEFAULT_WIRE_API = "responses"
DEFAULT_CLOUD_ROUTE = "bridge"
SECRET_SHAPED_RE = re.compile(r"(sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]{12,}|[A-Za-z0-9_-]{32,})")


def default_codex_home(platform: str | None = None) -> str:
    name = platform or ("windows" if os.name == "nt" else "macos")
    if name == "windows":
        return "~\\.codex"
    return "~/.codex"


def looks_like_secret(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if text.startswith("$") or text.startswith("%"):
        return False
    return bool(SECRET_SHAPED_RE.search(text))


def prompt_default(prompt: str, default: str, *, input_func: Callable[[str], str] = input) -> str:
    value = input_func(f"{prompt} [{default}]: ").strip()
    return value or default


def prompt_yes_no(prompt: str, default: bool, *, input_func: Callable[[str], str] = input) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = input_func(f"{prompt} [{suffix}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def build_first_run_config(
    *,
    platform: str | None = None,
    codex_home: str | None = None,
    provider_id: str = DEFAULT_PROVIDER_ID,
    provider_label: str = DEFAULT_PROVIDER_LABEL,
    base_url: str,
    model: str = DEFAULT_MODEL,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    wire_api: str = DEFAULT_WIRE_API,
    cloud_route: str = DEFAULT_CLOUD_ROUTE,
    include_official: bool = True,
    include_local: bool = False,
    local_model_id: str = "local/gemma",
    local_label: str = "Local Gemma",
    llama_server_path: str | None = None,
    model_path: str | None = None,
    mmproj_path: str | None = None,
) -> dict:
    providers: list[dict[str, object]] = []
    if include_official:
        providers.append(
            {
                "id": "openai-official",
                "label": "OpenAI Official",
                "kind": "official",
                "model": "gpt-5.5",
            }
        )
    providers.append(
        {
            "id": provider_id,
            "label": provider_label,
            "kind": "cloud",
            "base_url": base_url,
            "api_key_env": api_key_env,
            "model": model,
            "wire_api": wire_api,
            "route": cloud_route,
        }
    )

    local_model: dict[str, object] = {
        "id": local_model_id,
        "display_name": local_label,
        "context_window": 8192,
        "llama_server_path": llama_server_path or "~/path/to/llama-server",
        "model_path": model_path or "~/path/to/model.gguf",
        "mmproj_path": mmproj_path or "~/path/to/mmproj.gguf",
        "system_prompt": "You are a concise local coding assistant running through llama.cpp.",
        "max_output_tokens": 512,
        "extra_args": [
            "--jinja",
            "--reasoning",
            "off",
            "--reasoning-format",
            "none",
            "--reasoning-budget",
            "0",
            "--no-mmproj-offload",
        ],
    }

    if include_local:
        providers.append(
            {
                "id": "local-gemma",
                "label": local_label,
                "kind": "local",
                "base_url": "http://127.0.0.1:19030/v1",
                "model": local_model_id,
                "wire_api": "responses",
            }
        )

    return {
        "codex_home": codex_home or default_codex_home(platform),
        "cc_switch_home": "~/.cc-switch",
        "bridge": {
            "host": "127.0.0.1",
            "port": 19030,
            "llama_port": 19031,
            "idle_seconds": 600,
        },
        "providers": providers,
        "local_model": local_model,
    }


def write_config(path: Path, data: dict, *, force: bool = False) -> int:
    if path.exists() and not force:
        print(f"config already exists: {path}")
        print("Use --force to replace it.")
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Created private config: {path}")
    return 0


def print_next_steps(path: Path, provider_id: str, *, platform_name: str | None = None) -> None:
    if platform_name == "windows":
        setup_output = r"%USERPROFILE%\Desktop\codex-hybrid-setup-report.md"
        canary_output = r"%USERPROFILE%\Desktop\codex-hybrid-canary-evidence.md"
        real_canary_output = r"%USERPROFILE%\Desktop\codex-hybrid-real-clean-machine-canary.md"
    else:
        setup_output = "~/Desktop/codex-hybrid-setup-report.md"
        canary_output = "~/Desktop/codex-hybrid-canary-evidence.md"
        real_canary_output = "~/Desktop/codex-hybrid-real-clean-machine-canary.md"
    print()
    print("Next safe steps:")
    print(f"  1. Set the API key in your shell or OS environment for this provider.")
    print(f"  2. Run: codex-hybrid-switcher validate-config --config {path}")
    print(f"  3. For bridge route, run: codex-hybrid-switcher bridge-health --config {path}")
    print(f"  4. Run: codex-hybrid-switcher guarded-switch {provider_id} --dry-run --config {path}")
    print("  5. For a real switch, quit Codex Desktop completely first.")
    print(f"  6. After real apply, run: codex-hybrid-switcher setup-report --config {path} --output {setup_output}")
    print(
        "  7. After visible Codex checks pass, run: "
        f"codex-hybrid-switcher canary-report --config {path} --provider-id {provider_id} "
        f"--setup-report {setup_output} "
        "--account-visible yes --plugins-visible yes --mcp-visible yes --project-list-visible yes "
        "--test-chat-responded yes --bridge-health-passed yes --setup-report-reviewed yes --verdict complete "
        f"--output {canary_output}"
    )
    print(
        "  8. For a real clean-machine canary, run: "
        f"codex-hybrid-switcher real-canary-template --config {path} --provider-id {provider_id} "
        f"--setup-report {setup_output} --canary-report {canary_output} --output {real_canary_output}"
    )
    print("  9. Use FINAL_CHECK.md for the final verdict.")
    print()
    print("History note:")
    print("  This setup does not rewrite Codex history. Existing official conversations may")
    print("  belong to the openai bucket and can appear separate after switching to custom.")


def run_setup_wizard(
    *,
    output: str | None = None,
    platform: str | None = None,
    codex_home: str | None = None,
    provider_id: str | None = None,
    provider_label: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    api_key_env: str | None = None,
    wire_api: str | None = None,
    cloud_route: str | None = None,
    include_local: bool = False,
    llama_server_path: str | None = None,
    model_path: str | None = None,
    mmproj_path: str | None = None,
    non_interactive: bool = False,
    force: bool = False,
    input_func: Callable[[str], str] = input,
) -> int:
    target = expand_path(output or DEFAULT_CONFIG)
    platform_name = platform or ("windows" if os.name == "nt" else "macos")
    chosen_provider_id = provider_id or DEFAULT_PROVIDER_ID
    chosen_provider_label = provider_label or DEFAULT_PROVIDER_LABEL
    chosen_wire_api = wire_api or DEFAULT_WIRE_API
    chosen_cloud_route = cloud_route or DEFAULT_CLOUD_ROUTE

    if non_interactive:
        if not base_url:
            print("--base-url is required in --non-interactive mode.")
            return 2
        chosen_codex_home = codex_home or default_codex_home(platform_name)
        chosen_model = model or DEFAULT_MODEL
        chosen_api_key_env = api_key_env or DEFAULT_API_KEY_ENV
    else:
        print("Codex Hybrid Model Switcher first-run setup")
        print("This creates a private config only. It does not switch Codex.")
        print()
        chosen_codex_home = prompt_default("Codex home", codex_home or default_codex_home(platform_name), input_func=input_func)
        chosen_provider_id = prompt_default("Cloud provider id", chosen_provider_id, input_func=input_func)
        chosen_provider_label = prompt_default("Cloud provider label", chosen_provider_label, input_func=input_func)
        base_url = prompt_default("OpenAI-compatible base_url", base_url or "https://YOUR-ENDPOINT.example/v1", input_func=input_func)
        chosen_model = prompt_default("Model id", model or DEFAULT_MODEL, input_func=input_func)
        chosen_api_key_env = prompt_default("API key environment variable name", api_key_env or DEFAULT_API_KEY_ENV, input_func=input_func)
        chosen_cloud_route = prompt_default("Cloud route (bridge or direct)", chosen_cloud_route, input_func=input_func)
        include_local = prompt_yes_no("Add a local llama.cpp provider now", include_local, input_func=input_func)
        if include_local:
            llama_server_path = prompt_default("llama-server path", llama_server_path or "~/path/to/llama-server", input_func=input_func)
            model_path = prompt_default("GGUF model path", model_path or "~/path/to/model.gguf", input_func=input_func)
            mmproj_path = prompt_default("mmproj path", mmproj_path or "~/path/to/mmproj.gguf", input_func=input_func)

    assert base_url is not None
    if looks_like_secret(chosen_api_key_env):
        print("api_key_env should be an environment variable name, not the API key itself.")
        return 2
    if chosen_cloud_route not in {"bridge", "direct"}:
        print("cloud route must be either 'bridge' or 'direct'.")
        return 2

    data = build_first_run_config(
        platform=platform_name,
        codex_home=chosen_codex_home,
        provider_id=chosen_provider_id,
        provider_label=chosen_provider_label,
        base_url=base_url,
        model=chosen_model,
        api_key_env=chosen_api_key_env,
        wire_api=chosen_wire_api,
        cloud_route=chosen_cloud_route,
        include_local=include_local,
        llama_server_path=llama_server_path,
        model_path=model_path,
        mmproj_path=mmproj_path,
    )
    code = write_config(target, data, force=force)
    if code != 0:
        return code

    config = load_config(str(target))
    errors = validate_config(config)
    if errors:
        print("Generated config has validation errors:")
        for error in errors:
            print(f"  - {error}")
        return 1
    run_validate_config(str(target))
    print_next_steps(target, chosen_provider_id, platform_name=platform_name)
    return 0
