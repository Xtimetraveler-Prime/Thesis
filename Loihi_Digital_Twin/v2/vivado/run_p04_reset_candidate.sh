#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BASE_PROJECT="$SCRIPT_DIR/build/p04_impl/base_project/loihi_twin_v2_p04_impl.xpr"
RESET_RTL="$PROJECT_DIR/rtl/p04_reset_conditioner.v"
TCL_SCRIPT="$SCRIPT_DIR/apply_p04_reset_conditioner.tcl"
BUILD_DIR="$SCRIPT_DIR/build/p04_reset_conditioner"
REPORT_DIR="$BUILD_DIR/reports"
JOBS="${VIVADO_JOBS:-4}"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi
for input in "$BASE_PROJECT" "$RESET_RTL" "$TCL_SCRIPT"; do
    [[ -f "$input" ]] || {
        echo "ERROR: required P04 reset-candidate input missing: $input" >&2
        echo "Run vivado/run_p04_impl.sh first if the staged base project is missing." >&2
        exit 3
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$REPORT_DIR"

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs "$BASE_PROJECT" "$RESET_RTL" "$REPORT_DIR" "$JOBS" \
    2>&1 | tee "$BUILD_DIR/vivado_reset_conditioner.log"

for required in \
    "$REPORT_DIR/timing_summary_post_route.rpt" \
    "$REPORT_DIR/utilization_post_route.rpt" \
    "$REPORT_DIR/utilization_hierarchical_post_route.rpt" \
    "$REPORT_DIR/bus_skew_post_route.rpt" \
    "$REPORT_DIR/p04_post_route_metrics.txt" \
    "$REPORT_DIR/p04_post_route.dcp" \
    "$REPORT_DIR/p04_two_core.bit" \
    "$REPORT_DIR/p04_two_core.ltx"; do
    [[ -f "$required" ]] || {
        echo "ERROR: expected P04 reset-conditioned artifact missing: $required" >&2
        exit 4
    }
done

echo
echo '=== P04 reset-conditioned metrics ==='
cat "$REPORT_DIR/p04_post_route_metrics.txt"
echo
echo '=== P04 reset-conditioned utilization ==='
grep -E '^\| (CLB LUTs|CLB Registers|Block RAM Tile|URAM|DSPs)' \
    "$REPORT_DIR/utilization_post_route.rpt" || true

echo
echo "P04 reset-conditioned helper build completed."
echo "Bitstream: $REPORT_DIR/p04_two_core.bit"
echo "Debug probes: $REPORT_DIR/p04_two_core.ltx"
