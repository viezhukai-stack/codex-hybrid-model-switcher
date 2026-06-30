# Release Post Kit

Use these templates when sharing the project publicly. Keep all examples
sanitized. Do not include real endpoints, local paths, account state, or private
provider names.

## Short English Post

I released **Codex Hybrid Model Switcher**, a source-only tool for safely trying
OpenAI-compatible cloud providers and optional local llama.cpp models with Codex
Desktop.

The main design goal is boring safety:

- dry-run first
- back up `config.toml`
- do not edit `auth.json`
- do not edit `models_cache.json`
- do not edit `state_5.sqlite`
- no autostart or recovery-loop services

It is built for people who want provider switching without hand-editing fragile
Codex Desktop state.

Repo: https://github.com/viezhukai-stack/codex-hybrid-model-switcher

## Short Chinese Post

我开源了 **Codex Hybrid Model Switcher**，一个用于 Codex Desktop 的混合模型切换工具。

它的重点不是“魔法一键接管”，而是安全、可回滚：

- 先 dry-run 看脱敏 diff
- 真实切换前备份 `config.toml`
- 不改 `auth.json`
- 不改 `models_cache.json`
- 不改 `state_5.sqlite`
- 不安装常驻服务或循环恢复脚本

适合想在 Codex Desktop 里尝试 OpenAI-compatible 云端 provider，或者在合适硬件上接入本地 llama.cpp 模型的人。

项目地址：https://github.com/viezhukai-stack/codex-hybrid-model-switcher

## Longer English Launch Note

Codex Desktop keeps important state around account login, plugins, MCP servers,
projects, model cache, and conversations. That makes custom-provider
experiments risky when they rely on manual edits or background scripts.

Codex Hybrid Model Switcher takes a narrower approach:

1. Generate a private local config.
2. Validate it with redacted output.
3. Preview the planned Codex config diff.
4. Quit Codex Desktop.
5. Apply a guarded provider switch.
6. Reopen Codex and test in a new conversation.

The tool is source-only for now. It is most useful for advanced users who want a
recoverable workflow, not a black-box installer.

## Suggested Channels

- GitHub release notes
- project README
- personal blog
- X / LinkedIn
- Reddit communities that allow developer tools
- Chinese technical communities

## Safe Screenshot Checklist

Before posting screenshots, remove or blur:

- account names and emails
- provider hosts
- keys or tokens
- private local paths
- LAN IPs
- conversation contents
- model files that reveal private folder layouts
