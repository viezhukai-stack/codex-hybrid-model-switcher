# macOS Full One-Click Beginner Installer

`Codex-Hybrid-macOS-Full-Local-Setup-v2.18.6.zip` is the supported macOS
beginner distribution. It includes the local model path and can also configure
an optional OpenAI-compatible cloud provider.

The v2.18.6 shared router preserves message, reasoning, function-call, usage,
and terminal-status objects when a cloud model needs the non-streaming
Responses compatibility path. It also supports the HTTP/1.1 WebSocket upgrade
used by Codex Live voice.

Current macOS Codex builds may be installed as `ChatGPT.app`. The installer
discovers bundle id `com.openai.codex` first, then falls back to explicit
`ChatGPT.app` and legacy `Codex.app` paths.

## What It Includes

- Double-click entries: `Install Codex Hybrid.command`,
  `Start Codex Hybrid 2.0.command`, `Enable Codex Hybrid 2.0.command`,
  `Restore Codex 19030 Mode.command`, `Codex Hybrid Diagnostics.command`, and
  `Restore Official Codex.command`.
- A bundled project payload under `payload/codex-hybrid-model-switcher`.
- A sample `provider-preset.example.json` for distributors.

It does not include Codex Desktop, CC Switch, account files, or API keys.

## Beginner Flow

1. Install and sign in to official ChatGPT/Codex Desktop.
2. Extract the whole zip.
3. Optionally create `provider-preset.json` next to the installer with
   `base_url`, `model`, and `api_key_env`. Do not put the API key value in this
   file.
4. Double-click `Install Codex Hybrid.command`.
5. Paste the provider API key only when prompted. The installer writes it to
   `~/.codex-hybrid-model-switcher/env.sh` with permission `600`.
6. Optional: type `MIGRATE` if old official project chats should remain visible
   after switching into the `custom` provider bucket. The installer dry-runs this
   migration first.
7. Review the guarded dry-run.
8. Quit Codex Desktop completely, type `APPLY`, then use
   `Start Codex Hybrid 2.0.command` to open Codex and verify
   account, plugins, project conversations, and one new test chat.

## Safety Rules

- Real apply is refused while Codex appears to be running.
- Real apply writes only `~/.codex/config.toml` and creates a timestamped
  backup.
- The installer does not edit `auth.json`, `models_cache.json`,
  sessions, or rollout logs during normal provider switching.
- Optional history unification is disabled unless the user types `MIGRATE` or
  passes `--unify-history`. It backs up `state_5.sqlite` and changed session
  metadata before moving existing `openai` history rows into `custom`.
- History unification is for project conversation visibility after provider
  bucket changes; it does not guarantee old official encrypted context can be
  continued by another provider.
- Python 3.10+ is required. If Python is missing, the installer opens the
  official macOS Python download page and asks the user to rerun after install.
- In normal 2.0 mode, the bottom-right Codex model selector is the model
  switching interface. `Codex Model Switcher.command` is maintenance-only.

## Build

```bash
python scripts/build-macos-one-click-package.py --full-local
```

The package is written to
`dist/Codex-Hybrid-macOS-Full-Local-Setup-v2.18.6.zip`.

## Validation

Run these before sharing the package:

```bash
python -m compileall -q src tests scripts
pytest
python -m codex_hybrid_switcher security-scan .
python scripts/build-macos-one-click-package.py
```

For a real macOS canary, use a signed-in stock Codex Desktop app, run the
installer, apply only after dry-run passes and Codex is closed, then verify the
visible UI state and a new cloud reply.
