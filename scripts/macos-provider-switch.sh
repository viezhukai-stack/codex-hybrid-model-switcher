#!/usr/bin/env bash
set -euo pipefail

provider_id="cloud-gpt-main"
config="${HOME}/.codex-hybrid-model-switcher/config.json"
apply=false
allow_local=false
skip_local_smoke=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider-id)
      provider_id="$2"
      shift 2
      ;;
    --config)
      config="$2"
      shift 2
      ;;
    --apply)
      apply=true
      shift
      ;;
    --allow-local)
      allow_local=true
      shift
      ;;
    --skip-local-smoke)
      skip_local_smoke=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON:-python3}"

invoke_switcher() {
  PYTHONPATH="${repo_dir}/src" "${python_bin}" -m codex_hybrid_switcher "$@"
}

assert_codex_stopped() {
  if pgrep -f "Codex.app|codex app-server|codex-command-runner" >/dev/null 2>&1; then
    echo "Codex appears to be running. Quit Codex completely before applying the switch." >&2
    exit 2
  fi
}

provider_kind="$(
  "${python_bin}" - "${config}" "${provider_id}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]).expanduser()
provider_id = sys.argv[2]
data = json.loads(path.read_text(encoding="utf-8"))
for provider in data.get("providers", []):
    if provider.get("id") == provider_id:
        print(provider.get("kind") or "")
        raise SystemExit(0)
print(f"Provider not found in private config: {provider_id}", file=sys.stderr)
raise SystemExit(2)
PY
)"

args=("guarded-switch" "${provider_id}" "--config" "${config}")
if [[ "${provider_kind}" == "local" ]]; then
  if [[ "${allow_local}" != true ]]; then
    echo "Local provider switches require --allow-local. Run local-smoke first if this is the first local validation." >&2
    exit 2
  fi
  args+=("--allow-local")
  if [[ "${skip_local_smoke}" == true ]]; then
    args+=("--skip-local-smoke")
  fi
fi

echo "macOS provider switch"
echo "provider: ${provider_id}"
echo "kind: ${provider_kind}"
echo "config: <private-config>"
echo

invoke_switcher validate-config --config "${config}"
echo

invoke_switcher "${args[@]}" --dry-run
echo

if [[ "${apply}" != true ]]; then
  echo "Dry-run complete. No files were changed."
  echo "After quitting Codex, rerun with --apply to perform the guarded switch."
  exit 0
fi

assert_codex_stopped
invoke_switcher "${args[@]}"
echo
echo "Provider switch applied. Open Codex manually and verify account, plugins, project conversations, and one new test chat."
