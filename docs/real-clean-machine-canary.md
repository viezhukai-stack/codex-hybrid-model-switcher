# Real clean machine canary

Use this workflow when a tester starts with stock Codex Desktop, gives this
repository to Codex, and asks Codex to complete the guarded hybrid setup.

This is the strongest evidence before a public release because it tests the
actual user handoff, not only the simulated repository path.

For the preferred final Windows proof, use
[`docs/windows-hyperv-clean-vm-canary.md`](windows-hyperv-clean-vm-canary.md).
That workflow starts from a Windows 11 Hyper-V VM checkpoint named
`stock-codex-baseline`, uses fixed release `v2.11.0`, configures one
`cloud_route=bridge` provider, and keeps local llama.cpp out of the canary.

## Safety boundary

- Do not copy another machine's `.codex` directory.
- Do not paste API keys into chat, docs, issue comments, or reports.
- Do not attach `auth.json`, `models_cache.json`, `state_5.sqlite`,
  `sessions/`, or rollout logs.
- Do not test local llama.cpp in the same first canary unless cloud setup has
  already passed.
- Do not mark the canary complete until a new test conversation responds.
- For the Hyper-V final proof, do not use floating `main`; use release
  `v2.11.0` and record the checkpoint `stock-codex-baseline`.

## Suggested test order

1. Start from a machine with stock Codex Desktop.
2. Clone or download this repository.
3. Give Codex the repository and ask it to follow `START_HERE.md`.
4. Let Codex run the simulated checks first:

   ```sh
   python3 scripts/validate-agent-handoff-drill.py
   ```

5. Let Codex create the private config and run `guarded-switch --dry-run`.
6. Review the dry-run. It should only change provider/model fields in
   `config.toml`.
7. Quit Codex Desktop completely before the real guarded switch.
8. Apply the real guarded switch.
9. Reopen Codex Desktop and check account, plugins, MCP, project list, and a new
   test conversation.
10. Generate `setup-report`, `canary-report`, this real-machine template, and
    `final-check`.
11. Use `FINAL_CHECK.md` to review the final verdict.

## Generate the template

After `setup-report` and `canary-report` exist, run:

```sh
codex-hybrid-switcher real-canary-template \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --provider-id cloud-gpt-main \
  --setup-report ~/Desktop/codex-hybrid-setup-report.md \
  --canary-report ~/Desktop/codex-hybrid-canary-evidence.md \
  --output ~/Desktop/codex-hybrid-real-clean-machine-canary.md
```

Without an installed package, run from the repository:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher real-canary-template \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --provider-id cloud-gpt-main \
  --setup-report ~/Desktop/codex-hybrid-setup-report.md \
  --canary-report ~/Desktop/codex-hybrid-canary-evidence.md \
  --output ~/Desktop/codex-hybrid-real-clean-machine-canary.md
```

On Windows, use PowerShell paths:

```powershell
py -3 -m codex_hybrid_switcher real-canary-template `
  --config "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json" `
  --provider-id cloud-gpt-main `
  --setup-report "$env:USERPROFILE\Desktop\codex-hybrid-setup-report.md" `
  --canary-report "$env:USERPROFILE\Desktop\codex-hybrid-canary-evidence.md" `
  --output "$env:USERPROFILE\Desktop\codex-hybrid-real-clean-machine-canary.md"
```

Then generate the final read-only verdict report:

```sh
codex-hybrid-switcher final-check \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --setup-report ~/Desktop/codex-hybrid-setup-report.md \
  --canary-report ~/Desktop/codex-hybrid-canary-evidence.md \
  --real-canary-template ~/Desktop/codex-hybrid-real-clean-machine-canary.md \
  --output ~/Desktop/codex-hybrid-final-check.md
```

## What complete means

A real clean-machine canary is complete only when:

- the user started from stock Codex Desktop
- Codex followed `START_HERE.md` and `AGENTS.md`
- dry-run was reviewed before a real switch
- Codex Desktop was fully quit before the real switch
- only `config.toml` changed
- `auth.json`, `models_cache.json`, and `state_5.sqlite` hashes stayed unchanged
- account information is visible
- plugin and MCP entry points are visible, or MCP is not used on that machine
- project list is visible
- A new test conversation responds through the selected provider
- redacted `setup-report`, `canary-report`, real canary template, and
  `final-check` report exist
- `final-check` returns `Complete`
- `FINAL_CHECK.md` returns `Complete`

If any item is missing, record `partial`, `failed`, or `rollback-needed` instead
of stretching the result.
