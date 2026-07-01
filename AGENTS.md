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

1. `HANDOFF_TO_CODEX.md`
2. `START_HERE.md`
3. `FINAL_CHECK.md`
4. `README.md`
5. `docs/bootstrap.md`
6. `docs/first-run-wizard.md`
7. `docs/agent-assisted-setup.md`
8. `docs/api-key-environment.md`
9. `docs/bridge-health.md`
10. `docs/recovery.md`
11. `docs/setup-report.md`
12. `docs/canary-report.md`
13. `docs/real-clean-machine-canary.md`
14. `docs/windows-hyperv-clean-vm-canary.md` for the final clean Windows VM
    public-readiness proof
15. `docs/supervised-handoff-drill.md` for checking beginner handoff command
    executability before doing a real switch
16. `docs/windows-one-click-installer.md` for Windows computers that may not
    have Codex Desktop, Python, Git, llama.cpp, or local model files yet
17. `docs/final-check.md`
18. `docs/agent-handoff-drill.md`
19. `docs/stock-codex-handoff-validation.md`
20. `docs/user-success-criteria.md`
21. `docs/local-llama-smoke.md` only if the user asks for local models

## Required User Inputs

For a first cloud setup, collect:

- operating system: macOS or Windows
- OpenAI-compatible `base_url`
- model id
- environment variable name that contains the API key
- cloud route: use `bridge` by default; use `direct` only when the provider is
  known to work with Codex Desktop's direct custom-provider auth
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

Use `bootstrap.py` first when possible. It runs from the repository without
installing the package, creates a private config, validates it, and runs a
guarded dry-run.

Use the current Python executable where possible. On macOS, `python3` is usually
available. On Windows, try `py -3` or `python`.

1. Inspect the repository and current branch.
2. Run bootstrap:

   ```sh
   python3 bootstrap.py
   ```

   On Windows, use:

   ```powershell
   py -3 bootstrap.py
   ```

   If the user already provided all cloud fields, use non-interactive bootstrap:

   ```sh
   python3 bootstrap.py --non-interactive \
     --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 \
     --model provider-gpt-main \
     --api-key-env OPENAI_COMPATIBLE_API_KEY \
     --cloud-route bridge
   ```

3. If bootstrap cannot run, install the package locally and use the setup
   command:

   ```sh
   python3 -m pip install -e .
   codex-hybrid-switcher setup
   ```

4. Validate the private config if bootstrap did not already do it:

   ```sh
   codex-hybrid-switcher validate-config --config ~/.codex-hybrid-model-switcher/config.json
   ```

5. If validation shows `api_key_env(...unset)`, print safe OS-specific setup
   instructions:

   ```sh
   codex-hybrid-switcher env-help --config ~/.codex-hybrid-model-switcher/config.json
   ```

   If running from the repository without installation, use:

   ```sh
   PYTHONPATH=src python3 -m codex_hybrid_switcher env-help --config ~/.codex-hybrid-model-switcher/config.json
   ```

   Do not ask the user to paste the API key into repository files or commit it.

6. Preview the change if bootstrap did not already do it:

   ```sh
   codex-hybrid-switcher guarded-switch cloud-gpt-main --dry-run --config ~/.codex-hybrid-model-switcher/config.json
   ```

7. Confirm the dry-run only changes provider/model settings and preserves MCP,
   plugins, desktop, projects, and unrelated settings.

8. For bridge-routed cloud providers, confirm the API key environment variable
   is set before the real switch. If it is unset, stop and help the user set it
   outside the repository.

9. For bridge-routed cloud providers, run `bridge-health` before the real
   switch or immediately after a failed/silent test chat:

   ```sh
   codex-hybrid-switcher bridge-health --config ~/.codex-hybrid-model-switcher/config.json
   ```

   If it reports a closed bridge port before the real switch, that can be
   acceptable because guarded apply can start the managed bridge. If it reports
   missing API key variables, stale models, or an unhealthy HTTP API, fix that
   before asking the user to test Codex Desktop again.

10. Ask the user to fully quit Codex Desktop.

11. Apply the guarded switch using the command printed by bootstrap. If running
   from the repository on macOS, the command shape is:

   ```sh
   PYTHONPATH=src python3 -m codex_hybrid_switcher guarded-switch cloud-gpt-main --config ~/.codex-hybrid-model-switcher/config.json
   ```

   If the package was installed, `codex-hybrid-switcher guarded-switch ...` is
   also acceptable.

