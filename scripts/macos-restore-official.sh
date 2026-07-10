#!/usr/bin/env bash
set -euo pipefail

config="${HOME}/.codex-hybrid-model-switcher/config.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      config="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
switch_script="${repo_dir}/scripts/macos-provider-switch.sh"
hot_router_mode_script="${repo_dir}/scripts/macos-hot-router-mode.sh"

if [[ ! -f "${switch_script}" ]]; then
  echo "Provider switch script was not found." >&2
  exit 1
fi

echo
echo "Restore Official Codex"
echo "======================"
echo "This restores Codex provider settings to the official OpenAI provider."
echo "It still uses guarded dry-run first and will not touch auth.json, models_cache.json, or state_5.sqlite."
echo

bash "${switch_script}" --provider-id "openai-official" --config "${config}"

echo
echo "Dry-run finished. No files were changed."
echo "Before restoring, quit Codex Desktop completely."
echo "To restore now, type APPLY exactly."
read -r -p "Restore official Codex now: " confirm
if [[ "${confirm}" != "APPLY" ]]; then
  echo "Cancelled. No files were changed."
  exit 0
fi

if [[ -f "${hot_router_mode_script}" ]]; then
  status_output="$(bash "${hot_router_mode_script}" status --config "${config}" 2>/dev/null || true)"
  if [[ "${status_output}" == *'"active": true'* ]]; then
    bash "${hot_router_mode_script}" restore --config "${config}"
  fi
fi

bash "${switch_script}" --provider-id "openai-official" --config "${config}" --apply

echo
echo "Done. Open Codex Desktop manually and verify account, plugins, and project conversations."
