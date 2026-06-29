#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
LOG_DIR="${ROOT_DIR}/logs"
PID_DIR="${ROOT_DIR}/pids"

mkdir -p "${LOG_DIR}" "${PID_DIR}"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Virtualenv not found at ${VENV_DIR}. Run ./microservices/install_deps.sh first."
  exit 1
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

start_service() {
  local name="$1"
  local port="$2"
  local dir="${ROOT_DIR}/${name}"
  local pid_file="${PID_DIR}/${name}.pid"
  local log_file="${LOG_DIR}/${name}.log"

  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name} already running on pid $(cat "${pid_file}")"
    return
  fi

  (
    cd "${dir}"
    export SERVICE_PORT="${port}"
    uvicorn service.main:app --host 127.0.0.1 --port "${SERVICE_PORT}" >"${log_file}" 2>&1 &
    echo $! > "${pid_file}"
  )

  echo "Started ${name} on port ${port}"
}

# Runbook startup order
start_service auditor 8005
start_service client_index 8002
start_service data_handling 8004
start_service payments 8003
start_service support_hub 8008
start_service workforce_ops 8009
start_service watchdog 8007
start_service orchestrator 8006

echo "All microservices start commands issued."
