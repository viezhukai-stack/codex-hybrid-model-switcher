# User Success Criteria

Use this checklist after a guarded switch. It is written for non-technical users
who need to decide whether the hybrid Codex setup actually worked.

## Before You Test

- Codex Desktop was fully quit before the guarded switch.
- The guarded switch command finished without errors.
- The output said protected Codex files were unchanged.
- A `config.toml.bak-codex-hybrid-*` backup was created.
- A redacted setup report was generated or is about to be generated.
- A canary evidence report will be generated after the visible checks.

## In Codex Desktop

Open Codex Desktop normally after the guarded switch.

Mark setup as successful only when all of these are true:

- [ ] Codex Desktop opens without an error page.
- [ ] Account information is still visible.
- [ ] Plugin and MCP entry points are still visible.
- [ ] The project list is still visible.
- [ ] Existing conversations are not deleted. Some may appear under a different
  provider bucket; that is visibility behavior, not deletion.
- [ ] A new test conversation responds using the configured provider.
- [ ] For bridge-routed providers, `bridge-health` passes or clearly identifies
  the remaining bridge/key/model-list issue.
- [ ] The generated setup report does not contain API keys, tokens, raw
  provider hostnames, private paths, account data, session text, or database
  content.
- [ ] A `canary-report` was generated with account, plugins/MCP, project list,
  test chat, bridge health, and setup report review recorded as `yes` or `na`.

## What Counts as Not Finished

The setup is not complete yet if:

- only bootstrap ran
- only `guarded-switch --dry-run` ran
- Codex Desktop has not been reopened after the real switch
- no new test conversation has responded
- the user has not checked account, plugins/MCP, and project visibility
- no `canary-report` has recorded the visible checks

Say exactly which milestone passed instead of claiming the full setup is done.

## If Something Looks Wrong

1. Quit Codex Desktop completely.
2. Restore the newest `config.toml.bak-codex-hybrid-*` backup.
3. Do not edit `auth.json`, `models_cache.json`, `state_5.sqlite`, `sessions/`,
   or rollout logs.
4. Keep the redacted setup report and command output for troubleshooting.

## Local llama.cpp Success

Local model setup is optional and machine-dependent. Mark local setup as
successful only when:

- [ ] `local-smoke` passes on that machine.
- [ ] The local provider switch was applied only after `local-smoke` passed.
- [ ] A new Codex test conversation responds through the local provider.
- [ ] For multimodal models, an image smoke test also passes.

Do not treat a local model failure as a cloud-provider setup failure when the
cloud provider already works.

## Final Agent Verdict

After walking through this checklist, use the copy-paste prompt in
[`../FINAL_CHECK.md`](../FINAL_CHECK.md). It asks Codex to classify the result as
`Complete`, `Partially complete`, `Not complete`, or `Needs rollback`.
