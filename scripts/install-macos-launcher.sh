#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
launcher="${HOME}/Desktop/Codex Model Switcher.command"

cat >"${launcher}" <<EOF
#!/usr/bin/env bash
cd "${repo_dir}"
bash scripts/macos-provider-menu.sh --config "\${HOME}/.codex-hybrid-model-switcher/config.json"
read -r -p "Press Enter to close..."
EOF

chmod +x "${launcher}"
echo "Installed: ${launcher}"
