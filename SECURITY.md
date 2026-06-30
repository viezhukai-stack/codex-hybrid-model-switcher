# Security Policy

This project changes Codex provider configuration and may route requests through
local or OpenAI-compatible endpoints. Treat all security issues seriously,
especially anything that could expose account state, provider credentials, model
traffic, local files, or Codex history.

## Supported Versions

Security reports are accepted for the latest tagged release and the current
`main` branch.

## Reporting a Vulnerability

For now, report privately through the repository owner's preferred private
channel. Do not open a public issue that includes:

- API keys or bearer tokens
- account files
- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- session transcripts
- private provider endpoints
- private LAN IPs or hostnames

If you can reproduce the issue without sensitive data, include:

- operating system and Python version
- command used
- redacted config snippet
- expected behavior
- actual behavior
- whether Codex Desktop was running

## Security Boundaries

The project must not:

- edit `auth.json`
- edit `models_cache.json`
- edit `state_5.sqlite`
- mutate Codex sessions or rollout logs
- install KeepAlive services, recovery loops, LaunchAgents, or scheduled
  auto-restart tasks
- commit private config, credentials, runtime logs, or local model files

Real provider switches must use guarded flows that dry-run first, back up
`config.toml`, and hash protected Codex files before and after apply.

## Secret Handling

Provider keys belong in environment variables or private machine-local config
outside the repository. The repository should contain placeholders only.

Run before sharing or publishing:

```sh
python -m codex_hybrid_switcher security-scan .
```
