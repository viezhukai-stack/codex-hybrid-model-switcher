# Windows Codex Update Canary

This canary validates the v2.18.6 Windows AppX registration, Browser/CLI update
guard, and optional account switch on a real Windows Codex Hybrid 2.0
installation.

## Safety boundary

- Fully quit Codex/ChatGPT before CLI-bundle repair or account operations. The
  bounded Browser plugin check is the only repair phase that intentionally runs
  after Codex starts and finishes feature initialization.
- Back up `config.toml`, `auth.json`, `models_cache.json`, `state_5.sqlite`,
  `sessions`, launchers, and the private switcher config before the app update.
- Record protected-file hashes and thread/provider counts.
- Do not edit official Browser/Chrome plugin caches, Codex databases, session
  JSONL, rollout logs, Windows proxy settings, services, or scheduled tasks.
- A Codex Store/AppX update may not have a reliable version rollback. Run all
  v2.18.6 dry-runs against the old app before updating it.

## Candidate flow

1. Run `windows-update-doctor --skip-resource-check` on the old Codex app. It
   must report `launch_safe: yes` and write nothing.
2. Run `windows-update-repair` without `--apply`; it must finish as a dry-run.
   The narrower `windows-update-ensure` path remains available for a
   version-only CLI refresh, and the manual fallback is
   `windows-update-repair --apply` with the exact `REPAIR` confirmation.
3. Run `change-account` without `--apply`; it must report the existing login,
   Hot Router entry, optional proxy state, and no interrupted transaction.
4. Update Codex through its official Windows update path while Codex is closed.
5. Before first launch, run `windows-update-doctor` again. If
   `pending_registration=true`, run `windows-update-orchestrate` dry-run, then
   apply it while Codex is closed. The apply path uses the Microsoft Store
   product `9PLM9XGG6VKS` through official `winget`, requires three identical
   current/staged-version observations before registration, waits for the
   post-registration view to settle, and allows at most two registration
   passes. It then refreshes the complete CLI companion set and rebinds
   `CODEX_CLI_PATH` only when needed.
6. The same orchestrator refreshes the current AppX bundled marketplace with
   the official CLI and installs both `browser@openai-bundled` and
   `chrome@openai-bundled`; it must not copy or delete old plugin cache
   directories.
7. Start `Start Codex Hot Router.cmd`. Confirm its one-shot post-start helper
   invokes `windows-browser-ensure`, waits for Codex feature initialization,
   reports Browser healthy or installs it through the official CLI, then exits
   without restarting Codex.
8. Restart Codex twice through the same daily entry. Confirm neither restart
   reverts the Browser plugin or CLI path.
9. Confirm account UI, projects, plugins, MCP, model catalog, one cloud model,
   local Gemma, and any machine-private second local model still work.
10. Confirm only one llama.cpp model runs at a time and the local runtime exits
   under the configured idle policy.
11. Keep the real account unchanged for the release canary. Run only the
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
- Portable Python's `python312._pth` points to the current release `src`, and a
  simulated old release path is replaced atomically before the switcher starts.
- The post-start Browser helper is bounded, deduplicated, and exits after one
  check. It does not close or reopen Codex.

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
- The effective Browser recovery sequence was verified after the desktop had
  completed feature initialization: the official CLI installed
  `browser@openai-bundled`, Browser and Chrome both reported installed/enabled/
  `AVAILABLE`, and both remained present after two controlled restarts. This
  sequence is the bounded post-start phase added in v2.18.2.

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

## v2.18.3 guarded canary — 2026-07-26

- Windows canary A was already registered to Codex `26.721.4979.0`.
  The v2.18.3 candidate doctor reported `healthy`, `launch_safe=true`, no newer
  staged package, a complete configured CLI bundle, and matching Browser
  bundled/cache version `26.721.41059`.
- Windows canary B was still registered to `26.715.10079.0` while
  `26.721.4979.0` existed for SYSTEM in `Staged` state. The candidate reported
  `highest_staged_version=26.721.4979.0`, `pending_registration=true`, and
  `launch_safe=false`, proving the daily gate stops before reopening the older
  app during registration.
- Both machines passed an isolated portable-Python test: a fake
  `python312._pth` containing a v2.18.2 release path was atomically rewritten to
  the v2.18.3 candidate `src`, the old path disappeared, and `import site` was
  enabled. The real portable runtime file was not used for this canary.
- Canary B protected hashes stayed unchanged. Canary A was actively using Codex, so the
  SQLite file was intermittently locked during the first aggregate comparison;
  a follow-up three-second check confirmed `config.toml`, `auth.json`, and
  `models_cache.json` unchanged while `state_5.sqlite` remained locked by the
  running app.
- The candidate used temporary source and fake-runtime directories only. It did
  not switch providers, restart Codex, register AppX, edit plugin caches, or
  install a service/scheduled task. All temporary canary files were removed.
