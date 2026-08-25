#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${WVAB_EDGE_ENV_FILE:-$ROOT_DIR/deployment/rpi/wvab_edge.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: missing $ENV_FILE" >&2
  echo "Generate a matched device pair first: python3 tools/generate_device_secrets.py" >&2
  exit 2
fi

# Validate the generated port before Compose uses it for host/container mapping.
UDP_PORT="$(awk -F= '$1 == "WVAB_UDP_PORT" {print $2}' "$ENV_FILE" | tail -n1 | tr -d '\r')"
if [[ ! "$UDP_PORT" =~ ^[0-9]+$ ]] || (( UDP_PORT < 1 || UDP_PORT > 65535 )); then
  echo "ERROR: invalid WVAB_UDP_PORT in $ENV_FILE" >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed" >&2
  exit 2
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Compose v2 is required" >&2
  exit 2
fi

cd "$ROOT_DIR"
if (( $# == 0 )); then
  set -- up
fi

# --env-file is required so the generated custom UDP port is available to
# Compose interpolation as well as to the container service environment.
exec docker compose --env-file "$ENV_FILE" "$@"
