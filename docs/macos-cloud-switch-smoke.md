# macOS Cloud Switch Smoke

Use this only after private config dry-run validation passes. This is the first
workflow that can write real Codex `config.toml`.

## Boundary

This smoke test may write:

- `~/.codex/config.toml`
- `~/.codex/config.toml.bak-codex-hybrid-*`

It must not write:

- `~/.codex/auth.json`
- `~/.codex/models_cache.json`
- `~/.codex/state_5.sqlite`
- Codex sessions
- CC Switch state

It does not test local llama.cpp or local models.

## Preflight

1. Confirm your private config is not in the repository.
2. Run install validation:

   ```sh
   python3 scripts/validate-install.py
   ```

3. Validate the private config:

   ```sh
   codex-hybrid-switcher validate-config --config ~/.codex-hybrid-model-switcher/config.json
   ```

4. Preview the rendered config. Known private fields are redacted, but still
   treat this output as private:

   ```sh
   codex-hybrid-switcher guarded-switch cloud-gpt-main --dry-run --config ~/.codex-hybrid-model-switcher/config.json
   ```

## Switch

1. Quit Codex Desktop completely.
2. Run the guarded switch:

   ```sh
   codex-hybrid-switcher guarded-switch cloud-gpt-main --config ~/.codex-hybrid-model-switcher/config.json
   ```

3. Confirm the command prints `Protected Codex files unchanged.`
4. Open Codex Desktop normally.
5. Confirm account information, plugin entry points, and project list are still visible.
6. Start a new test chat and send a minimal prompt.

## Restore

To switch back to the official provider:

```sh
codex-hybrid-switcher guarded-switch openai-official --config ~/.codex-hybrid-model-switcher/config.json
```

If anything looks wrong, quit Codex and restore the newest
`config.toml.bak-codex-hybrid-*` backup from `~/.codex`.

## Stop Conditions

Stop immediately if:

- Codex is still running and the command refuses to switch.
- Any protected file hash changes.
- Account information, plugins, or project conversations disappear.
- A local provider is selected by mistake.
