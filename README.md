# Codex Hybrid Model Switcher

Cross-platform tooling for using Codex Desktop with:

- official OpenAI/Codex account state preserved
- OpenAI-compatible cloud providers configured by the user
- local llama.cpp models, including multimodal GGUF + mmproj models
- CC Switch-style provider switching outside Codex's bottom-right model menu

The project is intentionally conservative. It does not edit `models_cache.json`,
does not mutate Codex session history, and does not install KeepAlive services.

## Safety Model

- Treat the external switcher as the source of truth.
- Quit Codex Desktop before switching providers.
- Keep project history unified under the `custom` provider bucket.
- Keep API keys outside the repository. Use environment variables or your local
  provider manager.
- Route local models through the bridge on `127.0.0.1:19030`; the raw
  llama.cpp server stays behind it on `127.0.0.1:19031`.

## Quick Start

1. Install locally:

   ```sh
   python3 -m pip install -e .
   ```

2. Copy an example config:

   ```sh
   codex-hybrid-switcher init-config --platform macos --output ~/.codex-hybrid-model-switcher/config.json
   ```

3. Edit paths and provider endpoints in that private config.

4. Check the environment:

   ```sh
   codex-hybrid-switcher validate-config --config ~/.codex-hybrid-model-switcher/config.json
   ```

5. Preview the Codex config change without writing anything:

   ```sh
   codex-hybrid-switcher guarded-switch cloud-gpt-main --dry-run --config ~/.codex-hybrid-model-switcher/config.json
   ```

6. For a real cloud switch, quit Codex Desktop completely, then use guarded
   apply:

   ```sh
   codex-hybrid-switcher guarded-switch cloud-gpt-main --config ~/.codex-hybrid-model-switcher/config.json
   ```

7. Test local models only on machines that have suitable hardware, llama.cpp,
   and model files:

   ```sh
   codex-hybrid-switcher local-smoke --config ~/.codex-hybrid-model-switcher/config.json
   ```

8. Switch to a local provider only after local smoke passes:

   ```sh
   codex-hybrid-switcher guarded-switch local-gemma --allow-local --config ~/.codex-hybrid-model-switcher/config.json
   ```

## Commands

```sh
python -m codex_hybrid_switcher status
python -m codex_hybrid_switcher doctor
python -m codex_hybrid_switcher doctor --strict
python -m codex_hybrid_switcher init-config --platform macos --output ~/.codex-hybrid-model-switcher/config.json
python -m codex_hybrid_switcher validate-config --config ~/.codex-hybrid-model-switcher/config.json
python -m codex_hybrid_switcher bridge
python -m codex_hybrid_switcher local-smoke
python -m codex_hybrid_switcher smoke
python -m codex_hybrid_switcher security-scan .
python -m codex_hybrid_switcher menu
python -m codex_hybrid_switcher switch <provider-id> --dry-run
python -m codex_hybrid_switcher guarded-switch <provider-id> --dry-run
python -m codex_hybrid_switcher guarded-switch local-gemma --allow-local
python -m codex_hybrid_switcher guarded-switch <provider-id>
python -m codex_hybrid_switcher switch <provider-id>
```

## Isolated Install Validation

Before using this project with a real Codex profile, run the isolated validation:

```sh
python3 scripts/validate-install.py
```

It creates a temporary workspace, installs the package, runs tests and security
checks, and exercises `switch --dry-run` against a simulated Codex config. See
`docs/install-validation.md` for macOS and Windows details.

## Private Config Dry-run

After install validation, use `docs/private-config-dryrun.md` to initialize and
validate a machine-local config. The validation output redacts provider hostnames
and local file paths. Stop at `switch --dry-run` until you are ready for a real
Codex provider switch.

For the first real cloud-provider smoke test, use a canary machine and prefer
`guarded-switch` so protected Codex state files are hashed before and after the
switch. Start with `docs/windows-cloud-canary.md` for Windows or
`docs/macos-cloud-switch-smoke.md` for macOS. Do not test local llama.cpp models
in the cloud canary workflow.

After cloud canary verification, use `docs/local-llama-smoke.md` to validate the
local bridge and llama.cpp model before switching Codex Desktop to a local
provider.

For the Windows end-user switching flow after both canaries pass, use
`docs/windows-user-flow.md`.

To repeat the validation on another Windows machine, follow
`docs/windows-second-canary.md` before installing the end-user launcher.

For the current validation coverage and release gate, see
`docs/validation-matrix.md` and `docs/release-checklist.md`.

## What This Repository Must Not Contain

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- API keys, bearer tokens, refresh tokens, or passwords
- personal backups, cleanup quarantine folders, or runtime logs
- machine-specific private paths except inside example placeholders

See `docs/safety.md` before adapting this to a real Codex installation.
