# Public Release Plan

Use this document after a final release has passed validation and before making
the repository public or publishing the GitHub release.

## Current Release

The current public-readiness release is `v1.0.0`.

`v1.0.0-rc.1`, `v1.0.0-rc.2`, and `v1.0.0-rc.3` are kept for audit history
only. Do not use them as the current public release because final-readiness
updates landed after those tags.

## Required Manual Review

Before making the repository public or publishing the `v1.0.0` release,
manually review:

- README quick start and user paths
- `CHANGELOG.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `docs/open-source-readiness.md`
- `docs/release-checklist.md`
- `docs/validation-matrix.md`
- draft release notes for `v1.0.0`

Confirm the docs do not include:

- private endpoint names
- private LAN addresses
- real usernames or machine names
- absolute personal paths
- provider credentials, tokens, account files, or model files

## Final Visibility Steps

1. Start from a clean `main` at the final `v1.0.0` release.
2. Run the repository checks from `docs/release-checklist.md`.
3. Confirm CI is green on Python 3.10, 3.11, and 3.12.
4. Confirm badges, issue-template links, and release notes point to the current
   repository owner.
5. Re-read the draft `v1.0.0` release notes before publishing.
6. Switch repository visibility to public.
7. Publish the `v1.0.0` GitHub release.
8. Pin the repository on the GitHub profile after it is public.

Do not publish PyPI, Homebrew, winget, or installer packages as part of
`v1.0.0` unless a separate packaging plan has been reviewed.

## Repository Visibility

If the repository is private, switch visibility only after:

- `security-scan .` passes
- GitHub Actions is green on `main`
- `docs/open-source-readiness.md` has been checked manually
- the draft `v1.0.0` release notes have been reviewed

Changing repository visibility is a manual owner action. It should not be done
by automation.

## No-Go Conditions

Do not promote or publish if any of these are found:

- real Codex state files in the repository
- private provider endpoints or credentials in docs, examples, issues, or
  release notes
- generated backups, quarantine folders, runtime logs, model binaries, or
  llama.cpp release archives
- tests or security scan failing
- release notes implying that local llama.cpp validation must pass on every
  machine
