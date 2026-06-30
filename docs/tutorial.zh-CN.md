# 中文上手教程

这篇教程面向第一次使用 **Codex Hybrid Model Switcher** 的中文用户。
目标是让你把 Codex Desktop 切到一个 OpenAI-compatible 云端 provider，
同时尽量保留原有账号状态、插件、MCP 配置和项目对话可见性。

如果你只想先看一个不会改真实 Codex 的演示，请先读
[`quickstart-demo.md`](quickstart-demo.md)。

## 这个项目解决什么问题

Codex Desktop 本身有自己的账号、插件、项目和对话历史。直接改模型缓存、
历史库或启动后台恢复脚本很容易把桌面端弄坏。

这个项目采用更保守的方式：

- 只把外部模型切换写进 Codex 的 `config.toml`。
- 不改 `auth.json`。
- 不改 `models_cache.json`。
- 不改 `state_5.sqlite`。
- 不安装 LaunchAgent、KeepAlive、计划任务或自动重启脚本。
- 真正写配置前先做 `--dry-run`，确认只会改 provider/model 相关内容。

换句话说，它追求的是“能切换、能回滚、尽量不破坏 Codex 现有状态”。

## 适合谁

你适合使用它，如果你想：

- 在 Codex Desktop 中使用 OpenAI-compatible 云端模型。
- 在支持的机器上接入本地 llama.cpp 模型。
- 切换模型时保留 Codex 账号、插件、MCP 和项目对话。
- 用一个可审计、可回滚的工具替代手工改配置。

你不适合一上来就用它做真实切换，如果你：

- 还没有备份重要配置。
- 不清楚当前 Codex 是否能正常打开。
- 想直接改 Codex 右下角原生模型菜单。
- 想把 API key、真实 endpoint 或本地模型文件提交到仓库。

## 安装前准备

你需要：

- Python 3.10、3.11 或 3.12。
- 可以正常打开的 Codex Desktop。
- 一个 OpenAI-compatible provider。
- provider 的 API key，放在环境变量或你的本机私有配置中。
- 可选：本地 llama.cpp、GGUF 模型和 mmproj 文件。

不要把下面这些文件复制到本仓库，也不要发到 issue：

- `auth.json`
- `models_cache.json`
- `state_5.sqlite`
- `sessions/`
- API key、token、密码
- 本地模型文件
- 私有 endpoint、局域网 IP、真实机器路径

## 第一步：优先使用 bootstrap

从 GitHub clone 后，在项目目录中运行：

```sh
python3 bootstrap.py
```

`bootstrap.py` 不需要先安装项目。它会直接从仓库里运行：

- 生成本机私有配置。
- 校验配置。
- 执行 guarded dry-run。
- 提示下一步真实切换命令。

如果你已经知道 provider 信息，可以这样：

```sh
python3 bootstrap.py --non-interactive \
  --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 \
  --model provider-gpt-main \
  --api-key-env OPENAI_COMPATIBLE_API_KEY
```

Windows 使用：

```powershell
py -3 bootstrap.py
```

## 备用方式：安装项目后使用命令

```sh
python3 -m pip install -e .
```

如果你要参与开发或跑测试，可以安装开发依赖：

```sh
python3 -m pip install -e ".[dev]"
```

## 第二步：先跑隔离安装验收

在碰真实 Codex 配置之前，先运行：

```sh
python3 scripts/validate-install.py
```

这个脚本会创建一个临时目录，安装项目、运行测试、安全扫描，并用模拟的
`config.toml` 跑 dry-run。它不会修改你的真实 Codex 配置。

看到类似下面结果才继续：

```text
42 passed
No sensitive-looking content found.
install validation passed
```

## 第三步：用首次向导生成私有配置

推荐新用户先用向导：

```sh
codex-hybrid-switcher setup
```

这个命令只会生成你的本机私有配置，不会切换 Codex，也不会改
`~/.codex/config.toml`。

它会问你：

- Codex 配置目录。
- 云端 provider 名称。
- OpenAI-compatible `base_url`。
- 模型 ID。
- API key 的环境变量名。
- 是否现在就添加本地 llama.cpp 模型。

第一次使用建议先不要添加本地 llama.cpp 模型。先把云端 provider 跑通，
再单独处理本地模型。

如果你不想交互输入，也可以这样：

```sh
codex-hybrid-switcher setup --non-interactive \
  --base-url https://YOUR-OPENAI-COMPATIBLE-ENDPOINT.example/v1 \
  --model provider-gpt-main \
  --api-key-env OPENAI_COMPATIBLE_API_KEY
```

注意：`--api-key-env` 填的是环境变量名，不是 API key 原文。

## 备用方式：复制示例配置

macOS 示例：

```sh
codex-hybrid-switcher init-config --platform macos --output ~/.codex-hybrid-model-switcher/config.json
```

Windows 示例：

```powershell
codex-hybrid-switcher init-config --platform windows --output "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
```

无论用向导还是复制示例，生成的 `config.json` 都是你的本机私有配置，
不要提交到 Git。

你需要编辑里面的字段，例如：

