#!/usr/bin/env bash
set -euo pipefail

action="${1:-status}"
if [[ $# -gt 0 ]]; then
  shift
fi
config="${HOME}/.codex-hybrid-model-switcher/config.json"
env_file="${CODEX_HYBRID_ENV_FILE:-${HOME}/.codex-hybrid-model-switcher/env.sh}"

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
python_bin="${PYTHON:-python3}"
if [[ -f "${env_file}" ]]; then
  # shellcheck disable=SC1090
  source "${env_file}"
  python_bin="${PYTHON:-${python_bin}}"
fi

PYTHONPATH="${repo_dir}/src" "${python_bin}" -m codex_hybrid_switcher \
  hot-router-mode "${action}" --config "${config}"
