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
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

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
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "ERROR: project virtualenv Python not found: $VENV_PYTHON" >&2
  echo "Create it first: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 2
fi
if ! "$VENV_PYTHON" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  echo "ERROR: WVAB service virtualenv must use Python 3.10+." >&2
  exit 2
fi
chmod +x "$ROOT_DIR/deployment/rpi/wvab_edge_start.sh"

# Render without eval or shell expansion of replacement values.
python3 - "$TEMPLATE" "$TARGET" "$ROOT_DIR" "$RUN_USER" "$VENV_PYTHON" <<'PY'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
target_path = Path(sys.argv[2])
root = sys.argv[3]
user = sys.argv[4]
python_bin = sys.argv[5]
if not user or any(ch.isspace() for ch in user):
    raise SystemExit("invalid service user")
if any(ch.isspace() for ch in root) or any(ch.isspace() for ch in python_bin):
    raise SystemExit("service root/python path may not contain whitespace")
text = template_path.read_text(encoding="utf-8")
for placeholder in ("@ROOT@", "@USER@", "@PYTHON@"):
    if placeholder not in text:
        raise SystemExit(f"service template placeholder is missing: {placeholder}")
text = (
    text.replace("@ROOT@", root)
    .replace("@USER@", user)
    .replace("@PYTHON@", python_bin)
)
target_path.write_text(text, encoding="utf-8")
PY

systemctl daemon-reload
systemctl enable wvab_edge.service
systemctl restart wvab_edge.service
systemctl --no-pager --full status wvab_edge.service
