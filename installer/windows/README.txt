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
12. After setup, use Start Codex Hot Router.cmd on the Desktop for normal daily launches. The shortcut uses a stable current-release pointer instead of one permanently embedded release path. It checks for a staged Microsoft Store update, waits for three identical Store observations, completes the current-user AppX registration while Codex is closed, waits again for a newly staged build, and allows at most two registration passes. If Store registration fails but the matching official package is already staged locally, it registers that package for the current user and continues. It then refreshes the complete matching CLI bundle and the current AppX Browser/Chrome marketplace, checks the lightweight local bridge on 127.0.0.1:19030, starts the hot router on 127.0.0.1:19032, and opens Codex. A healthy installation takes the fast path. After Codex feature initialization, one bounded background check verifies Browser again; it never restarts Codex.
13. Use Codex Model Switcher.cmd only for guarded maintenance switches.
14. To return to official Codex, double-click Restore Official Codex.cmd.
15. If the daily launcher's automatic update transaction stops after a Codex update, fully quit Codex and double-click Repair Codex Update and Plugins.cmd. It completes the official Store registration, copies the complete matching CLI bundle, refreshes the current AppX marketplace, and restores Browser/Chrome through the official Codex CLI. Repair Codex Browser and CLI.cmd remains the narrower CLI-only fallback.
16. If Codex Live does not start, double-click Repair Codex Live Audio.cmd. It checks microphone consent and default recording roles without writing; type REPAIR only after Codex is fully closed, or RESTORE to restore the latest audio backup.
17. To change the ChatGPT account, fully quit Codex and double-click Change Codex Account.cmd. It uses device-code login and a local transaction backup.
18. If setup fails, double-click Codex Hybrid Diagnostics.cmd and send the generated diagnostics text file.

This package does not install CC Switch. It includes this project's own guarded external switcher.
In hot-router mode, Codex's bottom-right model selector is the source of truth. In maintenance mode, Codex Model Switcher.cmd is the source of truth.

Normal setup and routing never edit auth.json. The optional account switch uses the official Codex login command after an explicit confirmation and local backup.

Never upload or share auth.json, account-switch backups, models_cache.json, state_5.sqlite, sessions, rollout logs, API keys, or screenshots containing secrets.
