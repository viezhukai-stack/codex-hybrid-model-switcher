#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_dir}"

python_bin="${PYTHON:-python3}"
"${python_bin}" bootstrap.py

echo
read -r -p "Press Enter to close..."
