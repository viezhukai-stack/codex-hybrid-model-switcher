# Changelog

All notable changes to this project are summarized here. This project follows a
conservative release process because it edits Codex provider configuration.

## Unreleased

## v2.18.7

- Added an offline-safe current-user AppX registration fallback for Windows.
  The updater still tries the official Microsoft Store product through
  `winget` first; when that command fails and the matching official
  `OpenAI.Codex` package is already staged locally, it registers that package's
  `AppxManifest.xml` and then resumes the existing CLI and Browser/Chrome
  alignment transaction.
- Replaced the installed daily desktop shortcut's fixed release path with a
  stable launcher under `%LOCALAPPDATA%\CodexHybridModelSwitcher\launcher`.
  It reads `current-project.txt`, discovers newer valid installed releases when
  necessary, atomically refreshes the pointer, and then invokes the selected
  release. No service, scheduled task, watchdog, or background updater is
  installed.
- Added the private `hot_router.ignore_system_proxy` option. When enabled, only
  the Hot Router process bypasses stale Windows system-proxy entries; Windows
  proxy, DNS, TUN, account, and Codex settings are not rewritten.
- Added focused tests for Store failure fallback, official staged-package
  selection, local manifest registration, stable release discovery, proxy
  isolation, package contents, and protected-state boundaries.

## v2.18.6

- Added a bounded Windows Store stability gate to the daily Hot Router launch.
  When a Codex AppX update is pending, the launcher now requires three
  consecutive identical current/staged-version observations before registering
  it.
- Added a post-registration stability pass and support for up to two bounded
  registration passes. If Microsoft Store stages another build during the
  transaction, the matching CLI and official Browser/Chrome marketplace are
  realigned before Codex is opened; if the queue still changes, Codex stays
  closed instead of reopening an older build.
- Kept the no-update path fast: a healthy installation does not wait through
  the full Store settling window and now exits before creating a transaction
  backup or copying CLI/plugin files. The stability wait is used for a pending
  update and after each registration.
- Forced official `winget` output decoding to UTF-8 with replacement for
  malformed bytes. This removes the GBK reader-thread exception observed by
  the Kevin physical canary while preserving the real command exit status.
- Added focused tests for version settling, a second staged build, the bounded
  failure path, the no-pending fast path, and protected-state invariants.
- No service, scheduled task, KeepAlive job, background updater, automatic
  process termination, account change, database edit, or plugin-cache delete
  was added.

## v2.18.5

- Added a closed-app Windows update orchestrator for the daily Hot Router
  entry. It detects a staged Microsoft Store Codex AppX, completes the
  current-user registration through the official `winget` Store product, then
  rechecks the registered AppX before continuing.
- Added current-AppX bundled marketplace refresh. The official Codex CLI now
  removes and re-adds only `openai-bundled`, then installs Browser and Chrome
  from the matching AppX source instead of reusing an older `.tmp` marketplace
  snapshot. Old plugin cache directories are left untouched.
- Added transaction backups and invariant checks for `config.toml`,
  `auth.json`, `models_cache.json`, `state_5.sqlite`, and SQLite sidecars.
  Provider routing, user MCP entries, projects, account state, and protected
  files are verified before Codex is opened; no account login or database
  repair is performed by the update path.
- Added `Repair Codex Update and Plugins.cmd` as an explicit manual fallback
  while retaining the narrower CLI-only repair entry. No service, scheduled
  task, KeepAlive job, watchdog, or automatic restart loop was added.
- Fixed the Windows maintenance wrappers so Python output is streamed to the
  user without becoming part of the PowerShell function return value. Update,
  repair, and account-switch launchers now preserve the actual child-process
  exit code instead of risking a false success result.
- The Windows launch gate now also normalizes a hash-matching CLI that still
  lives in an older managed version directory. `CODEX_CLI_PATH` is moved to the
  directory for the currently registered AppX version, preventing stale folder
  names from being mistaken for the active CLI after later upgrades.

## v2.18.4

- Added HTTP/1.1 WebSocket upgrade tunneling for Codex Live voice sessions.
  The Hot Router now preserves Realtime WebSocket negotiation headers, applies
  the configured cloud-provider credential, and relays the upgraded connection
  bidirectionally without recording audio, prompts, or frame contents.
- Added strict curated Hot Router catalogs. A non-empty `visible_model_ids`
  allowlist now applies to cloud and local entries, optional display-name
  overrides keep selector labels clear, and multi-model local bridges can
  provide per-model catalog metadata through `local_catalog_models` while the
  singular `local_model` runtime configuration remains backward compatible.
  Explicitly allowlisted entries are normalized to `visibility = "list"` so
  upstream hidden flags cannot silently remove intended selector entries.
- Added the explicit Windows `Repair Codex Live Audio.cmd` maintenance entry.
  It diagnoses packaged-app microphone consent and default capture roles without
  writing, requires exact `REPAIR` or `RESTORE` confirmation while Codex is
  closed, treats a surviving Codex `app-server` or unsettled protected-file hash
  as still running, stores a timestamped rollback record, and never kills Codex
  or installs a service, scheduled task, watchdog, or restart loop.

