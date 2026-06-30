# Quickstart Demo

This demo shows the safest path for trying **Codex Hybrid Model Switcher**
without touching a real Codex profile first.

It uses generated private config files, temporary validation workspaces, and
`--dry-run` output. You can copy the commands, inspect what would change, and
stop before any real Codex Desktop configuration is written.

## What This Demo Proves

By the end, you should have verified that:

- the package installs locally
- tests pass in an isolated environment
- the security scanner finds no sensitive-looking content
- a private config can be generated and validated
- `guarded-switch --dry-run` prints a redacted Codex config diff
- no real `auth.json`, `models_cache.json`, `state_5.sqlite`, or session files
  are modified

## 1. Clone and Install

```sh
git clone https://github.com/viezhukai-stack/codex-hybrid-model-switcher.git
cd codex-hybrid-model-switcher
python3 -m pip install -e .
```

For development checks:

```sh
python3 -m pip install -e ".[dev]"
```

## 2. Run Isolated Install Validation

Before pointing the tool at your real Codex profile, run:

```sh
python3 scripts/validate-install.py
```

Expected high-level result:

```text
42 passed
No sensitive-looking content found.
install validation passed
```

The script creates a temporary workspace and exercises the tool against a
simulated Codex config. It does not write your real `~/.codex` directory.

## 3. Generate a Private Config

macOS:

```sh
codex-hybrid-switcher init-config --platform macos --output ~/.codex-hybrid-model-switcher/config.json
```

Windows PowerShell:

```powershell
codex-hybrid-switcher init-config --platform windows --output "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

This file is private machine-local state. Do not commit it.

## 4. Edit Provider Placeholders

Open the generated config and replace placeholder provider values.

The cloud provider section should look conceptually like this:

```json
{
  "id": "cloud-gpt-main",
  "kind": "cloud",
  "name": "Cloud GPT Main",
  "base_url": "https://your-openai-compatible-provider.example/v1",
  "model": "provider-gpt-main",
  "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
  "wire_api": "responses"
}
```

Keep the API key outside the config file:

```sh
export OPENAI_COMPATIBLE_API_KEY="replace-with-your-provider-key"
```

Windows PowerShell:

```powershell
$env:OPENAI_COMPATIBLE_API_KEY = "replace-with-your-provider-key"
```

## 5. Validate the Private Config

macOS:

```sh
codex-hybrid-switcher validate-config --config ~/.codex-hybrid-model-switcher/config.json
```

Windows PowerShell:

```powershell
codex-hybrid-switcher validate-config --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

The output redacts provider hosts and local paths:

```text
Private config validation
config: <private-config>
codex_home: configured
bridge: 127.0.0.1:19030 -> llama:19031
providers:
  - openai-official [official] model=gpt-5.5
  - cloud-gpt-main [cloud] model=provider-gpt-main base_url=https://<redacted>/v1 api_key_env=OPENAI_COMPATIBLE_API_KEY(set)
Config validation passed.
```

Warnings about local llama.cpp paths are not blockers if you are only testing a
cloud provider.

## 6. Preview the Switch

macOS:

```sh
codex-hybrid-switcher guarded-switch cloud-gpt-main --dry-run --config ~/.codex-hybrid-model-switcher/config.json
```

Windows PowerShell:

```powershell
codex-hybrid-switcher guarded-switch cloud-gpt-main --dry-run --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

Expected shape:

```diff
-model_provider = "openai"
-model = "gpt-5.5"
-review_model = "gpt-5.5"
+model_provider = "custom"
+model = "provider-gpt-main"
+review_model = "provider-gpt-main"

 [model_providers.custom]
 name = "<redacted>"
 base_url = "<redacted>"
 wire_api = "responses"
```

Dry-run means:

- no files changed
- no backup created
- no bridge started
- no Codex Desktop restart

## 7. Decide Whether to Apply

Only apply for real after the dry-run looks narrow and you have quit Codex
Desktop completely.

Real cloud switch:

```sh
codex-hybrid-switcher guarded-switch cloud-gpt-main --config ~/.codex-hybrid-model-switcher/config.json
```

Real Windows cloud switch:

```powershell
codex-hybrid-switcher guarded-switch cloud-gpt-main --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

The guarded flow backs up `config.toml` and hashes protected files before and
after applying:

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`

## 8. Optional Local Model Demo

Local llama.cpp support is optional and machine-dependent.

Before switching Codex to a local model, run:

```sh
codex-hybrid-switcher local-smoke --config ~/.codex-hybrid-model-switcher/config.json
```

Only if the smoke test passes:

```sh
codex-hybrid-switcher guarded-switch local-gemma --allow-local --config ~/.codex-hybrid-model-switcher/config.json
```

If local smoke fails because of CUDA, VRAM, model size, missing llama.cpp, or a
missing mmproj file, that is an environment limitation rather than a cloud
provider failure.

## Recovery

If a real provider switch behaves unexpectedly:

1. Quit Codex Desktop.
2. Restore the newest `config.toml.bak-codex-hybrid-*` backup.
3. Reopen Codex Desktop.

The tool is designed not to edit account state, model cache, session history,
or rollout logs.

## More Reading

- Chinese tutorial: [`tutorial.zh-CN.md`](tutorial.zh-CN.md)
- Safety model: [`safety.md`](safety.md)
- Recovery guide: [`recovery.md`](recovery.md)
- Windows user flow: [`windows-user-flow.md`](windows-user-flow.md)
- Local llama.cpp smoke: [`local-llama-smoke.md`](local-llama-smoke.md)
