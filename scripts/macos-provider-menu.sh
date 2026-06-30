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
python_bin="${PYTHON:-python3}"
switch_script="${repo_dir}/scripts/macos-provider-switch.sh"

if [[ ! -f "${config}" ]]; then
  echo "Private config not found: ${config}" >&2
  echo "Run first-run setup or bootstrap.py before using the provider menu." >&2
  exit 2
fi

providers="$(
  "${python_bin}" - "${config}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]).expanduser()
data = json.loads(path.read_text(encoding="utf-8"))
providers = data.get("providers", [])
if not providers:
    print("No providers found in private config.", file=sys.stderr)
    raise SystemExit(2)
for idx, provider in enumerate(providers, 1):
    label = provider.get("label") or provider.get("id")
    kind = provider.get("kind") or ""
    model = provider.get("model") or ""
    provider_id = provider.get("id") or ""
    print(f"{idx}\t{provider_id}\t{kind}\t{label}\t{model}")
PY
)"

echo
echo "Codex Model Switcher"
echo "===================="
echo "Codex Desktop must be fully closed before applying a switch."
echo "The bottom-right Codex model selector is not the source of truth."
echo

printf "%s\n" "${providers}" | while IFS=$'\t' read -r idx provider_id kind label model; do
  printf "%s. %s [%s] %s\n" "${idx}" "${label}" "${kind}" "${model}"
done

echo
read -r -p "Choose provider number, or Q to quit: " choice
if [[ "${choice}" =~ ^[Qq]$ ]]; then
  exit 0
fi
if [[ ! "${choice}" =~ ^[0-9]+$ ]]; then
  echo "Invalid selection." >&2
  exit 2
fi

selected_line="$(printf "%s\n" "${providers}" | awk -F '\t' -v n="${choice}" '$1 == n {print; exit}')"
if [[ -z "${selected_line}" ]]; then
  echo "Invalid selection." >&2
  exit 2
fi

IFS=$'\t' read -r _idx selected_id selected_kind _label _model <<EOF
${selected_line}
EOF

args=("--provider-id" "${selected_id}" "--config" "${config}")
if [[ "${selected_kind}" == "local" ]]; then
  args+=("--allow-local")
fi

echo
echo "Selected provider: ${selected_id} [${selected_kind}]"
echo "Step 1: guarded dry-run"
echo

bash "${switch_script}" "${args[@]}"

echo
echo "Dry-run finished. No files were changed."
echo "Before applying, quit Codex Desktop completely."
echo "To apply this switch, type APPLY exactly."
read -r -p "Apply now: " confirm
if [[ "${confirm}" != "APPLY" ]]; then
  echo "Cancelled. No files were changed."
  exit 0
fi

echo
echo "Step 2: guarded apply"
echo

bash "${switch_script}" "${args[@]}" --apply

echo
echo "Done. Open Codex Desktop manually and verify account, plugins, project conversations, then start a new test chat."
