#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

if [[ -n "${PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$repo_root/src:$PYTHONPATH"
else
  export PYTHONPATH="$repo_root/src"
fi

exec python3 -m codex_hybrid_switcher local-smoke "$@"
