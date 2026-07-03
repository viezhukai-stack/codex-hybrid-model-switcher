#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "${script_dir}/Install-CodexHybrid.sh" --diagnostics-only "$@"

echo
read -r -p "Press Enter to close this window..."