## v2.18.3

- Replaced the Gemini `gemini-pro-agent` text-only non-streaming shim with a
  complete Responses JSON-to-SSE conversion. Message content, reasoning
  summaries, function calls, Chat Completions `tool_calls`, terminal status,
  and usage now survive the compatibility path instead of collapsing into an
  empty fixed-size stream when the upstream answer is tool-oriented. The same
  shim retries an HTTP 200 terminal response with empty `output` at most twice;
  a live Gemini function-call canary required one such retry and then preserved
  the complete tool call.
- Added bounded HTTP 429 retries to the hot router. The router follows
  `Retry-After`, caps both retry count and wait duration, and records only
  retry/status/byte-count metadata; prompts, response text, API keys, and
  tokens remain outside router logs.
- Added an AppX registration launch gate on Windows. The update doctor now
  compares the current-user Codex version with `Get-AppxPackage -AllUsers`
  staged packages, reports `highest_staged_version` and
  `pending_registration`, and prevents the daily launcher from reopening an
  older app while a newer package is waiting to finish registration.
- Disabled PowerShell download progress rendering in the Windows installer,
  bootstrap, and daily Hot Router watcher to avoid the `Write-Progress`
  console failure seen with `Invoke-WebRequest` on some hosts.
- Added a reusable portable-Python path self-heal. Windows entry points now
  atomically replace stale release `src` paths in `python312._pth` before
  loading the switcher, so a new package cannot silently run an older router
  module merely because the portable runtime survived an upgrade.
- Kept the Hybrid 2.0 safety boundary unchanged: no service, scheduled task,
  KeepAlive job, recovery loop, automatic Codex restart, or normal-path write
  to `auth.json`, `models_cache.json`, `state_5.sqlite`, sessions, rollout
  logs, plugins/MCP, or project conversations.

## v2.18.2

- Split Windows Codex update handling into two bounded phases. The existing
  pre-start phase still repairs only a hash-matched CLI bundle while Codex is
  closed; the new post-start phase waits for Codex feature initialization and
  then checks the official plugin catalog.
- Added `windows-browser-ensure` and a one-shot
  `windows-browser-post-start.ps1` helper. When Browser is already installed,
  enabled, available, and version-aligned, it performs no write. When Browser
  is available but missing or stale, it invokes the current official Codex CLI
  with `plugin add browser@openai-bundled --json` and verifies the final state.
- Updated `Start Codex Hot Router.cmd` to launch the bounded Browser check after
  opening Codex. The check uses a short-lived lock and one local diagnostic log;
  it does not close or restart Codex and does not create a service, scheduled
  task, watchdog, KeepAlive job, or recovery loop.
- Preserved the existing Hybrid 2.0 safety boundary: normal update and Browser
  repair code does not edit `auth.json`, `models_cache.json`, `state_5.sqlite`,
  sessions, rollout logs, provider routing, plugins/MCP other than the explicit
  Browser install, or project conversations.
- Revalidated the fix on the HL physical Windows canary after the Codex
  `26.715.10079.0` update. Browser and Chrome remained installed and enabled
  across two controlled restarts, `19030` and `19032` stayed healthy, all 100
  tasks remained in the `custom` bucket, and the task database returned
  `quick_check=ok`.

## v2.18.1

- Added a Windows Codex update doctor that checks the current AppX version,
  Browser/Chrome bundled and cached versions, the configured
  `CODEX_CLI_PATH`, stale staging paths, and recent low-memory events without
  reading conversation content or changing Codex state.
- Added a guarded Windows CLI repair. It copies the current bundled Codex CLI
  plus `rg.exe`, sandbox setup, command runner, and code-mode host into a
  versioned project-owned cache and validates the complete bundle. It persists
  `CODEX_CLI_PATH` in the current-user environment because the upgraded Windows
  app can regenerate the Browser config block during startup; an existing TOML
  key is updated in place but a missing key is not forced into `config.toml`.
- Fixed the upgraded Windows Browser failure that presented every external URL
  as blocked. The underlying error was `failed to start codex app-server:
  program not found` after the app removed the old CLI path. Browser and Chrome
  versions are now also detected from the official bundled marketplace layout
  instead of only the legacy plugin cache.
- Added an optional Windows device-code account switch with dry-run by default,
  local backup and transaction recovery, optional private proxy configuration,
  and checks that projects, plugins/MCP, model cache, database, and sessions do
  not change during the switch. It also accepts the repaired current-user
  `CODEX_CLI_PATH`.
- Added `Repair Codex Browser and CLI.cmd` and `Change Codex Account.cmd` to the
  Windows desktop and netdisk package. The normal Hot Router launcher now
  detects a supported AppX CLI version change while Codex is closed, performs
  the same guarded hash-verified repair automatically, reruns the launch gate,
  and then opens Codex. Unsupported failures still stop and point to the manual
  repair entry.
- Expanded redacted Windows diagnostics with Codex app, CLI, plugin-version,
  staging, and low-memory fields. No service, scheduled task, auto-restart loop,
  or automatic process termination was added.
