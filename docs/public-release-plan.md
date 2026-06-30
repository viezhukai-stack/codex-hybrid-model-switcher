# Public Release Plan

Use this document after a release candidate has passed validation and before
making the repository public or publishing a final `v1.0.0` GitHub release.

## Current Candidate

The current public-readiness candidate is `v1.0.0-rc.3`.

`v1.0.0-rc.1` and `v1.0.0-rc.2` are kept for audit history only. Do not use
them as the current candidate because public-readiness updates landed after
those tags.

## Required Manual Review

Before promoting to `v1.0.0`, manually review:

- README quick start and user paths
- `CHANGELOG.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `docs/open-source-readiness.md`
- `docs/release-checklist.md`
- `docs/validation-matrix.md`
- draft release notes for `v1.0.0-rc.3`

Confirm the docs do not include:

- private endpoint names
- private LAN addresses
- real usernames or machine names
- absolute personal paths
- provider credentials, tokens, account files, or model files

## Final Promotion Steps

1. Start from a clean `main` at the accepted release candidate.
2. Create a release branch, for example `v1.0-final-release`.
3. Change package metadata from `1.0.0rc3` to `1.0.0`.
4. Change `src/codex_hybrid_switcher/__init__.py` to `1.0.0`.
5. Add a `v1.0.0` section to `CHANGELOG.md`.
6. Run the repository checks from `docs/release-checklist.md`.
7. Open a PR and wait for Python 3.10, 3.11, and 3.12 CI to pass.
8. Merge the PR into `main`.
9. Tag `v1.0.0` from the merge commit and push the tag.
10. Create a draft GitHub release for `v1.0.0`.
11. Re-read the release notes before publishing.

Do not publish PyPI, Homebrew, winget, or installer packages as part of
`v1.0.0` unless a separate packaging plan has been reviewed.

## Repository Visibility

If the repository is private, switch visibility only after:

- `security-scan .` passes
- GitHub Actions is green on the final PR
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
