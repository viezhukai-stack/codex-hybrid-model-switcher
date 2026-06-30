# Public Release Plan

Use this document after a final release has passed validation and before making
the repository public or publishing the GitHub release.

## Current Release

The current public-readiness release is `v2.4.0`.

Earlier `v1.0.0-rc.*`, `v1.0.0`, and v2.x tags are kept for audit history.
Use the newest non-draft release unless a maintainer explicitly pins a
different version.

## Required Manual Review

Before making the repository public or publishing the current release,
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

1. Start from a clean `main` at the current public-readiness release.
2. Run the repository checks from `docs/release-checklist.md`.
3. Run `python scripts/validate-release-acceptance.py`.
4. Confirm CI is green on Python 3.10, 3.11, and 3.12.
5. Confirm badges, issue-template links, and release notes point to the current
   repository owner.
6. Re-read the release notes before publishing.
7. Switch repository visibility to public.
8. Publish or verify the GitHub release.
9. Pin the repository on the GitHub profile after it is public.

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
