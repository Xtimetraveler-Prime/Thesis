#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="loihi-digital-twin.org:hls:loihi_core_v2_tick:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v2"
MONITOR_RTL="$PROJECT_DIR/rtl/p03_run_monitor.v"
HOST_BRIDGE_RTL="$PROJECT_DIR/rtl/p03_memory_host_bridge.v"
MEMORY_FABRIC_RTL="$PROJECT_DIR/rtl/p03_memory_fabric.v"
TCL_SCRIPT="$SCRIPT_DIR/create_p03_impl_project.tcl"
BUILD_DIR="$SCRIPT_DIR/build/p03_impl"
REPORT_DIR="$BUILD_DIR/reports"
VIVADO_PROJECT_DIR="$BUILD_DIR/project"
JOBS="${VIVADO_JOBS:-4}"

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
    echo "ERROR: P03 is frozen to $EXPECTED_PART, got HLS_PART=$HLS_PART" >&2
    exit 2
fi

for rtl in "$MONITOR_RTL" "$HOST_BRIDGE_RTL" "$MEMORY_FABRIC_RTL"; do
    [[ -f "$rtl" ]] || {
        echo "ERROR: required P03 RTL missing: $rtl" >&2
        exit 2
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$REPORT_DIR"

bash "$HLS_DIR/run_package.sh" | tee "$BUILD_DIR/hls_package.log"
IP_REPO_DIR="$HLS_DIR/build/p03_package/ip_repo"
[[ -f "$IP_REPO_DIR/loihi_core_v2_tick/component.xml" ]] || {
    echo "ERROR: packaged P03 component.xml not found under $IP_REPO_DIR" >&2
    exit 3
}

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs \
      "$IP_REPO_DIR" \
      "$VIVADO_PROJECT_DIR" \
      "$EXPECTED_PART" \
      "$EXPECTED_VLNV" \
      "$MONITOR_RTL" \
      "$HOST_BRIDGE_RTL" \
      "$MEMORY_FABRIC_RTL" \
      "$REPORT_DIR" \
      "$JOBS" \
    2>&1 | tee "$BUILD_DIR/vivado_impl.log"

for required in \
    "$REPORT_DIR/timing_summary_post_route.rpt" \
    "$REPORT_DIR/utilization_post_route.rpt" \
    "$REPORT_DIR/utilization_hierarchical_post_route.rpt" \
    "$REPORT_DIR/memory_primitives_post_route.rpt" \
    "$REPORT_DIR/bus_skew_post_route.rpt" \
    "$REPORT_DIR/p03_post_route_metrics.txt" \
    "$REPORT_DIR/p03_post_route.dcp"; do
    [[ -f "$required" ]] || {
        echo "ERROR: expected P03 implementation artifact missing: $required" >&2
        exit 4
    }
done

echo
echo '=== P03 XPM-shell post-route metrics ==='
cat "$REPORT_DIR/p03_post_route_metrics.txt"
echo
echo '=== P03 utilization summary ==='
grep -E '^\| (CLB LUTs|CLB Registers|Slice LUTs|Slice Registers|Block RAM Tile|URAM|DSPs)' \
    "$REPORT_DIR/utilization_post_route.rpt" || true

echo
echo '=== P03 XPM memory hierarchy ==='
grep -E \
    'p03_memory_fabric_0|u_config_words|u_state_words|u_axon_words|u_synapse_words|u_route_desc_words|u_route_words|u_input_events|u_trace_words|u_packet_words' \
    "$REPORT_DIR/utilization_hierarchical_post_route.rpt" || true

echo
echo "P03 fixed-depth XPM routed implementation gate completed."
echo "Reports: $REPORT_DIR"
