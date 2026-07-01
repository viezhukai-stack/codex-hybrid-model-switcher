Codex Hybrid Model Switcher - Windows 网盘一键安装包

给小白用户的用法：

1. 解压整个 zip，不要只拖出单个文件。
2. 双击 Install Codex Hybrid.cmd。
3. 如果电脑还没安装或登录 Codex，安装器会打开 Codex 官方页面。请先安装 Codex、登录账号、完全关闭 Codex，然后重新双击安装器。
4. 如果电脑没有 Python，安装器会尝试用 winget 安装 Python 3.12。
5. 这个网盘包已经内置项目源码，不需要安装 Git，也不需要从 GitHub 下载项目源码。
6. 按提示输入你的 OpenAI-compatible 服务地址、模型名、API key 环境变量名和 API key。API key 只会写入 Windows 用户环境变量，不会写进项目配置文件。
7. 如果要用本地模型，请选择你自己的 GGUF 模型文件和 mmproj 文件。本包不包含模型文件。
8. 如果 payload\llama.cpp 里已经带有 llama-server.exe，安装器会优先使用它；否则会在需要本地模型时尝试从 ggml-org 官方 GitHub Releases 下载 llama.cpp。
9. 默认运行只做到 dry-run 检查，不会真正切换 Codex。
10. 只有你确认 dry-run 没问题，并且已经完全退出 Codex 后，才可以用 -Apply 执行真实切换。

不要上传或分享这些内容：

- auth.json
- models_cache.json
- state_5.sqlite
- sessions
- rollout logs
- API key
- 含有账号、密钥或个人路径的截图
