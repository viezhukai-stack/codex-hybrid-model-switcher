# Windows User Flow

Use this after both canaries pass:

- cloud provider canary
- local llama.cpp smoke

This document covers both Windows modes:

- 2.0 hot-router mode: `Start Codex Hot Router.cmd` is the daily launcher, and
  Codex Desktop's bottom-right model selector is the source of truth.
- Maintenance mode: `Codex Model Switcher.cmd` remains available for guarded
  provider switches and older external-switcher workflows.

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

## Desktop Launcher

After cloud and local canaries pass, install the guarded launcher:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-windows-launcher.ps1
```

This creates `Start Codex Hot Router.cmd`, `Codex Model Switcher.cmd`,
`Enable Codex Hot Router Mode.cmd`, `Restore Codex 19030 Mode.cmd`,
`Repair Codex Update and Plugins.cmd`, `Repair Codex Browser and CLI.cmd`,
`Repair Codex Live Audio.cmd`,
`Change Codex Account.cmd`, and
`Restore Official Codex.cmd` on the desktop.

`Start Codex Hot Router.cmd` always:

- runs the closed-app Windows update orchestrator, completes a staged official
  Store registration when needed, refreshes the matching complete CLI bundle,
  and rebinds the current AppX Browser/Chrome marketplace
- checks or starts the lightweight bridge on `127.0.0.1:19030`
- starts or reuses the hot router on `127.0.0.1:19032`
- enables `19032` hot-router mode while Codex is closed when needed
- opens Codex Desktop after the router is healthy
- runs one bounded post-start Browser check after Codex feature initialization;
  it is a no-op when Browser is healthy and uses the official Codex CLI only
  when Browser is available but missing or stale
- keeps the router in the foreground window instead of installing a service

`Codex Model Switcher.cmd` runs `scripts\windows-provider-menu.ps1`, not the raw
Python `menu` command.

The launcher always:

- lists providers from the private config
- runs a guarded dry-run first
- requires typing `APPLY` exactly before writing
- delegates the real switch to `scripts\windows-provider-switch.ps1`
- requires `-AllowLocal` internally for local providers

The maintenance switcher does not open Codex automatically. The hot-router
launcher does open Codex automatically after health checks pass.

After a Codex app update, the next daily launch normally waits for three stable
Store observations, completes registration, performs a second bounded
stability check for newly staged builds, refreshes the matching CLI and
Browser/Chrome bundle, and then opens Codex. A healthy installation skips the
full wait. Run
`Repair Codex Update and Plugins.cmd` when the full transaction needs an
explicit retry; `Repair Codex Browser and CLI.cmd` is the CLI-only fallback. To
change the ChatGPT account,
use `Change Codex Account.cmd`; it uses device-code login, keeps a local
transaction backup, and does not move project conversations between provider
buckets.

The Browser/CLI repair copies the complete current AppX CLI bundle into a
versioned project-owned directory and stores that path in the current-user
`CODEX_CLI_PATH` environment value. This survives the Windows app regenerating
its Browser configuration during startup. It does not create a service,
scheduled task, watchdog, or restart loop.

The current AppX marketplace and both official Browser/Chrome plugins are
refreshed while Codex is closed. Browser feature-gate verification remains a
separate post-start step.
`windows-browser-post-start.ps1` waits for the running app to finish loading its
feature gates, then invokes `windows-browser-ensure`. The command checks the
official plugin catalog and, only when needed, runs the current official CLI's
`plugin add browser@openai-bundled --json`. It writes a single diagnostic log at
`%LOCALAPPDATA%\CodexHybridModelSwitcher\logs\browser-post-start.log`, exits
after the bounded check, and never closes or reopens Codex.

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

## Gemini High Notes

Codex may show `Gemini 3.1 Pro (High)` in the bottom-right selector while the
request body uses the internal model id `gemini-pro-agent`. Do not remove the
menu item just because the id does not match a `gemini-*-preview` name.

Some upstreams return malformed streaming Responses events for
`gemini-pro-agent`: the stream may contain only `response.created` and
`response.in_progress`, then close without `output_text`,
`response.completed`, or `[DONE]`. The hot router has a built-in shim for this
model. It sends the upstream request as non-streaming and wraps the final text
back into a Codex-compatible SSE stream.

The shim is local to the hot router. It does not edit Codex history, account
files, model cache, or CC Switch state. Router logs mark successful protected
requests with `gemini_stream_shim=true`.

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
