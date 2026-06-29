# Second Windows Canary

Use this workflow after one Windows machine has already passed:

- cloud provider guarded switch
- local llama.cpp text and vision smoke
- Codex Desktop UI validation

The second canary proves that the repository workflow can be repeated on
another Windows machine without depending on machine-local residue from the
first canary.

## Boundary

Start with read-only inspection. Do not assume the second machine is clean.

The apply step may write only:

- `%USERPROFILE%\.codex\config.toml`
- `%USERPROFILE%\.codex\config.toml.bak-codex-hybrid-*`
- `%USERPROFILE%\.codex-hybrid-model-switcher\bridge.pid`
- `%USERPROFILE%\.codex-hybrid-model-switcher\bridge.log`

It must not write:

- `%USERPROFILE%\.codex\auth.json`
- `%USERPROFILE%\.codex\models_cache.json`
- `%USERPROFILE%\.codex\state_5.sqlite`
- Codex sessions
- CC Switch state

Do not copy API keys, account files, or private config files from another
machine. Create a new private config on the target machine, then fill in its own
paths and provider settings.

## Phase 1: Read-only Inventory

Run these checks before changing anything:

```powershell
whoami
Get-ComputerInfo | Select-Object CsName, WindowsProductName, WindowsVersion
Test-Path "$env:USERPROFILE\.codex\config.toml"
Test-Path "$env:USERPROFILE\.codex\auth.json"
Test-Path "$env:USERPROFILE\.codex\models_cache.json"
Test-Path "$env:USERPROFILE\.codex\state_5.sqlite"
Get-Command py -ErrorAction SilentlyContinue
Get-Command python -ErrorAction SilentlyContinue
```

If Codex is currently unusable, capture the current state first. Do not delete
the existing `.codex` directory and do not move session history.

## Phase 2: Install and Private Config

Clone or copy the repository to a normal working directory outside `.codex`.
Then initialize a private config:

```powershell
cd path\to\codex-hybrid-model-switcher
py -m pip install -e .[dev]
py -m codex_hybrid_switcher init-config --platform windows --output "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

Edit the generated private config on the target machine:

- cloud provider `base_url`
- cloud provider `model`
- cloud provider `api_key_env`
- local `llama_server_path`
- local `model_path`
- local `mmproj_path`

Validate it:

```powershell
py -m codex_hybrid_switcher validate-config --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

## Phase 3: Cloud Canary

Dry-run first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-provider-switch.ps1 -ProviderId cloud-gpt-main
```

Stop if the redacted diff removes unrelated `notify`, `sandbox_mode`, auth,
plugin, MCP, project, or desktop settings.

Apply only after Codex Desktop is fully closed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-provider-switch.ps1 -ProviderId cloud-gpt-main -Apply
```

Open Codex Desktop manually and confirm:

- account information is visible
- plugins/MCP entry points are visible
- project conversations are visible
- a new test chat gets a cloud-model reply

## Phase 4: Local Canary

Run local smoke first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\local-smoke-windows.ps1 --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

Only after text and vision smoke pass, dry-run the local provider:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-provider-switch.ps1 -ProviderId local-gemma -AllowLocal
```

Apply only after Codex Desktop is fully closed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-provider-switch.ps1 -ProviderId local-gemma -AllowLocal -Apply
```

Open Codex Desktop manually and test a new text prompt and one image prompt.

## Phase 5: End-user Launcher

After both cloud and local canaries pass, install the guarded launcher:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-windows-launcher.ps1
```

The desktop `Codex Model Switcher.cmd` launcher runs:

1. provider selection
2. guarded dry-run
3. explicit `APPLY` confirmation
4. guarded apply through `windows-provider-switch.ps1`

It does not use the unsafe Python `menu` command.

## Stop Conditions

Stop immediately if:

- Codex is running when an apply is attempted
- any protected file hash changes
- project conversations disappear
- account information disappears
- plugin/MCP entries disappear
- local smoke fails
- the bridge is not listening on `127.0.0.1:19030` after a local apply

If anything looks wrong, quit Codex and restore the newest
`config.toml.bak-codex-hybrid-*` backup from `%USERPROFILE%\.codex`.
