Codex Hybrid Model Switcher - Windows netdisk one-click setup

1. Double-click Install Codex Hybrid.cmd.
2. If Codex Desktop is not installed or not signed in, the installer opens the official Codex app page. Install Codex, sign in, close Codex, then run this installer again.
3. The installer can install Python 3.12 with winget if Python is missing.
4. The project source is bundled in payload\codex-hybrid-model-switcher, so this package does not need Git or a GitHub project download.
5. If provider-preset.json exists next to the installer, its base URL, model id, and API key environment variable name are prefilled.
6. Enter your OpenAI-compatible provider base URL, model id, API key environment variable name, and API key when prompted.
7. For local models, choose your own GGUF model file and mmproj file. This package does not include model files.
8. The installer uses bundled llama.cpp if payload\llama.cpp contains llama-server.exe; otherwise it downloads llama.cpp from the official ggml-org GitHub releases when local model files are selected.
9. The default run stops at dry-run. After dry-run, you can type APPLY to apply only after Codex Desktop is fully closed.
10. If setup fails, double-click Codex Hybrid Diagnostics.cmd and send the generated diagnostics text file.

Never upload or share auth.json, models_cache.json, state_5.sqlite, sessions, rollout logs, API keys, or screenshots containing secrets.
