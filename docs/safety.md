# Safety Rules

- Do not edit `models_cache.json`.
- Do not edit `state_5.sqlite` unless performing a deliberate, backed-up
  history repair outside this tool.
- Do not write API keys into repo files.
- Do not install LaunchAgents, KeepAlive jobs, or recovery loops.
- Quit Codex before switching providers.
- Keep local model files outside the repository.
- Keep bridge runtime files outside the repository. The Windows local provider
  may create `%USERPROFILE%\.codex-hybrid-model-switcher\bridge.pid` and
  `bridge.log`.
- Bridge-routed cloud providers may start the same local bridge, but this is a
  manual runtime process, not a LaunchAgent, KeepAlive job, scheduled task, or
  recovery loop.
- Use one canary machine for the first real cloud-provider switch before
  repeating the workflow elsewhere.
- Require explicit `--allow-local` before switching Codex Desktop to a local
  provider.
- Treat local model validation as optional per machine. A failed or skipped
  local smoke on one machine is not a release blocker if another canary already
  validated the local bridge and llama.cpp path.

Before publishing, run:

```sh
python -m codex_hybrid_switcher security-scan .
```
