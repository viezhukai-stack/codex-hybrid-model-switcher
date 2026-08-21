# Validation Matrix

This project treats model switching safety as the core requirement. Local model
support is an optional capability because it depends on each machine's GPU,
driver, CUDA runtime, llama.cpp build, and model size.

## Validation Summary

| Environment | Cloud Provider | Local Model | Codex UI | Notes |
| --- | --- | --- | --- | --- |
| macOS working setup | Proven in the original field workflow | Proven in the original field workflow | Proven in the original field workflow | The current repository has not replaced the existing Mac field scripts. Mac remains the active working Codex environment and should not be used for risky canaries. |
| Windows canary 1 | Passed | Passed | Passed | Validated guarded cloud switch, local llama.cpp/Gemma text smoke, image smoke, and Codex Desktop UI behavior. |
| Windows canary 2 | Passed | Not required | Passed | Validated second-machine migration, Python 3.10 compatibility, guarded cloud switch, user-facing launcher, account visibility, project conversations, plugin/MCP visibility, and a test chat. Local Qwen3.6 35B candidates were found but not tested because local hardware/model fit is not a release requirement. |
| GitHub handoff entrypoint | Passed | Not applicable | Simulated | `HANDOFF_TO_CODEX.md` gives stock Codex users a single copy-paste prompt from the GitHub page, and `scripts/validate-github-entrypoint.py` verifies the prompt includes provider inputs, safety boundaries, bootstrap, dry-run, reports, and final verdict guidance. |
| Real canary issue template | Passed | Not applicable | Template | `.github/ISSUE_TEMPLATE/real_clean_machine_canary.yml` gives field testers a safe checklist for reporting stock Codex handoff results without uploading account/cache/history files or secrets. |
| Stock Codex simulation | Passed | Not applicable | Simulated | `scripts/validate-stock-codex-flow.py` creates a temporary stock-like Codex home, runs bootstrap dry-run, runs guarded apply, verifies only `config.toml` changed while account/cache/history-like files stayed unchanged, and checks the generated setup report is redacted. |
| Stock Codex handoff | Passed | Not applicable | Simulated | `scripts/validate-stock-codex-handoff.py` copies the repository to a clean temporary directory, verifies default bridge bootstrap/dry-run plus `bridge-health`, verifies bootstrap does not pollute the repository, and confirms private config plus guarded apply behavior. |
| Agent handoff drill | Passed | Not applicable | Simulated | `scripts/validate-agent-handoff-drill.py` rehearses the stock Codex agent path through bootstrap, dry-run, env-help, bridge-health, guarded apply, setup-report, canary-report, and final verdict guidance in a temporary profile. |
| Real clean-machine canary template | Passed | Not applicable | Simulated | `scripts/validate-real-clean-machine-canary.py` verifies the field-test template for a stock Codex user can be generated without leaking provider hostnames, local paths, tokens, or Codex state. |
| Windows Hyper-V clean VM canary | Passed | Not included | Real UI | `docs/windows-hyperv-clean-vm-canary.md` defines the final field proof: Windows 11 Hyper-V VM, stock Codex Desktop only, checkpoint `stock-codex-baseline`, fixed release `v2.12.2`, one `cloud_route=bridge` provider, `guarded-switch --dry-run`, protected files unchanged, visible `gpt-5.4` and `gpt-5.5` OK replies, and `codex-hybrid-final-check.md` verdict `Complete`. |
| Supervised handoff drill | Passed with improvements filed | Not applicable | Command drill | `docs/supervised-handoff-drill.md` records the assisted dry-run path from a clean Windows VM. The drill found that stock Windows may lack Python and Git, so `scripts/bootstrap-windows.ps1` is now the beginner route for checking or installing Python, downloading a fixed release zip, creating a private config, and stopping at `guarded-switch --dry-run`. |
| Windows netdisk one-click installer | Passed v2.18.7 package audit and physical HL/Kevin synchronization | Optional | Package verified; HL live canary passed | `Codex-Hybrid-Windows-Netdisk-Setup-v2.18.7.zip` contains portable Python, the shared WebSocket Hot Router, strict catalog support, the bounded AppX registration/CLI/marketplace orchestrator, local official AppX-manifest fallback, Browser/Chrome and account maintenance, plus the stable current-release launcher; SHA256 `1c35d87b3d59d1126f8886152fcdd2aacc7c95f891e273b081ba6d873c7fcccf`. HL passed update doctor, 12-model catalog, database `quick_check=ok`, and a live `gpt-5.5` Responses HTTP 200 check. Kevin received the same release and stable pointer without restarting its active Codex session; its next closed start will finish the newer staged AppX registration. |
| Windows full local netdisk package | Passed v2.18.7 ZIP and payload-manifest audit | Passed existing field runtime | Package verified | `Codex-Hybrid-Windows-Full-Local-Setup-v2.18.7.zip` contains llama.cpp, VC++ Runtime, portable Python, and the unchanged verified `payload/models/local-gemma`; SHA256 `e22558c29fbb4dfbb7e86c184ed6166260621fa6e5d7a8cc42fd574a08b9c0c9`. ZIP integrity and embedded GGUF/mmproj SHA256 values passed. HL and Kevin retained their existing `19030 -> 19031` local bridge policy, with `19031` idle and stopped during the non-interrupting release synchronization. |
| macOS netdisk one-click installer | Implemented v2.16.0; superseded by full-local distribution | Not included | Not required | `installer/macos` and `docs/macos-one-click-installer.md` define the beginner macOS cloud-only setup zip. It remains available as a code path, but private netdisk distribution now prioritizes the full-local package so users can start without a cloud API key. |
| macOS full local netdisk package | Passed prior UI canaries plus v2.18.7 package audit | Passed | Package verified | `Codex-Hybrid-macOS-Full-Local-Setup-v2.18.7.zip` is the current private full-local package; SHA256 `440ecdf303050981ebc346a0825f2fd3e4e91fbdadaa90089a24e0bae3593d20`. ZIP integrity and the embedded GGUF/mmproj manifest passed. It retains the verified local runtime and shared router; the Windows update transaction remains inert on macOS. |
| Shared v2.18.7 hot router and Windows update path | 241 tests and release acceptance passed | Existing local runtimes preserved | Simulated plus physical field evidence | The suite covers strict cloud/local catalogs, local metadata, Responses conversion, retries, HTTP/1.1 WebSocket tunneling, bounded AppX registration and stability passes, offline-safe registration of an already staged official package, current-marketplace refresh, managed CLI directory normalization, stable installed-release discovery, router-only proxy isolation, and protected-state invariants. |
| Windows physical v2.18.7 synchronization | HL live request passed; Kevin recent real requests remained HTTP 200 | Existing bridge policy preserved | No active session interruption | HL retained 119 `custom` tasks and Kevin retained 379 `custom` tasks with database `quick_check=ok`. Both machines received `v2.18.7`, `current-project.txt`, stable launcher files, and dynamic maintenance entries while their existing Codex process IDs and protected files remained unchanged. Kevin's pending `26.818.3698.0` AppX registration is intentionally deferred until Codex is fully closed. |
| Bridge-routed cloud unit path | Passed | Not applicable | Simulated | Unit tests verify `route=bridge` renders Codex to `127.0.0.1:19030`, refuses real switches when `api_key_env` is unset, starts the bridge when the env var is set, and preserves protected Codex files. |
| API key env handoff | Passed | Not applicable | Simulated | `env-help` is covered by unit tests and install validation, including macOS and Windows command templates without exposing key values. |
| Bridge health diagnostic | Passed | Not applicable | Simulated | `bridge-health` checks the bridge port, `/v1/health`, `/v1/models`, bridge-routed API key env status, and expected model ids without starting services or editing Codex state. |
| Canary evidence report | Passed | Not applicable | Simulated | `canary-report` records user-visible account, plugins/MCP, project list, test chat, bridge health, and setup report review evidence without exposing secrets or editing Codex state. |
| Final check report | Passed | Not applicable | Simulated | `final-check` combines the private config, setup report, canary evidence, and real canary template into a read-only Complete / Partially complete / Not complete / Needs rollback verdict. |
| Release acceptance gate | Passed | Not applicable | Simulated | `scripts/validate-release-acceptance.py` checks required handoff files, documentation markers, version consistency, Python compilation, security scan, and clean-copy handoff validation. |

