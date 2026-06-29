# Windows Notes

- Desktop launcher extension: `.cmd`
- Typical Codex home: `%USERPROFILE%\.codex`
- Typical CC Switch home: `%USERPROFILE%\.cc-switch`
- CUDA llama.cpp builds usually live outside the repository on a data drive.

Use `config/examples/config.windows.example.json` as the starting point.

For the first real cloud-provider verification on Windows, use one canary
machine and follow `docs/windows-cloud-canary.md`. That workflow only tests a
cloud provider and does not start local llama.cpp.

For local llama.cpp validation, follow `docs/local-llama-smoke.md`. The Windows
example config assumes a user-managed CUDA llama.cpp path outside the repository.

After cloud and local canaries pass, use `docs/windows-user-flow.md` for regular
provider switching.

To prove the workflow is portable, repeat the guarded validation on a second
Windows machine with `docs/windows-second-canary.md`. Do this before treating a
desktop launcher as the normal user-facing entry point on a new machine.
