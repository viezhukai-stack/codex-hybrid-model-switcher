# Final Check: Ask Codex If Setup Is Complete

Use this page after the guarded switch, after reopening Codex Desktop, and after
creating a new test conversation.

The goal is to make Codex say one of these clearly:

- `Complete`
- `Partially complete`
- `Not complete`
- `Needs rollback`

## Copy This Prompt Into Codex

```text
请按照这个仓库的 FINAL_CHECK.md 和 docs/user-success-criteria.md，帮我判断 Codex Hybrid Model Switcher 是否已经配置完成。

请不要修改任何文件，除非我明确让你修复。
这一步只做核对和结论，不做新的 provider 切换。

请检查并询问我必要的可见状态：
- Codex Desktop 是否能正常打开，没有错误页？
- 左下角或账号区域是否还能看到账号信息？
- 插件/MCP 入口是否还在？
- 项目列表是否还在？
- 新建测试对话是否已经成功回复？
- setup report 是否已经生成？
- setup report 中是否没有 API key、token、原始 provider hostname、本机路径、账号数据、会话文本或数据库内容？
- canary-report 是否已经生成，并记录账号、插件/MCP、项目列表、新建测试对话、bridge-health/setup report review 的 yes/no/na 状态？
- final-check 是否已经生成，并给出 Complete / Partially complete / Not complete / Needs rollback 之一？
- 如果 provider 使用 bridge 路由，bridge-health 是否通过，或者是否明确指出了 bridge/key/model list 的问题？

请同时核对命令侧证据：
- guarded-switch 是否显示 protected files unchanged？
- 是否有 config.toml.bak-codex-hybrid-* 备份？
- 是否没有修改 auth.json、models_cache.json、state_5.sqlite、sessions 或 rollout logs？
- 如果新对话没有回复，是否已经运行 bridge-health，而不是猜测问题原因？
- 如果 final-check 不是 Complete，是否列出了缺失项或回滚项？

最后请只给出一个结论：
- Complete：全部通过。
- Partially complete：只完成了 bootstrap、validate-config、dry-run 或 guarded-switch，但还没有完成 Codex Desktop 可见状态/新对话测试/setup report。
- Not complete：关键步骤缺失，不能确认成功。
- Needs rollback：账号、插件/MCP、项目列表、新对话、或受保护文件出现异常。

请列出缺失项和下一步动作。不要为了让结论好看而假设我已经完成了没有证据的步骤。
```

## Evidence Codex Should Prefer

Use direct evidence first:

- visible user confirmation from Codex Desktop
- generated setup report
- generated canary evidence report
- guarded switch output
- backup filename
- protected file hash output

Do not claim completion from intent, old screenshots, or a dry-run alone.

## Rollback Boundary

If the result is `Needs rollback`, the default rollback is:

1. Ask the user to quit Codex Desktop.
2. Restore the newest `config.toml.bak-codex-hybrid-*` backup.
3. Do not edit `auth.json`, `models_cache.json`, `state_5.sqlite`, `sessions/`,
   or rollout logs.
4. Reopen Codex Desktop and re-check account, plugins/MCP, and project list.
