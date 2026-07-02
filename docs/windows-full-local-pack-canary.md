# Windows Full Local Pack Canary

This canary validates the private netdisk full local model package:

```text
Codex-Hybrid-Windows-Full-Local-Setup-v2.15.1.zip
```

The full local package is intentionally not uploaded to GitHub. It is distributed
through a private netdisk link and includes the Windows installer, portable
Python, llama.cpp CPU runtime, a GGUF local model, a mmproj vision model, and a
red-square test image.

## Current Status

Status: Pending HL Hyper-V VM canary.

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
