Codex Hybrid macOS beginner setup
=================================

1. Install and sign in to the official Codex Desktop app first.
   Official page: https://developers.openai.com/codex/app
2. Extract the entire zip. Do not run files from inside the zip preview.
3. Optional: copy provider-preset.example.json to provider-preset.json and fill
   in base_url, model, and api_key_env. Never put the API key value in the preset.
4. Double-click Install Codex Hybrid.command.
5. The installer creates a private config, validates it, runs guarded dry-run,
   and installs Codex Model Switcher.command on the Desktop.
6. A real switch only happens after dry-run passes, Codex is fully closed, and
   you type APPLY exactly.
7. Optional: type MIGRATE only if you want existing official project chats moved
   into the custom provider bucket. The installer dry-runs this first and backs
   up the history database before any real migration.

Python 3.10 or newer is required. If Python is missing, the installer opens the
official macOS Python download page and tells the user to rerun after installing
Python. Packages do not bundle Python by default.

The lightweight macOS package is cloud-only. It does not include local GGUF
models or llama.cpp.

The full local macOS package may include payload/models/local-gemma and
payload/llama.cpp. In that case, the installer can configure local-gemma without
a cloud API key.

No macOS package includes CC Switch, API keys, or Codex Desktop. Install Codex
only from the official page.

Protected Codex files are not edited during normal provider switching:
- auth.json
- models_cache.json
- sessions and rollout logs

If optional history unification is enabled, state_5.sqlite and matching session
metadata are backed up before the openai history bucket is migrated to custom.