- Validated the update path on a physical Windows Hybrid 2.0 canary across two
  consecutive Codex AppX versions. The complete CLI bundle refreshed to the
  new version, Browser/Chrome matched the new bundled marketplace, an external
  DOM page loaded, all 100 local tasks remained in the `custom` provider bucket,
  and the heavy local runtime stayed stopped while idle.

## v2.18.0

- Added macOS compatibility for the upgraded ChatGPT desktop app that now hosts
  Codex. macOS launchers, guarded switch checks, installer detection, and
  diagnostics now recognize both `ChatGPT.app` and legacy `Codex.app`.
- Aligned the current macOS 2.0 hot-router catalog behavior with Windows 2.0:
  cloud models now come from the live provider catalog by default, so new models
  such as `gpt-5.6-sol` are not blocked by a stale static visible allowlist.
- Made the repository hot router the shared macOS and Windows 2.0 runtime. The
  live cloud catalog is dynamic by default, while model aliases, hidden models,
  and an optional default cloud provider are private-config settings.
- Added verified CA discovery for HTTPS cloud providers, preferring `certifi`
  and common system/OpenSSL CA bundles without disabling certificate checks.
- Added a local-only hot-router catalog so the full local package can expose
  `local/gemma` on `127.0.0.1:19032` without a cloud API key.
- Added the macOS `Start Codex Hybrid 2.0.command`, enable, and `19030` restore
  launchers. The legacy model switcher remains a maintenance entry.
- Added bundle-id-first macOS app discovery, dynamic Windows AppID discovery,
  and explicit `ChatGPT.exe` running-process protection.
- Added backup-first official configuration baselines. When no baseline exists,
  official restore no longer pins an old model and lets Codex choose its current
  recommended model.
- Added optional native Codex diagnostics through `doctor --native-codex` and
  unified package versions through generated `VERSION.txt` files. Native
  diagnostics now report inaccessible WindowsApps CLI binaries or locked state
  files as warnings instead of terminating with a traceback.
- Fixed macOS running-app detection under `set -o pipefail` by avoiding
  `ps | grep -q` pipelines, so guarded apply and canary launchers do not
  mistakenly treat a running ChatGPT/Codex app as closed.
- Rebuilt the private full-local netdisk packages after the compatibility fixes:
  macOS SHA256
  `1636f56cf27b1008967d34f4f10f84ee76fcd61a69c46c990676cca7cfa49334`
  and Windows SHA256
  `cb057af4cd7adae07ddaa54b2dd35b333d63620aa1cb97de2765bfeca3f5e9a8`.
- Recorded the controlled macOS v2.18.0 UI canary after the upgraded
  ChatGPT/Codex app restart: account, plugins, project conversations, model
  list, `gpt-5.6-sol`, and the configured local model were confirmed working.
  `auth.json` and `state_5.sqlite` stayed unchanged; the upgraded app refreshed
  `models_cache.json` during launch.

## v2.17.5

- Added a hot-router stream shim for `gemini-pro-agent` / `Gemini 3.1 Pro
  (High)` so malformed upstream streams that stop after
  `response.created` / `response.in_progress` can be retried upstream as
  non-streaming and returned to Codex as a complete Responses SSE stream.
- Added structured llama.cpp local-model tuning keys for low-VRAM multimodal
  machines, including `gpu_layers`, `batch_size`, `ubatch_size`,
  `threads_batch`, `flash_attn`, `op_offload`, `mmproj_offload`, `fit`,
  `cache_ram`, and `ctx_checkpoints`, while keeping `extra_args` available for
  advanced flags.
- Added a Windows 2.0 hot-router runtime and desktop launcher so the normal
  Windows flow can keep Codex pointed at `127.0.0.1:19032` and use Codex's
  bottom-right model selector while routing local models through the lightweight
  bridge on `127.0.0.1:19030`.
- Added `ensure-bridge` and hot-router mode helpers. The helper starts only the
  lightweight bridge; llama.cpp on `19031` still starts on local-model demand and
  exits by the existing idle policy.
- Made private JSON config loading UTF-8 BOM tolerant for Windows PowerShell
  generated files.
- Kept packaged local model defaults generic as `local-gemma` / `local/gemma`;
  machine-specific private model ids are not hard-coded into GitHub defaults.

## v2.17.4

- Cleaned the netdisk package payload so beginner full-local zips no longer
  include repository development files such as `.github`, `docs`, `tests`, or
  `scripts/validate-*`.
- Updated the current private netdisk package line to Windows and macOS
  `v2.17.4` full-local artifacts and refreshed beginner distribution notes.
- This release does not change the local model runtime path; it is a packaging
  and distribution cleanup on top of the already-canary-tested full-local flow.

## v2.17.3

- Fixed macOS full-local canaries when a previous Codex Hybrid bridge is already
  listening on `127.0.0.1:19030`. The installer now stops only managed
  `codex_hybrid_switcher bridge` processes before local smoke, and refuses to do
  so while Codex Desktop is still running.
