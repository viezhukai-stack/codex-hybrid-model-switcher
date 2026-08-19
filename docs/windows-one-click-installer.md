# Windows Netdisk One-Click Installer

Use this path for a beginner Windows computer that may not have Codex Desktop,
Python, Git, llama.cpp, or local model files yet.

The recommended installer package is:

```text
Codex-Hybrid-Windows-Netdisk-Setup-v2.18.6.zip
```

For private netdisk sharing with a bundled local model, build and share:

```text
Codex-Hybrid-Windows-Full-Local-Setup-v2.18.6.zip
```

It contains:

- `Install Codex Hybrid.cmd`
- `Start Codex Hot Router.cmd`
- `Codex Hybrid Diagnostics.cmd`
- `Repair Codex Update and Plugins.cmd`
- `Repair Codex Browser and CLI.cmd`
- `Repair Codex Live Audio.cmd`
- `Change Codex Account.cmd`
- `Restore Official Codex.cmd`
- `Install-CodexHybrid.ps1`
- `README.txt`
- `README.zh-CN.txt`
- `provider-preset.example.json`
- `payload/codex-hybrid-model-switcher/`
- `payload/python/`

The full local package also contains:

- `payload/llama.cpp/`
- `payload/vcredist/vc_redist.x64.exe`
- `payload/models/local-gemma/`
- `payload/models/local-gemma/MODEL_MANIFEST.json`

## What It Does

- Checks that it is running on Windows.
- Checks whether Codex Desktop appears installed and signed in.
- Recognizes both current `ChatGPT.exe` and legacy Codex process names before
  any guarded apply, and resolves the installed `OpenAI.Codex` AppID instead of
  depending only on one hard-coded package family.
- Opens the official Codex app page when Codex is missing or not signed in:
  `https://developers.openai.com/codex/app`
- Uses bundled portable Python from `payload/python` and installs it under
  `%LOCALAPPDATA%\CodexHybridModelSwitcher\python` for later desktop switcher
  runs.
- Before every packaged maintenance or daily entry imports the switcher, it
  atomically repairs portable Python's `python312._pth` so the only managed
  project path points to the current release `src` directory.
- Installs Python 3.12 with `winget` only if bundled portable Python and system
  Python are both missing.
- Uses the bundled project payload from
  `payload/codex-hybrid-model-switcher`; Git is not required.
- Falls back to downloading the fixed project release zip from GitHub only when
  the bundled payload is missing.
- Creates the private config at
  `%USERPROFILE%\.codex-hybrid-model-switcher\config.json`.
- Prefills provider settings from `provider-preset.json` when that file exists
  next to the installer.
- Stores the provider API key only in a Windows User environment variable when
  a cloud provider is configured.
- Automatically uses bundled local GGUF and mmproj files from
  `payload/models/local-gemma` when present, after copying them into
  `%LOCALAPPDATA%\CodexHybridModelSwitcher\models\local-gemma`.
- Shows free disk space at startup and recommends at least 15-20 GB free space
  for full local setup.
- Writes local-only diagnostics showing whether llama.cpp, the installed local
  model, and the local provider are present.
- Lets the user choose local GGUF and mmproj files when the package does not
  include a local model payload.
- Uses bundled llama.cpp when `payload/llama.cpp` contains `llama-server.exe`;
  otherwise downloads official llama.cpp Windows release assets from
  `https://github.com/ggml-org/llama.cpp/releases`.
- Checks whether `llama-server.exe --version` can run before local smoke. If
  Microsoft Visual C++ Runtime DLLs are missing and
  `payload/vcredist/vc_redist.x64.exe` exists, the installer runs the bundled
  redistributable and checks `llama-server.exe` again.
- Runs `validate-config`, `bridge-health`, optional `local-smoke`, and a guarded
  provider dry-run.
- Gives local model smoke requests up to 900 seconds in the Windows installer,
  because CPU-only VMs can need several minutes for the first local response.
- Can optionally unify Codex history from the `openai` bucket into `custom`
  after creating `state_5.sqlite.bak-codex-hybrid-*` and matching
  `sessions/*.jsonl.bak-codex-hybrid-*` backups, so existing project chats
  remain visible after switching.
- Installs the desktop `Start Codex Hot Router.cmd` launcher. This is the
  recommended daily Windows 2.0 entry: it checks/starts the lightweight bridge
  on `127.0.0.1:19030`, starts or reuses the hot router on `127.0.0.1:19032`,
  enables hot-router mode while Codex is closed when needed, then opens Codex
  Desktop.
- Preserves complete Responses output when Gemini High uses its non-streaming
  compatibility path, including reasoning summaries and function calls, and
  performs only bounded `Retry-After`-aware 429 retries.
