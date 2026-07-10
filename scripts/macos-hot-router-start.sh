#!/usr/bin/env bash
set -euo pipefail

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
# shellcheck disable=SC1091
source "${repo_dir}/scripts/macos-app-common.sh"

python_bin="${PYTHON:-python3}"
if [[ -f "${env_file}" ]]; then
  # shellcheck disable=SC1090
  source "${env_file}"
  python_bin="${PYTHON:-${python_bin}}"
fi

invoke_switcher() {
  PYTHONPATH="${repo_dir}/src" "${python_bin}" -m codex_hybrid_switcher "$@"
}

eval "$(
  "${python_bin}" - "${config}" <<'PY'
import json
import shlex
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).expanduser().read_text(encoding="utf-8-sig"))
router = data.get("hot_router") or {}
print("router_host=" + shlex.quote(str(router.get("host") or "127.0.0.1")))
print("router_port=" + shlex.quote(str(router.get("port") or 19032)))
PY
)"

router_pid=""
cleanup() {
  if [[ -n "${router_pid}" ]]; then
    kill "${router_pid}" >/dev/null 2>&1 || true
    wait "${router_pid}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

router_healthy() {
  "${python_bin}" - "http://${router_host}:${router_port}/health" <<'PY'
import json
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=2) as response:
        data = json.loads(response.read().decode("utf-8-sig"))
    raise SystemExit(0 if data.get("router") == "codex-hot-router" else 1)
except Exception:
    raise SystemExit(1)
PY
}

config_points_to_router() {
  "${python_bin}" - "${HOME}/.codex/config.toml" "http://${router_host}:${router_port}/v1" <<'PY'
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    raise SystemExit(1)

try:
    data = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    provider = (data.get("model_providers") or {}).get(data.get("model_provider")) or {}
    raise SystemExit(0 if provider.get("base_url") == sys.argv[2] else 1)
except Exception:
    raise SystemExit(1)
PY
}

echo "Checking lightweight bridge on 127.0.0.1:19030..."
invoke_switcher ensure-bridge --config "${config}" || \
  echo "WARNING: bridge is not healthy; cloud models may still work, but local models will not."

if router_healthy; then
  echo "Codex hot router is already healthy on ${router_host}:${router_port}."
else
  echo "Starting Codex hot router on ${router_host}:${router_port}..."
  invoke_switcher hot-router --config "${config}" --host "${router_host}" --port "${router_port}" &
  router_pid="$!"
  for _ in $(seq 1 30); do
    router_healthy && break
    sleep 1
  done
  if ! router_healthy; then
    echo "Codex hot router did not become healthy." >&2
    exit 1
  fi
fi

if ! config_points_to_router; then
  if codex_is_running; then
    echo "Codex is running and must quit before 2.0 mode can be enabled."
    wait_for_codex_to_quit || exit 2
  fi
  invoke_switcher hot-router-mode enable --config "${config}"
fi

echo "Opening ChatGPT/Codex..."
open_codex_desktop

if [[ -n "${router_pid}" ]]; then
  echo "Codex Hybrid 2.0 is active. Keep this window open while using Codex."
  wait "${router_pid}"
fi
