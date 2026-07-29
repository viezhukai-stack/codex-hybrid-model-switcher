# Windows Codex Live Audio Repair

Use `Repair Codex Live Audio.cmd` only when Codex Live does not start or the Hot
Router never receives `POST /v1/live` after the Live button is pressed.

The first pass is read-only. It reports:

- the installed `OpenAI.Codex` package family;
- the global and Codex-specific microphone consent values;
- the Console, Multimedia, and Communications default capture endpoints;
- active or hidden recording endpoints eligible for repair.

To apply, fully quit Codex and type `REPAIR` exactly. The script creates a
timestamped backup under
`%USERPROFILE%\.codex-hybrid-model-switcher\backups\live-audio-*`, hashes the
protected Codex files, sets only the current user's Codex microphone consent,
and fills missing default capture roles. Existing defaults are preserved. A
single eligible endpoint is selected automatically; multiple endpoints require
an explicit numbered choice.

The repair also treats a surviving Codex `app-server` process or a protected
file hash that is still changing as an incomplete exit. It asks the user to wait
and rerun rather than editing settings during the shutdown flush window. The
guard includes a short bounded quiet period before the repair writes anything.

Type `RESTORE` in the same desktop entry to replay the newest consent/default
backup. The maintenance path does not stop Codex, edit the provider, install a
service or scheduled task, or write `auth.json`, `models_cache.json`,
`state_5.sqlite`, sessions, or rollout logs.

After repair, start Codex through `Start Codex Hot Router.cmd`. A successful
Live session produces a normal `POST /v1/live` response followed by an HTTP 101
WebSocket upgrade in the Hot Router log. Audio frame contents are not logged.

## v2.18.4 physical canary

On 2026-07-29 the packaged doctor reported `healthy` on both Windows machines.
HL completed `REPAIR` and `RESTORE`; Kevin completed an idempotent `REPAIR`.
The scripts detected a shutdown-settling edge case and now wait for both the
Codex `app-server` and protected hashes to become quiet. Final canaries preserved
the protected files, kept every task in the `custom` provider bucket, reopened
Codex through the daily launcher, and left `19031` stopped while idle.
