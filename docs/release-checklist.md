# Release Checklist

Use this checklist before marking a release candidate ready.

## Repository Checks

- `python -m compileall -q src tests scripts/validate-install.py`
- `pytest`
- `python -m codex_hybrid_switcher security-scan .`
- `python scripts/validate-install.py`
- `python scripts/validate-stock-codex-flow.py`
- `python scripts/validate-stock-codex-handoff.py`
- `python -m codex_hybrid_switcher setup-report --config <temp-config>`
- GitHub Actions passes on Python 3.10, 3.11, and 3.12.
- Working tree is clean before tagging.

## Sensitive Content Checks

Confirm the repository does not contain:

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- API keys
- bearer tokens
- refresh tokens
- account passwords
- personal backup directories
- runtime logs
- private endpoint hostnames
- private LAN IP addresses
- real machine usernames in example configs

## Safety Checks

- No LaunchAgent, KeepAlive job, recovery loop, or scheduled auto-restart service is installed by this project.
- Real provider switches go through `guarded-switch` or the Windows guarded scripts.
- Dry-run mode prints a redacted diff and writes nothing.
- Real apply backs up `config.toml`.
- Protected Codex files are hashed before and after apply.
- Stock-Codex simulation changes only `config.toml` and adds a
  `config.toml.bak-codex-hybrid-*` backup.
- Stock-Codex handoff validation passes from a clean repository copy.
- Setup report redacts provider hostnames, local paths, session content, and
  database content.
- Local providers require explicit local approval and run local smoke before writing config.
- Desktop launchers do not use the unsafe raw Python `menu` command.

## Documentation Checks

- README points new users toward dry-run and guarded canary flows.
- `CHANGELOG.md`, `SECURITY.md`, and `CONTRIBUTING.md` are present and current.
- Windows docs describe the guarded launcher.
- Local model docs say local validation is optional and machine-dependent.
- Recovery docs explain how to restore `config.toml` from the newest backup.
- Validation matrix reflects the actual canaries performed.
- Public release plan explains how to promote the accepted release candidate to
  a final `v1.0.0` tag without moving existing tags.

## Canary Checks

Before a release candidate:

- One Windows canary passes cloud switch and UI validation.
- One Windows canary passes local llama.cpp text and image validation.
- A second Windows canary passes cloud switch and guarded launcher validation.
- Protected files are unchanged in each real apply.

macOS real switching may remain deferred when the Mac is the active working
Codex environment. Do not risk interrupting the active Mac session solely for a
release checklist item.

## Tagging

After checks pass:

```sh
git checkout main
git pull --ff-only origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

Do not tag from a dirty tree or an unmerged feature branch.

For release candidates, keep the Python package version normalized, such as
`1.0.0rc1`, and use the Git tag style `v1.0.0-rc.1`.

For the final release, use package version `1.0.0` and Git tag `v1.0.0`.
Never move an existing release-candidate tag after it has been pushed.
