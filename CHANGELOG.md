# Changelog

All notable changes to this project are summarized here. This project follows a
conservative release process because it edits Codex provider configuration.

## Unreleased

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
