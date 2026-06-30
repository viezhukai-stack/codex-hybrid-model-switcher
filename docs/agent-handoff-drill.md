# Agent handoff drill

`scripts/validate-agent-handoff-drill.py` is an end-to-end simulated drill for
the project's main promise:

> A user with stock Codex Desktop can hand this repository to Codex, and Codex
> can safely complete a guarded hybrid provider setup.

The drill does not use a real Codex profile. It creates a temporary stock-like
Codex home, runs the same commands that an agent should run, and writes a
redacted drill report inside the temporary workspace.

## What it proves

- `START_HERE.md`, `AGENTS.md`, and `FINAL_CHECK.md` contain the handoff prompt,
  stop conditions, completion rules, and final verdict language.
- `bootstrap.py` creates a private config outside the repository.
- Guarded dry-run changes no simulated Codex files.
- API-key help is available without printing a key value.
- `bridge-health` gives closed-port diagnostics without leaking the upstream
  provider hostname.
- A guarded apply changes only `config.toml` and creates a backup.
- `auth.json`, `models_cache.json`, and `state_5.sqlite` hash prefixes stay
  unchanged.
- `setup-report` and `canary-report` are generated and remain redacted.
- The final evidence path reaches a simulated `Complete` verdict.

## What it does not prove

- It does not open Codex Desktop.
- It does not prove a real provider credential is valid.
- It does not verify a real user's account, plugin, MCP, or project UI.
- It does not validate local llama.cpp models.
- It does not migrate conversation history.

Those checks are still machine-specific. The drill proves the repository's
agent handoff path is internally complete and safe to attempt.

## Run it

```sh
python3 scripts/validate-agent-handoff-drill.py
```

Keep the temporary workspace and generated drill report:

```sh
python3 scripts/validate-agent-handoff-drill.py --keep
```

Expected ending:

```text
agent handoff drill validation passed
```

## Release use

Run this before a public release together with:

```sh
python3 scripts/validate-stock-codex-handoff.py
python3 scripts/validate-release-acceptance.py
```

If this drill fails, do not claim that a stock Codex user can complete the setup
from the repository handoff path.
