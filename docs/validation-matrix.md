# Validation Matrix

This project treats model switching safety as the core requirement. Local model
support is an optional capability because it depends on each machine's GPU,
driver, CUDA runtime, llama.cpp build, and model size.

## Validation Summary

| Environment | Cloud Provider | Local Model | Codex UI | Notes |
| --- | --- | --- | --- | --- |
| macOS working setup | Proven in the original field workflow | Proven in the original field workflow | Proven in the original field workflow | The current repository has not replaced the existing Mac field scripts. Mac remains the active working Codex environment and should not be used for risky canaries. |
| Windows canary 1 | Passed | Passed | Passed | Validated guarded cloud switch, local llama.cpp/Gemma text smoke, image smoke, and Codex Desktop UI behavior. |
| Windows canary 2 | Passed | Not required | Passed | Validated second-machine migration, Python 3.10 compatibility, guarded cloud switch, user-facing launcher, account visibility, project conversations, plugin/MCP visibility, and a test chat. Local Qwen3.6 35B candidates were found but not tested because local hardware/model fit is not a release requirement. |
| Stock Codex simulation | Passed | Not applicable | Simulated | `scripts/validate-stock-codex-flow.py` creates a temporary stock-like Codex home, runs bootstrap dry-run, runs guarded apply, verifies only `config.toml` changed while account/cache/history-like files stayed unchanged, and checks the generated setup report is redacted. |
| Stock Codex handoff | Passed | Not applicable | Simulated | `scripts/validate-stock-codex-handoff.py` copies the repository to a clean temporary directory, verifies default bridge bootstrap/dry-run plus `bridge-health`, verifies bootstrap does not pollute the repository, and confirms private config plus guarded apply behavior. |
| Bridge-routed cloud unit path | Passed | Not applicable | Simulated | Unit tests verify `route=bridge` renders Codex to `127.0.0.1:19030`, refuses real switches when `api_key_env` is unset, starts the bridge when the env var is set, and preserves protected Codex files. |
| API key env handoff | Passed | Not applicable | Simulated | `env-help` is covered by unit tests and install validation, including macOS and Windows command templates without exposing key values. |
| Bridge health diagnostic | Passed | Not applicable | Simulated | `bridge-health` checks the bridge port, `/v1/health`, `/v1/models`, bridge-routed API key env status, and expected model ids without starting services or editing Codex state. |
| Release acceptance gate | Passed | Not applicable | Simulated | `scripts/validate-release-acceptance.py` checks required handoff files, documentation markers, version consistency, Python compilation, security scan, and clean-copy handoff validation. |

## Required Before a Release

- CI passes on Python 3.10, 3.11, and 3.12.
- `security-scan .` finds no sensitive-looking content.
- Install validation passes in a temporary directory.
- Stock-Codex bootstrap-to-apply simulation passes in a temporary directory.
- Stock-Codex handoff validation passes from a clean temporary repository copy,
  including the default bridge dry-run and bridge-health diagnostic path.
- Release acceptance validation passes before tagging.
- Redacted setup report generation passes in the stock-Codex simulation.
- The setup report includes user-visible success criteria for account,
  plugins/MCP, project list, and a new responding test conversation.
- `FINAL_CHECK.md` gives users a final agent prompt for classifying completion
  as complete, partial, incomplete, or rollback-needed.
- The stock-Codex handoff prompt in `START_HERE.md` is covered by documentation
  tests.
- Bridge-routed cloud providers have tests for local bridge rendering,
  missing API-key refusal, and protected-file preservation.
- `env-help` is tested as the next step when `api_key_env(...unset)` appears.
- `bridge-health` is tested as the next step when Codex opens but a
  bridge-routed provider does not reply.
- At least one Windows canary has validated cloud provider switching.
- At least one Windows canary has validated local llama.cpp text and image smoke.
- At least one second-machine Windows canary has validated cloud switching and the guarded launcher.
- Protected Codex files are unchanged during guarded switch canaries:
  - `auth.json`
  - `models_cache.json`
  - `state_5.sqlite`

## Optional Local Model Validation

Local model validation is not expected to pass on every machine. A machine may
skip local validation when:

- no suitable GPU is present
- CUDA runtime is missing or incompatible
- the only available local model is too large for the machine
- no matching mmproj file exists for a multimodal model
- llama.cpp is missing or too old

Skipping local validation on one machine does not block release readiness if
another canary already validated the local bridge and llama.cpp flow.

## What Counts as a Failed Canary

Stop and investigate if any of these happen:

- account information disappears
- project conversations disappear
- plugin or MCP entry points disappear
- `auth.json`, `models_cache.json`, or `state_5.sqlite` hash changes
- the dry-run diff removes unrelated settings
- Codex is running and the switch still writes config
- local smoke fails but the tool continues to write config

## What Does Not Count as a Project Failure

These are environment limitations, not release blockers:

- a particular machine cannot fit a large local model in VRAM
- a local model is slow
- a machine lacks CUDA
- a machine has a different local model family than the examples
- the Codex bottom-right model selector displays a stale or generic label

The external switcher and `config.toml` provider/model fields are the source of
truth for this project.
