#!/usr/bin/env bash
set -euo pipefail

release_tag=""
provider_id="cloud-gpt-main"
provider_label="Cloud GPT Main"
base_url=""
model=""
api_key_env="OPENAI_COMPATIBLE_API_KEY"
config_path="${HOME}/.codex-hybrid-model-switcher/config.json"
provider_preset_path=""
dry_run_only=false
apply=false
non_interactive=false
skip_codex_check=false
diagnostics_only=false
skip_cloud=false
skip_local_smoke=false
local_smoke_timeout=900
llama_backend="auto"
unify_history=false
skip_history_unify=false
history_unify_requested=false
switch_model=""

codex_download_url="https://developers.openai.com/codex/app"
python_download_url="https://www.python.org/downloads/macos/"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
package_version="$(tr -d '\r\n' <"${script_dir}/VERSION.txt" 2>/dev/null || true)"
if [[ -z "${package_version}" ]]; then
  for project_file in \
    "${script_dir}/payload/codex-hybrid-model-switcher/pyproject.toml" \
    "${script_dir}/../../pyproject.toml"; do
    if [[ -f "${project_file}" ]]; then
      package_version="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "${project_file}" | head -1)"
      [[ -n "${package_version}" ]] && break
    fi
  done
fi
if [[ -z "${package_version}" ]]; then
  echo "Package version could not be read from VERSION.txt or pyproject.toml." >&2
  exit 2
fi
release_tag="v${package_version}"
install_root="${HOME}/Library/Application Support/CodexHybridModelSwitcher"
release_root="${install_root}/releases/${release_tag}"
project_path="${release_root}/project"
runtime_root="${HOME}/.codex-hybrid-model-switcher"
env_file="${runtime_root}/env.sh"
bundled_project_default="${script_dir}/payload/codex-hybrid-model-switcher"
bundled_python_root="${script_dir}/payload/python"
bundled_model_root="${script_dir}/payload/models/local-gemma"
bundled_llama_root="${script_dir}/payload/llama.cpp"
installed_python_root="${install_root}/python"
model_root="${install_root}/models"
llama_root="${install_root}/llama.cpp"
include_local=false
include_cloud=false
local_smoke_passed=false
local_model_path=""
local_mmproj_path=""
llama_server_path=""
switch_provider_id="${provider_id}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release-tag)
      release_tag="$2"
      release_root="${install_root}/releases/${release_tag}"
      project_path="${release_root}/project"
      shift 2
      ;;
    --provider-id)
      provider_id="$2"
      shift 2
      ;;
    --provider-label)
      provider_label="$2"
      shift 2
      ;;
    --base-url)
      base_url="$2"
      shift 2
      ;;
    --model)
      model="$2"
      shift 2
      ;;
    --api-key-env)
      api_key_env="$2"
      shift 2
      ;;
    --config)
      config_path="$2"
      shift 2
      ;;
    --provider-preset-path)
      provider_preset_path="$2"
      shift 2
      ;;
    --dry-run-only)
      dry_run_only=true
      shift
      ;;
    --apply)
      apply=true
      shift
      ;;
    --non-interactive)
      non_interactive=true
      shift
      ;;
    --skip-codex-check)
      skip_codex_check=true
      shift
      ;;
    --diagnostics-only)
      diagnostics_only=true
      shift
      ;;
    --skip-cloud)
      skip_cloud=true
      shift
      ;;
    --skip-local-smoke)
      skip_local_smoke=true
      shift
      ;;
    --local-smoke-timeout)
      local_smoke_timeout="$2"
      shift 2
      ;;
    --llama-backend)
      llama_backend="$2"
      shift 2
      ;;
    --unify-history)
      unify_history=true
      shift
      ;;
    --skip-history-unify)
      skip_history_unify=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

write_step() {
  echo
  echo "==> $1"
}

fail() {
  echo
  echo "ERROR: $1" >&2
  exit "${2:-1}"
}

format_size_gb() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    echo "0.0"
    return
  fi
  du -sg "${path}" | awk '{printf "%.1f", $1}'
}

show_disk_space_check() {
  write_step "Checking disk space"
  local free_gb
  free_gb="$(free_space_gb)"
  echo "Free space on the install drive: ${free_gb} GB"
  if [[ -d "${bundled_model_root}" ]]; then
    echo "Bundled local model payload: about $(format_size_gb "${bundled_model_root}") GB"
    echo "Recommended free space for full local setup: 15-20 GB or more."
    if [[ "${free_gb}" =~ ^[0-9]+$ ]] && (( free_gb < 15 )); then
      echo "WARNING: free space is low. Local model copy or smoke test may fail."
    fi
  fi
}

