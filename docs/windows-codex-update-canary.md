# Windows Codex Update Canary

This canary validates the v2.18.1 Browser/CLI update guard and optional account
switch on a real Windows Codex Hybrid 2.0 installation.

## Safety boundary

- Fully quit Codex/ChatGPT before any repair or account operation.
- Back up `config.toml`, `auth.json`, `models_cache.json`, `state_5.sqlite`,
  `sessions`, launchers, and the private switcher config before the app update.
- Record protected-file hashes and thread/provider counts.
- Do not edit official Browser/Chrome plugin caches, Codex databases, session
  JSONL, rollout logs, Windows proxy settings, services, or scheduled tasks.
- A Codex Store/AppX update may not have a reliable version rollback. Run all
  v2.18.1 dry-runs against the old app before updating it.

## Candidate flow

1. Run `windows-update-doctor --skip-resource-check` on the old Codex app. It
   must report `launch_safe: yes` and write nothing.
2. Run `windows-update-repair` without `--apply`; it must finish as a dry-run.
3. Run `change-account` without `--apply`; it must report the existing login,
   Hot Router entry, optional proxy state, and no interrupted transaction.
4. Update Codex through its official Windows update path while Codex is closed.
5. Before first launch, run `windows-update-doctor` again. If the CLI hash/path
   is stale, verify the repair dry-run, then run `windows-update-ensure`. It must
   accept only the supported version-only repair, copy the complete CLI
   companion set, write the versioned path to the current-user
   `CODEX_CLI_PATH` environment value, and return a healthy launch gate.
   If automatic eligibility is intentionally rejected, verify the manual
   fallback with `windows-update-repair --apply` and type `REPAIR` instead.
6. Start `Start Codex Hot Router.cmd` twice. Confirm the second restart does not
   revert the Browser plugin or CLI path.
7. Confirm account UI, projects, plugins, MCP, model catalog, one cloud model,
   local Gemma, and any machine-private second local model still work.
8. Confirm only one llama.cpp model runs at a time and the local runtime exits
   under the configured idle policy.
9. Keep the real account unchanged for the release canary. Run only the
   `change-account` dry-run on the real profile; exercise success/failure and
   interrupted recovery against an isolated temporary Codex home and fake CLI.

## Pass criteria

- Browser and Chrome bundled/cache versions are aligned after the official app
  refresh.
- The configured CLI is current, executable, and stored in the project-owned
  versioned CLI cache after repair is required. The cache contains `codex.exe`,
  `rg.exe`, sandbox setup, command runner, and code-mode host.
- A Browser smoke must read real DOM from an external test page after restart;
  `failed to start codex app-server: program not found` and blanket network
  policy rejection are release blockers.
- Account information, existing project conversations, plugins, MCP, and the
  Hybrid 2.0 model list remain visible after two restarts.
- Repair changes only its own CLI cache, the current-user `CODEX_CLI_PATH`, and
  an already-existing TOML CLI key when present. Account-switch dry-run changes
  nothing.
- No service, scheduled task, background watchdog, recovery loop, or automatic
  process termination is introduced.

## Physical canary result — 2026-07-22

- Codex AppX moved from `26.715.9079.0` / CLI `0.145.0-alpha.27` to
  `26.715.10079.0` / CLI `0.145.0-alpha.30` during the canary.
- The stale CLI path was detected before Codex opened. The complete five-file
  bundle was copied into the versioned project cache, the current-user
  environment and existing TOML key were refreshed, and protected Codex files
  stayed unchanged.
- On first launch, Browser and Chrome refreshed from `26.715.70719` to the new
  bundled marketplace version `26.715.72359`. The app-server used the new
  managed CLI path and the final launch gate reported `healthy`.
- A real external DOM page returned the expected title and first heading.
- The local task database reported `quick_check=ok`, 100 tasks in the `custom`
  provider bucket, and 47 archived tasks. `19030` and `19032` were healthy;
  the heavy `19031` local runtime was not resident while idle.

## Evidence template

```text
Package:
SHA256:
Old Codex app/CLI:
New Codex app/CLI:
Threads/provider baseline:
Update doctor before/after:
Browser/Chrome versions:
Account visible:
Projects visible:
Plugins/MCP visible:
Cloud reply:
Local Gemma reply:
Second local model reply:
Local idle exit:
Account-switch dry-run:
Protected-file comparison:
Verdict:
```
