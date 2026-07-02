# Windows Netdisk One-Click Installer

Use this path for a beginner Windows computer that may not have Codex Desktop,
Python, Git, llama.cpp, or local model files yet.

The recommended installer package is:

```text
Codex-Hybrid-Windows-Netdisk-Setup-v2.15.1.zip
```

For private netdisk sharing with a bundled local model, build and share:

```text
Codex-Hybrid-Windows-Full-Local-Setup-v2.15.1.zip
```

It contains:

- `Install Codex Hybrid.cmd`
- `Codex Hybrid Diagnostics.cmd`
- `Restore Official Codex.cmd`
- `Install-CodexHybrid.ps1`
- `README.txt`
- `README.zh-CN.txt`
- `provider-preset.example.json`
- `payload/codex-hybrid-model-switcher/`
- `payload/python/`

The full local package also contains:

- `payload/llama.cpp/`
- `payload/models/local-gemma/`
- `payload/models/local-gemma/MODEL_MANIFEST.json`

## What It Does

- Checks that it is running on Windows.
- Checks whether Codex Desktop appears installed and signed in.
- Opens the official Codex app page when Codex is missing or not signed in:
  `https://developers.openai.com/codex/app`
- Uses bundled portable Python from `payload/python` and installs it under
  `%LOCALAPPDATA%\CodexHybridModelSwitcher\python` for later desktop switcher
  runs.
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
- Runs `validate-config`, `bridge-health`, optional `local-smoke`, and a guarded
  provider dry-run.
- Can optionally unify Codex history from the `openai` bucket into `custom`
  after creating `state_5.sqlite.bak-codex-hybrid-*` and matching
  `sessions/*.jsonl.bak-codex-hybrid-*` backups, so existing project chats
  remain visible after switching.
- Installs the desktop `Codex Model Switcher.cmd` launcher.
- Installs the desktop `Restore Official Codex.cmd` launcher.
- Writes a redacted diagnostics report when `Codex Hybrid Diagnostics.cmd` is
  double-clicked.

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
- It does not edit `state_5.sqlite` unless the user explicitly enables backed-up
  history unification.
- It does not edit `sessions/*.jsonl` unless the user explicitly enables
  backed-up history unification.
- It does not apply a real Codex switch by default.
- It does not install LaunchAgents, KeepAlive jobs, scheduled tasks, or recovery
  loops.

## Beginner Flow

1. Download `Codex-Hybrid-Windows-Netdisk-Setup-v2.15.1.zip` from the netdisk
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
12. Use the desktop `Codex Model Switcher.cmd` for later model switches.
13. Use the desktop `Restore Official Codex.cmd` if you need to return to the
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
dist\Codex-Hybrid-Windows-Netdisk-Setup-v2.15.1.zip
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
  --output dist\Codex-Hybrid-Windows-Full-Local-Setup-v2.15.1.zip `
  --include-llama-dir D:\Tools\llama.cpp `
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
