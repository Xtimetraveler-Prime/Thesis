#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="loihi-digital-twin.org:hls:loihi_core_v2_tick:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v2"
TCL_SCRIPT="$SCRIPT_DIR/create_p05_impl_project.tcl"
BUILD_DIR="$SCRIPT_DIR/build/p05_impl"
REPORT_DIR="$BUILD_DIR/reports"
VIVADO_PROJECT_DIR="$BUILD_DIR/project"
JOBS="${VIVADO_JOBS:-4}"

STREAMER_RTL="$PROJECT_DIR/rtl/p04_packet_memory_streamer.v"
CONTROLLER_RTL="$PROJECT_DIR/rtl/p05_virtualized_controller.v"
MEMORY_RTL="$PROJECT_DIR/rtl/p05_context_memory_fabric.v"
RESET_RTL="$PROJECT_DIR/rtl/p04_reset_conditioner.v"
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
    echo "ERROR: P05 is targeted to $EXPECTED_PART, got HLS_PART=$HLS_PART" >&2
    exit 2
fi

for input in "$TCL_SCRIPT" "$STREAMER_RTL" "$CONTROLLER_RTL" "$MEMORY_RTL" "$RESET_RTL" "$HOSTMUX_RTL"; do
    [[ -f "$input" ]] || {
        echo "ERROR: required P05 source missing: $input" >&2
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
      "$STREAMER_RTL" \
      "$CONTROLLER_RTL" \
      "$MEMORY_RTL" \
      "$RESET_RTL" \
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
    "$REPORT_DIR/p05_post_route_metrics.txt" \
    "$REPORT_DIR/p05_post_route.dcp" \
    "$REPORT_DIR/p05_virtualized.bit" \
    "$REPORT_DIR/p05_virtualized.ltx"; do
    [[ -f "$required" ]] || {
        echo "ERROR: expected P05 implementation artifact missing: $required" >&2
        exit 4
    }
done

metric_value() {
    local key="$1"
    sed -n "s/^${key}=//p" "$REPORT_DIR/p05_post_route_metrics.txt" | tail -n 1
}

WNS="$(metric_value wns_ns)"
WHS="$(metric_value whs_ns)"
for pair in "wns_ns:$WNS" "whs_ns:$WHS"; do
    key="${pair%%:*}"
    value="${pair#*:}"
    if [[ -z "$value" || "$value" == "NA" ]]; then
        echo "ERROR: P05 post-route metric $key is unavailable" >&2
        exit 5
    fi
    if ! awk -v value="$value" 'BEGIN { exit !(value + 0 >= 0) }'; then
        echo "ERROR: P05 post-route timing failed: $key=$value" >&2
        exit 5
    fi
done

[[ "$(metric_value logical_contexts)" == "3" ]] || {
    echo "ERROR: P05 route did not report three logical contexts" >&2
    exit 5
}
[[ "$(metric_value physical_engines)" == "1" ]] || {
    echo "ERROR: P05 route did not report one physical engine" >&2
    exit 5
}
[[ "$(metric_value logical_capacity_changed)" == "0" ]] || {
    echo "ERROR: P05 route changed the logical-capacity contract" >&2
    exit 5
}

echo
echo '=== P05 post-route metrics ==='
cat "$REPORT_DIR/p05_post_route_metrics.txt"
echo
echo '=== P05 utilization summary ==='
grep -E '^\| (CLB LUTs|CLB Registers|Slice LUTs|Slice Registers|Block RAM Tile|URAM|DSPs)' \
    "$REPORT_DIR/utilization_post_route.rpt" || true

echo
echo '=== P05 hierarchy ==='
grep -E \
    'loihi_core_v2_tick_0|p05_virtualized_controller_0|p05_context_memory_0' \
    "$REPORT_DIR/utilization_hierarchical_post_route.rpt" || true

echo
echo "P05 routed implementation gate completed successfully."
echo "Bitstream: $REPORT_DIR/p05_virtualized.bit"
echo "Debug probes: $REPORT_DIR/p05_virtualized.ltx"
echo "Reports: $REPORT_DIR"