- Recorded the 2026-07-04 real Mac UI canary for the full-local package:
  account, plugin entry, project conversations, and a responding test chat were
  confirmed after package use and main-profile restore.

## v2.17.2

- Updated the macOS installer to automatically open Codex Desktop after a
  successful guarded `APPLY`, reducing beginner confusion after provider switch.

## v2.17.1

- Added optional macOS installer history unification so users can dry-run and,
  after explicit `MIGRATE` plus guarded `APPLY`, back up and migrate existing
  `openai` history metadata into the `custom` bucket for project conversation
  visibility.
- Improved macOS Python handling with clearer Python 3.10+ beginner guidance,
  official macOS download fallback, diagnostics fields, and optional
  `payload/python` packaging support for a future tested portable runtime.
- Updated macOS one-click and full-local documentation to distinguish normal
  config-only switching from explicit, backup-first history unification.

## v2.17.0

- Added a macOS full-local private netdisk package path that bundles Gemma 4
  E4B GGUF, mmproj, test image, generated model manifest, source notice, and
  both macOS x64 and arm64 llama.cpp runtimes.
- Extended the macOS installer to detect bundled local payloads, copy the model
  to user app support, select the matching `llama-server` by Mac architecture,
  run local text and vision smoke, and configure `local-gemma` without requiring
  a cloud API key.
- Added full-local package documentation and package-builder options while
  keeping the real Codex switch guarded by dry-run, Codex-quit, and explicit
  `APPLY`.

## v2.16.0

- Added a lightweight macOS netdisk one-click package path with double-click
  install, diagnostics, and restore entries.
- Added macOS installer support for bundled project payloads, provider presets,
  private `env.sh` API-key storage with permission `600`, guarded dry-run, and
  Desktop switcher launcher installation.
- Added `scripts/build-macos-one-click-package.py` and macOS beginner
  documentation. The macOS package is cloud-only; local GGUF/llama.cpp bundling
  remains a later package line.

## v2.15.5

- Added a Windows managed bridge start fallback for restricted job/remoting
  environments: if `CREATE_BREAKAWAY_FROM_JOB` returns access denied, the
  switcher retries without that flag, then retries once more without detached
  flags.

## v2.15.4

- Fixed Windows PowerShell 5 handling for the bundled `llama-server.exe
  --version` runtime check by running it through `Start-Process` with temporary
  stdout/stderr files and using only the process exit code.
- This prevents normal llama.cpp version text written to stderr from aborting
  the full-local installer before local smoke.

## v2.15.3

- Added optional bundled Microsoft Visual C++ Redistributable support for the
  Windows full-local package so clean machines can run bundled llama.cpp CPU
  builds before local smoke.
- Added a Windows installer llama-server runtime check before local smoke. If
  the runtime fails because VC++ Runtime DLLs are missing, the installer tries
  the bundled redistributable and reruns the check.
- Fixed local-only failure handling so a failed local smoke reports the local
  failure directly instead of attempting an invalid cloudless/providerless
  config rewrite.
- Added package-builder support for `payload/vcredist/vc_redist.x64.exe`.

## v2.15.2

- Increased the Windows full-local installer smoke-test request timeout to 900
  seconds so low-performance Hyper-V VMs and CPU-only machines are not rejected
  while the local model is still loading or generating.
- Added a conservative Windows installer cleanup for previous managed Codex
  Hybrid bridge processes on port `19030`, preventing stale cloud bridges from
  blocking full-local setup retries.

## v2.15.1

- Added Windows installer disk-space reporting for full local packages, with a
  15-20 GB free-space recommendation before copying bundled model files.
- Added clearer local model copy progress messaging and expanded diagnostics
  for installed llama.cpp, installed local model files, local provider status,
  local-only config status, and install-drive free space.
- Added Chinese netdisk distribution materials for the full local model package,
  including beginner installation notes and a SHA256 checksum companion file.

## v2.15.0

- Added a private netdisk full local package path that can bundle
  `payload/models/local-gemma` with a GGUF model, mmproj file, test image,
  generated `MODEL_MANIFEST.json`, and license/source notice.
- Added local-only first-run setup so a beginner Windows package can configure
  and switch to `local-gemma` without requiring a cloud base URL or API key.
- Updated the Windows installer to auto-detect bundled local model files, run
  local smoke before enabling the local provider, and run guarded provider
  dry-run/apply against either cloud or local providers.

## v2.14.8

- Fixed Windows beginner history unification to migrate matching
  `sessions/*.jsonl` metadata alongside `state_5.sqlite`, preventing Codex
  Desktop from rebuilding migrated project chats back into the old provider or
  model bucket on next launch.
- Confirmed on the HL Hyper-V clean VM canary that account visibility, plugin
  visibility, temporary chats, project chats, and a cloud test reply all remain
  working after the backed-up history unification.

## v2.14.7

- Extended backed-up history unification so Windows beginner installs can move
  existing official Codex project chats to both the custom provider bucket and
  the active custom model, avoiding empty project folders after switching.

## v2.14.6

- Fixed Windows installer command-output handling so switcher command text is displayed without polluting function return codes.


## v2.14.5

