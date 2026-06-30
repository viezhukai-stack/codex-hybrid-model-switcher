# Release Checklist

Use this checklist before marking a release candidate ready.

## Repository Checks

- `python -m compileall -q src tests scripts/validate-install.py`
- `pytest`
- `python -m codex_hybrid_switcher security-scan .`
- `python scripts/validate-release-acceptance.py`
- `python scripts/validate-github-entrypoint.py`
- `python scripts/validate-install.py`
- `python scripts/validate-stock-codex-flow.py`
- `python scripts/validate-stock-codex-handoff.py`
- `python scripts/validate-agent-handoff-drill.py`
- `python scripts/validate-real-clean-machine-canary.py`
- `python scripts/validate-release-acceptance.py --quick`
- `python -m codex_hybrid_switcher setup-report --config <temp-config>`
- `python -m codex_hybrid_switcher canary-report --config <temp-config> --verdict partial`
- `python -m codex_hybrid_switcher final-check --config <temp-config>`
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
- GitHub handoff entrypoint validation passes for the root copy-paste prompt.
- Agent handoff drill passes and writes a redacted temporary drill report.
- Real clean-machine canary template validation passes.
- GitHub issue template for real clean-machine canaries is present and blocks
  private Codex state attachments.
- `docs/windows-hyperv-clean-vm-canary.md` documentation is present and requires
  checkpoint `stock-codex-baseline`, fixed release `v2.11.0`, one
  `cloud_route=bridge` provider, `guarded-switch --dry-run`, and
  `codex-hybrid-final-check.md` with `Complete`.
- Release acceptance validation passes and confirms the stock Codex handoff
  evidence is present.
- Bridge-routed cloud providers refuse real apply when `api_key_env` is unset.
- `env-help` prints OS-specific setup instructions without reading, printing,
  or storing API keys.
- `bridge-health` checks bridge port, `/v1/health`, `/v1/models`, model ids,
  and bridge-routed API key env status without starting services or writing
  Codex files.
- Bridge-routed cloud providers render Codex's `base_url` to the local bridge,
  not the private upstream provider hostname.
- Setup report redacts provider hostnames, local paths, session content, and
  database content.
- Setup report includes the user-visible success checklist.
- Canary evidence report records account, plugin, MCP, project list, test chat,
  bridge health, and setup report review status without editing Codex files.
- Canary evidence report warns when a `complete` verdict lacks required
  evidence.
- Final check report combines setup, canary, and real-canary evidence into a
  read-only Complete / Partially complete / Not complete / Needs rollback
  verdict.
- Local providers require explicit local approval and run local smoke before writing config.
- Desktop launchers do not use the unsafe raw Python `menu` command.

## Documentation Checks

- README points new users toward dry-run and guarded canary flows.
- `HANDOFF_TO_CODEX.md` gives stock Codex users a single copy-paste prompt from
  the GitHub page.
- `.github/ISSUE_TEMPLATE/real_clean_machine_canary.yml` gives field testers a
  safe reporting path.
- `CHANGELOG.md`, `SECURITY.md`, and `CONTRIBUTING.md` are present and current.
- Windows docs describe the guarded launcher.
- Local model docs say local validation is optional and machine-dependent.
- Recovery docs explain how to restore `config.toml` from the newest backup.
- User success criteria explain when setup is complete versus only partially
  complete.
- Canary evidence docs explain how to record final user-visible checks.
- Final check docs explain the read-only verdict command and required reports.
- Final check prompt asks Codex to classify completion without making new
  changes.
- Agent handoff drill docs explain how to rehearse the full stock Codex path.
- Real clean-machine canary docs explain how to collect final field evidence.
- Windows Hyper-V clean VM canary docs explain the final stock-Codex proof from
  a clean Windows 11 VM without testing local llama.cpp.
- Cloud route documentation explains `bridge` versus `direct` and recommends
  `bridge` for normal API-key providers.
- Bridge health documentation explains what to do when Codex opens but a
  bridge-routed test chat does not reply.
- Validation matrix reflects the actual canaries performed.
- Public release plan explains how to promote the accepted release candidate to
  a final `v1.0.0` tag without moving existing tags.

## Canary Checks

Before a release candidate:

- One Windows canary passes cloud switch and UI validation.
- One Windows canary passes local llama.cpp text and image validation.
- A second Windows canary passes cloud switch and guarded launcher validation.
- Protected files are unchanged in each real apply.
- Before public release, one Windows Hyper-V clean VM canary should pass from
  stock Codex Desktop using release `v2.11.0`, checkpoint
  `stock-codex-baseline`, one cloud provider, and `final-check` verdict
  `Complete`.

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
