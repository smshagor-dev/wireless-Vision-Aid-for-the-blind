#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 tool/materialize_branding.py

flutter create \
  --platforms=android \
  --org com.smshagor \
  --project-name wvab_mobile \
  .

python3 tool/configure_android.py
dart run flutter_launcher_icons

echo "Android host project ready with WVAB launcher branding."
