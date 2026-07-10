# Recovery

If a switch fails:

1. Quit Codex Desktop.
2. Restore the latest `config.toml.bak-codex-hybrid-*` file in your Codex home.
3. Start Codex normally.
4. Do not repair history or cache files unless you have a fresh backup and know
   the exact failure.

This project intentionally does not provide automated recovery loops.

On the first guarded switch away from the official provider, v2.18.0 also saves
a private `official-config-baseline-*.toml` under
`~/.codex-hybrid-model-switcher`. `Restore Official Codex` uses that exact
baseline when available. If it is missing, the fallback restores the built-in
`openai` provider without pinning an old model ID.
