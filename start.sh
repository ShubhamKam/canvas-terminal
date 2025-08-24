#!/data/data/com.termux/files/usr/bin/bash
# POSIX-ish launcher for Android Termux / Linux / macOS
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PY=${PYTHON_BIN:-python3}
exec "$PY" "$SCRIPT_DIR/start.py" "$@"