- Fixed portable Python path cleanup so reinstalling a newer netdisk package removes older `CodexHybridModelSwitcher\\releases\\...\\project\\src` entries before adding the current payload.


## v2.14.4

- Added an explicit, backed-up history unification step for Windows installer
  users who want existing official Codex project chats to remain visible after
  switching to the custom provider bucket.
- Added CLI commands to inspect history provider buckets, dry-run/apply
  `openai` to `custom` thread migration, and restore a backed-up history
  database.

## v2.14.3

- Fixed Windows PowerShell function output pollution during Python version
  checks so `Python 3.12.x` text is not treated as an executable path.

## v2.14.2

- Fixed Windows PowerShell 5 strict-mode handling when installer helper
  functions return a single Python command item.
- Kept the beginner netdisk installer ASCII-only so stock Windows consoles can
  parse it without requiring UTF-8 profile changes.

## v2.14.1

- Removed non-ASCII text from the Windows installer PowerShell script so stock
  Windows PowerShell 5 can parse the script when the netdisk zip is extracted
  without UTF-8 BOM preservation.

## v2.14.0

- Changed the Windows netdisk package builder to include official portable
  Python by default, with checksum verification, so beginner users do not need
  Git, GitHub downloads, or a separate Python install for the normal path.
- The installer now copies bundled portable Python into a stable local app data
  directory and configures it so the later desktop switcher can run without
  system Python.
- Added `Restore Official Codex.cmd` and a desktop restore launcher for guarded
  return to the official OpenAI provider.
- Updated beginner documentation to clarify that the package does not install
  CC Switch; it includes this project's own guarded external switcher.

## v2.13.2

- Added `Codex Hybrid Diagnostics.cmd`, a double-click diagnostic entry that
  writes a redacted installer diagnostics text file to the Desktop.
- Added optional `provider-preset.json` support so netdisk distributors can
  prefill provider id, label, base URL, model id, and API-key environment
  variable name without embedding the API key value.
- Added optional portable Python bundling through `payload/python` and
  `scripts/build-windows-one-click-package.py --include-python-dir`.
- Added an interactive post-dry-run `APPLY` prompt, so beginner users do not
  need to learn command-line flags for the first real guarded switch.

## v2.13.1

- Changed the Windows beginner package into a netdisk-friendly bundle:
  `Codex-Hybrid-Windows-Netdisk-Setup-v2.13.1.zip`.
- The package now includes a bundled project payload under
  `payload/codex-hybrid-model-switcher`, so recipients do not need Git and do
  not need to download the project source from GitHub during setup.
- The installer still falls back to GitHub release download when the bundled
  payload is missing.
- Added optional bundled llama.cpp runtime support under `payload/llama.cpp`;
  when absent, the installer keeps the existing official-download behavior.

## v2.13.0

- Added a Windows one-click beginner setup package source under
  `installer/windows`, with `Install Codex Hybrid.cmd` and
  `Install-CodexHybrid.ps1`.
- The installer checks for Codex Desktop, opens the official Codex app page when
  Codex is missing or not signed in, installs Python 3.12 with `winget` when
  needed, downloads a fixed project release zip, and stops at guarded dry-run by
  default.
- Added optional local setup support: users select their own GGUF and mmproj
  files, while the installer downloads official llama.cpp release assets and
  only keeps the local provider when local smoke succeeds.
- Added `scripts/build-windows-one-click-package.py` to build
  `Codex-Hybrid-Windows-Setup-v2.13.0.zip` for GitHub Releases.

## v2.12.2

- Added `scripts/bootstrap-windows.ps1`, a beginner Windows bootstrap that can
  download the fixed release zip, check or install Python 3.12 with winget,
  create a private config, run validation, show API-key environment help, run
  bridge-health, and stop at guarded dry-run without applying a real switch.
- Updated the stock-Codex handoff docs to treat the release zip and Windows
  bootstrap path as the default beginner route when Git or Python are missing.
- Recorded the supervised handoff drill findings from a clean Hyper-V VM.

## v2.12.1

- Allowed clean-machine canary evidence to mark MCP entry points as `not applicable`
  without downgrading `final-check` from `Complete`, matching the documented
  Hyper-V VM path where MCP may be unused.

## v2.12.0

- Added `docs/windows-hyperv-clean-vm-canary.md`, a dedicated final
  public-readiness workflow for testing from a clean Windows 11 Hyper-V VM with
  stock Codex Desktop only.
- The Hyper-V canary requires checkpoint `stock-codex-baseline`, fixed release
  `v2.12.0`, one cloud provider with `cloud_route=bridge`, guarded dry-run
  before apply, and `codex-hybrid-final-check.md` verdict `Complete`.
- Fixed bridge routing for stock Codex model selections such as `gpt-5.5` when
  exactly one bridge cloud provider is configured, and stopped cloud-only bridge
  catalogs from advertising unconfigured local models.
- Updated README, AGENTS, real clean-machine canary docs, validation matrix,
  release checklist, release acceptance, tests, and the GitHub canary issue
  template so this final field proof is explicit and repeatable.