## Required Before a Release

- CI passes on Python 3.10, 3.11, and 3.12.
- `security-scan .` finds no sensitive-looking content.
- Install validation passes in a temporary directory.
- Stock-Codex bootstrap-to-apply simulation passes in a temporary directory.
- GitHub handoff entrypoint validation passes, so a stock Codex user can start
  from the repository URL and a single copy-paste prompt.
- Real canary issue template exists, so field testers can submit the final
  clean-machine evidence without sharing private Codex state.
- Stock-Codex handoff validation passes from a clean temporary repository copy,
  including the default bridge dry-run and bridge-health diagnostic path.
- Agent handoff drill passes and proves the simulated stock Codex agent path
  reaches setup report, canary evidence, and final verdict guidance.
- Real clean-machine canary template validation passes, so a field tester has a
  standard artifact for final stock Codex handoff evidence.
- Windows Hyper-V clean VM canary has passed for the final public proof, using
  `stock-codex-baseline`, `v2.12.2`, `cloud_route=bridge`,
  `guarded-switch --dry-run`, `codex-hybrid-final-check.md`, protected file
  checks for `auth.json`, `models_cache.json`, `state_5.sqlite`, and
  `sessions/`, plus visible `gpt-5.4` and `gpt-5.5` OK replies.
- Supervised handoff drill has passed far enough to prove command executability
  and has a beginner Windows bootstrap path for missing Python/Git.
