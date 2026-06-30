# GitHub Labels and Community Setup

This document defines the recommended public issue labels and community
categories for the repository.

The labels are written as a source-of-truth checklist. They can be created
manually in GitHub repository settings or later synced by a maintenance script.
Do not add a script that mutates repository settings unless it supports dry-run
first.

## Recommended Labels

| Label | Color | Description |
| --- | --- | --- |
| `setup-help` | `#0ea5e9` | Help with installation, config generation, or first dry-run. |
| `windows` | `#2563eb` | Windows launcher, PowerShell, or Windows Codex behavior. |
| `macos` | `#64748b` | macOS launcher, shell, or macOS Codex behavior. |
| `local-llama` | `#16a34a` | Local llama.cpp, GGUF, mmproj, or GPU smoke tests. |
| `provider-config` | `#9333ea` | OpenAI-compatible provider configuration and routing. |
| `security` | `#dc2626` | Safety boundary, secret handling, or sensitive-data reporting. |
| `docs` | `#f59e0b` | Documentation, screenshots, tutorials, and examples. |
| `good-first-issue` | `#22c55e` | Small, well-scoped tasks suitable for new contributors. |
| `bug` | `#ef4444` | Confirmed defect in source, scripts, tests, or docs. |
| `enhancement` | `#8b5cf6` | Feature request or improvement proposal. |

## Suggested Discussion Categories

- **Setup Help**: installation, dry-run, config validation, launcher questions.
- **Provider Recipes**: sanitized provider templates and compatibility notes.
- **Local Models**: llama.cpp, GGUF, mmproj, GPU, and smoke-test reports.
- **Show and Tell**: safe screenshots, demos, and workflow write-ups.
- **Roadmap Ideas**: GUI, packaging, config wizard, and recovery diagnostics.

## Maintainer Rules

- Move sensitive reports to the process described in `SECURITY.md`.
- Ask users to sanitize screenshots before attaching them.
- Do not request `auth.json`, `models_cache.json`, `state_5.sqlite`, session
  files, API keys, private endpoints, or local model files in public issues.
- When triaging local llama.cpp problems, separate hardware limitations from
  switcher defects.
- When a report involves real Codex state, start with dry-run output and file
  hashes rather than raw account files.