- Kept the scope cloud-only; local llama.cpp remains optional and separate from
  the final clean VM canary.

## v2.11.0

- Added `final-check`, a read-only verdict command that combines the private
  config, setup report, canary evidence, and real canary template into a
  Complete / Partially complete / Not complete / Needs rollback result.
- Wired `final-check` into bootstrap output, first-run setup output, README,
  START_HERE, AGENTS, FINAL_CHECK, user success criteria, real canary docs, and
  release acceptance.
- Updated stock-Codex handoff and agent handoff drills so simulated handoffs now
  generate a final check report and require a `Complete` verdict.

## v2.10.0

- Added `.github/ISSUE_TEMPLATE/real_clean_machine_canary.yml`, a safe GitHub
  reporting path for real stock Codex Desktop handoff tests.
- Added the `canary` label definition.
- Release acceptance now verifies the real clean-machine canary issue template.
- Updated release checklist and validation matrix so field-test reporting is
  part of the public-readiness path.

## v2.9.0

- Added `HANDOFF_TO_CODEX.md`, a root copy-paste prompt for users who only have
  stock Codex Desktop and a GitHub repository URL.
- Added `scripts/validate-github-entrypoint.py` to verify the root handoff
  prompt includes provider inputs, safety boundaries, bootstrap, dry-run,
  reports, and final verdict guidance.
- Wired the GitHub entrypoint validation into release acceptance and install
  validation.
- Updated README, START_HERE, AGENTS, release checklist, install validation,
  public release plan, and validation matrix to make the GitHub handoff path a
  first-class entrypoint.

## v2.8.0

- Added `real-canary-template`, a redacted checklist generator for real
  clean-machine stock Codex field tests.
- Added `docs/real-clean-machine-canary.md` with the required evidence chain for
  public-readiness canaries.
- Added `scripts/validate-real-clean-machine-canary.py` and wired it into
  release acceptance and install validation.
- Updated START_HERE, AGENTS, README, validation matrix, and release checklist so
  real-machine canary evidence is part of the final handoff path.

## v2.7.0

- Added `scripts/validate-agent-handoff-drill.py`, an end-to-end simulated
  stock Codex agent handoff drill.
- The drill rehearses bootstrap, guarded dry-run, env-help, bridge-health,
  guarded apply, setup-report, canary-report, protected-file hash checks, and
  final verdict guidance in a temporary stock-like Codex home.
- Added `docs/agent-handoff-drill.md` and linked it from README, START_HERE,
  AGENTS, validation matrix, release checklist, and public release plan.
- Release acceptance and install validation now run the agent handoff drill,
  making the "hand this repo to Codex" promise part of the release gate.

## v2.6.0

- Strengthened the stock Codex bootstrap handoff by printing the full
  post-apply completion path directly in command output.
- `bootstrap.py` now prints setup-report, canary-report, and FINAL_CHECK next
  steps after the guarded switch instructions.
- The first-run setup wizard now prints the same final evidence/reporting
  path for installed CLI users.
- Stock handoff validation now requires bootstrap output to include
  `canary-report` and `FINAL_CHECK.md`, reducing the chance that an agent stops
  at dry-run or setup-report and incorrectly claims completion.

## v2.5.0

- Added `canary-report`, a redacted final evidence report for real or simulated
  Codex Desktop canaries.
- The new report records manual UI confirmations for account visibility,
  plugin entry points, MCP entry points, project list visibility, a responding
  test chat, bridge health, setup report review, and an explicit completion
  verdict.
- `canary-report` is read-only for Codex state and writes only the chosen
  Markdown output file.
- Added warnings when a `complete` verdict is claimed without required visible
  evidence.
- Wired canary evidence into the stock Codex handoff validation, release
  acceptance gate, README, START_HERE, FINAL_CHECK, AGENTS runbook, validation
  matrix, release checklist, and setup-report guidance.

## v2.4.0

- Added `scripts/validate-release-acceptance.py`, a read-only release
  acceptance gate for the stock Codex handoff promise.
- The new gate checks required handoff files, documentation markers, version
  consistency, Python compilation, security scan, and clean-copy handoff
  validation.
- Added quick mode for CI/documentation checks that should avoid the heavier
  clean-copy handoff run.
- Updated release-readiness documentation to point to the current `v2.4.0`
  line instead of the older v1.0 wording.

## v2.3.0

- Strengthened the clean-copy stock Codex handoff validation for the default
  `bridge` route.
- `scripts/validate-stock-codex-handoff.py` now verifies the default bridge
  bootstrap/dry-run path from a clean repository copy before running the direct
  guarded-apply simulation.
- The handoff validation now also runs `bridge-health` against a deterministic
  closed bridge port and confirms it gives safe next steps without leaking the
  private upstream provider hostname.
- Updated validation docs to show that the default bridge handoff path is
  covered without starting a real bridge or touching real Codex state.

## v2.2.0

- Added `bridge-health`, a read-only diagnostic for bridge-routed cloud and
  local providers.
- The command checks the configured bridge TCP port, `/v1/health`,
  `/v1/models`, expected model ids, and bridge-routed API key environment
  variables without starting services or editing Codex files.
