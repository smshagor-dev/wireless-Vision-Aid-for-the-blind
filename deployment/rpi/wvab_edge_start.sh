#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/deployment/rpi/wvab_edge.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ "${WVAB_UDP_AUTH:-1}" != "1" || "${WVAB_UDP_ENCRYPT:-1}" != "1" ]]; then
  echo "ERROR: WVAB edge deployment requires UDP authentication and encryption." >&2
  exit 2
fi

if [[ -z "${WVAB_UDP_TOKEN:-}" ]]; then
  echo "ERROR: set a unique WVAB_UDP_TOKEN in deployment/rpi/wvab_edge.env" >&2
  exit 2
fi

if [[ ! "${WVAB_UDP_KEY_HEX:-}" =~ ^([0-9A-Fa-f]{32}|[0-9A-Fa-f]{48}|[0-9A-Fa-f]{64})$ ]]; then
  echo "ERROR: WVAB_UDP_KEY_HEX must contain a 16, 24, or 32-byte hexadecimal key." >&2
  exit 2
fi

exec python udp_streaming.py server \
  --host 0.0.0.0 \
  --port 9999 \
  --language en \
  --headless \
  --auto-restart
