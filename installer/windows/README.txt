Codex Hybrid Model Switcher - Windows netdisk one-click setup

1. Double-click Install Codex Hybrid.cmd.
2. If Codex Desktop is not installed or not signed in, the installer opens the official Codex app page. Install Codex, sign in, close Codex, then run this installer again.
3. The netdisk package includes the project payload and portable Python, so it does not need Git or a GitHub project download. Most computers do not need a separate Python install.
4. If portable Python is missing from the package, the installer can still install Python 3.12 with winget.
5. If provider-preset.json exists next to the installer, its base URL, model id, and API key environment variable name are prefilled.
6. Enter your OpenAI-compatible provider base URL, model id, API key environment variable name, and API key when prompted.
7. If you only want cloud models, skip local model file selection.
8. For local models, choose your own GGUF model file and mmproj file. This package does not include model files.
9. The installer uses bundled llama.cpp if payload\llama.cpp contains llama-server.exe; otherwise it downloads llama.cpp from the official ggml-org GitHub releases when local model files are selected.
10. The default run stops at dry-run. After dry-run, you can type APPLY to apply only after Codex Desktop is fully closed.
11. After setup, use Codex Model Switcher.cmd on the Desktop to switch models.
12. To return to official Codex, double-click Restore Official Codex.cmd.
13. If setup fails, double-click Codex Hybrid Diagnostics.cmd and send the generated diagnostics text file.

This package does not install CC Switch. It includes this project's own guarded external switcher.
Codex's bottom-right model label is not the source of truth; the desktop switcher is.

Never upload or share auth.json, models_cache.json, state_5.sqlite, sessions, rollout logs, API keys, or screenshots containing secrets.
