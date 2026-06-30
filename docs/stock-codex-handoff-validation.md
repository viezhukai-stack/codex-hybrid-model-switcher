# Stock Codex Handoff Validation

`scripts/validate-stock-codex-handoff.py` is the closest automated check to the
project's main promise:

> A user with stock Codex Desktop can hand this GitHub repository to Codex and
> let Codex complete a guarded hybrid provider setup.

The script does not use a real Codex profile. It creates a temporary clean copy
of the repository and a simulated stock Codex home.

## What It Proves

- `START_HERE.md`, `AGENTS.md`, `README.md`, and `bootstrap.py` are present in a
  clean repository copy.
- `START_HERE.md` includes the copy-paste prompt, dry-run requirement, protected
  file list, backup rule, and setup report instruction.
- `bootstrap.py` can run from the clean copy without installing the package.
- The private config is created outside the repository.
- The default `bridge` bootstrap dry-run does not mutate the clean repository
  or simulated Codex home.
- The default `bridge` path points users to `bridge-health` and confirms a
  closed bridge port plus unset `api_key_env` produces safe next steps without
  leaking the upstream provider hostname.
- A guarded apply changes only `config.toml` and creates a
  `config.toml.bak-codex-hybrid-*` backup.
- Simulated protected files, session files, and rollout logs are unchanged.
- The redacted setup report is generated and does not leak the simulated
  endpoint, private temp path, session text, database placeholder, or rollout
  content.
- The canary evidence command is available for recording live UI confirmations
  after a real user-visible test.

## What It Does Not Prove

- It does not prove a real user's provider credentials are correct.
- It does not open Codex Desktop or verify a live UI.
- It does not replace the need for a real `canary-report` after the user checks
  account, plugin/MCP, project list, and test-chat behavior in Codex Desktop.
- It does not start a real bridge service during the default bridge validation.
- It does not validate a real local llama.cpp model.
- It does not migrate old conversations between provider buckets.

Those checks remain machine-specific and should be done after the dry-run looks
safe.

## Run It

```sh
python3 scripts/validate-stock-codex-handoff.py
```

Keep the temporary workspace for inspection:

```sh
python3 scripts/validate-stock-codex-handoff.py --keep
```

Expected ending:

```text
stock Codex handoff validation passed
```
