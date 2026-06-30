# Bootstrap entry

`bootstrap.py` is the lowest-friction first-run entry point. It runs directly
from the repository with the Python standard library and the local `src/`
directory. It does not require `pip install -e .` before the first dry-run.

Use it when a user opens this repository in Codex and says: "configure this for
my Codex Desktop."

## What bootstrap does

- creates a private config if one does not already exist
- validates that private config
- runs `guarded-switch --dry-run`
- prints the real guarded-switch command for later

## What bootstrap does not do

- it does not apply a real switch by default
- it does not edit `auth.json`
- it does not edit `models_cache.json`
- it does not edit `state_5.sqlite`
- it does not edit session history
- it does not install background services
- it does not download local model files

## Interactive bootstrap

macOS:

```sh
python3 bootstrap.py
```

Windows:

```powershell
py -3 bootstrap.py
```

The script asks for provider details, creates
`~/.codex-hybrid-model-switcher/config.json`, then runs dry-run.

## Non-interactive bootstrap

macOS:

```sh
python3 bootstrap.py --non-interactive \
  --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 \
  --model provider-gpt-main \
  --api-key-env OPENAI_COMPATIBLE_API_KEY
```

Windows:

```powershell
py -3 bootstrap.py --non-interactive `
  --platform windows `
  --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 `
  --model provider-gpt-main `
  --api-key-env OPENAI_COMPATIBLE_API_KEY
```

`--api-key-env` is the name of the environment variable containing the API key.
It is not the API key itself.

## Double-click helpers

For users who prefer a visible launcher:

- macOS: `scripts/Codex Hybrid Bootstrap.command`
- Windows: `scripts/Codex Hybrid Bootstrap.cmd`

These launchers run bootstrap. They still only create/validate private config
and dry-run. They do not apply a real provider switch.

After dry-run looks correct, quit Codex Desktop completely and run the guarded
apply command that bootstrap prints.
