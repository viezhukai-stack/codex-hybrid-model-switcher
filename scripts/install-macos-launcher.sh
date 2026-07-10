#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
desktop="${HOME}/Desktop"
mkdir -p "${desktop}"

write_launcher() {
  local path="$1"
  local command="$2"
  local wait_prompt="${3:-true}"
  {
    echo '#!/usr/bin/env bash'
    echo 'set -e'
    echo 'env_file="${HOME}/.codex-hybrid-model-switcher/env.sh"'
    echo 'if [[ -f "${env_file}" ]]; then source "${env_file}"; fi'
    printf 'cd %q\n' "${repo_dir}"
    printf '%s\n' "${command}"
    if [[ "${wait_prompt}" == true ]]; then
      echo 'read -r -p "Press Enter to close..."'
    fi
  } >"${path}"
  chmod +x "${path}"
  echo "Installed: ${path}"
}

write_launcher \
  "${desktop}/Start Codex Hybrid 2.0.command" \
  'bash scripts/macos-hot-router-start.sh --config "${HOME}/.codex-hybrid-model-switcher/config.json"' \
  false

write_launcher \
  "${desktop}/Codex Model Switcher.command" \
  'bash scripts/macos-provider-menu.sh --config "${HOME}/.codex-hybrid-model-switcher/config.json"'

write_launcher \
  "${desktop}/Enable Codex Hybrid 2.0.command" \
  'bash scripts/macos-hot-router-mode.sh enable --config "${HOME}/.codex-hybrid-model-switcher/config.json"'

write_launcher \
  "${desktop}/Restore Codex 19030 Mode.command" \
  'bash scripts/macos-hot-router-mode.sh restore --config "${HOME}/.codex-hybrid-model-switcher/config.json"'

write_launcher \
  "${desktop}/Restore Official Codex.command" \
  'bash scripts/macos-restore-official.sh --config "${HOME}/.codex-hybrid-model-switcher/config.json"'