- Installs the desktop `Codex Model Switcher.cmd` launcher for guarded
  maintenance switches and legacy mode.
- Installs the desktop `Enable Codex Hot Router Mode.cmd` and
  `Restore Codex 19030 Mode.cmd` helpers for the custom provider `base_url`
  toggle.
- Installs the desktop `Restore Official Codex.cmd` launcher.
- Writes a redacted diagnostics report when `Codex Hybrid Diagnostics.cmd` is
  double-clicked.
- Checks the active Codex AppX CLI and Browser/Chrome plugin versions before
  the daily hot-router launch. `windows-update-orchestrate` runs while Codex is
  closed, waits for three identical Store observations, completes a pending
  Microsoft Store registration through official `winget` product
  `9PLM9XGG6VKS`, performs a bounded post-registration stability pass for a
  newly staged build, and then invokes the guarded CLI refresh and
  copies/hash-checks `codex.exe`, `rg.exe`,
  `codex-windows-sandbox-setup.exe`, `codex-command-runner.exe`, and
  `codex-code-mode-host.exe` when needed.
- The same transaction removes and re-adds only the current AppX
  `openai-bundled` marketplace and installs both `browser@openai-bundled` and
  `chrome@openai-bundled` through the official CLI. It leaves old cache
  directories untouched, verifies provider
  routing and protected-file hashes, and only then lets the daily entry open
  Codex.
- Compares the current-user AppX registration with all-user staged Codex
  packages. If `highest_staged_version` is newer, the doctor sets
  `pending_registration`; the orchestrator completes registration while Codex
  remains closed, allows at most two registration passes, and leaves Codex
  closed if Store versions keep changing. A healthy installation takes the
  fast path. `Repair Codex Update and Plugins.cmd` is the explicit manual
  fallback for the same transaction.
- Disables PowerShell progress rendering around `Invoke-WebRequest`, avoiding
  the console `Write-Progress` failure while preserving normal download errors.
- Stops on any update condition outside that narrow automatic repair and points
  to `Repair Codex Browser and CLI.cmd`; it never creates a service, scheduled
  task, watchdog, restart loop, or background updater.
- After opening Codex, starts one hidden, bounded post-start check. It waits for
  Codex feature initialization, verifies the official Browser plugin state, and
  runs `windows-browser-ensure`, which calls
  `plugin add browser@openai-bundled --json` through the current official CLI
  only when Browser is available but missing or stale. It never restarts Codex
  and exits after writing a small local diagnostic log.
- The narrower `windows-update-ensure` and `Repair Codex Browser and CLI.cmd`
  paths remain available when only the versioned CLI bundle needs repair.
- Installs `Change Codex Account.cmd` for an explicit, backup-first device-code
  login. Account switching is separate from normal model routing and remains a
  dry-run until the user types `SWITCH`.
- Installs `Repair Codex Live Audio.cmd`. Its first pass is read-only and reports
  packaged-app microphone consent, the Console/Multimedia/Communications capture
  defaults, and eligible recording endpoints. It requires Codex to be fully
  closed plus exact `REPAIR` confirmation before writing, preserves existing
  defaults, and stores a timestamped rollback record accepted through
  `RESTORE`.
- Proxies Codex Live's HTTP/1.1 WebSocket upgrade through the same Hot Router.
  The Router records only route, status, and byte counts, not audio frames or
  prompt contents.

## What It Does Not Do

- It does not redistribute Codex Desktop.
- The base package does not include local model files.
- The full local package may include local model files for private netdisk
  distribution. Those files are not committed to GitHub.
- It does not require CC Switch. The package includes this project's own
  guarded external switcher.
- It does not require Git or a GitHub project download when the netdisk payload
  is intact.
- It does not write API keys into the repository or private config.
- It does not edit `auth.json`, `models_cache.json`, or rollout logs.
- It does not automatically change microphone consent or the Windows default
  recording device during installation or daily launch.
- The optional account-switch entry invokes the official Codex logout/login
  commands after a local backup; normal install, repair, and routing commands
  still do not edit `auth.json`.
- It does not edit `state_5.sqlite` unless the user explicitly enables backed-up
  history unification.
- It does not edit `sessions/*.jsonl` unless the user explicitly enables
  backed-up history unification.
- It does not apply a real Codex switch by default.
- It does not install LaunchAgents, KeepAlive jobs, scheduled tasks, or recovery
  loops.
- It does not hard-code machine-specific local model ids. The package default is
  the generic `local/gemma`; private machines can override that in their private
  config.

## Beginner Flow

1. Download `Codex-Hybrid-Windows-Netdisk-Setup-v2.18.6.zip` from the netdisk
   link.
2. Extract the zip.
3. Double-click `Install Codex Hybrid.cmd`.
4. If Codex is missing, install Codex from the official page, sign in, fully
   close Codex, then run the installer again.
