Codex Hybrid Model Switcher - Windows 网盘一键安装包

给小白用户的用法：

1. 解压整个 zip，不要只拖出单个文件。
2. 双击 Install Codex Hybrid.cmd。
3. 如果电脑还没安装或登录 Codex，安装器会打开 Codex 官方页面。请先安装 Codex、登录账号、完全关闭 Codex，然后重新双击安装器。
4. 这个网盘包已经内置项目源码和 portable Python，不需要安装 Git，也不需要从 GitHub 下载项目源码。大多数电脑也不需要单独安装 Python。
5. 如果安装器旁边有 provider-preset.json，服务地址、模型名和 API key 环境变量名会自动预填。
6. 完整本地模型包会带有 payload\models\local-gemma，安装器会把里面的 GGUF 模型和 mmproj 视觉模型复制到本机应用数据目录，再使用这个稳定路径，不需要你手动选择文件。
7. 如果没有填写云端服务地址，但包里有本地模型，安装器会自动走本地-only 模式，不需要 API key。
8. 如果你要使用云端模型，再按提示输入 OpenAI-compatible 服务地址、模型名、API key 环境变量名和 API key。API key 只会写入 Windows 用户环境变量，不会写进项目配置文件。
9. 如果不是完整本地模型包，也可以手动选择你自己的 GGUF 模型文件和 mmproj 文件。
10. 如果 payload\llama.cpp 里已经带有 llama-server.exe，安装器会优先使用它；否则会在需要本地模型时尝试从 ggml-org 官方 GitHub Releases 下载 llama.cpp。
11. 默认运行只做到 dry-run 检查，不会真正切换 Codex。
12. 只有你确认 dry-run 没问题，并且已经完全退出 Codex 后，才可以输入 APPLY 执行真实切换。
13. 安装成功后，日常使用优先双击 Start Codex Hot Router.cmd。这个入口会自动寻找已安装的最新混合配置版本，不再永久绑定某一个旧目录。它会先检查是否有尚未完成注册的 Microsoft Store 更新；如果有更新，会先连续观察三次，确认版本稳定后完成当前用户的 AppX 注册，注册后再检查是否出现更高版本，最多处理两轮。如果 Store 联网注册失败，但官方新版已经下载到本机，它会直接为当前用户注册这个本地官方包并继续。然后复制并校验与当前版本匹配的完整 CLI 套件，并通过官方 Codex CLI 刷新当前 AppX 自带的 Browser/Chrome marketplace。没有待处理更新时走快速路径。接着检查 127.0.0.1:19030 轻量 bridge，启动 127.0.0.1:19032 hot router，最后自动打开 Codex。Codex 完成功能初始化后，还会执行一次有时限的 Browser 检查；全程不会自动登录、重启 Codex 或改写历史数据库。
14. Codex Model Switcher.cmd 只作为维护/旧模式切换工具保留。
15. 如果想恢复官方 Codex，双击 Restore Official Codex.cmd。
16. Codex 更新后，如果日常入口的自动更新流程停止，请完全退出 Codex，再双击 Repair Codex Update and Plugins.cmd。它会完成官方 Store 注册、复制与新版 App 匹配的完整 CLI 套件，并刷新当前 AppX marketplace 及 Browser/Chrome。Repair Codex Browser and CLI.cmd 只作为 CLI 路径问题的窄范围备用入口。
17. 如果 Codex Live 无法启动，双击 Repair Codex Live Audio.cmd。它先只读检查麦克风授权和默认录音设备；完全退出 Codex 后输入 REPAIR 才会备份并修复，输入 RESTORE 可恢复最近一次音频备份。
18. 需要更换 ChatGPT 账号时，请完全退出 Codex，再双击 Change Codex Account.cmd。它使用设备代码登录，并先创建本地事务备份。
19. 如果安装失败，双击 Codex Hybrid Diagnostics.cmd，然后把桌面生成的诊断 txt 发回来。

说明：

- 这个包不安装 CC Switch。本包内置的是本项目自己的安全切换器。
- hot-router 模式下，Codex 右下角模型选择就是主要切换入口；维护模式下，才以 Codex Model Switcher.cmd 为准。
- 正常安装和模型路由不会修改 auth.json；只有用户明确运行更换账号入口时，才会通过官方 Codex 登录命令更新账号文件。

不要上传或分享这些内容：

- auth.json
- account-switch 账号备份
- models_cache.json
- state_5.sqlite
- sessions
- rollout logs
- API key
- 含有账号、密钥或个人路径的截图
