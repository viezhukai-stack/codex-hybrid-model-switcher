# Bridge health check

Use `bridge-health` when a provider uses `route=bridge`, or when Codex Desktop
opens but a new test conversation does not reply.

The command is read-only. It does not start the bridge, stop the bridge, switch
providers, or edit Codex files.

## Run it

Installed command:

```sh
codex-hybrid-switcher bridge-health --config ~/.codex-hybrid-model-switcher/config.json
```

From the repository without installation:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher bridge-health --config ~/.codex-hybrid-model-switcher/config.json
```

On Windows from the repository:

```powershell
set PYTHONPATH=src
py -3 -m codex_hybrid_switcher bridge-health --config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
```

## What it checks

- whether the configured bridge TCP port is open
- whether `/v1/health` responds
- whether `/v1/models` responds
- which model ids the bridge reports
- whether bridge-routed cloud provider `api_key_env` variables are set
- whether the running bridge appears to be using the current private config

The output redacts provider endpoints and never prints API key values.

## Common results

If the bridge port is closed, start the bridge or rerun the guarded switch that
manages it:

```sh
python3 -m codex_hybrid_switcher bridge --config ~/.codex-hybrid-model-switcher/config.json
```

If `api_key_env` is unset, get safe setup instructions:

```sh
codex-hybrid-switcher env-help --config ~/.codex-hybrid-model-switcher/config.json
```

If the port is open but `/v1/health` or `/v1/models` fails, another service may
be using the same port. Stop that service or change the bridge port in the
private config, then rerun `guarded-switch --dry-run` before applying again.

If expected models are missing, restart the bridge so it reloads the current
private config.

## Safety boundary

`bridge-health` does not edit:

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- `sessions/`
- rollout logs

It is safe to run while diagnosing a failed or silent Codex Desktop test chat.
