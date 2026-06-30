# First-run wizard

The `setup` command is the safest beginner entry point. It creates a private
machine-local config and tells the user how to run a dry-run. It does not switch
Codex Desktop by itself.

If the package is not installed yet, start with [`bootstrap.md`](bootstrap.md).
Bootstrap runs from the repository and calls this setup flow for you.

Use it for a stock Codex Desktop install when the user wants to try an
OpenAI-compatible cloud provider without editing Codex files by hand.

## What it does

- Detects a default platform-specific Codex home.
- Asks for one cloud provider endpoint and model id.
- Stores the API key reference as an environment variable name.
- Uses `bridge` cloud routing by default, so Codex talks to the local bridge
  and the bridge forwards to the real provider with the API key from the
  environment.
- Creates `~/.codex-hybrid-model-switcher/config.json`.
- Validates the generated config.
- Prints the next `guarded-switch --dry-run` command.

## What it does not do

- It does not edit `~/.codex/config.toml`.
- It does not edit `auth.json`.
- It does not edit `models_cache.json`.
- It does not edit `state_5.sqlite`.
- It does not install background services.
- It does not migrate old `openai` conversations into the `custom` bucket.
- It does not download llama.cpp or model files.

That last point matters: old official Codex conversations can appear separate
after switching to a custom provider. The wizard keeps history untouched on
purpose.

## Interactive setup

```sh
python3 -m pip install -e .
codex-hybrid-switcher setup
```

The wizard asks for:

- Codex home
- cloud provider id
- cloud provider label
- OpenAI-compatible `base_url`
- model id
- API key environment variable name
- cloud route: `bridge` or `direct`
- whether to add a local llama.cpp provider now

For most new users, answer `no` to the local llama.cpp provider during first
setup. Add local models later after the cloud flow works.

## Non-interactive setup

Use this in scripts, support instructions, or reproducible tests:

```sh
codex-hybrid-switcher setup --non-interactive \
  --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 \
  --model provider-gpt-main \
  --api-key-env OPENAI_COMPATIBLE_API_KEY
```

Windows PowerShell:

```powershell
codex-hybrid-switcher setup --non-interactive `
  --platform windows `
  --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 `
  --model provider-gpt-main `
  --api-key-env OPENAI_COMPATIBLE_API_KEY
```

The `api_key_env` value must be the name of an environment variable, not the
API key itself.

Use the default `bridge` route for normal OpenAI-compatible providers that need
their own API key. Use `direct` only when the provider is known to work with
Codex Desktop's direct custom-provider authentication path.

## Safe first switch

After setup, validate:

```sh
codex-hybrid-switcher validate-config --config ~/.codex-hybrid-model-switcher/config.json
```

Preview the Codex config change:

```sh
codex-hybrid-switcher guarded-switch cloud-gpt-main --dry-run --config ~/.codex-hybrid-model-switcher/config.json
```

Only after the dry-run looks correct:

1. Quit Codex Desktop completely.
2. For `bridge` cloud route, make sure the API key environment variable is set.
3. Run the real guarded switch.
4. Reopen Codex Desktop.
5. Create a new test conversation.

```sh
codex-hybrid-switcher guarded-switch cloud-gpt-main --config ~/.codex-hybrid-model-switcher/config.json
```

If the account, plugin entry, MCP entry, or project list looks wrong, quit
Codex Desktop and restore the newest `config.toml.bak-codex-hybrid-*` backup.

## Adding local llama.cpp later

Local models are machine-dependent. Before switching Codex to a local provider,
the user needs:

- a working `llama-server`
- a compatible GGUF model
- a matching mmproj file for multimodal models
- enough CPU/GPU/RAM/VRAM for that model

Then run:

```sh
codex-hybrid-switcher local-smoke --config ~/.codex-hybrid-model-switcher/config.json
```

Only switch after smoke passes:

```sh
codex-hybrid-switcher guarded-switch local-gemma --allow-local --config ~/.codex-hybrid-model-switcher/config.json
```
