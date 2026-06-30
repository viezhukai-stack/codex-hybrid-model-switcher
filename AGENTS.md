# Agent Runbook: Configure Codex Hybrid Model Switcher

This repository is meant to be handed to a Codex agent on a user's machine.
Follow this runbook when the user asks you to configure Codex Desktop for
OpenAI-compatible cloud providers or optional local llama.cpp models.

## Mission

Help a stock Codex Desktop user reach a working, recoverable hybrid setup:

- preserve Codex account state
- preserve plugins, MCP, project settings, and visible conversations as much as
  Codex provider bucketing allows
- configure one or more user-provided OpenAI-compatible providers
- optionally configure local llama.cpp only after cloud setup works
- keep every real write backup-first and guarded

## Non-negotiable Safety Rules

Never edit, overwrite, delete, migrate, or synthesize these files:

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- `sessions/`
- rollout logs

Never install LaunchAgents, KeepAlive jobs, scheduled tasks, recovery loops, or
auto-restart scripts.

Never switch providers while Codex Desktop is running. A real switch requires:

1. user confirms Codex Desktop is fully quit
2. `guarded-switch --dry-run` has been reviewed
3. `guarded-switch` backs up `config.toml`
4. protected file hashes are checked after the switch

Never store raw API keys in this repository. Use an environment variable name in
the private config, for example `OPENAI_COMPATIBLE_API_KEY`.

## Start Here

Read these files before making changes:

1. `README.md`
2. `docs/first-run-wizard.md`
3. `docs/agent-assisted-setup.md`
4. `docs/recovery.md`
5. `docs/local-llama-smoke.md` only if the user asks for local models

## Required User Inputs

For a first cloud setup, collect:

- operating system: macOS or Windows
- OpenAI-compatible `base_url`
- model id
- environment variable name that contains the API key
- whether the user wants only cloud setup now or also local llama.cpp later

Do not ask the user to paste API keys into the repository. If they paste a key
into chat, do not write it to files or quote it back unnecessarily.

For local llama.cpp, also collect:

- `llama-server` path
- GGUF model path
- mmproj path for multimodal models
- expected hardware limits if known

Local models are optional and machine-dependent. Do not configure them before
the cloud path works.

## Standard Cloud Setup Flow

Use the current Python executable where possible. On macOS, `python3` is usually
available. On Windows, try `py -3` or `python`.

1. Inspect the repository and current branch.
2. Install the package locally:

   ```sh
   python3 -m pip install -e .
   ```

3. Generate a private config only:

   ```sh
   codex-hybrid-switcher setup
   ```

   If the user already provided all cloud fields, use non-interactive setup:

   ```sh
   codex-hybrid-switcher setup --non-interactive \
     --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 \
     --model provider-gpt-main \
     --api-key-env OPENAI_COMPATIBLE_API_KEY
   ```

4. Validate the private config:

   ```sh
   codex-hybrid-switcher validate-config --config ~/.codex-hybrid-model-switcher/config.json
   ```

5. Preview the change:

   ```sh
   codex-hybrid-switcher guarded-switch cloud-gpt-main --dry-run --config ~/.codex-hybrid-model-switcher/config.json
   ```

6. Confirm the dry-run only changes provider/model settings and preserves MCP,
   plugins, desktop, projects, and unrelated settings.

7. Ask the user to fully quit Codex Desktop.

8. Apply the guarded switch:

   ```sh
   codex-hybrid-switcher guarded-switch cloud-gpt-main --config ~/.codex-hybrid-model-switcher/config.json
   ```

9. Ask the user to reopen Codex Desktop and create a new test conversation.

10. If anything looks wrong, quit Codex Desktop and restore the newest
    `config.toml.bak-codex-hybrid-*` backup. Do not edit databases or caches.

## History Visibility Caveat

Stock Codex conversations usually belong to the `openai` provider bucket. This
project uses the `custom` provider bucket for third-party providers. Existing
official conversations may appear separate after switching.

That is not deletion. Do not "fix" it by editing `state_5.sqlite` or session
files. Explain the provider-bucket behavior and only consider history migration
if the user explicitly asks for a separate, backed-up repair workflow outside
this project.

## Local llama.cpp Flow

Only after cloud setup works:

1. Fill local paths in the private config.
2. Run local smoke:

   ```sh
   codex-hybrid-switcher local-smoke --config ~/.codex-hybrid-model-switcher/config.json
   ```

3. Only if smoke passes, ask the user to quit Codex Desktop and switch:

   ```sh
   codex-hybrid-switcher guarded-switch local-gemma --allow-local --config ~/.codex-hybrid-model-switcher/config.json
   ```

If local smoke fails because of missing files, CUDA, VRAM, or model issues,
report the concrete failure and leave the cloud setup intact.

## Completion Criteria

Do not claim setup is complete until current evidence shows:

- private config exists outside the repository
- config validation passes
- dry-run diff is redacted and scoped to provider/model settings
- real switch, if performed, changed only `config.toml`
- protected file hashes are unchanged
- user confirms Codex account, plugins/MCP, and project list are visible
- user confirms a new test conversation responds

If only setup/dry-run is complete, say exactly that. Do not imply the real
Codex Desktop switch has been tested.
