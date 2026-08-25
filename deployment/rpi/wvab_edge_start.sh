#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${WVAB_EDGE_ENV_FILE:-$ROOT_DIR/deployment/rpi/wvab_edge.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: missing $ENV_FILE" >&2
  echo "Generate credentials with: python3 tools/generate_device_secrets.py" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

export WVAB_OFFLINE="${WVAB_OFFLINE:-1}"
export WVAB_ALLOW_INSECURE_UDP=0

UDP_TOKEN="${WVAB_UDP_TOKEN:-}"
WS_TOKEN="${WVAB_WS_TOKEN:-}"
if [[ "${WVAB_UDP_AUTH:-}" != "1" || "${WVAB_UDP_ENCRYPT:-}" != "1" ]]; then
  echo "ERROR: WVAB edge deployment requires UDP authentication and encryption." >&2
  exit 2
fi
if (( ${#UDP_TOKEN} < 16 )); then
  echo "ERROR: WVAB_UDP_TOKEN must be at least 16 characters." >&2
  exit 2
fi
if [[ ! "${WVAB_UDP_KEY_HEX:-}" =~ ^([0-9A-Fa-f]{32}|[0-9A-Fa-f]{48}|[0-9A-Fa-f]{64})$ ]]; then
  echo "ERROR: WVAB_UDP_KEY_HEX must contain a 16, 24, or 32-byte hexadecimal key." >&2
  exit 2
fi
if [[ "${WVAB_WS_CONTROL:-1}" == "1" && "${WVAB_WS_CONTROL_HOST:-127.0.0.1}" != "127.0.0.1" ]] && (( ${#WS_TOKEN} < 16 )); then
  echo "ERROR: remote WebSocket control requires a dedicated WVAB_WS_TOKEN." >&2
  exit 2
fi

PYTHON_BIN="${WVAB_PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN not found" >&2
  exit 2
fi
if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  echo "ERROR: WVAB requires Python 3.10 or newer." >&2
  exit 2
fi

MODEL_PATH="${WVAB_MODEL_PATH:-yolov8n.pt}"
if [[ ! -f "$MODEL_PATH" ]]; then
  echo "ERROR: model not found: $MODEL_PATH" >&2
  exit 2
fi

exec "$PYTHON_BIN" udp_streaming.py server \
  --host "${WVAB_UDP_BIND_HOST:-0.0.0.0}" \
  --port "${WVAB_UDP_PORT:-9999}" \
  --model "$MODEL_PATH" \
  --language "${WVAB_LANGUAGE:-en}" \
  --headless \
  --auto-restart
