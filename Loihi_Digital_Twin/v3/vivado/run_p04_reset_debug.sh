#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BASE_BUILD_DIR="$SCRIPT_DIR/build/p04_impl"
PROJECT_XPR="$BASE_BUILD_DIR/project/loihi_twin_v2_p04_impl.xpr"
DEBUG_RTL="$PROJECT_DIR/rtl/p04_reset_debug_probe.v"
TCL_SCRIPT="$SCRIPT_DIR/create_p04_reset_debug.tcl"
REPORT_DIR="$SCRIPT_DIR/build/p04_reset_debug"
JOBS="${VIVADO_JOBS:-4}"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi
for input in "$PROJECT_XPR" "$DEBUG_RTL" "$TCL_SCRIPT"; do
    [[ -f "$input" ]] || {
        echo "ERROR: P04 reset diagnostic input missing: $input" >&2
        echo "Run vivado/run_p04_impl.sh first if the base P04 project is missing." >&2
        exit 3
    }
done

rm -rf "$REPORT_DIR"
mkdir -p "$REPORT_DIR"

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs "$PROJECT_XPR" "$DEBUG_RTL" "$REPORT_DIR" "$JOBS" \
    2>&1 | tee "$REPORT_DIR/vivado_reset_debug.log"

for artifact in \
    "$REPORT_DIR/p04_reset_diag.bit" \
    "$REPORT_DIR/p04_reset_diag.ltx" \
    "$REPORT_DIR/timing_summary_post_route.rpt"; do
    [[ -f "$artifact" ]] || {
        echo "ERROR: expected P04 reset diagnostic artifact missing: $artifact" >&2
        exit 4
    }
done

echo
echo "P04 reset diagnostic build completed."
echo "Bitstream: $REPORT_DIR/p04_reset_diag.bit"
echo "Debug probes: $REPORT_DIR/p04_reset_diag.ltx"
