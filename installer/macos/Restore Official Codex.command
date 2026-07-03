#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
payload_restore="${script_dir}/payload/codex-hybrid-model-switcher/scripts/macos-restore-official.sh"
installed_restore="${HOME}/Library/Application Support/CodexHybridModelSwitcher/releases/v2.17.3/project/scripts/macos-restore-official.sh"

if [[ -f "${installed_restore}" ]]; then
  bash "${installed_restore}" "$@"
elif [[ -f "${payload_restore}" ]]; then
  bash "${payload_restore}" "$@"
else
  echo "Restore script was not found."
  echo "Run Install Codex Hybrid.command first, then try again."
fi

echo
read -r -p "Press Enter to close this window..."
