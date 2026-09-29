#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="loihi-digital-twin.org:hls:loihi_core_v2_tick:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v2"
TCL_SCRIPT="$SCRIPT_DIR/create_p04_impl_project.tcl"
RESET_TCL="$SCRIPT_DIR/apply_p04_reset_conditioner.tcl"
RESET_RTL="$PROJECT_DIR/rtl/p04_reset_conditioner.v"
BUILD_DIR="$SCRIPT_DIR/build/p04_impl"
BASE_REPORT_DIR="$BUILD_DIR/base_reports"
BASE_PROJECT_DIR="$BUILD_DIR/base_project"
REPORT_DIR="$BUILD_DIR/reports"
VIVADO_PROJECT_DIR="$BUILD_DIR/project"
JOBS="${VIVADO_JOBS:-4}"

ROUTER_RTL="$PROJECT_DIR/rtl/p04_packet_router_barrier.v"
STREAMER_RTL="$PROJECT_DIR/rtl/p04_packet_memory_streamer.v"
CONTROLLER_RTL="$PROJECT_DIR/rtl/p04_two_core_controller.v"
MEMORY_RTL="$PROJECT_DIR/rtl/p04_endpoint_memory_fabric.v"
HOSTMUX_RTL="$PROJECT_DIR/rtl/p04_host_mux.v"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado/Vitis 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    vivado -version >&2 || true
    exit 2
fi

export HLS_PART="${HLS_PART:-$EXPECTED_PART}"
if [[ "$HLS_PART" != "$EXPECTED_PART" ]]; then
    echo "ERROR: P04 is targeted to $EXPECTED_PART, got HLS_PART=$HLS_PART" >&2
    exit 2
fi

for input in \
    "$TCL_SCRIPT" "$RESET_TCL" "$RESET_RTL" \
    "$ROUTER_RTL" "$STREAMER_RTL" "$CONTROLLER_RTL" "$MEMORY_RTL" "$HOSTMUX_RTL"; do
    [[ -f "$input" ]] || {
        echo "ERROR: required P04 source missing: $input" >&2
        exit 2
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$BASE_REPORT_DIR" "$REPORT_DIR"

bash "$HLS_DIR/run_package.sh" | tee "$BUILD_DIR/hls_package.log"
IP_REPO_DIR="$HLS_DIR/build/p03_package/ip_repo"
[[ -f "$IP_REPO_DIR/loihi_core_v2_tick/component.xml" ]] || {
    echo "ERROR: packaged loihi_core_v2_tick component.xml not found under $IP_REPO_DIR" >&2
    exit 3
}

# Build the ordinary two-endpoint project first. This establishes the complete
# P04 block design and packaged HLS endpoints. Its proc_sys_reset-routed output
# is staging only and is never published as the canonical P04 artifact.
vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs \
      "$IP_REPO_DIR" \
      "$BASE_PROJECT_DIR" \
      "$EXPECTED_PART" \
      "$EXPECTED_VLNV" \
      "$ROUTER_RTL" \
      "$STREAMER_RTL" \
      "$CONTROLLER_RTL" \
      "$MEMORY_RTL" \
      "$HOSTMUX_RTL" \
      "$BASE_REPORT_DIR" \
      "$JOBS" \
      route \
    2>&1 | tee "$BUILD_DIR/vivado_base_impl.log"

BASE_PROJECT="$BASE_PROJECT_DIR/loihi_twin_v2_p04_impl.xpr"
[[ -f "$BASE_PROJECT" ]] || {
    echo "ERROR: staged P04 Vivado project missing: $BASE_PROJECT" >&2
    exit 4
}

# Promote the physically verified source-controlled synchronous reset strategy
# into an isolated final project. Only this conditioned route writes the
# canonical reports/bitstream consumed by the P04 physical conformance harness.
vivado -mode batch \
    -source "$RESET_TCL" \
    -tclargs "$BASE_PROJECT" "$RESET_RTL" "$REPORT_DIR" "$JOBS" \
    2>&1 | tee "$BUILD_DIR/vivado_impl.log"

for required in \
    "$REPORT_DIR/timing_summary_post_route.rpt" \
    "$REPORT_DIR/utilization_post_route.rpt" \
    "$REPORT_DIR/utilization_hierarchical_post_route.rpt" \
    "$REPORT_DIR/memory_primitives_post_route.rpt" \
    "$REPORT_DIR/bus_skew_post_route.rpt" \
    "$REPORT_DIR/p04_post_route_metrics.txt" \
    "$REPORT_DIR/p04_post_route.dcp" \
    "$REPORT_DIR/p04_two_core.bit" \
    "$REPORT_DIR/p04_two_core.ltx"; do
    [[ -f "$required" ]] || {
        echo "ERROR: expected canonical P04 implementation artifact missing: $required" >&2
        exit 5
    }
done

echo
echo '=== P04 canonical post-route metrics ==='
cat "$REPORT_DIR/p04_post_route_metrics.txt"
echo
echo '=== P04 canonical utilization summary ==='
grep -E '^\| (CLB LUTs|CLB Registers|Slice LUTs|Slice Registers|Block RAM Tile|URAM|DSPs)' \
    "$REPORT_DIR/utilization_post_route.rpt" || true

echo
echo '=== P04 canonical endpoint hierarchy ==='
grep -E \
    'loihi_core_v2_tick_[01]|p04_two_core_controller_0|p04_endpoint_memory_[01]|p04_reset_conditioner_0' \
    "$REPORT_DIR/utilization_hierarchical_post_route.rpt" || true

echo
echo "P04 canonical routed implementation gate completed."
echo "Bitstream: $REPORT_DIR/p04_two_core.bit"
echo "Debug probes: $REPORT_DIR/p04_two_core.ltx"
echo "Reports: $REPORT_DIR"
