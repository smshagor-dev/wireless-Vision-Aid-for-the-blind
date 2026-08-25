#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python not found. Install Python 3.10+ first." >&2
  exit 1
fi

if ! "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  echo "WVAB requires Python 3.10 or newer." >&2
  exit 1
fi

setup_env() {
  echo "[setup] Creating virtual environment in ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install -r "${ROOT_DIR}/requirements.txt"
  echo "[setup] Done"
}

activate_env() {
  if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Virtual environment not found. Running setup first."
    setup_env
  fi
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
}

require_udp_credentials() {
  local token="${WVAB_UDP_TOKEN:-}"
  if (( ${#token} < 16 )); then
    echo "ERROR: export a unique WVAB_UDP_TOKEN of at least 16 characters before using UDP mode." >&2
    exit 2
  fi
  if [[ ! "${WVAB_UDP_KEY_HEX:-}" =~ ^([0-9A-Fa-f]{32}|[0-9A-Fa-f]{48}|[0-9A-Fa-f]{64})$ ]]; then
    echo "ERROR: WVAB_UDP_KEY_HEX must be a 16, 24, or 32-byte hexadecimal key." >&2
    exit 2
  fi
}

run_doctor() {
  activate_env
  python "${ROOT_DIR}/test_system.py" "$@"
}

run_esp32_edge() {
  activate_env
  export WVAB_PYTHON_BIN="$(command -v python)"
  bash "${ROOT_DIR}/deployment/rpi/wvab_edge_start.sh"
}

run_phone() {
  activate_env
  python "${ROOT_DIR}/smartphone_camera.py"
}

run_udp_server() {
  activate_env
  require_udp_credentials
  python "${ROOT_DIR}/udp_streaming.py" server --config "${ROOT_DIR}/wvab_config.sample.json"
}

run_udp_client() {
  local server_ip="${1:-192.168.4.1}"
  activate_env
  require_udp_credentials
  python "${ROOT_DIR}/udp_streaming.py" client \
    --config "${ROOT_DIR}/wvab_config.sample.json" \
    --server-ip "${server_ip}" \
    --camera 0
}

show_help() {
  cat <<'EOF'
WVAB quick start

Usage:
  ./quick_start.sh setup
  ./quick_start.sh doctor [--full] [--camera SOURCE] [--tts] [--deployment]
  ./quick_start.sh run esp32
  ./quick_start.sh run phone
  ./quick_start.sh run udp-server
  ./quick_start.sh run udp-client [server_ip]

ESP32 edge mode uses the generated deployment/rpi/wvab_edge.env file:
  python tools/generate_device_secrets.py --server-ip 192.168.4.2
  ./quick_start.sh doctor --deployment
  ./quick_start.sh run esp32

Python UDP modes require these environment variables:
  WVAB_UDP_KEY_HEX=<16/24/32-byte hex key>
  WVAB_UDP_TOKEN=<unique token, at least 16 chars>

Examples:
  ./quick_start.sh setup
  ./quick_start.sh doctor --full --camera 0
  ./quick_start.sh run esp32
  ./quick_start.sh run phone
  ./quick_start.sh run udp-server
  ./quick_start.sh run udp-client 192.168.1.10
EOF
}

main() {
  local cmd="${1:-help}"
  case "${cmd}" in
    setup) setup_env ;;
    doctor)
      shift
      run_doctor "$@"
      ;;
    run)
      local mode="${2:-}"
      case "${mode}" in
        esp32) run_esp32_edge ;;
        phone) run_phone ;;
        udp-server) run_udp_server ;;
        udp-client) run_udp_client "${3:-}" ;;
        *) show_help; exit 1 ;;
      esac
      ;;
    help|-h|--help) show_help ;;
    *) show_help; exit 1 ;;
  esac
}

main "$@"
