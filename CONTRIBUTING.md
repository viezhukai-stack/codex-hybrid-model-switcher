# Contributing

Contributions should preserve the project's main safety goal: switch Codex
providers without damaging account state, plugins, MCP configuration, or project
conversation visibility.

## Development Setup

```sh
python -m pip install -e ".[dev]"
python -m compileall -q src tests scripts/validate-install.py
pytest
python -m codex_hybrid_switcher security-scan .
```

Use `python scripts/validate-install.py` before release-oriented changes.

## Contribution Rules

- Do not commit real Codex state:
  - `auth.json`
  - `models_cache.json`
  - `state_5.sqlite`
  - `sessions/`
- Do not commit provider credentials, API keys, bearer tokens, refresh tokens,
  passwords, or private endpoints.
- Do not commit local model files, llama.cpp binaries, generated archives,
  backups, quarantine folders, runtime logs, or pid files.
- Do not add LaunchAgents, KeepAlive jobs, recovery loops, or scheduled
  auto-restart tasks.
- Do not introduce behavior that writes while Codex Desktop is running.
- Do not bypass guarded dry-run and protected-file hash checks for real
  provider switches.

## Pull Request Checklist

Before opening a PR:

- run unit tests
- run security scan
- update docs for user-facing behavior
- keep examples generic and placeholder-based
- mention whether the change touches real switching behavior, local bridge
  behavior, or docs only

For release-candidate PRs, also run:

```sh
python scripts/validate-install.py
```

## Local Testing Guidance

Use temporary Codex homes for development. Real Codex profiles should only be
used in documented canary flows, after dry-run output has been reviewed.

Local llama.cpp testing is optional per machine. A local smoke failure on weak
or incompatible hardware is not automatically a project bug.
