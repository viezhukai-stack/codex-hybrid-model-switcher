#!/usr/bin/env bash

codex_app_path() {
  local app
  if command -v mdfind >/dev/null 2>&1; then
    while IFS= read -r app; do
      if [[ -d "${app}" && "${app}" == *.app ]]; then
        printf '%s\n' "${app}"
        return 0
      fi
    done < <(mdfind "kMDItemCFBundleIdentifier == 'com.openai.codex'" 2>/dev/null)
  fi
  for app in \
    "/Applications/ChatGPT.app" \
    "${HOME}/Applications/ChatGPT.app" \
    "/Applications/Codex.app" \
    "${HOME}/Applications/Codex.app"; do
    if [[ -d "${app}" ]]; then
      printf '%s\n' "${app}"
      return 0
    fi
  done
  return 1
}

codex_cli_path() {
  local app
  app="$(codex_app_path 2>/dev/null || true)"
  if [[ -n "${app}" && -x "${app}/Contents/Resources/codex" ]]; then
    printf '%s\n' "${app}/Contents/Resources/codex"
    return 0
  fi
  return 1
}

codex_is_running() {
  ps -ww -axo args= 2>/dev/null \
    | grep -q -E '/(ChatGPT|Codex)\.app/Contents/MacOS/(ChatGPT|Codex)$|/(ChatGPT|Codex)\.app/Contents/Resources/codex( .*)? app-server|/(ChatGPT|Codex)\.app/Contents/Resources/(codex-command-runner|codex-code-mode-host)'
}

request_codex_quit() {
  /usr/bin/osascript -e 'tell application id "com.openai.codex" to quit' >/dev/null 2>&1 || true
  /usr/bin/osascript -e 'tell application "ChatGPT" to quit' >/dev/null 2>&1 || true
  /usr/bin/osascript -e 'tell application "Codex" to quit' >/dev/null 2>&1 || true
}

wait_for_codex_to_quit() {
  local waited=0
  request_codex_quit
  while codex_is_running; do
    if (( waited >= 60 )); then
      echo "Codex did not quit within 60 seconds." >&2
      return 1
    fi
    sleep 1
    waited=$((waited + 1))
  done
}

open_codex_desktop() {
  local cli app cli_pid
  cli="$(codex_cli_path 2>/dev/null || true)"
  if [[ -n "${cli}" ]]; then
    "${cli}" app "${HOME}" >/dev/null 2>&1 &
    cli_pid="$!"
    sleep 1
    if kill -0 "${cli_pid}" >/dev/null 2>&1; then
      return 0
    fi
    if wait "${cli_pid}"; then
      return 0
    fi
  fi
  if /usr/bin/open -b com.openai.codex >/dev/null 2>&1; then
    return 0
  fi
  app="$(codex_app_path 2>/dev/null || true)"
  if [[ -n "${app}" ]]; then
    /usr/bin/open "${app}" >/dev/null 2>&1
    return 0
  fi
  /usr/bin/open -a ChatGPT >/dev/null 2>&1 \
    || /usr/bin/open -a Codex >/dev/null 2>&1
}
