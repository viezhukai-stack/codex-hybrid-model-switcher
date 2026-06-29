# Windows Notes

- Desktop launcher extension: `.cmd`
- Typical Codex home: `%USERPROFILE%\.codex`
- Typical CC Switch home: `%USERPROFILE%\.cc-switch`
- CUDA llama.cpp builds usually live outside the repository on a data drive.

Use `config/examples/config.windows.example.json` as the starting point.

For the first real cloud-provider verification on Windows, use one canary
machine and follow `docs/windows-cloud-canary.md`. That workflow only tests a
cloud provider and does not start local llama.cpp.