5. If `provider-preset.json` exists, provider fields are prefilled.
6. If this is the full local package and no cloud `base_url` is provided, the
   installer continues in local-only mode without an API key.
7. If you want cloud model support, enter the OpenAI-compatible provider
   `base_url`, cloud model id, environment variable name, and API key when
   prompted.
8. Choose local GGUF and mmproj files only when the package does not already
   include `payload/models/local-gemma`.
9. Choose whether to enable history unification. Enable it if you want existing
   official project chats to remain visible after switching to the custom
   provider bucket.
10. Review the dry-run output.
11. Only after dry-run looks correct and Codex Desktop is fully closed, type
   `APPLY` when prompted if you want to perform the real guarded provider
   switch.
12. For Windows 2.0 hot-router mode, quit Codex and use
   `Start Codex Hot Router.cmd`. It automatically refreshes the guarded Browser
   CLI bundle after a supported Codex update, enables `19032` mode when needed,
   then opens Codex. Use Codex's bottom-right model selector for normal model
   switching.
13. Use the desktop `Codex Model Switcher.cmd` only for guarded maintenance
   switches or the older external-switcher mode.
14. Use the desktop `Restore Official Codex.cmd` if you need to return to the
    official provider.

## Command-Line Examples

Dry-run only, using prompts:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-CodexHybrid.ps1
```

Non-interactive cloud dry-run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-CodexHybrid.ps1 `
  -NonInteractive `
  -SkipCodexCheck `
  -BaseUrl https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 `
  -Model provider-gpt-main `
  -ApiKeyEnv OPENAI_COMPATIBLE_API_KEY `
  -SkipLocal
```

Local model paths:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-CodexHybrid.ps1 `
  -BaseUrl https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 `
  -Model provider-gpt-main `
  -ApiKeyEnv OPENAI_COMPATIBLE_API_KEY `
  -ModelPath D:\Models\model.gguf `
  -MmprojPath D:\Models\mmproj.gguf
```

Local-only dry-run with bundled or selected local model files:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-CodexHybrid.ps1 `
  -SkipCloud
```

Real apply is explicit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-CodexHybrid.ps1 `
  -BaseUrl https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 `
  -Model provider-gpt-main `
  -ApiKeyEnv OPENAI_COMPATIBLE_API_KEY `
  -SkipLocal `
  -Apply
```

Codex Desktop must be fully closed before real apply.

Real apply while keeping existing project chats visible:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-CodexHybrid.ps1 `
  -BaseUrl https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 `
  -Model provider-gpt-main `
  -ApiKeyEnv OPENAI_COMPATIBLE_API_KEY `
  -SkipLocal `
  -UnifyHistory `
  -Apply
```

This backs up `state_5.sqlite` and matching `sessions/*.jsonl` files before
migrating `openai` thread rows and session metadata to `custom` and the active
model.

## Build The Release Zip

From the repository root:

```powershell
py scripts\build-windows-one-click-package.py
```

The default output is the netdisk-ready package:

```text
dist\Codex-Hybrid-Windows-Netdisk-Setup-v2.18.6.zip
```

Upload that zip to your netdisk.

If you intentionally want the old script-only package that downloads the project
source from GitHub, run:

```powershell
py scripts\build-windows-one-click-package.py --thin
```

If you want to bundle a prepared llama.cpp runtime, run:

```powershell
py scripts\build-windows-one-click-package.py --include-llama-dir D:\Tools\llama.cpp
```

If you want to build the private full local model package for netdisk sharing,
prepare a Windows llama.cpp runtime directory and a local model directory with
one GGUF model and one mmproj GGUF file, then run:

```powershell
py scripts\build-windows-one-click-package.py `
  --output dist\Codex-Hybrid-Windows-Full-Local-Setup-v2.18.6.zip `
  --include-llama-dir D:\Tools\llama.cpp `
  --include-vcredist-file D:\Installers\vc_redist.x64.exe `
  --include-model-dir D:\Models\gemma-4-e4b
```

The model payload is written under `payload/models/local-gemma` and includes a
generated `MODEL_MANIFEST.json` with file sizes, SHA256 hashes, source URL, and
license.

The default build bundles official Windows embeddable Python 3.12.10. To build
the smaller package without portable Python, run:

```powershell
py scripts\build-windows-one-click-package.py --no-python
```

If you want to bundle a prepared portable Python directory instead, run:

```powershell
py scripts\build-windows-one-click-package.py --include-python-dir D:\Tools\python-portable
```

To prefill provider settings for a private netdisk package, copy
`provider-preset.example.json` to `provider-preset.json` next to
`Install-CodexHybrid.ps1` before zipping. Do not put the API key value in that
file.
