# macOS Full Local Model Package

`Codex-Hybrid-macOS-Full-Local-Setup-v2.17.3.zip` is the private netdisk
package for Mac users who should be able to use a bundled local model without a
cloud API key.

## What It Includes

- The same double-click installer entries as the lightweight macOS package.
- The bundled project payload under `payload/codex-hybrid-model-switcher`.
- macOS llama.cpp runtimes for both `macos-x64` and `macos-arm64`.
- `payload/models/local-gemma` with the GGUF model, mmproj file, test image,
  `MODEL_MANIFEST.json`, and `NOTICE.txt`.

It does not include Codex Desktop, CC Switch, account files, API keys, or any
real Codex state.

## Beginner Flow

1. Install and sign in to official Codex Desktop.
2. Extract the whole zip.
3. Double-click `Install Codex Hybrid.command`.
4. Wait while the installer copies about 6 GB of local model files into
   `~/Library/Application Support/CodexHybridModelSwitcher/models/local-gemma`.
5. The installer selects the bundled `llama-server` matching the Mac
   architecture and runs local text plus image smoke.
6. If existing official project chats should remain visible after switching to
   `custom/local-gemma`, type `MIGRATE` when the installer asks about history
   unification. The installer dry-runs this first.
7. After local smoke and guarded dry-run pass, quit Codex Desktop completely,
   type `APPLY`, let the installer reopen Codex, and verify
   account, plugins, project conversations, and one new local test chat.

## Build

```bash
python3 scripts/build-macos-one-click-package.py --full-local
```

The package is written to
`dist/Codex-Hybrid-macOS-Full-Local-Setup-v2.17.3.zip`.

The build script uses the cached model directory by default:

```text
.package-cache/models/local-gemma
```

It downloads fixed llama.cpp `b9860` macOS runtimes when they are not already in
`.package-cache/llama.cpp`.

## Safety Rules

- Local smoke must pass before the installer enables `local-gemma`, unless
  `--skip-local-smoke` is used for troubleshooting.
- Real apply is refused while Codex appears to be running.
- Real apply writes only `~/.codex/config.toml` and creates a timestamped
  backup.
- The installer does not edit `auth.json`, `models_cache.json`,
  sessions, or rollout logs during normal provider switching.
- Optional history unification runs only when the user types `MIGRATE` or passes
  `--unify-history`. It backs up `state_5.sqlite` and changed session files
  before moving existing `openai` history metadata into the `custom` bucket.
- History unification helps old project chats stay visible after switching
  provider buckets. It does not guarantee old official encrypted context can be
  seamlessly continued by the local model.
- Python 3.10+ is required. The package does not bundle Python by default; if
  Python is missing, the installer opens the official Python macOS download page.

## Validation

Before sharing the package:

```bash
python3 -m compileall -q src tests scripts
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m codex_hybrid_switcher security-scan .
.venv/bin/python scripts/validate-release-acceptance.py --quick
```

Also inspect the zip and verify it contains both macOS llama.cpp runtimes, the
GGUF model, mmproj, test image, manifest, and notice, while excluding `.git`,
`.venv`, `dist`, `.package-cache`, account files, databases, and tokens.
