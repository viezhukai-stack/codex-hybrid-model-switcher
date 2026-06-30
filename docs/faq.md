# FAQ and Troubleshooting

This project changes Codex provider configuration. Treat real Codex profiles as
important local state and prefer dry-runs before applying changes.

## Why must Codex Desktop be closed before switching?

Codex Desktop reads configuration while it is running and may keep local state
open. Switching while it is open can create confusing UI state or partially
loaded provider settings. Guarded switch flows are designed to stop before
writing when Codex appears to be running.

## Why does the bottom-right model selector show a different model?

This project treats the external switcher and rendered `config.toml` as the
source of truth. Codex Desktop may show a stale, generic, or cached label in its
own model selector. Check the active provider config instead of relying only on
that label.

## Project conversations disappeared after switching. Are they deleted?

Usually no. Conversation visibility can depend on provider buckets or desktop
state. First quit Codex Desktop and switch back to the previous provider or
restore the latest `config.toml.bak-codex-hybrid-*` backup.

Do not edit `state_5.sqlite`, session files, or caches as a first response.
Those files can contain important account and conversation state.

## What should I do if account info or plugins disappear?

Stop testing and restore the latest `config.toml.bak-codex-hybrid-*` backup.
This project is designed not to edit `auth.json`, `models_cache.json`, or
`state_5.sqlite`, so those files should remain unchanged during guarded flows.

## Why did local llama.cpp smoke fail?

Local model support depends on hardware, drivers, model size, quantization,
llama.cpp build, and mmproj compatibility. A local smoke failure on one machine
does not necessarily mean the project is broken.

Common causes include:

- the model is too large for the GPU or memory available
- CUDA or GPU drivers are missing or incompatible
- `llama-server` is too old or built for the wrong platform
- the model path or mmproj path is wrong
- the model does not support the multimodal input being tested

## Can this project download models or llama.cpp for me?

No. Users should install llama.cpp and download model files separately. The
repository contains configuration and bridge tooling only, not model binaries or
runtime archives.

## How do I safely recover after a failed switch?

1. Quit Codex Desktop.
2. Find the newest `config.toml.bak-codex-hybrid-*` file in your Codex home.
3. Restore it as `config.toml`.
4. Start Codex Desktop normally.
5. Re-run `security-scan` and `guarded-switch --dry-run` before trying again.

Avoid automated recovery loops. Manual recovery is slower, but it is easier to
audit and less likely to damage working account state.

## What files should never be uploaded in issues?

Do not upload:

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- `sessions/`
- provider API keys, bearer tokens, passwords, or private config files
- local model files, llama.cpp archives, runtime logs, backups, or quarantine
  folders

Use redacted snippets instead.
