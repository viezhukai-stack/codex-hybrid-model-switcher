# Windows User Flow

Use this after both canaries pass:

- cloud provider canary
- local llama.cpp smoke

This workflow makes the external switcher the source of truth. Codex Desktop's
bottom-right model selector is not the source of truth.

## Boundary

The apply step may write:

- `%USERPROFILE%\.codex\config.toml`
- `%USERPROFILE%\.codex\config.toml.bak-codex-hybrid-*`

It must not write:

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- Codex sessions
- CC Switch state

Local provider switches may start the bridge on `127.0.0.1:19030`; the bridge
then starts llama.cpp on `127.0.0.1:19031` on demand.

Bridge runtime files are written outside the repository:

- `%USERPROFILE%\.codex-hybrid-model-switcher\bridge.pid`
- `%USERPROFILE%\.codex-hybrid-model-switcher\bridge.log`

## Dry-run

Cloud provider:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows-provider-switch.ps1 -ProviderId cloud-gpt-main
```

Local provider:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows-provider-switch.ps1 -ProviderId local-gemma -AllowLocal
```

Dry-run mode must finish with `Dry-run complete. No files were changed.`

## Apply

1. Quit Codex Desktop completely.
2. Apply the selected provider.

Cloud provider:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows-provider-switch.ps1 -ProviderId cloud-gpt-main -Apply
```

Local provider:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows-provider-switch.ps1 -ProviderId local-gemma -AllowLocal -Apply
```

3. Confirm protected files are unchanged.
4. Open Codex manually.
5. Confirm account information, plugins, and project conversations are still visible.
6. Start a new test chat.

If the local provider was applied from a remote SSH session and Codex reports
`error sending request for url (http://127.0.0.1:19030/v1/responses)`, first
check whether the bridge is still listening:

```powershell
netstat -ano | Select-String ':19030|:19031'
Get-Content "$env:USERPROFILE\.codex-hybrid-model-switcher\bridge.log" -Tail 80
```

The guarded switch starts the bridge detached on Windows, but UI validation
should still be done from the Windows desktop session.

## Local Provider Notes

The local provider apply runs local smoke first by default. This verifies:

- configured llama.cpp paths exist
- bridge can start
- text returns `OK`
- vision returns `red`
- managed smoke bridge stops before the actual provider switch writes config

Use `-SkipLocalSmoke` only after a local smoke passed recently on the same
machine and no local model paths changed.

## Restore

Quit Codex and switch back to the official provider:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows-provider-switch.ps1 -ProviderId openai-official -Apply
```

If anything looks wrong, quit Codex and restore the newest
`config.toml.bak-codex-hybrid-*` backup from `%USERPROFILE%\.codex`.

## Stop Conditions

Stop immediately if:

- Codex is still running and the command refuses to switch
- any protected file hash changes
- account information, plugins, or project conversations disappear
- local smoke fails
- the dry-run diff removes unrelated auth, plugin, MCP, project, or sandbox settings
