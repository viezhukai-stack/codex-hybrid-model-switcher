# Setup intake checklist

Use this checklist before a real Codex provider switch. It is safe to share the
filled checklist with a helper as long as you do not include raw API keys.

## Required for cloud setup

```text
Operating system:
Codex Desktop can open normally: yes/no
Provider base_url:
Model id:
API key environment variable name:
Cloud route: bridge/direct
Do you want cloud-only setup first: yes/no
```

Do not write the API key itself here. Put the key in your operating system or
shell environment, then give the variable name to the setup wizard.

For most OpenAI-compatible providers, use `bridge`. It keeps the provider API
key outside Codex Desktop and lets the local bridge forward requests. Use
`direct` only when the provider is known to work with Codex Desktop's direct
custom-provider authentication path.

## Optional for local llama.cpp

Only fill this after the cloud setup works.

```text
llama-server path:
GGUF model path:
mmproj path:
Text smoke expected word:
Vision smoke expected word/color:
Known hardware limits:
```

## Files that must stay protected

The setup workflow should not edit:

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- `sessions/`
- rollout logs

If a helper says they need to edit these during first setup, stop and ask them
to explain why. Normal cloud setup should only require a guarded `config.toml`
change after dry-run.
