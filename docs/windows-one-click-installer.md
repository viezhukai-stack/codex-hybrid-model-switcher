# Windows One-Click Installer

Use this path for a beginner Windows computer that may not have Codex Desktop,
Python, Git, llama.cpp, or local model files yet.

The installer package is:

```text
Codex-Hybrid-Windows-Setup-v2.13.0.zip
```

It contains:

- `Install Codex Hybrid.cmd`
- `Install-CodexHybrid.ps1`
- `README.txt`

## What It Does

- Checks that it is running on Windows.
- Checks whether Codex Desktop appears installed and signed in.
- Opens the official Codex app page when Codex is missing or not signed in:
  `https://developers.openai.com/codex/app`
- Installs Python 3.12 with `winget` if Python is missing.
- Downloads the fixed project release zip from GitHub; Git is not required.
- Creates the private config at
  `%USERPROFILE%\.codex-hybrid-model-switcher\config.json`.
- Stores the provider API key only in a Windows User environment variable.
- Lets the user choose local GGUF and mmproj files.
- Downloads official llama.cpp Windows release assets from
  `https://github.com/ggml-org/llama.cpp/releases`.
- Runs `validate-config`, `bridge-health`, optional `local-smoke`, and a guarded
  cloud dry-run.
- Installs the desktop `Codex Model Switcher.cmd` launcher.

## What It Does Not Do

- It does not redistribute Codex Desktop.
- It does not include local model files.
- It does not write API keys into the repository or private config.
- It does not edit `auth.json`, `models_cache.json`, `state_5.sqlite`,
  `sessions/`, or rollout logs.
- It does not apply a real Codex switch by default.
- It does not install LaunchAgents, KeepAlive jobs, scheduled tasks, or recovery
  loops.

## Beginner Flow

1. Download `Codex-Hybrid-Windows-Setup-v2.13.0.zip` from the GitHub Release.
2. Extract the zip.
3. Double-click `Install Codex Hybrid.cmd`.
4. If Codex is missing, install Codex from the official page, sign in, fully
   close Codex, then run the installer again.
5. Enter the OpenAI-compatible provider `base_url`, cloud model id, environment
   variable name, and API key when prompted.
6. Choose local GGUF and mmproj files if you want local model support.
7. Review the dry-run output.
8. Only after dry-run looks correct, fully quit Codex Desktop and rerun with
   `-Apply` if you want to perform the real guarded cloud switch.

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

## Build The Release Zip

From the repository root:

```powershell
py scripts\build-windows-one-click-package.py
```

The output is:

```text
dist\Codex-Hybrid-Windows-Setup-v2.13.0.zip
```

Upload that zip as a GitHub Release asset.