find_python() {
  if [[ -x "${installed_python_root}/bin/python3" ]]; then
    echo "${installed_python_root}/bin/python3"
    return 0
  fi
  if [[ -x "${bundled_python_root}/bin/python3" ]]; then
    echo "${bundled_python_root}/bin/python3"
    return 0
  fi
  if [[ -x "${bundled_python_root}/python3" ]]; then
    echo "${bundled_python_root}/python3"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if [[ -x "/usr/bin/python3" ]]; then
    echo "/usr/bin/python3"
    return 0
  fi
  return 1
}

python_bin="$(find_python || true)"

install_bundled_python_if_available() {
  if [[ ! -x "${bundled_python_root}/bin/python3" && ! -x "${bundled_python_root}/python3" ]]; then
    return 1
  fi
  write_step "Installing bundled Python runtime"
  rm -rf "${installed_python_root}"
  mkdir -p "${installed_python_root}"
  ditto "${bundled_python_root}" "${installed_python_root}"
  xattr -dr com.apple.quarantine "${installed_python_root}" >/dev/null 2>&1 || true
  chmod +x "${installed_python_root}/bin/python3" >/dev/null 2>&1 || true
  chmod +x "${installed_python_root}/python3" >/dev/null 2>&1 || true
  echo "Installed bundled Python runtime to local app support."
  return 0
}

show_python_install_help() {
  local reason="$1"
  echo
  echo "Python 3.10 or newer is required to run this installer."
  echo "需要安装 Python 3.10 或更高版本后再重新双击安装器。"
  echo "Reason: ${reason}"
  echo "Opening official Python macOS download page:"
  echo "${python_download_url}"
  open "${python_download_url}" >/dev/null 2>&1 || true
}

invoke_python() {
  if [[ -z "${python_bin}" ]]; then
    fail "Python 3.10+ is not available. Install Python from python.org, then rerun this installer." 2
  fi
  "${python_bin}" "$@"
}

