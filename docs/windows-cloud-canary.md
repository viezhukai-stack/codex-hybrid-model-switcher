# Windows Cloud Canary Smoke

Use this after private config dry-run validation passes. The first Windows
canary should use only one already-working cloud provider. Do not test local
llama.cpp or local models in this workflow.

## Boundary

This smoke test may write:

- `%USERPROFILE%\.codex\config.toml`
- `%USERPROFILE%\.codex\config.toml.bak-codex-hybrid-*`

It must not write:

- `%USERPROFILE%\.codex\auth.json`
- `%USERPROFILE%\.codex\models_cache.json`
- `%USERPROFILE%\.codex\state_5.sqlite`
- Codex sessions
- CC Switch state

It does not start the bridge, llama.cpp, or any local model.

## Preflight

1. Confirm the private config is outside the repository.
2. From the repository root, run install validation:

   ```powershell
   py scripts\validate-install.py --tmp-root $env:TEMP
   ```

3. Validate the private config:

   ```powershell
   codex-hybrid-switcher validate-config --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
   ```

4. Run the Windows canary in dry-run mode:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\windows-cloud-canary.ps1 -ProviderId cloud-gpt-main
   ```

   Dry-run mode validates the config and prints a redacted guarded diff. It
   must finish with `Dry-run complete. No files were changed.`

## Apply

1. Quit Codex Desktop completely.
2. Run the canary apply:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\windows-cloud-canary.ps1 -ProviderId cloud-gpt-main -Apply
   ```

3. Confirm the output says protected files are unchanged.
4. Open Codex Desktop normally.
5. Confirm account information, plugin entry points, and project conversations
   are still visible.
6. Start a new test chat and send a minimal prompt.

## Restore

To switch back to the official provider, quit Codex and run:

```powershell
codex-hybrid-switcher guarded-switch openai-official --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

If anything looks wrong, quit Codex and restore the newest
`config.toml.bak-codex-hybrid-*` backup from `%USERPROFILE%\.codex`.

## Stop Conditions

Stop immediately if:

- Codex is still running and the command refuses to switch.
- Any protected file hash changes.
- Account information, plugins, or project conversations disappear.
- A local provider is selected by mistake.

Only one Windows machine is required for this canary. A second Windows machine
can be used later as cross-machine regression coverage.