12. Ask the user to reopen Codex Desktop and create a new test conversation.

13. If Codex opens but the new conversation does not reply, run `bridge-health`
    again before changing any Codex files.

14. Generate a redacted setup report:

    ```sh
    PYTHONPATH=src python3 -m codex_hybrid_switcher setup-report --config ~/.codex-hybrid-model-switcher/config.json --output ~/Desktop/codex-hybrid-setup-report.md
    ```

15. After the user confirms account, plugins/MCP, project list, and a new test
    conversation, generate a canary evidence report:

    ```sh
    PYTHONPATH=src python3 -m codex_hybrid_switcher canary-report --config ~/.codex-hybrid-model-switcher/config.json --provider-id cloud-gpt-main --account-visible yes --plugins-visible yes --mcp-visible yes --project-list-visible yes --test-chat-responded yes --bridge-health-passed yes --setup-report-reviewed yes --verdict complete --output ~/Desktop/codex-hybrid-canary-evidence.md
    ```

16. Generate a real clean-machine canary checklist:

    ```sh
    PYTHONPATH=src python3 -m codex_hybrid_switcher real-canary-template --config ~/.codex-hybrid-model-switcher/config.json --provider-id cloud-gpt-main --setup-report ~/Desktop/codex-hybrid-setup-report.md --canary-report ~/Desktop/codex-hybrid-canary-evidence.md --output ~/Desktop/codex-hybrid-real-clean-machine-canary.md
    ```

17. Generate the read-only final check:

    ```sh
    PYTHONPATH=src python3 -m codex_hybrid_switcher final-check --config ~/.codex-hybrid-model-switcher/config.json --setup-report ~/Desktop/codex-hybrid-setup-report.md --canary-report ~/Desktop/codex-hybrid-canary-evidence.md --real-canary-template ~/Desktop/codex-hybrid-real-clean-machine-canary.md --output ~/Desktop/codex-hybrid-final-check.md
    ```

18. If anything looks wrong, quit Codex Desktop and restore the newest
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
- bridge-routed providers have either passed `bridge-health` or have a clear
  bridge/key/model-list action item
- protected file hashes are unchanged
- user confirms Codex account, plugins/MCP, and project list are visible
- user confirms a new test conversation responds
- a redacted setup report has been generated or the user explicitly skipped it
- a canary evidence report has recorded the visible checks or the user
  explicitly skipped it
- a real clean-machine canary template has been generated for a first public
  handoff test, or the user explicitly skipped real canary evidence
- a final check report has been generated, or the user explicitly skipped final
  verification
- the user success checklist has been reviewed, or the user explicitly skipped
  it
- final verdict from `FINAL_CHECK.md` is `Complete`, or the user explicitly
  skipped final verification

For repository release work, also run `scripts/validate-stock-codex-handoff.py`,
`scripts/validate-agent-handoff-drill.py`, and
`scripts/validate-real-clean-machine-canary.py` to prove the `START_HERE.md`
flow still works from a clean repository copy and reaches final evidence.

For a stock Windows machine that may not have Python or Git, prefer
`scripts/bootstrap-windows.ps1` for the beginner path. It can download the fixed
release zip, check or install Python 3.12 with `winget`, create a private config,
run validation and bridge diagnostics, and stop at `guarded-switch --dry-run`.

For a beginner Windows machine that may not have Codex Desktop at all, use
`docs/windows-one-click-installer.md` and the release asset
`Codex-Hybrid-Windows-Setup-v2.13.0.zip`. The installer opens the official Codex
app page when Codex is missing, installs Python with `winget`, downloads this
project release, can download official llama.cpp assets, lets the user select
their own GGUF and mmproj files, and defaults to guarded dry-run. It must not
redistribute Codex Desktop, model files, or API keys.

For the final public-readiness field proof, follow
`docs/windows-hyperv-clean-vm-canary.md`: start from a Windows 11 Hyper-V VM
with stock Codex Desktop only, create checkpoint `stock-codex-baseline`, use the
fixed release `v2.12.2`, configure one cloud provider with
`cloud_route=bridge`, run `guarded-switch --dry-run`, require the user to quit
Codex Desktop before real apply, and require `codex-hybrid-final-check.md` to
report `Complete`. Do not include local llama.cpp in that canary.

If only setup/dry-run is complete, say exactly that. Do not imply the real
Codex Desktop switch has been tested.