ensure_python() {
  write_step "Checking Python 3"
  if [[ -n "${python_bin}" && "${python_bin}" == "${bundled_python_root}"/* ]]; then
    install_bundled_python_if_available || true
    python_bin="$(find_python || true)"
  fi
  if [[ -z "${python_bin}" ]]; then
    show_python_install_help "Python was not found on this Mac and no bundled Python runtime is present."
    fail "Install Python 3.10+, close this window, then rerun Install Codex Hybrid.command." 20
  fi
  invoke_python --version
  if ! invoke_python - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(2)
PY
  then
    show_python_install_help "The detected Python is older than 3.10."
    fail "Install Python 3.10+, close this window, then rerun Install Codex Hybrid.command." 20
  fi
}

source_private_env() {
  if [[ -f "${env_file}" ]]; then
    # shellcheck disable=SC1090
    source "${env_file}"
  fi
}

apply_provider_preset() {
  local preset="${provider_preset_path}"
  if [[ -z "${preset}" ]]; then
    preset="${script_dir}/provider-preset.json"
  fi
  if [[ ! -f "${preset}" ]]; then
    return
  fi
  write_step "Loading provider preset"
  eval "$(
    invoke_python - "${preset}" "${provider_id}" "${provider_label}" "${base_url}" "${model}" "${api_key_env}" <<'PY'
import json
import shlex
import sys

path, provider_id, provider_label, base_url, model, api_key_env = sys.argv[1:7]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

values = {
    "provider_id": data.get("provider_id") or provider_id,
    "provider_label": data.get("provider_label") or provider_label,
    "base_url": data.get("base_url") or base_url,
    "model": data.get("model") or model,
    "api_key_env": data.get("api_key_env") or api_key_env,
}
for key, value in values.items():
    print(f"{key}={shlex.quote(str(value))}")
PY
  )"
  echo "Provider preset loaded. API key value is never read from the preset."
}

codex_app_path() {
  local app
  if command -v mdfind >/dev/null 2>&1; then
    while IFS= read -r app; do
      if [[ -d "${app}" && "${app}" == *.app ]]; then
        echo "${app}"
        return 0
      fi
    done < <(mdfind "kMDItemCFBundleIdentifier == 'com.openai.codex'" 2>/dev/null)
  fi
  for app in \
    "/Applications/ChatGPT.app" \
    "${HOME}/Applications/ChatGPT.app" \
    "/Applications/Codex.app" \
    "${HOME}/Applications/Codex.app"; do
    if [[ -d "${app}" ]]; then
      echo "${app}"
      return 0
    fi
  done
  return 1
}

codex_app_info_value() {
  local key="$1"
  local app_path
  app_path="$(codex_app_path 2>/dev/null || true)"
  if [[ -z "${app_path}" || ! -f "${app_path}/Contents/Info.plist" ]]; then
    return 1
  fi
  /usr/libexec/PlistBuddy -c "Print :${key}" "${app_path}/Contents/Info.plist" 2>/dev/null
}

codex_app_name() {
  local app_path
  app_path="$(codex_app_path 2>/dev/null || true)"
  if [[ -z "${app_path}" ]]; then
    echo "Codex Desktop"
    return
  fi
  basename "${app_path}" .app
}

codex_app_present() {
  codex_app_path >/dev/null 2>&1
}

codex_auth_present() {
  [[ -f "${HOME}/.codex/auth.json" ]]
}

codex_running() {
  local process_list
  process_list="$(ps -ww -axo args= 2>/dev/null || true)"
  grep -q -E '/(ChatGPT|Codex)\.app/Contents/MacOS/(ChatGPT|Codex)$|/(ChatGPT|Codex)\.app/Contents/Resources/codex( .*)? app-server|/(ChatGPT|Codex)\.app/Contents/Resources/(codex-command-runner|codex-code-mode-host)' <<<"${process_list}"
}

ensure_codex_ready() {
  if [[ "${skip_codex_check}" == true ]]; then
    return
  fi
  write_step "Checking Codex Desktop"
  if codex_app_present && codex_auth_present; then
    echo "$(codex_app_name) app and Codex sign-in state found."
    return
  fi
  echo "ChatGPT/Codex Desktop is not installed, not opened yet, or not signed in."
  echo "Opening the official Codex app page."
  open "${codex_download_url}" >/dev/null 2>&1 || true
  echo
  echo "Install ChatGPT/Codex Desktop, sign in, fully close it, then run this installer again."
  exit 20
}

open_codex_desktop() {
  local app_path cli_path cli_pid
  echo
  echo "Opening Codex Desktop..."
  app_path="$(codex_app_path 2>/dev/null || true)"
  cli_path="${app_path}/Contents/Resources/codex"
  if [[ -n "${app_path}" && -x "${cli_path}" ]]; then
    "${cli_path}" app "${HOME}" >/dev/null 2>&1 &
    cli_pid="$!"
    sleep 1
    if kill -0 "${cli_pid}" >/dev/null 2>&1; then
      return
    fi
    if wait "${cli_pid}"; then
      return
    fi
  fi
  open -b com.openai.codex >/dev/null 2>&1 \
    || open -a ChatGPT >/dev/null 2>&1 \
    || open -a Codex >/dev/null 2>&1 \
    || open "${codex_download_url}" >/dev/null 2>&1 \
    || true
  echo "If Codex does not appear, open ChatGPT or Codex manually from Applications."
}

open_hot_router_launcher() {
  local launcher="${HOME}/Desktop/Start Codex Hybrid 2.0.command"
  if [[ -x "${launcher}" ]]; then
    echo
    echo "Opening Codex Hybrid 2.0 launcher..."
    open "${launcher}" >/dev/null 2>&1 || true
    return
  fi
  open_codex_desktop
}

copy_project_payload() {
  write_step "Preparing bundled project payload"
  if [[ ! -f "${bundled_project_default}/bootstrap.py" ]]; then
    fail "Bundled project payload was not found. This netdisk package is incomplete." 2
  fi
  mkdir -p "${release_root}"
  rm -rf "${project_path}"
  mkdir -p "${project_path}"
  ditto "${bundled_project_default}" "${project_path}"
  echo "Installed project payload."
}

find_bundled_local_model() {
  if [[ ! -d "${bundled_model_root}" ]]; then
    return 1
  fi
  eval "$(
    invoke_python - "${bundled_model_root}" <<'PY'
import shlex
import sys
from pathlib import Path

root = Path(sys.argv[1])
ggufs = sorted([p for p in root.glob("*.gguf") if p.is_file()], key=lambda p: p.stat().st_size, reverse=True)
model = next((p for p in ggufs if "mmproj" not in p.name.lower()), None)
mmproj = next((p for p in ggufs if "mmproj" in p.name.lower()), None)
if not model or not mmproj:
    raise SystemExit(1)
print(f"bundled_model_path={shlex.quote(str(model))}")
print(f"bundled_mmproj_path={shlex.quote(str(mmproj))}")
PY
  )" || return 1
  [[ -n "${bundled_model_path:-}" && -n "${bundled_mmproj_path:-}" ]]
}

copy_file_if_changed() {
  local source="$1"
  local destination="$2"
  if [[ -f "${destination}" ]]; then
    local source_size destination_size
    source_size="$(stat -f %z "${source}")"
    destination_size="$(stat -f %z "${destination}")"
    if [[ "${source_size}" == "${destination_size}" ]]; then
      return
    fi
  fi
  cp -p "${source}" "${destination}"
}

install_bundled_local_model() {
  if ! find_bundled_local_model; then
    return 1
  fi
  write_step "Installing bundled local model files"
  local target="${model_root}/local-gemma"
  mkdir -p "${target}"
  echo "Copying about $(format_size_gb "${bundled_model_root}") GB of local model files. Please wait; this can take several minutes."
  while IFS= read -r -d '' file; do
    copy_file_if_changed "${file}" "${target}/$(basename "${file}")"
  done < <(find "${bundled_model_root}" -maxdepth 1 -type f -print0)
  eval "$(
    invoke_python - "${target}" <<'PY'
import shlex
import sys
from pathlib import Path

root = Path(sys.argv[1])
ggufs = sorted([p for p in root.glob("*.gguf") if p.is_file()], key=lambda p: p.stat().st_size, reverse=True)
model = next((p for p in ggufs if "mmproj" not in p.name.lower()), None)
mmproj = next((p for p in ggufs if "mmproj" in p.name.lower()), None)
if not model or not mmproj:
    raise SystemExit(1)
print(f"local_model_path={shlex.quote(str(model))}")
print(f"local_mmproj_path={shlex.quote(str(mmproj))}")
PY
  )"
  echo "Bundled local model installed under local app support."
}

resolve_llama_backend() {
  case "${llama_backend}" in
    auto)
      case "$(uname -m)" in
        arm64) echo "macos-arm64" ;;
        x86_64) echo "macos-x64" ;;
        *) fail "Unsupported Mac architecture for bundled llama.cpp: $(uname -m)" 2 ;;
      esac
      ;;
    macos-x64|macos-arm64)
      echo "${llama_backend}"
      ;;
    *)
      fail "Invalid --llama-backend: ${llama_backend}. Use auto, macos-x64, or macos-arm64." 2
      ;;
  esac
}

install_bundled_llama_runtime() {
  local backend
  backend="$(resolve_llama_backend)"
  local source_root="${bundled_llama_root}/${backend}"
  if [[ ! -d "${source_root}" ]]; then
    fail "Bundled llama.cpp runtime was not found for ${backend}." 2
  fi
  local source_server
  source_server="$(find "${source_root}" -type f -name "llama-server" | head -n 1)"
  if [[ -z "${source_server}" ]]; then
    fail "Bundled llama-server was not found for ${backend}." 2
  fi
  write_step "Installing bundled llama.cpp runtime (${backend})"
  local target="${llama_root}/${backend}"
  rm -rf "${target}"
  mkdir -p "${target}"
  ditto "${source_root}" "${target}"
  xattr -dr com.apple.quarantine "${target}" >/dev/null 2>&1 || true
  local installed_server
  installed_server="$(find "${target}" -type f -name "llama-server" | head -n 1)"
  if [[ -z "${installed_server}" ]]; then
    fail "Installed llama-server was not found for ${backend}." 2
  fi
  chmod +x "${installed_server}" || true
  if ! "${installed_server}" --version >/dev/null 2>&1; then
    fail "Installed llama-server did not pass --version. Use diagnostics and check macOS architecture." 2
  fi
  llama_server_path="${installed_server}"
  echo "llama-server runtime check passed."
}

backup_private_config() {
  if [[ ! -f "${config_path}" ]]; then
    return
  fi
  local stamp
  stamp="$(date +%Y%m%d-%H%M%S)"
  cp -p "${config_path}" "${config_path}.bak-codex-hybrid-${stamp}"
  echo "Backed up private config."
}

read_required() {
  local prompt="$1"
  local default_value="${2:-}"
  local value
  if [[ "${non_interactive}" == true ]]; then
    if [[ -n "${default_value}" ]]; then
      printf "%s" "${default_value}"
      return
    fi
    fail "${prompt} is required in --non-interactive mode." 2
  fi
  if [[ -n "${default_value}" ]]; then
    read -r -p "${prompt} [${default_value}]: " value
    printf "%s" "${value:-$default_value}"
  else
    read -r -p "${prompt}: " value
    if [[ -z "${value}" ]]; then
      fail "${prompt} is required." 2
    fi
    printf "%s" "${value}"
  fi
}

write_private_env_value() {
  local env_name="$1"
  local value="$2"
  mkdir -p "${runtime_root}"
  invoke_python - "${env_file}" "${env_name}" "${value}" <<'PY'
import os
import re
import shlex
import sys
from pathlib import Path

path = Path(sys.argv[1]).expanduser()
name = sys.argv[2]
value = sys.argv[3]
if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
    print("Invalid environment variable name.")
    raise SystemExit(2)
path.parent.mkdir(parents=True, exist_ok=True)
exports = {}
if path.exists():
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if match:
            exports[match.group(1)] = match.group(2)
exports[name] = shlex.quote(value)
lines = ["# Codex Hybrid private environment. Do not commit or share this file."]
for key in sorted(exports):
    lines.append(f"export {key}={exports[key]}")
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
os.chmod(path, 0o600)
PY
}

write_api_key_env_file() {
  write_private_env_value "$1" "$2"
}

persist_python_env_if_needed() {
  if [[ -n "${python_bin}" && ( "${python_bin}" == "${installed_python_root}"/* || "${python_bin}" == "${bundled_python_root}"/* ) ]]; then
    write_private_env_value "PYTHON" "${python_bin}"
  fi
}

ensure_api_key_environment() {
  local name="$1"
  if [[ ! "${name}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    fail "Invalid API key environment variable name: ${name}" 2
  fi
  source_private_env
  if [[ -n "${!name:-}" ]]; then
    echo "API key environment variable is set: ${name}"
    return
  fi
  if [[ "${non_interactive}" == true ]]; then
    echo "API key environment variable is not set: ${name}"
    echo "The installer will continue to dry-run and print env help."
    return
  fi
  echo
  echo "Paste the provider API key for environment variable ${name}."
  echo "Input is hidden. Leave blank to skip and set it later."
  local secret
  read -r -s -p "API key: " secret
  echo
  if [[ -z "${secret}" ]]; then
    echo "No API key was entered. You can set it later."
    return
  fi
  write_api_key_env_file "${name}" "${secret}"
  source_private_env
  echo "API key was stored in the private user env file with permission 600."
}

invoke_switcher() {
  source_private_env
  PYTHONPATH="${project_path}/src" invoke_python -m codex_hybrid_switcher "$@"
}

write_config() {
  write_step "Creating private config"
  backup_private_config
  local args=(
    setup
    --output "${config_path}" \
    --platform macos \
    --codex-home "${HOME}/.codex" \
    --wire-api responses \
    --cloud-route bridge \
    --non-interactive \
    --force
  )
  if [[ "${include_cloud}" == true ]]; then
    args+=(
    --provider-id "${provider_id}" \
    --provider-label "${provider_label}" \
    --base-url "${base_url}" \
    --model "${model}" \
      --api-key-env "${api_key_env}"
    )
  else
    args+=(--skip-cloud)
  fi
  if [[ "${include_local}" == true ]]; then
    args+=(
      --include-local
      --llama-server-path "${llama_server_path}"
      --model-path "${local_model_path}"
      --mmproj-path "${local_mmproj_path}"
    )
  fi
  invoke_switcher "${args[@]}"
}

install_desktop_launcher() {
  write_step "Installing desktop switcher launcher"
  bash "${project_path}/scripts/install-macos-launcher.sh"
}

run_bridge_health() {
  write_step "Checking bridge health"
  if ! invoke_switcher bridge-health --config "${config_path}"; then
    echo "Bridge health reported a setup gap. This can be expected before final apply or before the bridge is started."
  fi
}

stop_managed_bridge_on_port() {
  local port="$1"
  local pids pid cmd
  pids="$(lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -z "${pids}" ]]; then
    return
  fi
  if codex_running; then
    echo "Bridge port ${port} is in use, but Codex Desktop is running."
    echo "The installer will not stop an existing bridge while Codex is open. Quit Codex completely and rerun the installer."
    return
  fi
  while IFS= read -r pid; do
    [[ -z "${pid}" ]] && continue
    cmd="$(ps -p "${pid}" -o command= 2>/dev/null || true)"
    if [[ "${cmd}" == *"codex_hybrid_switcher bridge"* || "${cmd}" == *"${install_root}"* ]]; then
      echo "Stopping previous Codex Hybrid bridge on port ${port} (PID ${pid})."
      kill "${pid}" >/dev/null 2>&1 || true
    else
      echo "Port ${port} is already in use by a non-managed process (PID ${pid}). Local smoke may fail until that process exits."
    fi
  done <<<"${pids}"
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if ! lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      return
    fi
    sleep 0.5
  done
}

run_guarded_dry_run() {
  write_step "Running guarded provider dry-run"
  local args=(--provider-id "${switch_provider_id}" --config "${config_path}")
  if [[ "${switch_provider_id}" == "local-gemma" ]]; then
    args+=(--allow-local)
    if [[ "${local_smoke_passed}" == true || "${skip_local_smoke}" == true ]]; then
      args+=(--skip-local-smoke)
    fi
  fi
  bash "${project_path}/scripts/macos-provider-switch.sh" "${args[@]}"
}

run_guarded_apply() {
  write_step "Applying guarded provider switch"
  local args=(--provider-id "${switch_provider_id}" --config "${config_path}" --apply)
  if [[ "${switch_provider_id}" == "local-gemma" ]]; then
    args+=(--allow-local)
    if [[ "${local_smoke_passed}" == true || "${skip_local_smoke}" == true ]]; then
      args+=(--skip-local-smoke)
    fi
  fi
  bash "${project_path}/scripts/macos-provider-switch.sh" "${args[@]}"
  if [[ "${history_unify_requested}" == true ]]; then
    run_history_unify_apply
  fi
  open_hot_router_launcher
}

run_local_smoke() {
  if [[ "${skip_local_smoke}" == true ]]; then
    echo "Skipping local smoke because --skip-local-smoke was provided."
    local_smoke_passed=true
    return
  fi
  write_step "Running local llama.cpp smoke test"
  stop_managed_bridge_on_port 19030
  if invoke_switcher local-smoke --config "${config_path}" --request-timeout "${local_smoke_timeout}"; then
    local_smoke_passed=true
    return
  fi
  fail "Local smoke failed. No real Codex switch was applied. Run diagnostics or retry with --skip-local-smoke only for troubleshooting." 1
}

resolve_history_unify() {
  history_unify_requested=false
  if [[ "${skip_history_unify}" == true ]]; then
    echo "History unification skipped by option."
    return
  fi
  write_step "Checking optional history unification"
  if ! invoke_switcher history-status --config "${config_path}"; then
    echo "History status could not be read. History unification will be skipped."
    return
  fi
  if [[ "${unify_history}" == true ]]; then
    echo "History unification enabled by option."
    history_unify_requested=true
    return
  fi
  if [[ "${non_interactive}" == true ]]; then
    echo "History unification is disabled in non-interactive mode unless --unify-history is provided."
    return
  fi
  echo
  echo "Codex Desktop shows project chats by provider bucket."
  echo "To keep existing official project chats visible after switching to custom, this installer can migrate openai history rows to custom/${switch_model}."
  echo "A state_5.sqlite backup and changed session backups are created first. Press Enter to skip."
  local confirm
  read -r -p "Type MIGRATE to enable history unification: " confirm
  if [[ "${confirm}" == "MIGRATE" ]]; then
    history_unify_requested=true
  fi
}

run_history_unify_dry_run() {
  write_step "Running history unification dry-run"
  invoke_switcher unify-history --config "${config_path}" --from-provider openai --to-provider custom --to-model "${switch_model}" --dry-run
}

run_history_unify_apply() {
  write_step "Applying history unification"
  invoke_switcher unify-history --config "${config_path}" --from-provider openai --to-provider custom --to-model "${switch_model}" --apply
}

prompt_apply_after_dry_run() {
  if [[ "${dry_run_only}" == true || "${non_interactive}" == true ]]; then
    echo "Next: review the dry-run, fully quit Codex Desktop, then rerun with --apply only when you are ready."
    return
  fi
  echo
  echo "If Codex Desktop is fully closed and you want to apply now, type APPLY exactly."
  echo "Press Enter to exit without changing Codex."
  local confirm
  read -r -p "Apply now: " confirm
  if [[ "${confirm}" != "APPLY" ]]; then
    echo "Cancelled. No real Codex switch was applied."
    return
  fi
  run_guarded_apply
}

free_space_gb() {
  df -g "${HOME}" | awk 'NR==2 {print $4}'
}

write_diagnostics_report() {
  mkdir -p "${HOME}/Desktop"
  local report="${HOME}/Desktop/codex-hybrid-macos-installer-diagnostics.txt"
  local python_state="false"
  local app_state="false"
  local auth_state="false"
  local running_state="false"
  local config_state="false"
  local env_file_state="false"
  local env_set_state="false"
  local payload_state="false"
  local payload_llama_x64="false"
  local payload_llama_arm64="false"
  local payload_local_model="false"
  local bundled_python_present="false"
  local codex_app_path_state="not-found"
  local codex_app_name_state="not-found"
  local codex_app_bundle_id_state="not-found"
  local codex_app_version_state="not-found"
  local codex_cli_version_state="not-found"
  local installed_llama="false"
  local installed_local_model="false"
  local local_provider_enabled="false"
  local python_version_state="not-found"
  local python_min_version_ok="false"
  [[ -n "${python_bin}" ]] && python_state="true"
  [[ -x "${bundled_python_root}/bin/python3" || -x "${bundled_python_root}/python3" ]] && bundled_python_present="true"
  if [[ -n "${python_bin}" ]]; then
    python_version_state="$("${python_bin}" --version 2>&1 || true)"
    if "${python_bin}" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
    then
      python_min_version_ok="true"
    fi
  fi
  codex_app_present && app_state="true"
  codex_app_path_state="$(codex_app_path 2>/dev/null || echo "not-found")"
  codex_app_name_state="$(codex_app_name)"
  codex_app_bundle_id_state="$(codex_app_info_value CFBundleIdentifier 2>/dev/null || echo "not-found")"
  codex_app_version_state="$(codex_app_info_value CFBundleShortVersionString 2>/dev/null || echo "not-found")"
  if [[ "${codex_app_path_state}" != "not-found" && -x "${codex_app_path_state}/Contents/Resources/codex" ]]; then
    codex_cli_version_state="$("${codex_app_path_state}/Contents/Resources/codex" --version 2>/dev/null || echo "not-found")"
  fi
  codex_auth_present && auth_state="true"
  codex_running && running_state="true"
  [[ -f "${config_path}" ]] && config_state="true"
  [[ -f "${env_file}" ]] && env_file_state="true"
  [[ -f "${bundled_project_default}/bootstrap.py" ]] && payload_state="true"
  [[ -n "$(find "${bundled_llama_root}/macos-x64" -type f -name "llama-server" 2>/dev/null | head -n 1)" ]] && payload_llama_x64="true"
  [[ -n "$(find "${bundled_llama_root}/macos-arm64" -type f -name "llama-server" 2>/dev/null | head -n 1)" ]] && payload_llama_arm64="true"
  find_bundled_local_model >/dev/null 2>&1 && payload_local_model="true"
  [[ -n "$(find "${llama_root}" -type f -name "llama-server" 2>/dev/null | head -n 1)" ]] && installed_llama="true"
  [[ -d "${model_root}/local-gemma" && -n "$(find "${model_root}/local-gemma" -maxdepth 1 -type f -name "*.gguf" 2>/dev/null | head -n 1)" ]] && installed_local_model="true"
  if [[ -f "${config_path}" ]]; then
    invoke_python - "${config_path}" <<'PY' >/tmp/codex_hybrid_local_provider_check.$$ 2>/dev/null || true
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(any(p.get("kind") == "local" for p in data.get("providers", []) if isinstance(p, dict)))
PY
    [[ "$(cat /tmp/codex_hybrid_local_provider_check.$$ 2>/dev/null)" == "True" ]] && local_provider_enabled="true"
    rm -f /tmp/codex_hybrid_local_provider_check.$$
  fi
  source_private_env
  [[ -n "${!api_key_env:-}" ]] && env_set_state="true"
  {
    echo "Codex Hybrid macOS Installer Diagnostics"
    echo "generated_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "version=${release_tag}"
    echo "macos=$(sw_vers -productVersion 2>/dev/null || true)"
    echo "arch=$(uname -m)"
    echo "python_found=${python_state}"
    echo "python_version=${python_version_state}"
    echo "python_min_version_ok=${python_min_version_ok}"
    echo "python_install_help_url=${python_download_url}"
    echo "bundled_python_present=${bundled_python_present}"
    echo "codex_app_present=${app_state}"
    echo "codex_app_name=${codex_app_name_state}"
    echo "codex_app_path=${codex_app_path_state}"
    echo "codex_app_bundle_id=${codex_app_bundle_id_state}"
    echo "codex_app_version=${codex_app_version_state}"
    echo "codex_cli_version=${codex_cli_version_state}"
    echo "codex_auth_present=${auth_state}"
    echo "codex_process_running=${running_state}"
    echo "private_config_present=${config_state}"
    echo "private_env_file_present=${env_file_state}"
    echo "api_key_env_name=${api_key_env}"
    echo "api_key_env_set=${env_set_state}"
    echo "bundled_project_payload=${payload_state}"
    echo "bundled_llama_macos_x64=${payload_llama_x64}"
    echo "bundled_llama_macos_arm64=${payload_llama_arm64}"
    echo "bundled_local_model=${payload_local_model}"
    echo "installed_llama_cpp=${installed_llama}"
    echo "installed_local_model=${installed_local_model}"
    echo "local_provider_enabled=${local_provider_enabled}"
    echo "install_drive_free_gb=$(free_space_gb)"
    echo
    echo "This report does not include API keys, tokens, raw Codex databases, session content, provider hostnames, local file contents, or full local paths."
  } >"${report}"
  echo "Wrote diagnostics report: ${report}"
}

echo "Codex Hybrid Model Switcher macOS one-click setup"
echo "Release: ${release_tag}"
echo "Default mode: guarded dry-run first. A real switch requires APPLY after Codex is closed."

ensure_python
persist_python_env_if_needed
apply_provider_preset
source_private_env
show_disk_space_check

if [[ "${diagnostics_only}" == true ]]; then
  write_diagnostics_report
  exit 0
fi

ensure_codex_ready
copy_project_payload

if install_bundled_local_model; then
  install_bundled_llama_runtime
  include_local=true
else
  echo "No bundled local model payload detected."
fi

if [[ "${skip_cloud}" == true ]]; then
  include_cloud=false
elif [[ -n "${base_url}" ]]; then
  include_cloud=true
elif [[ "${include_local}" == true ]]; then
  include_cloud=false
  echo "No cloud base_url was provided. Continuing with local-only setup."
  echo "You can rerun later with --base-url, --model, and --api-key-env to add a cloud provider."
else
  include_cloud=true
fi

if [[ "${include_cloud}" == true ]]; then
  if [[ -z "${base_url}" ]]; then
    base_url="$(read_required "OpenAI-compatible base_url" "${base_url}")"
  fi
  if [[ -z "${model}" ]]; then
    model="$(read_required "Cloud model id" "provider-gpt-main")"
  fi
  api_key_env="$(read_required "API key environment variable name" "${api_key_env}")"
  ensure_api_key_environment "${api_key_env}"
fi

if [[ "${include_local}" != true && "${include_cloud}" != true ]]; then
  fail "No usable provider was configured. Provide cloud settings or use a full local package with bundled model files." 2
fi

switch_provider_id="${provider_id}"
if [[ "${include_cloud}" != true && "${include_local}" == true ]]; then
  switch_provider_id="local-gemma"
fi
switch_model="${model}"
if [[ "${switch_provider_id}" == "local-gemma" ]]; then
  switch_model="local/gemma"
fi

write_config

write_step "Validating private config"
validate_args=(validate-config --config "${config_path}")
if [[ "${include_local}" == true ]]; then
  validate_args+=(--check-paths)
fi
invoke_switcher "${validate_args[@]}"

if [[ "${include_local}" == true ]]; then
  run_local_smoke
fi

resolve_history_unify
if [[ "${history_unify_requested}" == true ]]; then
  run_history_unify_dry_run
fi

install_desktop_launcher
run_bridge_health
run_guarded_dry_run

if [[ "${apply}" == true ]]; then
  run_guarded_apply
else
  echo
  echo "INSTALLER DRY-RUN COMPLETE"
  echo "No real Codex switch was applied."
  if [[ "${history_unify_requested}" == true ]]; then
    echo "History unification status: enabled for real apply. A state_5.sqlite backup will be created before migration."
  else
    echo "History unification status: skipped. Existing openai project chats may be hidden while using custom."
  fi
  prompt_apply_after_dry_run
fi
