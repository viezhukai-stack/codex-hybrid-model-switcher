# Open Source Readiness

Use this checklist before making the repository public or sharing a support
bundle.

## Required Checks

- Run `python -m codex_hybrid_switcher security-scan .`.
- Run `python scripts/validate-release-acceptance.py`.
- Confirm `CHANGELOG.md`, `SECURITY.md`, and `CONTRIBUTING.md` are present and
  describe the current release candidate.
- Confirm example configs use placeholder endpoints and environment variable
  names only.
- Confirm no account state files are present:
  - `auth.json`
  - `models_cache.json`
  - `state_5.sqlite`
  - `sessions/`
- Confirm no generated recovery material is present:
  - backups
  - quarantine folders
  - runtime logs
  - machine-specific migration reports
- Confirm no model binaries are present:
  - `.gguf`
  - `.safetensors`
  - llama.cpp release archives
- Confirm docs do not include private LAN addresses, hostnames, usernames,
  private absolute paths, or personal provider endpoints.
- Confirm scanner rules do not hard-code organization-specific private endpoint
  names; project-specific deny-lists belong in private deployment checks.

## Project Boundary

This repository should contain reusable source code, tests, docs, and placeholder
configuration only. Real Codex state, CC Switch state, provider credentials, and
local model files stay on each user's machine.

## Provider Examples

Default documentation should refer to generic OpenAI-compatible providers. A
private deployment can use any compatible provider by setting `base_url`,
`api_key_env`, and `model` in a private config file outside the repository.

## Release Gate

Before publishing a release, verify:

- CI passes on all configured Python versions.
- Release acceptance validation passes.
- The package version follows Python packaging rules, while the Git tag may use
  the project release style, for example package `1.0.0rc1` and tag
  `v1.0.0-rc.1`.
- `switch --dry-run` shows the expected diff and writes nothing.
- Real `switch` creates a backup before writing `config.toml`.
- The tool never edits `auth.json`, `models_cache.json`, or `state_5.sqlite`.
- Local bridge tests do not require secrets and are documented separately from
  unit tests.
- `docs/validation-matrix.md` reflects the actual canaries performed.
- `docs/release-checklist.md` is complete for the release candidate.
- `docs/public-release-plan.md` has been reviewed before final `v1.0.0`
  promotion.
- Release notes do not imply that every machine must pass local model
  validation; local model support is hardware- and model-dependent.
