# Changelog

All notable changes to this project are summarized here. This project follows a
conservative release process because it edits Codex provider configuration.

## Unreleased

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
