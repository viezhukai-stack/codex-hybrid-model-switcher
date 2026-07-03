Codex Hybrid macOS 小白安装说明
==============================

1. 先安装并登录原版 Codex Desktop。
   官方页面：https://developers.openai.com/codex/app
2. 把整个 zip 解压出来，不要在压缩包预览里直接运行。
3. 如果你要预填云端模型信息，可以把 provider-preset.example.json 复制成
   provider-preset.json，然后填写 base_url、model、api_key_env。不要把 API key
   明文写进这个文件。
4. 双击 Install Codex Hybrid.command。
5. 安装器会创建私有配置、检查配置、执行安全 dry-run，并在桌面安装
   Codex Model Switcher.command。
6. 只有 dry-run 通过、Codex 完全退出、并且你输入 APPLY 后，才会真实切换。
7. 如果你想让旧的官方项目对话在切到 custom/local-gemma 后仍可见，可以按提示
   输入 MIGRATE。安装器会先 dry-run，真实迁移前会备份历史数据库和相关会话文件。

需要 Python 3.10 或更高版本。如果电脑没有 Python，安装器会打开官方 macOS
Python 下载页，并提示安装完成后重新双击安装器。本包默认不内置 Python。

轻量 macOS 包是云端版：
- 不包含本地 GGUF 模型。
- 不包含 llama.cpp。

完整本地 macOS 包会包含 payload/models/local-gemma 和 payload/llama.cpp：
- 不需要云端 API key。
- 不需要手动选择 GGUF/mmproj。
- 会先复制本地模型并通过 local smoke 后再允许切换。

所有 macOS 包都不安装 CC Switch，不包含 API key，也不包含原版 Codex 应用。

正常模型切换不会修改这些受保护文件：
- auth.json
- models_cache.json
- sessions 和 rollout logs

只有你明确输入 MIGRATE 启用历史统一时，才会在备份后迁移 state_5.sqlite 和相关
session 元数据，用来避免左侧项目对话因为 provider 桶不同而看不见。
