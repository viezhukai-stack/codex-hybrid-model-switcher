Codex Hybrid Model Switcher - Windows one-click setup

1. Double-click Install Codex Hybrid.cmd.
2. If Codex Desktop is not installed or not signed in, the installer opens the official Codex app page. Install Codex, sign in, close Codex, then run this installer again.
3. The installer can install Python 3.12 with winget if Python is missing.
4. Enter your OpenAI-compatible provider base URL, model id, API key environment variable name, and API key when prompted.
5. For local models, choose your own GGUF model file and mmproj file. This package does not include model files.
6. The installer downloads llama.cpp from the official ggml-org GitHub releases when local model files are selected.
7. The default run stops at dry-run. It does not apply a real Codex switch unless you explicitly pass -Apply and Codex Desktop is fully closed.

Never upload or share auth.json, models_cache.json, state_5.sqlite, sessions, rollout logs, API keys, or screenshots containing secrets.