- Windows netdisk one-click installer package builds and has passed a real HL
  Hyper-V VM canary with stock Codex login, visible temporary chats, visible
  project chats, plugin visibility, and a responding cloud test chat.
- Windows full local netdisk package has passed a real HL Hyper-V VM canary
  with no cloud API key, bundled local model install, text and image local
  smoke, guarded `APPLY`, unchanged protected files, visible account/plugins,
  visible project conversations, and a responding Codex Desktop test chat.
- macOS full local netdisk package has passed a real UI canary on the tested Mac
  with bundled local model install, account/plugin/project visibility, a
  responding test chat, and a successful main-profile restore afterward.
- Release acceptance validation passes before tagging.
- Redacted setup report generation passes in the stock-Codex simulation.
- The setup report includes user-visible success criteria for account,
  plugins/MCP, project list, and a new responding test conversation.
- Canary evidence generation records the final user-visible checks and warns
  when a `complete` verdict lacks required evidence.
- Final check generation reads the redacted reports and refuses to call the
  setup complete when final evidence is missing or failed.
- `FINAL_CHECK.md` gives users a final agent prompt for classifying completion
  as complete, partial, incomplete, or rollback-needed.
- The stock-Codex handoff prompt in `START_HERE.md` is covered by documentation
  tests.
- Bridge-routed cloud providers have tests for local bridge rendering,
  missing API-key refusal, and protected-file preservation.
- `env-help` is tested as the next step when `api_key_env(...unset)` appears.
- `bridge-health` is tested as the next step when Codex opens but a
  bridge-routed provider does not reply.
- At least one Windows canary has validated cloud provider switching.
- At least one Windows canary has validated local llama.cpp text and image smoke.
- At least one second-machine Windows canary has validated cloud switching and the guarded launcher.
- Protected Codex files are unchanged during guarded switch canaries:
  - `auth.json`
  - `models_cache.json`
  - `state_5.sqlite`

## Optional Local Model Validation

Local model validation is not expected to pass on every machine. A machine may
skip local validation when:

- no suitable GPU is present
- CUDA runtime is missing or incompatible
- the only available local model is too large for the machine
- no matching mmproj file exists for a multimodal model
- llama.cpp is missing or too old

Skipping local validation on one machine does not block release readiness if
another canary already validated the local bridge and llama.cpp flow.

## What Counts as a Failed Canary

Stop and investigate if any of these happen:

- account information disappears
- project conversations disappear
- plugin or MCP entry points disappear
- `auth.json`, `models_cache.json`, or `state_5.sqlite` hash changes
- the dry-run diff removes unrelated settings
- Codex is running and the switch still writes config
- local smoke fails but the tool continues to write config

## What Does Not Count as a Project Failure

These are environment limitations, not release blockers:

- a particular machine cannot fit a large local model in VRAM
- a local model is slow
- a machine lacks CUDA
- a machine has a different local model family than the examples
- the Codex bottom-right model selector displays a stale or generic label

The external switcher and `config.toml` provider/model fields are the source of
truth for this project.
