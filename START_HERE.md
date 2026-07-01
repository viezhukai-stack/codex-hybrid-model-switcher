# Start Here: Hand This Repo to Codex

This page is for a user who only has stock Codex Desktop and wants Codex itself
to configure Codex Hybrid Model Switcher.

If you are starting from the GitHub page and want the shortest copy-paste
prompt, use [`HANDOFF_TO_CODEX.md`](HANDOFF_TO_CODEX.md) first.

The intended workflow is:

1. Open this GitHub repository in Codex.
2. Give Codex the copy-paste prompt below.
3. Let Codex create a private config and run dry-run first.
4. Quit Codex Desktop only when Codex asks for the real guarded switch.
5. Reopen Codex Desktop and test a new conversation.
6. Ask Codex to generate the redacted setup report.
7. Ask Codex to generate canary evidence and the real clean-machine canary
   template.
8. Ask Codex to run `final-check` and generate `codex-hybrid-final-check.md`.
9. Use `docs/user-success-criteria.md` to confirm the setup is really done.
10. Use `FINAL_CHECK.md` for Codex's final completion verdict.

## Copy This Prompt Into Codex

Replace the placeholder values first. Do not paste a raw API key into this
prompt.

```text
请按照这个仓库的 START_HERE.md 和 AGENTS.md，帮我安全配置 Codex Hybrid Model Switcher。

最终目标：
- 我只有原版 Codex Desktop。
- 我想让 Codex Desktop 使用一个 OpenAI-compatible 云端模型。
- 必须保留 Codex 登录状态、插件、MCP、项目列表和已有对话可见性。
- 不要修改 auth.json、models_cache.json、state_5.sqlite、sessions 或 rollout 日志。
- 不要安装 LaunchAgent、KeepAlive、计划任务、恢复循环或后台自启动服务。
- 先只做云端模型；本地 llama.cpp 等云端成功后再单独处理。

我的 provider 信息：
- base_url: <填你的 OpenAI-compatible endpoint，例如 https://example.com/v1>
- model: <填模型 ID，例如 provider-gpt-main>
- api_key_env: <填保存 API key 的环境变量名，不要填 API key 原文>
- cloud_route: bridge（默认；Codex 连本机 bridge，bridge 用 api_key_env 转发到 provider）

请先：
1. 检查仓库和当前系统环境。
2. 优先运行 bootstrap.py。
3. 生成用户目录里的私有 config.json。
4. 运行 validate-config。
5. 如果看到 `api_key_env(...unset)`，运行 env-help 并告诉我怎么设置环境变量。
6. 如果使用 bridge 路由，运行 bridge-health，告诉我 bridge、key、模型列表目前是什么状态。
7. 运行 guarded-switch --dry-run。
8. 用人话解释 dry-run 会改什么、不会改什么。

只有 dry-run 安全后，再让我完全退出 Codex Desktop，然后再执行真实 guarded-switch。
真实切换后，请验证受保护文件 hash 没变，并生成脱敏 setup report。
```

## What Codex Should Do First

Codex should start with bootstrap because it does not require package
installation. On Windows, first check whether Python exists. If `py -3` is
missing, use `scripts/bootstrap-windows.ps1`; it can install Python 3.12 with
`winget` and then continue to the same dry-run flow.

Beginner Windows route:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1 `
  -BaseUrl https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 `
  -Model provider-gpt-main `
  -ApiKeyEnv OPENAI_COMPATIBLE_API_KEY `
  -CloudRoute bridge
```

The Windows bootstrap stops at `guarded-switch --dry-run`. It does not apply a
real switch.

Manual bootstrap commands:

macOS:

```sh
python3 bootstrap.py
```

Windows:

```powershell
py -3 bootstrap.py
```

If all provider details are already known, Codex may use non-interactive
bootstrap:

macOS:

```sh
python3 bootstrap.py --non-interactive \
  --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 \
  --model provider-gpt-main \
  --api-key-env OPENAI_COMPATIBLE_API_KEY \
  --cloud-route bridge
```

Windows:

```powershell
py -3 bootstrap.py --non-interactive `
  --platform windows `
  --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 `
  --model provider-gpt-main `
  --api-key-env OPENAI_COMPATIBLE_API_KEY `
  --cloud-route bridge
```

`bridge` is the beginner default. It writes Codex to `127.0.0.1:19030` and lets
the local bridge forward to the real provider using `api_key_env`. Use
`--cloud-route direct` only when the provider is known to work with Codex
Desktop's own custom-provider authentication path.

## Safe Milestones

First milestone, before any real switch:

- private config exists outside this repository
- config validation passes
- `api_key_env` is set, or Codex has shown the env-help instructions needed to
  set it
- for `cloud_route=bridge`, `bridge-health` has either passed or clearly
  explained that the bridge can be started during guarded apply