- `codex_home`
- `providers`
- `base_url`
- `model`
- `api_key_env`
- `local_model.llama_server_path`
- `local_model.model_path`
- `local_model.mmproj_path`

API key 推荐放到环境变量，比如：

```sh
export OPENAI_COMPATIBLE_API_KEY="replace-with-your-provider-key"
```

Windows PowerShell：

```powershell
$env:OPENAI_COMPATIBLE_API_KEY = "replace-with-your-provider-key"
```

## 第四步：验证私有配置

```sh
codex-hybrid-switcher validate-config --config ~/.codex-hybrid-model-switcher/config.json
```

输出会隐藏 provider host 和本地路径。你应该重点看：

- provider 是否都能识别。
- `codex_home` 是否指向正确目录。
- 本地模型路径是否只是警告，还是你这次必须使用的路径。

如果你只测试云端 provider，本地 llama.cpp 路径缺失不是阻塞项。

## 第五步：先 dry-run，不要直接切换

云端 provider 示例：

```sh
codex-hybrid-switcher guarded-switch cloud-gpt-main --dry-run --config ~/.codex-hybrid-model-switcher/config.json
```

你应该看到一个已脱敏 diff，类似：

```diff
-model_provider = "openai"
-model = "gpt-5.5"
+model_provider = "custom"
+model = "provider-gpt-main"

 [model_providers.custom]
 name = "<redacted>"
 base_url = "<redacted>"
 wire_api = "responses"
```

如果 diff 删除了插件、MCP、projects 或其他无关配置，停止，不要真实切换。

## 第六步：真实切换前退出 Codex Desktop

真实写入前，先完全退出 Codex Desktop。

不要在 Codex 正在运行时切换 provider。这样做是为了避免桌面端还在读写配置，
造成状态不一致。

确认 Codex 已退出后再运行：

```sh
codex-hybrid-switcher guarded-switch cloud-gpt-main --config ~/.codex-hybrid-model-switcher/config.json
```

`guarded-switch` 会做几件事：

- 记录受保护文件的 hash。
- 备份 `config.toml`。
- 只写 provider/model 相关配置。
- 再次检查 `auth.json`、`models_cache.json`、`state_5.sqlite` 没有变化。

## 第七步：重新打开 Codex Desktop 测试

打开 Codex Desktop 后检查：

- 账号信息还在。
- 插件和 MCP 入口还在。
- 左侧项目对话还在。
- 新建测试聊天能正常回复。

不要用重要历史线程做第一条测试。先新建一个测试聊天。

## 第八步：生成脱敏配置报告

测试正常后，生成一份可以自己保存或发给别人排查问题的脱敏报告：

```sh
codex-hybrid-switcher setup-report --config ~/.codex-hybrid-model-switcher/config.json --output ~/Desktop/codex-hybrid-setup-report.md
```

这份报告会隐藏 provider host、本机路径、账号 token、session 内容和数据库内容。
但你在公开分享前仍然应该自己看一眼。

## 本地 llama.cpp 模型怎么接

本地模型是可选能力，取决于机器 GPU、驱动、CUDA、模型大小和 mmproj 文件。

先跑 smoke test：

```sh
codex-hybrid-switcher local-smoke --config ~/.codex-hybrid-model-switcher/config.json
```

只有 smoke test 通过后，才允许真实切到本地 provider：

```sh
codex-hybrid-switcher guarded-switch local-gemma --allow-local --config ~/.codex-hybrid-model-switcher/config.json
```

如果本地模型太慢、显存不够、缺少 CUDA 或缺少 mmproj，这不是项目本身失败。
换一台机器或换更小的模型即可。

## 如何回滚

如果切换后 Codex 表现异常：

1. 完全退出 Codex Desktop。
2. 找到最新备份：

   ```text
   config.toml.bak-codex-hybrid-*
   ```

3. 把它恢复为 `config.toml`。
4. 重新打开 Codex。

这个项目设计上不会改 `auth.json`、`models_cache.json` 或 `state_5.sqlite`。
大多数问题都应该能通过恢复 `config.toml` 回滚。

## 常见误区

### Codex 右下角模型显示不变，是不是没切成功？

不一定。这个项目把外部 switcher 和 `config.toml` 作为真实来源。
Codex 右下角模型标签可能是旧的、泛化的或不可完全代表当前 provider。

### 可以直接改 `models_cache.json` 吗？

不建议。本项目明确不改它。过去很多桌面端异常都来自缓存、历史库或运行时状态被硬改。

### 能不能把 provider 配置提交到 GitHub？

不要提交真实 endpoint、API key、本地路径或机器信息。只提交占位示例。

### 本地模型一定要测吗？

不一定。云端 provider 和本地 provider 是两条路径。
本地模型依赖硬件，不应该阻塞云端 provider 使用。

## 下一步

- 想了解安全边界：读 [`safety.md`](safety.md)。
- 想看恢复流程：读 [`recovery.md`](recovery.md)。
- 想看 Windows 新手流程：读 [`windows-user-flow.md`](windows-user-flow.md)。
- 想看本地模型：读 [`local-llama-smoke.md`](local-llama-smoke.md)。
