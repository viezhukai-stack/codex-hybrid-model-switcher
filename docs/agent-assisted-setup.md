# Agent-assisted setup

This page is for users who have a stock Codex Desktop install and want to hand
this repository to Codex itself.

The short version:

1. Open this repository in Codex.
2. Start with the root `START_HERE.md` prompt.
3. Ask Codex to follow `AGENTS.md`.
4. Provide your provider details.
5. Let Codex run setup, validation, and dry-run first.
6. Quit Codex Desktop only when Codex asks you to perform the real switch.

## Copy-paste prompt for Codex

Use this prompt after opening the repository in Codex:

```text
请按照这个仓库根目录的 AGENTS.md 帮我配置 Codex Hybrid Model Switcher。

我的目标：
- 保留 Codex 登录状态、插件、MCP 和项目对话。
- 先只配置一个 OpenAI-compatible 云端模型。
- 不要修改 auth.json、models_cache.json、state_5.sqlite 或 sessions。
- 不要安装后台自启动服务。
- 优先用 bootstrap.py 生成私有配置并 dry-run。
- 确认安全后再让我退出 Codex 并执行真实切换。

我的 provider 信息：
- base_url: <填你的 OpenAI-compatible endpoint，例如 https://example.com/v1>
- model: <填模型 ID>
- api_key_env: <填保存 API key 的环境变量名，不要填 API key 原文>

请先检查环境并生成私有配置，然后把 dry-run 结果解释给我。
```

Replace the angle-bracket placeholders before sending it.

## What Codex should do

Codex should:

- run `bootstrap.py` first when possible
- install this package locally only if bootstrap cannot run
- generate `~/.codex-hybrid-model-switcher/config.json`
- validate the private config
- run `guarded-switch --dry-run`
- explain the redacted diff
- ask you to quit Codex Desktop before a real switch
- run guarded apply only after you confirm Codex Desktop is fully quit
- verify protected Codex files did not change
- generate a redacted setup report after the real switch

Codex should not:

- ask you to paste a raw API key into repository files
- edit `auth.json`
- edit `models_cache.json`
- edit `state_5.sqlite`
- edit session files
- install recovery loops, LaunchAgents, KeepAlive jobs, or scheduled tasks
- force local llama.cpp setup before cloud setup works

## Information you need before starting

For cloud models:

- provider `base_url`
- model id
- environment variable name that contains your API key

For local llama.cpp later:

- `llama-server` path
- GGUF model path
- mmproj path for image-capable models
- enough CPU/GPU/RAM/VRAM for the model

## Expected first milestone

The first milestone is not "everything is switched." The first milestone is:

- private config generated
- validation passed
- dry-run diff is safe and redacted
- no real Codex files changed

Only after that should you let Codex perform a real switch.

## Final report

After a real switch and a new test conversation, ask Codex to generate:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher setup-report \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --output ~/Desktop/codex-hybrid-setup-report.md
```

The report is redacted by design. Still review it before sharing it publicly.

## Bootstrap shortcut

If you already know the provider details, Codex can start with:

```sh
python3 bootstrap.py --non-interactive \
  --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 \
  --model provider-gpt-main \
  --api-key-env OPENAI_COMPATIBLE_API_KEY
```

On Windows, use `py -3 bootstrap.py ...`.

## About old project conversations

Stock Codex usually stores official conversations under the `openai` provider
bucket. Third-party providers use the `custom` bucket in this project.

If old conversations look separate after switching, that does not mean they
were deleted. This project intentionally does not rewrite history databases.
Ask for a separate backed-up history repair only if you really need it.
