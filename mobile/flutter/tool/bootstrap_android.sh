#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

flutter create \
  --platforms=android \
  --org com.smshagor \
  --project-name wvab_mobile \
  .

python3 tool/configure_android.py

echo "Android host project ready."
