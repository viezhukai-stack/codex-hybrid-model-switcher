# Canary evidence report

`canary-report` records the manual Codex Desktop checks that scripts cannot
prove on their own. Use it after a guarded switch, after reopening Codex
Desktop, and after creating a new test conversation.

The command is read-only for Codex state. It reads the private project config,
reads redacted status from the configured Codex home, and writes only the output
Markdown file you choose.

## Generate a report

From the repository:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher canary-report \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --provider-id cloud-gpt-main \
  --setup-report ~/Desktop/codex-hybrid-setup-report.md \
  --account-visible yes \
  --plugins-visible yes \
  --mcp-visible yes \
  --project-list-visible yes \
  --test-chat-responded yes \
  --bridge-health-passed yes \
  --setup-report-reviewed yes \
  --verdict complete \
  --output ~/Desktop/codex-hybrid-canary-evidence.md
```

If the package is installed:

```sh
codex-hybrid-switcher canary-report \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --provider-id cloud-gpt-main \
  --account-visible yes \
  --plugins-visible yes \
  --mcp-visible yes \
  --project-list-visible yes \
  --test-chat-responded yes \
  --bridge-health-passed yes \
  --setup-report-reviewed yes \
  --verdict complete \
  --output ~/Desktop/codex-hybrid-canary-evidence.md
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
py -3 -m codex_hybrid_switcher canary-report `
  --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json" `
  --provider-id cloud-gpt-main `
  --account-visible yes `
  --plugins-visible yes `
  --mcp-visible yes `
  --project-list-visible yes `
  --test-chat-responded yes `
  --bridge-health-passed yes `
  --setup-report-reviewed yes `
  --verdict complete `
  --output "$env:USERPROFILE\Desktop\codex-hybrid-canary-evidence.md"
```

## Status values

Each visible check accepts:

- `yes`: the user saw this pass in Codex Desktop
- `no`: the user saw this fail
- `na`: not applicable for this machine or provider

If a status is omitted, the report marks it as `not recorded`.

## Verdict values

- `complete`: account, plugins, MCP, project list, setup report review, and a
  responding test chat are all confirmed
- `partial`: some setup steps passed, but visible Codex Desktop evidence is not
  complete yet
- `failed`: a required step failed and the setup should not be treated as done
- `rollback-needed`: account, plugins, project visibility, or protected files
  look wrong and the user should restore the newest `config.toml` backup

If `--verdict complete` is used while required evidence is missing or marked
`no`, the report adds a warning instead of pretending the setup is finished.

## What it includes

- manual UI evidence for account, plugins, MCP, project list, test reply, bridge
  health, and setup report review
- active provider/model fields from `config.toml`
- configured provider ids and model ids
- protected Codex file presence and hash prefixes
- preserved config section presence
- newest `config.toml.bak-codex-hybrid-*` backup name
- redacted provider and local-model details inherited from the private config

## What it does not include

The report does not include API keys or account secrets.

- API keys
- account tokens
- provider hostnames
- full local paths
- session content
- database content
- contents of `auth.json`, `models_cache.json`, or `state_5.sqlite`

## How it fits with setup-report

Use `setup-report` for the machine/config summary. Use `canary-report` for the
final user-visible evidence. For support or release validation, keep both files:

1. `codex-hybrid-setup-report.md`
2. `codex-hybrid-canary-evidence.md`
3. `codex-hybrid-real-clean-machine-canary.md` for real clean-machine
   public-readiness tests

Review these files before sharing them.
