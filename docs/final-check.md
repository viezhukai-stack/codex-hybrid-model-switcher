# Final check

`final-check` is the last read-only gate after a real guarded switch and a user
visible Codex Desktop test.

It combines:

- the private config
- the redacted `setup-report`
- the redacted `canary-report`
- the real clean-machine canary template for public-readiness claims

It does not edit Codex files. It does not open Codex Desktop. It does not read
or write `auth.json`, `models_cache.json`, `state_5.sqlite`, `sessions/`, or
rollout logs.

## When To Run It

Run it only after:

1. `guarded-switch --dry-run` was reviewed.
2. Codex Desktop was fully quit.
3. The real `guarded-switch` completed.
4. Codex Desktop reopened.
5. Account, plugins/MCP, project list, and a new test conversation were checked.
6. `setup-report`, `canary-report`, and `real-canary-template` were generated.

## macOS

From an installed package:

```sh
codex-hybrid-switcher final-check \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --setup-report ~/Desktop/codex-hybrid-setup-report.md \
  --canary-report ~/Desktop/codex-hybrid-canary-evidence.md \
  --real-canary-template ~/Desktop/codex-hybrid-real-clean-machine-canary.md \
  --output ~/Desktop/codex-hybrid-final-check.md
```

From the repository without installing:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher final-check \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --setup-report ~/Desktop/codex-hybrid-setup-report.md \
  --canary-report ~/Desktop/codex-hybrid-canary-evidence.md \
  --real-canary-template ~/Desktop/codex-hybrid-real-clean-machine-canary.md \
  --output ~/Desktop/codex-hybrid-final-check.md
```

## Windows

From an installed package:

```powershell
py -3 -m codex_hybrid_switcher final-check `
  --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json" `
  --setup-report "$env:USERPROFILE\Desktop\codex-hybrid-setup-report.md" `
  --canary-report "$env:USERPROFILE\Desktop\codex-hybrid-canary-evidence.md" `
  --real-canary-template "$env:USERPROFILE\Desktop\codex-hybrid-real-clean-machine-canary.md" `
  --output "$env:USERPROFILE\Desktop\codex-hybrid-final-check.md"
```

From the repository without installing:

```powershell
$env:PYTHONPATH = "src"
py -3 -m codex_hybrid_switcher final-check `
  --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json" `
  --setup-report "$env:USERPROFILE\Desktop\codex-hybrid-setup-report.md" `
  --canary-report "$env:USERPROFILE\Desktop\codex-hybrid-canary-evidence.md" `
  --real-canary-template "$env:USERPROFILE\Desktop\codex-hybrid-real-clean-machine-canary.md" `
  --output "$env:USERPROFILE\Desktop\codex-hybrid-final-check.md"
```

## Verdicts

- `Complete`: config validation passed, reports are present, the canary verdict
  is complete, and all required user-visible checks are recorded as passed.
- `Partially complete`: some setup evidence exists, but one or more final
  reports or user-visible checks are missing.
- `Not complete`: there is not enough evidence to prove setup progressed beyond
  early setup.
- `Needs rollback`: a user-visible Codex check failed, such as account,
  plugins/MCP, project list, or a new test conversation.

`Complete` is the only verdict that supports a public clean-machine success
claim.

## Sharing

Review the generated final check before sharing it publicly. It is designed to
use report filenames only and avoid API keys, account tokens, provider
hostnames, session content, database content, and full local paths.
