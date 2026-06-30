# Roadmap

This roadmap tracks practical improvements for making Codex Hybrid Model
Switcher easier to trust, install, and operate. It is intentionally conservative:
new features should not weaken the safety boundary around Codex account,
plugin/MCP, cache, or session state.

## Guiding Principles

- Keep `auth.json`, `models_cache.json`, `state_5.sqlite`, session history, and
  rollout logs out of normal switching.
- Prefer dry-run, backup, and guarded apply over invisible automation.
- Do not add autostart, KeepAlive, recovery-loop, or background takeover
  behavior.
- Treat local llama.cpp support as optional and hardware-dependent.
- Keep public docs free of real endpoints, keys, private paths, machine names,
  and account data.

## Near Term

- Improve screenshots and short demos for first-time users.
- Add a lightweight config wizard for common cloud-provider fields.
- Add clearer Windows launcher packaging without changing the source-only
  release model.
- Add more examples for OpenAI-compatible providers using placeholder values.
- Add optional label-sync or repository-maintenance scripts that are dry-run
  first.

## Mid Term

- Build a small local GUI for provider selection and guarded switch previews.
- Add a local model configuration wizard for llama.cpp, GGUF, and mmproj paths.
- Expand local smoke tests for text-only and multimodal models.
- Add more recovery diagnostics for common Codex configuration mistakes.
- Add a compatibility matrix for Codex Desktop versions after community reports.

## Later

- Evaluate package distribution options such as signed archives or platform
  installers.
- Explore an optional provider registry format for sharing sanitized templates.
- Add automated documentation screenshots generated from sanitized fixtures.
- Consider a plugin-style architecture for provider adapters.

## Out of Scope

- Rewriting Codex Desktop's internal model cache.
- Mutating existing session history during normal provider switching.
- Shipping model binaries, private provider configs, or account files.
- Managing paid provider accounts or credentials inside this repository.
- Installing always-on services that restart Codex or the switcher.
