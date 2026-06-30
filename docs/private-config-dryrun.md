# Private Config Dry-run

Use this workflow before any real Codex provider switch. It validates a private
config file and previews the Codex config diff without writing to real Codex
state.

## 1. Create a Private Config

macOS:

```sh
codex-hybrid-switcher init-config --platform macos --output ~/.codex-hybrid-model-switcher/config.json
```

Windows PowerShell:

```powershell
codex-hybrid-switcher init-config --platform windows --output "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

The generated file is private machine state. Do not commit it.

## 2. Edit Private Values

Edit only your local private config:

- `codex_home`
- provider `base_url`
- provider `api_key_env`
- provider `model`
- provider `route` (`bridge` for normal API-key providers, `direct` only for
  providers known to work with Codex Desktop direct auth)
- local `llama_server_path`
- local `model_path`
- local `mmproj_path`

Keep API keys in environment variables or your local provider manager. Do not
write key values into the config.

With `route=bridge`, Codex's planned `config.toml` points at
`127.0.0.1:19030`; the bridge uses `api_key_env` to forward to the real
provider. With `route=direct`, Codex points directly at the provider `base_url`.

## 3. Validate Without Leaking Details

```sh
codex-hybrid-switcher validate-config --config ~/.codex-hybrid-model-switcher/config.json
```

The output redacts provider hostnames and local file paths. It only reports
whether required fields are configured. To also require local files to exist:

```sh
codex-hybrid-switcher validate-config --check-paths --config ~/.codex-hybrid-model-switcher/config.json
```

## 4. Preview the Codex Config Diff

Use `switch --dry-run` before any real switch:

```sh
codex-hybrid-switcher switch cloud-gpt-main --dry-run --config ~/.codex-hybrid-model-switcher/config.json
```

Dry-run mode does not:

- write `config.toml`
- create backups
- start or stop the bridge
- touch `auth.json`
- touch `models_cache.json`
- touch `state_5.sqlite`

The dry-run diff redacts known private fields such as `base_url` and token-like
keys. Still treat dry-run output as private when using a real provider.

## 5. Next: Cloud Canary

This validation proves that private config loading and rendered Codex config are
correct. Real cloud-provider switching must use a guarded canary workflow:

- Windows: `docs/windows-cloud-canary.md`
- macOS: `docs/macos-cloud-switch-smoke.md`

Local model smoke tests are separate later steps.
