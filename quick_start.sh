#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

PYTHON_BIN="python3"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python not found. Install Python 3.8+ first."
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

run_doctor() {
  activate_env
  python "${ROOT_DIR}/test_system.py"
}

run_esp32() {
  activate_env
  python "${ROOT_DIR}/vision_server.py"
}

run_phone() {
  activate_env
  python "${ROOT_DIR}/smartphone_camera.py"
}

run_udp_server() {
  activate_env
  printf "1\n" | python "${ROOT_DIR}/udp_streaming.py"
}

run_udp_client() {
  local server_ip="${1:-192.168.4.1}"
  activate_env
  {
    printf "2\n"
    printf "%s\n" "${server_ip}"
    printf "0\n"
  } | python "${ROOT_DIR}/udp_streaming.py"
}

show_help() {
  cat <<EOF
WVAB quick start

Usage:
  ./quick_start.sh setup
  ./quick_start.sh doctor
  ./quick_start.sh run esp32
  ./quick_start.sh run phone
  ./quick_start.sh run udp-server
  ./quick_start.sh run udp-client [server_ip]

Examples:
  ./quick_start.sh setup
  ./quick_start.sh doctor
  ./quick_start.sh run esp32
  ./quick_start.sh run phone
  ./quick_start.sh run udp-client 192.168.1.10
EOF
}

main() {
  local cmd="${1:-help}"
  case "${cmd}" in
    setup)
      setup_env
      ;;
    doctor)
      run_doctor
      ;;
    run)
      local mode="${2:-}"
      case "${mode}" in
        esp32) run_esp32 ;;
        phone) run_phone ;;
        udp-server) run_udp_server ;;
        udp-client) run_udp_client "${3:-}" ;;
        *) show_help; exit 1 ;;
      esac
      ;;
    help|-h|--help)
      show_help
      ;;
    *)
      show_help
      exit 1
      ;;
  esac
}

main "$@"