- guarded dry-run prints a redacted diff
- no real Codex files changed
- for `cloud_route=bridge`, the API key environment variable is set before the
  real switch

Real switch milestone:

- Codex Desktop was fully quit before the write
- only `config.toml` was changed
- a `config.toml.bak-codex-hybrid-*` backup exists
- `auth.json`, `models_cache.json`, `state_5.sqlite`, `sessions/`, and rollout
  logs are unchanged

Final user-visible milestone:

- Codex Desktop opens
- account information is still visible
- plugins/MCP/project list are still visible
- a new test conversation responds
- a redacted setup report exists
- a redacted canary evidence report exists
- a real clean-machine canary template exists
- a read-only final check report exists
- if a bridge-routed test chat does not reply, `bridge-health` has been run and
  its next steps have been followed
- the user success checklist in `docs/user-success-criteria.md` has been
  reviewed
- the final check in `FINAL_CHECK.md` reports `Complete`

## Stop Conditions

Stop and ask the user before continuing if any of these happen:

- Codex Desktop is still running during a real switch
- dry-run wants to edit anything beyond provider/model settings
- any command attempts to edit `auth.json`, `models_cache.json`,
  `state_5.sqlite`, `sessions/`, or rollout logs
- a script tries to install autostart, KeepAlive, recovery loops, or scheduled
  tasks
- the user wants old official conversations migrated into another provider
  bucket

History migration is intentionally outside the default setup. Existing official
conversations may look separate after switching providers; that is visibility
bucket behavior, not deletion.

## After Setup

Generate a redacted report:

```sh
python3 -m codex_hybrid_switcher setup-report \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --output ~/Desktop/codex-hybrid-setup-report.md
```

If the package was not installed, run from the repository:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher setup-report \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --output ~/Desktop/codex-hybrid-setup-report.md
```

Review the report before sharing it publicly. It is designed to redact
endpoints, paths, tokens, account data, and full hashes, but human review is
still part of the safety process.

After reopening Codex Desktop and confirming account, plugins/MCP, project
list, and a responding test chat, record final canary evidence:

```sh
python3 -m codex_hybrid_switcher canary-report \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --provider-id cloud-gpt-main \
  --account-visible yes \
  --plugins-visible yes \
  --mcp-visible yes \
  --project-list-visible yes \
  --test-chat-responded yes \
  --bridge-health-passed yes \
  --setup-report-reviewed yes \
  --verdict complete \
  --output ~/Desktop/codex-hybrid-canary-evidence.md
```

Generate the real clean-machine canary checklist:

```sh
python3 -m codex_hybrid_switcher real-canary-template \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --provider-id cloud-gpt-main \
  --setup-report ~/Desktop/codex-hybrid-setup-report.md \
  --canary-report ~/Desktop/codex-hybrid-canary-evidence.md \
  --output ~/Desktop/codex-hybrid-real-clean-machine-canary.md
```

Then use [`docs/user-success-criteria.md`](docs/user-success-criteria.md) to
decide whether setup is complete or only partially complete.

Generate the read-only final check:

```sh
python3 -m codex_hybrid_switcher final-check \
  --config ~/.codex-hybrid-model-switcher/config.json \
  --setup-report ~/Desktop/codex-hybrid-setup-report.md \
  --canary-report ~/Desktop/codex-hybrid-canary-evidence.md \
  --real-canary-template ~/Desktop/codex-hybrid-real-clean-machine-canary.md \
  --output ~/Desktop/codex-hybrid-final-check.md
```

Finally, copy the prompt in [`FINAL_CHECK.md`](FINAL_CHECK.md) into Codex and
ask for a final verdict.

## If Codex Needs A Safe Rehearsal

Before touching a real Codex profile, Codex can run the simulated handoff drill:

```sh
python3 scripts/validate-agent-handoff-drill.py
```

This uses a temporary stock-like Codex home and proves the repository path can
reach setup report, canary evidence, and final verdict guidance without editing
the real profile.

## If The API Key Variable Is Unset

Ask Codex to run:

```sh
python3 -m codex_hybrid_switcher env-help --config ~/.codex-hybrid-model-switcher/config.json
```

If running from the repository without installing:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher env-help --config ~/.codex-hybrid-model-switcher/config.json
```

The command prints OS-specific setup instructions. It does not ask for, print,
or store the API key.

## If A Bridge-Routed Test Chat Does Not Reply

Ask Codex to run:

```sh
python3 -m codex_hybrid_switcher bridge-health --config ~/.codex-hybrid-model-switcher/config.json
```

If running from the repository without installing:

```sh
PYTHONPATH=src python3 -m codex_hybrid_switcher bridge-health --config ~/.codex-hybrid-model-switcher/config.json
```

This checks the bridge port, `/v1/health`, `/v1/models`, expected model ids, and
`api_key_env` status without editing Codex files.
