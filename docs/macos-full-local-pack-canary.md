# macOS Full Local Pack Canary

This records the real macOS UI canaries for the private netdisk full-local
package.

Original full-local canary:

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

Current private netdisk distribution uses:

```text
Codex-Hybrid-macOS-Full-Local-Setup-v2.18.3.zip
sha256: 305606d0c282112f4ecbd7d71676e309721532955a00e7c4763821d5b7897c0e
```

v2.18.3 keeps the same full-local runtime and upgraded ChatGPT/Codex app path,
then adds complete Gemini Responses conversion, bounded 429/empty-output
retries, and rebuilt package payloads that exclude repository development
files.

## v2.18.3 isolated Router canary

Date: 2026-07-26

Result: Passed without changing the active Codex profile.

- The candidate ran on isolated `127.0.0.1:19132`; the normal `19032` route and
  Codex `config.toml` were not replaced.
- `/health` returned the v2.18.3 hot router and the live catalog returned 59
  models including `gemini-pro-agent`.
- A Gemini High text request completed with `[DONE]`, preserved both reasoning
  and message output, retained usage, and reported terminal status
  `completed`.
- A required function-call request reproduced one upstream HTTP 200 response
  with an empty `output`. The bounded retry then returned reasoning plus
  `function_call`; the SSE contained both function-argument events, the final
  function name/arguments, usage, and `[DONE]`.
- The temporary router used a separate HOME/runtime-state directory and was
  stopped after verification. No Codex account, cache, database, session,
  plugin/MCP, launcher, or project-conversation file was edited.

## v2.18.0 UI Canary

Date: 2026-07-10

Result: Passed.

The controlled v2.18.0 canary used `Begin v2.18 Mac Canary.command` to quit the
upgraded ChatGPT/Codex app, stop the previous managed bridge/router processes,
start the repository-maintained shared hot router on `127.0.0.1:19032`, and
reopen ChatGPT/Codex.

Confirmed by the operator after restart:

- Account information remained visible.
- Plugin/MCP entry points remained visible.
- Project conversations remained visible.
- The model list included `gpt-5.6-sol`.
- The model list included the configured local model.
- A `gpt-5.6-sol` test conversation replied normally.
- A local model test conversation replied normally.

Additional router checks before the UI confirmation showed the installed
v2.18.0 shared router could route `gpt-5.6-sol` to `OK`, the configured local
text model to `OK`, and local vision to `Red`.

Safety observation:

- `auth.json` hash stayed unchanged.
- `state_5.sqlite` hash stayed unchanged.
- `config.toml` changed as expected for the v2.18.0 hot-router launch path.
- `models_cache.json` hash changed during upgraded app launch. This is recorded
  as a Codex/ChatGPT model-cache refresh observation, not as an installer or
  switcher write.

Backup pointer:

```text
~/CodexModelSwitcher/backups/v2.18.0-mac-ui-canary-20260710-214909
```

## v2.17.3 UI Canary

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
- The v2.18.3 package has passed package integrity, model manifest, runtime,
  redaction audits, and isolated Router/Gemini tool-call checks. The prior
  controlled v2.18.0 upgraded-app UI canary remains the profile-preservation
  baseline on the tested Mac.
- It does not prove performance on every Mac. Local model speed remains
  hardware-dependent.
- Lightweight macOS cloud packages are no longer the distribution priority; the
  intended private netdisk artifact is the full-local package.
