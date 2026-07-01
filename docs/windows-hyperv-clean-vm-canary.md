# Windows Hyper-V clean VM canary

Use this workflow for the final real stock-Codex proof before a public release.
It starts from a clean Windows 11 Hyper-V virtual machine with only stock Codex
Desktop installed, then hands this GitHub project to Codex and asks Codex to
complete one guarded cloud-provider setup.

This canary is intentionally cloud-only. Do not test local llama.cpp, CUDA,
GPU, GGUF, or mmproj files in this pass. Local model validation is a separate
machine-dependent workflow.

## Goal

Prove that a user with only stock Codex Desktop can give Codex this repository
and have Codex safely configure one OpenAI-compatible cloud provider without
breaking account state, plugins/MCP, project visibility, or protected Codex
state files.

Use the fixed repository release `v2.12.1` for this canary. Do not use a
floating `main` branch for the final proof.

## Prepare the Hyper-V VM

1. Create a new Windows 11 Hyper-V VM.
2. Do not copy any existing machine state into the VM:
   - no `.codex`
   - no `.cc-switch`
   - no previous project folders
   - no old hybrid configs
   - no CC Switch profiles
   - no bridge services
3. Install stock Codex Desktop.
4. Open Codex Desktop and sign in normally.
5. Confirm the baseline UI:
   - account information is visible
   - plugin entry points are visible
   - MCP entry points are visible, or MCP is not used on this VM
   - project list is visible
   - no hybrid bridge, scheduled task, recovery loop, or old switcher is
     installed
6. Create a Hyper-V checkpoint named exactly:

   ```text
   stock-codex-baseline
   ```

This checkpoint is the rollback boundary. If the canary fails in a confusing
way, revert the VM instead of editing Codex databases, caches, sessions, or
rollout logs.

## Handoff to Codex

Inside the VM, give Codex the repository URL and ask it to follow
`HANDOFF_TO_CODEX.md` from release `v2.12.1`.

Use one cloud OpenAI-compatible provider only:

```text
cloud_route=bridge
```

Put the API key in an environment variable only. Do not paste the raw API key
into chat, repository files, reports, screenshots, issues, or logs.

Codex must complete these checks before any real switch. The dry-run step is
`guarded-switch --dry-run`; do not shorten it to a real apply command.

1. Read `HANDOFF_TO_CODEX.md`, `START_HERE.md`, `AGENTS.md`, and
   `FINAL_CHECK.md`.
2. Run the simulated handoff check:

   ```powershell
   py -3 scripts/validate-agent-handoff-drill.py
   ```

3. Create or validate the private config with the provider fields:
   - `base_url`
   - `model`
   - `api_key_env`
   - `cloud_route=bridge`
4. Run:

   ```powershell
   py -3 -m codex_hybrid_switcher validate-config --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
   ```

5. Run:

   ```powershell
   py -3 -m codex_hybrid_switcher bridge-health --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
   ```

6. Run guarded dry-run:

   ```powershell
   py -3 -m codex_hybrid_switcher guarded-switch cloud-gpt-main --dry-run --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
   ```

The dry-run must show only provider/model related `config.toml` changes. It
must not edit `auth.json`, `models_cache.json`, `state_5.sqlite`, `sessions/`,
or rollout logs.

## Real guarded switch

Only after dry-run is reviewed:

1. The user manually fully quits Codex Desktop.
2. Codex verifies Codex Desktop is not running.
3. Codex runs the real guarded switch:

   ```powershell
   py -3 -m codex_hybrid_switcher guarded-switch cloud-gpt-main --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
   ```

The real switch must:

- create `config.toml.bak-codex-hybrid-*`
- write only `config.toml`
- keep `auth.json`, `models_cache.json`, `state_5.sqlite`, `sessions/`, and
  rollout logs unchanged
- keep API key values out of output

## UI validation

After the real switch, reopen Codex Desktop manually and check:

- Codex Desktop opens without an error page
- account information is visible
- plugin entry points are visible
- MCP entry points are visible, or MCP is explicitly not used on this VM
- project list is visible
- a new test conversation responds through the selected cloud provider

The bottom-right model label is not the source of truth for this project. The
external provider configuration and bridge route are the source of truth.

## Required evidence

Generate all four redacted evidence files:

```powershell
py -3 -m codex_hybrid_switcher setup-report `
  --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json" `
  --output "$env:USERPROFILE\Desktop\codex-hybrid-setup-report.md"

py -3 -m codex_hybrid_switcher canary-report `
  --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json" `
  --provider-id cloud-gpt-main `
  --account-visible yes `
  --plugins-visible yes `
  --mcp-visible yes `
  --project-list-visible yes `
  --test-chat-responded yes `
  --bridge-health-passed yes `
  --setup-report-reviewed yes `
  --verdict complete `
  --output "$env:USERPROFILE\Desktop\codex-hybrid-canary-evidence.md"

py -3 -m codex_hybrid_switcher real-canary-template `
  --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json" `
  --provider-id cloud-gpt-main `
  --setup-report "$env:USERPROFILE\Desktop\codex-hybrid-setup-report.md" `
  --canary-report "$env:USERPROFILE\Desktop\codex-hybrid-canary-evidence.md" `
  --output "$env:USERPROFILE\Desktop\codex-hybrid-real-clean-machine-canary.md"

py -3 -m codex_hybrid_switcher final-check `
  --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json" `
  --setup-report "$env:USERPROFILE\Desktop\codex-hybrid-setup-report.md" `
  --canary-report "$env:USERPROFILE\Desktop\codex-hybrid-canary-evidence.md" `
  --real-canary-template "$env:USERPROFILE\Desktop\codex-hybrid-real-clean-machine-canary.md" `
  --output "$env:USERPROFILE\Desktop\codex-hybrid-final-check.md"
```

The final report must say:

```text
Complete
```

Then submit a sanitized GitHub issue using the Real clean-machine canary issue
template. The issue should mention this was a Windows Hyper-V clean VM canary,
the checkpoint was `stock-codex-baseline`, and release `v2.12.1` was tested.

Do not upload:

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- `sessions/`
- rollout logs
- API keys
- bearer tokens
- passwords
- private endpoints
- real usernames
- private LAN IPs
- unredacted screenshots

## Failure handling

If account visibility, plugins/MCP, project list, new test chat, protected file
hashes, or final-check fails:

1. Mark the result `Needs rollback`.
2. Quit Codex Desktop.
3. Restore the newest `config.toml.bak-codex-hybrid-*`, or revert the Hyper-V
   checkpoint `stock-codex-baseline`.
4. Do not edit `state_5.sqlite`.
5. Do not edit `models_cache.json`.
6. Do not edit `auth.json`.
7. Do not edit `sessions/` or rollout logs.
8. Do not install recovery loops, scheduled tasks, KeepAlive jobs, or automatic
   restart scripts.

Record the failure in a sanitized issue only if no private state or secret is
included.