- Added clear next-step output for common failures: missing API key
  environment variables, bridge not running, unhealthy HTTP endpoint, or stale
  model list after config changes.
- Wired bridge health guidance into the stock Codex handoff docs, README,
  AGENTS runbook, validation matrix, and install validation.
- Added tests that verify diagnostics stay redacted and do not leak provider
  hostnames or API key values.

## v2.1.0

- Added `env-help`, a read-only helper that prints macOS and Windows
  environment-variable setup instructions for configured cloud provider API
  keys.
- Kept API keys out of the command surface: `env-help` does not read, print, or
  store key values.
- Updated bootstrap output, START_HERE, AGENTS, README, first-run wizard,
  Chinese tutorial, and agent-assisted setup docs to route users to `env-help`
  when `api_key_env(...unset)` appears.
- Added `docs/api-key-environment.md` as a standalone explanation of how
  `api_key_env` works with bridge-routed cloud providers.
- Added tests and install validation coverage for the env-help handoff path.

## v2.0.0

- Added `bridge` and `direct` cloud-provider routing.
- Made `bridge` the beginner default so Codex Desktop can point at the local
  bridge while the bridge forwards to the real OpenAI-compatible provider using
  `api_key_env`.
- Kept `direct` routing available for providers known to work with Codex
  Desktop's direct custom-provider authentication path.
- Added guarded-switch checks that refuse a bridge-routed cloud switch when the
  required API key environment variable is not set.
- Updated START_HERE, AGENTS, bootstrap, first-run wizard, setup intake,
  private-config dry-run, README, architecture, safety, and tutorial docs for
  the new routing model.
- Added tests for route validation, bridge-routed rendering, protected-file
  preservation, missing API-key refusal, setup reports, and stock-Codex handoff
  validation.

## v1.9.0

- Added root `FINAL_CHECK.md`, a copy-paste final verification prompt for Codex.
- Linked final verification from START_HERE, README, AGENTS, user success
  criteria, validation matrix, release checklist, and agent-assisted setup docs.
- Added documentation tests to keep final verdict categories and rollback
  boundaries present.

## v1.8.0

- Added `docs/user-success-criteria.md`, a non-technical checklist for deciding
  whether a guarded hybrid Codex setup is actually complete.
- Added a user success checklist to generated setup reports.
- Linked the success criteria from START_HERE, README, AGENTS, setup-report
  docs, validation matrix, release checklist, and agent-assisted setup docs.

## v1.7.0

- Added `scripts/validate-stock-codex-handoff.py`, a clean-copy validation for
  the `START_HERE.md` handoff flow.
- Added `docs/stock-codex-handoff-validation.md` to explain what the handoff
  validation proves and what remains machine-specific.
- Wired handoff validation into install validation, tests, README, AGENTS,
  validation matrix, and the release checklist.

## v1.6.0

- Added root `START_HERE.md`, a stock-Codex handoff page with a copy-paste
  prompt, safe milestones, stop conditions, and final report instructions.
- Linked the handoff page from README, AGENTS, and agent-assisted setup docs so
  a user can hand the repository to Codex without knowing the internal docs.
- Added documentation tests to keep the stock-Codex handoff prompt aligned with
  the guarded switching safety model.

## v1.5.0

- Added `setup-report`, a redacted Markdown report for completed or in-progress
  Codex hybrid setup.
- Added report coverage for active provider/model, provider ids, protected file
  hash prefixes, preserved config sections, backups, and local model path
  status.
- Added setup report generation and redaction checks to the stock-Codex
  validation flow.
- Documented setup reports in README, AGENTS, install validation, validation
  matrix, release checklist, agent-assisted setup, and the Chinese tutorial.

## v1.4.0

- Added stock-Codex bootstrap-to-apply validation using a temporary simulated
  Codex home.
- Verified the stock flow keeps `auth.json`, `models_cache.json`,
  `state_5.sqlite`, `sessions/`, and rollout logs unchanged.
- Added CI coverage for the stock-Codex validation script.
- Extended install validation, release checklist, and validation matrix to
  include the stock-Codex simulation gate.

## v1.3.0

- Added root `bootstrap.py`, a zero-install first-run entry that creates a
  private config, validates it, and runs guarded dry-run directly from the
  repository.
- Added macOS and Windows bootstrap launchers for users who prefer visible
  double-click entry points.
- Replaced the macOS desktop switcher launcher path with a guarded dry-run then
  `APPLY` flow, matching the safer Windows provider menu behavior.
- Added macOS guarded provider switch scripts and regression tests for launcher
  safety.
- Added bootstrap documentation and validation coverage in isolated install
  tests.

## v1.2.0

- Added root `AGENTS.md` so another Codex agent can safely configure a stock
  Codex Desktop install from this repository.
- Added agent-assisted setup documentation with a copy-paste prompt for users
  who want Codex to perform setup.
- Added setup intake checklist for provider details and local llama.cpp paths
  without collecting raw API keys.
- Added documentation regression tests to keep the agent runbook's safety
  invariants in CI.

