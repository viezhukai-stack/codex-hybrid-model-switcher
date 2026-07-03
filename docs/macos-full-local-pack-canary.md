# macOS Full Local Pack Canary

This records the real macOS UI canary for the private netdisk full-local package:

```text
Codex-Hybrid-macOS-Full-Local-Setup-v2.17.3.zip
sha256: 27120d176555b542a0c046c937f3667c2e36cad763f881a1ef7e17b474964625
```

## Environment

- Date: 2026-07-04
- Host: macOS 15.7.2, Intel x86_64
- Package mode: full local, no cloud API key required
- Bundled local model: Gemma 4 E4B GGUF plus mmproj
- Bundled llama.cpp runtimes: macOS x64 and macOS arm64

## Result

Passed.

The operator completed a real UI test of the macOS full-local package and
confirmed:

- Codex account information remained visible.
- Plugin entry remained visible.
- Project conversations remained visible.
- A test message returned normally.
- The main Codex profile was restored afterward using `Restore Main Codex Profile.command`.

## Safety Evidence

Before the canary, the main profile was protected with a Desktop backup:

```text
~/Desktop/codex-main-profile-backup-20260704-013321
```

After running `Restore Main Codex Profile.command`, the main profile was checked:

- `auth.json` hash matched the pre-canary baseline.
- `state_5.sqlite` provider bucket remained unified as `custom`.
- Current main config key fields were back on `custom` with model `gpt-5.5`.
- Current config was not left on the package test model `local/gemma`.

The canary did not intentionally modify `auth.json` or `models_cache.json`.
Any `state_5.sqlite` changes after reopening Codex are expected to include normal
new-thread/runtime state from the restored main session.

## Notes

- This canary proves the v2.17.3 macOS full-local package can be installed and
  used in Codex Desktop without breaking account, plugin, project conversation,
  or reply behavior on the tested Mac.
- It does not prove performance on every Mac. Local model speed remains
  hardware-dependent.
- Lightweight macOS cloud packages are no longer the distribution priority; the
  intended private netdisk artifact is the full-local package.
