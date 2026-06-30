# Install Validation

Use this validation before replacing any existing Codex workflow with this
project. It installs and tests the package in a temporary directory and uses a
simulated Codex home.

## What It Verifies

- Editable install from the repository.
- Python syntax compilation.
- Unit tests.
- Repository security scan.
- `init-config` into temporary macOS and Windows private config paths.
- `validate-config` against the generated private config.
- `doctor` against a temporary config.
- `bootstrap.py --non-interactive` into a temporary private config path.
- Bootstrap guarded dry-run without touching the simulated Codex home.
- Stock-Codex bootstrap-to-apply simulation using a temporary `.codex` home.
- `switch --dry-run` against a simulated `config.toml`.
- MCP/plugin-like config blocks remain visible in the dry-run diff.
- The simulated `config.toml` is unchanged after dry-run.

## What It Does Not Touch

- Real `~/.codex` or `%USERPROFILE%\.codex`.
- `auth.json`.
- `models_cache.json`.
- `state_5.sqlite`.
- Real CC Switch state.
- Real provider credentials.
- Real llama.cpp or model files.

## macOS

From the repository root:

```sh
python3 scripts/validate-install.py
```

The default temporary root is `/private/tmp`. The script removes its validation
workspace after a successful run. To inspect the generated files:

```sh
python3 scripts/validate-install.py --keep
```

## Windows

From the repository root in PowerShell:

```powershell
py scripts\validate-install.py --tmp-root $env:TEMP
```

This uses a temporary validation workspace under `%TEMP%` and still uses only a
simulated Codex home.

## Expected Result

The final line should be:

```text
install validation passed
```

If the script fails during dependency installation, rerun it in an environment
that can reach the Python package index. If it fails during the security scan,
remove the reported private data from the repository before continuing.

## Stock-Codex Flow Only

To run only the stock-Codex bootstrap-to-apply simulation:

```sh
python3 scripts/validate-stock-codex-flow.py
```

The script creates a temporary Codex home with `auth.json`,
`models_cache.json`, `state_5.sqlite`, `sessions/`, rollout logs, and
MCP/plugin/project config blocks. It verifies bootstrap dry-run writes nothing,
then verifies guarded apply changes only `config.toml` and creates a backup.
