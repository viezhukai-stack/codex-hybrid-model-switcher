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

## Required Before a Release

- CI passes on Python 3.10, 3.11, and 3.12.
- `security-scan .` finds no sensitive-looking content.
- Install validation passes in a temporary directory.
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
