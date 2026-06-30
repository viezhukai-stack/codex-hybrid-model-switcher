# API key environment variables

Cloud providers usually need an API key. This project stores only the
environment variable name in the private config, not the key itself.

For example:

```json
"api_key_env": "OPENAI_COMPATIBLE_API_KEY"
```

That means the real key must live in the user's shell or operating-system
environment under the name `OPENAI_COMPATIBLE_API_KEY`.

## Get safe setup instructions

After creating the private config, run:

```sh
codex-hybrid-switcher env-help --config ~/.codex-hybrid-model-switcher/config.json
```

If running from the repository without installing:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher env-help --config ~/.codex-hybrid-model-switcher/config.json
```

The command prints macOS or Windows commands for setting the variable. It does not read, print, or store API keys.

## Why this step matters

For `route=bridge`, Codex Desktop points at the local bridge on
`127.0.0.1:19030`. The bridge forwards requests to the real provider and adds
the API key from the configured environment variable.

If the variable is unset, a real guarded switch stops before writing Codex
config.

## What not to do

- Do not paste raw API keys into this repository.
- Do not commit private config files.
- Do not put keys into `START_HERE.md`, `AGENTS.md`, issue templates, setup
  reports, or screenshots.
- Do not edit `auth.json`, `models_cache.json`, `state_5.sqlite`, or sessions
  to solve provider authentication.
