#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_DIR/vivado/build/p04_reset_debug"
BIT_FILE="$REPORT_DIR/p04_reset_diag.bit"
LTX_FILE="$REPORT_DIR/p04_reset_diag.ltx"
TCL_SCRIPT="$SCRIPT_DIR/p04_reset_diagnostic.tcl"
HW_SERVER_URL="${HW_SERVER_URL:-localhost:3121}"
LOG_FILE="$SCRIPT_DIR/build/p04_reset_diagnostic.log"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi
for artifact in "$BIT_FILE" "$LTX_FILE" "$TCL_SCRIPT"; do
    [[ -f "$artifact" ]] || {
        echo "ERROR: P04 reset diagnostic artifact missing: $artifact" >&2
        echo "Run vivado/run_p04_reset_debug.sh first." >&2
        exit 3
    }
done
mkdir -p "$(dirname "$LOG_FILE")"

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$HW_SERVER_URL" \
    2>&1 | tee "$LOG_FILE"

echo
echo '=== P04 reset diagnostic summary ==='
grep 'P04 RESET DIAG' "$LOG_FILE" || true