## v1.1.0

- Added a beginner first-run `setup` wizard that creates and validates a private
  config without switching Codex Desktop.
- Added non-interactive setup mode for repeatable support scripts and install
  validation.
- Documented the stock-Codex caveat that existing official conversations may
  remain in the `openai` bucket because the project does not rewrite history.
- Added a visual demo gallery with sanitized generated SVG assets for dry-run,
  Windows switching, and local llama.cpp smoke-test flows.
- Added ROADMAP, release-post templates, recommended GitHub labels, and
  discussion templates for public community operations.
- Added a README 3-minute tour with a safer onboarding summary, visual workflow,
  and first-demo entry points.
- Added a Chinese getting-started tutorial and an English quickstart demo for
  safer first-time adoption.
- Updated public repository links, security contact details, and release
  visibility documentation after moving the project under `viezhukai-stack`.
- Added public issue templates for bug reports, setup help, and security-report
  redirection.
- Added FAQ and troubleshooting documentation for switching, recovery, local
  llama.cpp smoke failures, and safe issue reporting.
- Added README badges and a platform compatibility summary.
- Added package metadata keywords and classifiers.

## v1.0.0

- Promoted the validated `v1.0.0-rc.3` release candidate to the final
  source-only `v1.0.0` release.
- Kept the release scoped to GitHub source, tag, and draft release artifacts.
  No PyPI, Homebrew, winget, or installer packaging is included.
- Preserved the established safety boundary: guarded config switching only,
  no edits to Codex account/cache/history files, and no autostart or recovery
  loop services.

## v1.0.0-rc.3

- Added a public release plan for promoting a validated release candidate to
  final `v1.0.0` without moving existing tags.
- Linked the public release plan from the README, release checklist, and open
  source readiness checklist.
- Renamed the README release-candidate user path section to a stable user path
  section for public-facing documentation.

## v1.0.0-rc.2

- Removed organization-specific private endpoint names from the built-in
  security scanner before public-readiness review.
- Replaced that check with a generic internal-hostname rule for `.local`,
  `.lan`, and `.internal` endpoints.
- Added a regression test for internal endpoint hostname detection.
- Documented that project-specific deny-lists belong in private deployment
  checks, not in the public repository.

## v1.0.0-rc.1

- Prepared the repository as a private release candidate.
- Added public-facing safety, contribution, and release documentation.
- Hardened sensitive-content scanning for common token, path, LAN IP, and
  username leaks.
- Kept the project scoped to GitHub source/tag/release artifacts. No PyPI,
  Homebrew, or winget packaging is included.

## v0.9.0

- Added the validation matrix for Mac and Windows canaries.
- Added the release checklist and release gate documentation.
- Clarified that local model validation is optional per machine.
- Updated README examples to prefer `guarded-switch`.

## v0.8.0

- Added a guarded Windows end-user launcher flow.
- Added a second Windows canary workflow.
- Added Python 3.10 CI coverage after validating a Windows machine with Python
  3.10 only.
- Validated a second Windows machine for cloud provider switching, account
  visibility, project conversations, plugin/MCP visibility, and the guarded
  launcher.

## v0.7.0

- Added Windows guarded provider switching.
- Required explicit local approval for local providers.
- Ran local smoke before writing local-provider config.
- Fixed Windows bridge startup so it stays alive after the shell or SSH session
  that launched the switch exits.

## v0.6.0

- Validated Windows local llama.cpp flow on the first Windows canary.
- Confirmed local text and image smoke responses.
- Preserved `auth.json`, `models_cache.json`, and `state_5.sqlite` during
  guarded switching.

## v0.5.0

- Completed the first Windows cloud-provider canary.
- Added guarded switch behavior that hashes protected Codex files before and
  after apply.
- Confirmed the cloud switch can preserve account, plugin/MCP, and project
  conversation visibility.

## v0.4.0

- Added private config initialization and validation.
- Kept provider endpoints, keys, and local paths out of the repository.
- Strengthened dry-run flows before real provider switching.

## v0.3.0

- Added isolated install validation in temporary directories.
- Verified install, tests, security scan, and dry-run behavior without touching
  a real Codex profile.

## v0.2.0

- Added the engineering hardening baseline.
- Added tests, CI, dry-run behavior, and initial security scanning.
- Reframed the project as a clean reusable repository rather than a copy of a
  live machine setup.

## Safety Lessons Locked In

- Do not edit `models_cache.json`.
- Do not edit `state_5.sqlite` except for a deliberate, backed-up history
  repair outside this project.
- Do not mutate Codex sessions or rollout logs.
- Do not install LaunchAgents, KeepAlive jobs, scheduled recovery loops, or
  automatic restart scripts.
- Do not switch providers while Codex Desktop is running.
- Do not commit account state, provider credentials, local model files, runtime
  logs, backups, or quarantine directories.
- Treat Codex Desktop's bottom-right model selector as informational only; the
  external switcher and provider config are the source of truth.
- Treat local llama.cpp validation as hardware- and model-dependent. One
  successful local canary is enough for release readiness.
