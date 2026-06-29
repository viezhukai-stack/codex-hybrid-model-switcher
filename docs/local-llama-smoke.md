# Local llama.cpp Smoke

Use this after cloud-provider canary verification. This workflow validates the
local bridge and llama.cpp multimodal model without switching Codex Desktop to a
local provider.

## Boundary

This smoke test may start:

- the bridge on `127.0.0.1:19030`
- the configured `llama-server` on `127.0.0.1:19031`

It must not write:

- Codex `config.toml`
- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- Codex sessions
- CC Switch state

The managed bridge is stopped at the end unless `--keep-bridge` is explicitly
used. The bridge also stops its llama.cpp child process when it exits.

## Preflight

1. Confirm the private config is outside the repository.
2. Confirm local paths are configured:

   ```sh
   codex-hybrid-switcher validate-config --check-paths --config ~/.codex-hybrid-model-switcher/config.json
   ```

   Windows PowerShell:

   ```powershell
   codex-hybrid-switcher validate-config --check-paths --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
   ```

3. Confirm no unrelated service is already using the bridge port:

   ```sh
   codex-hybrid-switcher doctor --config ~/.codex-hybrid-model-switcher/config.json
   ```

## Run

macOS from the repository root:

```sh
scripts/local-smoke-macos.sh --config ~/.codex-hybrid-model-switcher/config.json
```

Windows PowerShell from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\local-smoke-windows.ps1 --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

The default smoke test sends:

- a text prompt that should answer `OK`
- a 32x32 red PNG image prompt that should answer `red`

To test text only:

```sh
codex-hybrid-switcher local-smoke --skip-vision --config ~/.codex-hybrid-model-switcher/config.json
```

To reuse an already-running bridge deliberately:

```sh
codex-hybrid-switcher local-smoke --use-existing-bridge --config ~/.codex-hybrid-model-switcher/config.json
```

## Stop Conditions

Stop immediately if:

- required local files are missing
- the bridge port is already in use and you did not intend to reuse it
- llama.cpp fails to become healthy
- the text smoke does not return `OK`
- the vision smoke does not identify the red test image

Do not switch Codex Desktop to the local provider until this smoke test passes.
After it passes, use `guarded-switch <local-provider-id> --allow-local` or the
Windows workflow in `docs/windows-user-flow.md`.
