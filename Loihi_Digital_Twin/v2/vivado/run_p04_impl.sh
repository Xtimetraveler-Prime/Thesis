#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="loihi-digital-twin.org:hls:loihi_core_v2_tick:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v2"
TCL_SCRIPT="$SCRIPT_DIR/create_p04_impl_project.tcl"
BUILD_DIR="$SCRIPT_DIR/build/p04_impl"
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

for input in "$TCL_SCRIPT" "$ROUTER_RTL" "$STREAMER_RTL" "$CONTROLLER_RTL" "$MEMORY_RTL" "$HOSTMUX_RTL"; do
    [[ -f "$input" ]] || {
        echo "ERROR: required P04 source missing: $input" >&2
        exit 2
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$REPORT_DIR"

bash "$HLS_DIR/run_package.sh" | tee "$BUILD_DIR/hls_package.log"
IP_REPO_DIR="$HLS_DIR/build/p03_package/ip_repo"
[[ -f "$IP_REPO_DIR/loihi_core_v2_tick/component.xml" ]] || {
    echo "ERROR: packaged loihi_core_v2_tick component.xml not found under $IP_REPO_DIR" >&2
    exit 3
}

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs \
      "$IP_REPO_DIR" \
      "$VIVADO_PROJECT_DIR" \
      "$EXPECTED_PART" \
      "$EXPECTED_VLNV" \
      "$ROUTER_RTL" \
      "$STREAMER_RTL" \
      "$CONTROLLER_RTL" \
      "$MEMORY_RTL" \
      "$HOSTMUX_RTL" \
      "$REPORT_DIR" \
      "$JOBS" \
      route \
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
        echo "ERROR: expected P04 implementation artifact missing: $required" >&2
        exit 4
    }
done

echo
echo '=== P04 post-route metrics ==='
cat "$REPORT_DIR/p04_post_route_metrics.txt"
echo
echo '=== P04 utilization summary ==='
grep -E '^\| (CLB LUTs|CLB Registers|Slice LUTs|Slice Registers|Block RAM Tile|URAM|DSPs)' \
    "$REPORT_DIR/utilization_post_route.rpt" || true

echo
echo '=== P04 endpoint hierarchy ==='
grep -E \
    'loihi_core_v2_tick_[01]|p04_two_core_controller_0|p04_endpoint_memory_[01]' \
    "$REPORT_DIR/utilization_hierarchical_post_route.rpt" || true

echo
echo "P04 routed implementation gate completed."
echo "Bitstream: $REPORT_DIR/p04_two_core.bit"
echo "Debug probes: $REPORT_DIR/p04_two_core.ltx"
echo "Reports: $REPORT_DIR"
