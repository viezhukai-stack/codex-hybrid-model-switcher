# Codex Hybrid Model Switcher

Cross-platform tooling for using Codex Desktop with:

- official OpenAI/Codex account state preserved
- OpenAI-compatible cloud providers
- local llama.cpp models, including multimodal GGUF + mmproj models
- CC Switch-style provider switching outside Codex's bottom-right model menu

The project is intentionally conservative. It does not edit `models_cache.json`,
does not mutate Codex session history, and does not install KeepAlive services.

## Safety Model

- Treat the external switcher as the source of truth.
- Quit Codex Desktop before switching providers.
- Keep project history unified under the `custom` provider bucket.
- Keep API keys outside the repository. Use environment variables or your local
  provider manager.
- Route local models through the bridge on `127.0.0.1:19030`; the raw
  llama.cpp server stays behind it on `127.0.0.1:19031`.

## Quick Start

1. Install locally:

   ```sh
   python3 -m pip install -e .
   ```

2. Copy an example config:

   ```sh
   mkdir -p ~/.codex-hybrid-model-switcher
   cp config/examples/config.macos.example.json ~/.codex-hybrid-model-switcher/config.json
   ```

3. Edit paths and provider endpoints in that private config.

4. Check the environment:

   ```sh
   codex-hybrid-switcher doctor --config ~/.codex-hybrid-model-switcher/config.json
   ```

5. Run the bridge in one terminal:

   ```sh
   codex-hybrid-switcher bridge --config ~/.codex-hybrid-model-switcher/config.json
   ```

6. Run local bridge smoke tests in another terminal:

   ```sh
   codex-hybrid-switcher smoke --config ~/.codex-hybrid-model-switcher/config.json
   ```

7. Switch providers only after Codex Desktop is fully closed:

   ```sh
   codex-hybrid-switcher switch cpamc-gpt-5-5 --config ~/.codex-hybrid-model-switcher/config.json
   ```

## Commands

```sh
python -m codex_hybrid_switcher status
python -m codex_hybrid_switcher doctor
python -m codex_hybrid_switcher bridge
python -m codex_hybrid_switcher smoke
python -m codex_hybrid_switcher menu
python -m codex_hybrid_switcher switch <provider-id>
```

## What This Repository Must Not Contain

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- API keys, bearer tokens, refresh tokens, or passwords
- personal backups, cleanup quarantine folders, or runtime logs
- machine-specific private paths except inside example placeholders

See `docs/safety.md` before adapting this to a real Codex installation.
