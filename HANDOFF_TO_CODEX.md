# Hand This GitHub Project To Codex

This is the shortest path for a user who only has stock Codex Desktop.

Copy the prompt below into Codex. Replace the placeholders first. Do not paste a
raw API key.

```text
Please configure Codex Hybrid Model Switcher from this GitHub project:

https://github.com/viezhukai-stack/codex-hybrid-model-switcher

My starting point:
- I only have stock Codex Desktop.
- I want Codex Desktop to use one OpenAI-compatible cloud model first.
- Keep my Codex login state, plugins, MCP, project list, and visible
  conversations as safe as possible.
- Do not edit auth.json, models_cache.json, state_5.sqlite, sessions/, or
  rollout logs.
- Do not install LaunchAgent, KeepAlive, scheduled tasks, recovery loops, or
  background autostart services.
- Do not test local llama.cpp until cloud setup works.
- Do not paste a raw API key into Codex or repository files.

My provider details:
- base_url: <OpenAI-compatible endpoint, for example https://example.com/v1>
- model: <model id, for example provider-gpt-main>
- api_key_env: <environment variable name that stores the API key; do not ask me
  to paste the key itself>
- cloud_route: bridge

Please do this in order:
1. Open or clone the GitHub project above. On Windows, if Git or Python is not
   installed, use the fixed release zip route and `scripts/bootstrap-windows.ps1`
   instead of assuming `git` or `py -3` already exists.
2. Read HANDOFF_TO_CODEX.md, START_HERE.md, AGENTS.md, and FINAL_CHECK.md.
3. Run the simulated safety checks before touching my real Codex profile:
   python3 scripts/validate-agent-handoff-drill.py
4. Run bootstrap.py or codex-hybrid-switcher setup to create a private config
   outside the repository.
5. Run validate-config.
6. If api_key_env is unset, run env-help and tell me how to set the environment
   variable without showing the key value.
7. If cloud_route is bridge, run bridge-health and explain the result.
8. Run guarded-switch --dry-run and explain the exact planned diff in plain
   language.
9. Only after the dry-run is narrow and safe, ask me to fully quit Codex
   Desktop before the real guarded switch. In short: quit Codex Desktop before
   applying.
10. Apply the real guarded switch only after Codex Desktop is closed.
11. Verify protected file hashes after the switch.
12. Ask me to reopen Codex Desktop and create a new test conversation.
13. Generate setup-report, canary-report, and real-canary-template.
14. Run final-check to generate the read-only final verdict report.
15. Use FINAL_CHECK.md for the final Complete / Partially complete / Not
    complete / Needs rollback verdict.

Stop and ask before continuing if anything wants to edit auth.json,
models_cache.json, state_5.sqlite, sessions/, rollout logs, or anything beyond
provider/model fields in config.toml.
```

## Beginner Windows Bootstrap

On a stock Windows machine, Python and Git may both be missing. In that case,
Codex should use PowerShell to download the fixed release zip and run the
Windows bootstrap script. The script checks or installs Python 3.12 with
`winget`, creates the private config, validates it, prints safe API-key
environment help when needed, checks bridge health, and stops at
`guarded-switch --dry-run`.

It does not apply a real Codex switch.

Example after the release zip is downloaded and extracted:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1 `
  -BaseUrl https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 `
  -Model provider-gpt-main `
  -ApiKeyEnv OPENAI_COMPATIBLE_API_KEY `
  -CloudRoute bridge
```

## What The User Must Provide

- A provider `base_url`.
- A model id.
- The name of an environment variable that contains the API key.

Do not provide the API key value in the prompt.

## What Codex Should Produce

At the end of a successful real cloud canary, Codex should produce:

1. `codex-hybrid-setup-report.md`
2. `codex-hybrid-canary-evidence.md`
3. `codex-hybrid-real-clean-machine-canary.md`
4. `codex-hybrid-final-check.md`
5. A final verdict from `FINAL_CHECK.md`

If any visible Codex check fails, the verdict is not complete.
