# Windows Full Local Pack Canary

This canary validates the private netdisk full local model package:

```text
Codex-Hybrid-Windows-Full-Local-Setup-v2.15.5.zip
```

The full local package is intentionally not uploaded to GitHub. It is distributed
through a private netdisk link and includes the Windows installer, portable
Python, llama.cpp CPU runtime, a GGUF local model, a mmproj vision model, a
red-square test image, and the Microsoft Visual C++ Redistributable x64
installer under `payload/vcredist/`.

## Current Status

Status: Passed on the HL Hyper-V VM with `v2.15.5`.

Current private netdisk distribution uses
`Codex-Hybrid-Windows-Full-Local-Setup-v2.17.5.zip`. v2.17.5 keeps the same
full-local runtime path and cleans the netdisk payload by excluding repository
development files.

The v2.15.1 and v2.15.2 HL VM attempts found real setup gaps before final UI
apply:

- A stale managed bridge from an earlier cloud canary could occupy `127.0.0.1:19030`.
- The CPU-only local text smoke could exceed the old 180-second request timeout
  on a low-performance Hyper-V VM.
- A clean Windows VM could lack Microsoft Visual C++ Runtime DLLs required by
  the bundled llama.cpp CPU build, causing `llama-server.exe --version` to exit
  before local smoke.
- Local-only fallback after smoke failure tried to create a config with neither
  cloud nor local provider.

v2.15.5 addresses these by stopping previous managed Codex Hybrid bridge
processes before local smoke, using a 900-second installer smoke timeout,
checking `llama-server.exe` before local smoke, installing bundled VC++ Runtime
when available, reporting local-only smoke failure directly, and retrying
managed bridge startup without `CREATE_BREAKAWAY_FROM_JOB` when Windows
restricted-job execution denies that flag.

## HL Hyper-V VM Result

Package:
`Codex-Hybrid-Windows-Full-Local-Setup-v2.15.5.zip`

SHA256:
`aaa9626bac44fb08320d12f850b335a804a525b6d7918833744e97e28f3e9c33`

Result:

- The VM used the full local package without entering a cloud API key.
- The installer detected the bundled local model payload.
- The installer copied the local model into local app data.
- The installer used bundled portable Python.
- The installer used bundled llama.cpp CPU runtime.
- The installer verified or installed the bundled Microsoft VC++ Runtime.
- Local text smoke returned `OK`.
- Local image smoke returned `Red`.
- Guarded dry-run planned only the local provider/model switch.
- Real `APPLY` backed up `config.toml` and switched Codex to `local-gemma`.
- `auth.json`, `models_cache.json`, and `state_5.sqlite` remained unchanged.
- The managed bridge stayed available on `127.0.0.1:19030`.
- A direct post-apply bridge request returned `OK`.
- In Codex Desktop, account information remained visible.
- In Codex Desktop, plugins remained visible.
- In Codex Desktop, project conversations remained visible.
- A new Codex Desktop test message returned normally.

Verdict: Passed.

## Preconditions

- Windows VM has stock Codex Desktop installed and signed in.
- Codex Desktop is fully closed before running the installer.
- At least 15-20 GB free disk space is available.
- No cloud API key is required for this canary.
- The user does not upload or share `auth.json`, `models_cache.json`,
  `state_5.sqlite`, `sessions`, rollout logs, API keys, or screenshots with
  account secrets.

## Expected Installer Path

1. Extract the whole full local zip.
2. Double-click `Install Codex Hybrid.cmd`.
3. Confirm the installer reports free disk space.
4. Confirm it detects `payload\models\local-gemma`.
5. Confirm it copies the bundled model into local app data.
6. Confirm private config generation succeeds in local-only mode.
7. Confirm `local-smoke` runs and passes text plus vision checks.
8. Confirm guarded provider dry-run targets `local-gemma`.
9. Fully quit Codex Desktop.
10. Type `APPLY` only after dry-run passes.
11. Reopen Codex Desktop manually.

## Pass Criteria

- Codex Desktop opens without an error page.
- Account information remains visible.
- Plugin/MCP entry points remain visible, or the VM explicitly has no MCP setup.
- Project list and test project conversations remain visible.
- A new test chat responds through the local model.
- A test image can be described by the local vision path.
- `auth.json` and `models_cache.json` hashes are unchanged.
- `state_5.sqlite` is unchanged unless backed-up history unification is
  explicitly selected.
- `Restore Official Codex.cmd` can dry-run or apply a return to the official
  provider.

## Result Template

```text
Package:
SHA256:
VM:
Codex account visible:
Plugins/MCP visible:
Project list visible:
Local text reply:
Local image reply:
Protected files unchanged:
Restore entry verified:
Verdict:
Notes:
```
