# Safety Rules

- Do not edit `models_cache.json`.
- Do not edit `state_5.sqlite` unless performing a deliberate, backed-up
  history repair outside this tool.
- Do not write API keys into repo files.
- Do not install LaunchAgents, KeepAlive jobs, or recovery loops.
- Quit Codex before switching providers.
- Keep local model files outside the repository.

Before publishing, run:

```sh
python -m codex_hybrid_switcher security-scan .
```

