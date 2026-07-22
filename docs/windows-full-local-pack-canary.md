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

Status: Full-local install passed on the HL Hyper-V VM with `v2.15.5`;
v2.18.1 package integrity and physical Windows update compatibility passed.

Current private netdisk distribution uses
`Codex-Hybrid-Windows-Full-Local-Setup-v2.18.1.zip`. v2.18.1 keeps the proven
full-local runtime path, adds the guarded Codex update/Browser CLI refresh and
account-switch maintenance entries, and excludes repository development files.

Current v2.18.1 package SHA256:

```text
47fd0c231372338d1cedde35d08a1d2d2b48f1d1df4c046c5b6d4d7f37a58232
```

The rebuilt v2.18.1 package passed ZIP integrity checks and package structure
audits for bundled portable Python, llama.cpp, VC++ Runtime, local Gemma GGUF,
mmproj, test image, model manifest, the automatic update guard, both maintenance
entries, and the redacted project payload.

The 2026-07-22 physical Windows canary reproduced the Browser failure after a
Codex AppX update changed the CLI version. The five-file managed CLI bundle was
refreshed, the current-user `CODEX_CLI_PATH` survived the app regenerating its
Browser config, Browser/Chrome matched the new bundled marketplace, and a real
external DOM page loaded. A second AppX version change was detected before app
launch and repaired through the same guarded function. The packaged
`windows-update-ensure` wrapper adds the tested eligibility gate and invokes
that same repair automatically only while Codex is closed.

At the end of the physical canary, the task database returned `quick_check=ok`,
all 100 tasks remained in the `custom` provider bucket, 47 were archived,
`19030` and `19032` were healthy, and the heavy `19031` local runtime was not
resident while idle. The repair reported protected Codex files unchanged.

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
