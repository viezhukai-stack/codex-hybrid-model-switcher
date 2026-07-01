# Supervised Handoff Drill

Use this drill when you want to test whether the GitHub handoff path is clear
for a stock Codex Desktop user, without requiring Codex to fully complete a real
provider switch.

This is not the same as a real clean-machine canary. The goal is to verify that
each documented command can run or gives a clear next step. The real switch can
remain unperformed.

## What This Drill Checks

- The fixed release zip can be downloaded without Git.
- Required handoff files exist:
  - `HANDOFF_TO_CODEX.md`
  - `START_HERE.md`
  - `AGENTS.md`
  - `FINAL_CHECK.md`
- Windows can recover when Python is missing by using
  `scripts/bootstrap-windows.ps1`.
- `validate-agent-handoff-drill.py` runs once Python exists.
- `bootstrap.py` creates a private config outside the repository.
- `validate-config` runs.
- `env-help` gives safe API-key setup instructions without printing a key.
- `bridge-health` explains missing key or stopped bridge states.
- `guarded-switch --dry-run` prints a redacted, narrow diff.
- Bridge-routed cloud models can be smoke tested before a real Codex switch.

## Known Beginner Gaps This Drill Covers

Stock Windows machines may not have Python or Git. A handoff that starts with
`py -3 bootstrap.py` can fail immediately. The beginner route should therefore
use the release zip and `scripts/bootstrap-windows.ps1`.

Some VMs do not expose PowerShell Direct, SSH, WinRM, RDP, or Hyper-V Guest
Services to the supervising machine. That is an operator access limitation, not
a project failure. In that case, run the commands from the VM console and paste
only the redacted command result or generated reports back to the supervisor.

For `cloud_route=bridge`, the bridge process must be running while Codex tests
the provider. The handoff should say this plainly.

If MCP is not configured on a clean VM, record MCP as not applicable instead of
treating it as a failed setup.

## Passing Standard

The drill passes when:

- all non-destructive commands run, or print clear next steps;
- no real switch is applied unless explicitly chosen;
- `auth.json`, `models_cache.json`, `state_5.sqlite`, `sessions/`, and rollout
  logs are not edited;
- missing remote-control access is recorded separately from project command
  failures;
- remaining gaps are written down before public release claims are made.
