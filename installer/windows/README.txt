Codex Hybrid Model Switcher - Windows netdisk one-click setup

1. Double-click Install Codex Hybrid.cmd.
2. If Codex Desktop is not installed or not signed in, the installer opens the official Codex app page. Install Codex, sign in, close Codex, then run this installer again.
3. The netdisk package includes the project payload and portable Python, so it does not need Git or a GitHub project download. Most computers do not need a separate Python install.
4. If portable Python is missing from the package, the installer can still install Python 3.12 with winget.
5. If provider-preset.json exists next to the installer, its base URL, model id, and API key environment variable name are prefilled.
6. Full local model packages may include payload\models\local-gemma. In that case the installer copies the bundled GGUF model and mmproj file into local app data and uses that stable path.
7. If no cloud base URL is provided and a bundled local model exists, the installer continues in local-only mode. No API key is required.
8. If you want cloud models, enter your OpenAI-compatible provider base URL, model id, API key environment variable name, and API key when prompted.
9. For local models without a bundled model payload, choose your own GGUF model file and mmproj file.
10. The installer uses bundled llama.cpp if payload\llama.cpp contains llama-server.exe; otherwise it downloads llama.cpp from the official ggml-org GitHub releases when local model files are selected.
11. The default run stops at dry-run. After dry-run, you can type APPLY to apply only after Codex Desktop is fully closed.
12. After setup, use Start Codex Hot Router.cmd on the Desktop for normal daily launches. It checks the lightweight local bridge on 127.0.0.1:19030, starts the hot router on 127.0.0.1:19032, then opens Codex.
13. Use Codex Model Switcher.cmd only for guarded maintenance switches.
14. To return to official Codex, double-click Restore Official Codex.cmd.
15. If setup fails, double-click Codex Hybrid Diagnostics.cmd and send the generated diagnostics text file.

This package does not install CC Switch. It includes this project's own guarded external switcher.
In hot-router mode, Codex's bottom-right model selector is the source of truth. In maintenance mode, Codex Model Switcher.cmd is the source of truth.

Never upload or share auth.json, models_cache.json, state_5.sqlite, sessions, rollout logs, API keys, or screenshots containing secrets.
