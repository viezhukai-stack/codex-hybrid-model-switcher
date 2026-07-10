#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
version="$(tr -d '\r\n' <"${script_dir}/VERSION.txt" 2>/dev/null || true)"
if [[ -z "${version}" ]]; then
  for project_file in \
    "${script_dir}/payload/codex-hybrid-model-switcher/pyproject.toml" \
    "${script_dir}/../../pyproject.toml"; do
    if [[ -f "${project_file}" ]]; then
      version="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "${project_file}" | head -1)"
      [[ -n "${version}" ]] && break
    fi
  done
fi
if [[ -z "${version}" ]]; then
  echo "Package version could not be read from VERSION.txt or pyproject.toml."
  read -r -p "Press Enter to close this window..."
  exit 1
fi
payload_script="${script_dir}/payload/codex-hybrid-model-switcher/scripts/macos-hot-router-start.sh"
installed_script="${HOME}/Library/Application Support/CodexHybridModelSwitcher/releases/v${version}/project/scripts/macos-hot-router-start.sh"

if [[ -f "${installed_script}" ]]; then
  bash "${installed_script}" "$@"
elif [[ -f "${payload_script}" ]]; then
  bash "${payload_script}" "$@"
else
  echo "Codex Hybrid 2.0 start script was not found."
  echo "Run Install Codex Hybrid.command first, then try again."
  read -r -p "Press Enter to close this window..."
  exit 1
fi
