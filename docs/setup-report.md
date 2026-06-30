# Setup report

`setup-report` creates a redacted Markdown report after setup or switching. It
is designed for users who want a shareable "what happened on this machine"
summary without exposing account state, tokens, sessions, private endpoints, or
local paths.

## Generate a report

From the repository after setup:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher setup-report \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --output ~/Desktop/codex-hybrid-setup-report.md
```

If the package is installed:

```sh
codex-hybrid-switcher setup-report \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --output ~/Desktop/codex-hybrid-setup-report.md
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
py -3 -m codex_hybrid_switcher setup-report `
  --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json" `
  --output "$env:USERPROFILE\Desktop\codex-hybrid-setup-report.md"
```

## What it includes

- current provider/model fields from `config.toml`
- configured provider ids and model ids
- redacted provider URLs
- API key environment variable names and whether they are set
- protected Codex file presence and hash prefixes
- whether `sessions/` and `rollouts/` exist
- whether MCP, plugin, project, desktop, and feature config sections are present
- newest `config.toml.bak-codex-hybrid-*` backup name
- local model path status as `configured` or `missing`

## What it does not include

- API keys
- account tokens
- full local paths
- provider hostnames
- session content
- database content
- full protected-file hashes
- contents of `auth.json`, `models_cache.json`, or `state_5.sqlite`

## How to use it

After a real guarded switch:

1. Reopen Codex Desktop.
2. Confirm account, plugins/MCP, and project list still look right.
3. Start a new test chat.
4. Generate the setup report.
5. Share the report only after reviewing it for anything private.

The report is not a substitute for the user's visual UI check, but it gives a
stable text artifact for support and release validation.
