#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run with sudo: sudo bash deployment/rpi/install_service.sh" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -n "${SUDO_USER:-}" ]]; then
  RUN_USER="$SUDO_USER"
else
  RUN_USER="$(stat -c '%U' "$ROOT_DIR")"
fi
ENV_FILE="$ROOT_DIR/deployment/rpi/wvab_edge.env"
TEMPLATE="$SCRIPT_DIR/wvab_edge.service.template"
TARGET="/etc/systemd/system/wvab_edge.service"

if [[ -z "$RUN_USER" || "$RUN_USER" =~ [[:space:]] ]]; then
  echo "ERROR: invalid service user: '$RUN_USER'" >&2
  exit 2
fi
if [[ "$ROOT_DIR" =~ [[:space:]] ]]; then
  echo "ERROR: install WVAB in a path without whitespace before creating the service." >&2
  exit 2
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE does not exist." >&2
  echo "Generate it first with: python3 tools/generate_device_secrets.py" >&2
  exit 2
fi
if [[ ! -f "$TEMPLATE" ]]; then
  echo "ERROR: service template not found: $TEMPLATE" >&2
  exit 2
fi
chmod +x "$ROOT_DIR/deployment/rpi/wvab_edge_start.sh"

# Render without eval or shell expansion of replacement values.
python3 - "$TEMPLATE" "$TARGET" "$ROOT_DIR" "$RUN_USER" <<'PY'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
target_path = Path(sys.argv[2])
root = sys.argv[3]
user = sys.argv[4]
if not user or any(ch.isspace() for ch in user):
    raise SystemExit("invalid service user")
if any(ch.isspace() for ch in root):
    raise SystemExit("service root may not contain whitespace")
text = template_path.read_text(encoding="utf-8")
if "@ROOT@" not in text or "@USER@" not in text:
    raise SystemExit("service template placeholders are missing")
text = text.replace("@ROOT@", root).replace("@USER@", user)
target_path.write_text(text, encoding="utf-8")
PY

systemctl daemon-reload
systemctl enable wvab_edge.service
systemctl restart wvab_edge.service
systemctl --no-pager --full status wvab_edge.service
