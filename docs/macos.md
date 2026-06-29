# macOS Notes

- Desktop launcher extension: `.command`
- Typical Codex home: `~/.codex`
- Typical CC Switch home: `~/.cc-switch`
- llama.cpp binary path is user-configured and should not be hardcoded in the
  repository.

Use `config/examples/config.macos.example.json` as the starting point.

For local llama.cpp validation, follow `docs/local-llama-smoke.md`. The smoke
workflow starts a managed bridge and stops it after the text/image checks.
