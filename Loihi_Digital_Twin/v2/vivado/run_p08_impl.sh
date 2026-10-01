#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="loihi-digital-twin.org:hls:loihi_core_v2_tick:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v2"
TCL_SCRIPT="$SCRIPT_DIR/create_p08_impl_project.tcl"
BUILD_DIR="$SCRIPT_DIR/build/p08_impl"
REPORT_DIR="$BUILD_DIR/reports"
VIVADO_PROJECT_DIR="$BUILD_DIR/project"
JOBS="${VIVADO_JOBS:-4}"

CONTROLLER_RTL="$PROJECT_DIR/rtl/p08_paged_dispatch_controller.v"
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
    echo "ERROR: P08 is targeted to $EXPECTED_PART, got HLS_PART=$HLS_PART" >&2
    exit 2
fi

for input in "$TCL_SCRIPT" "$CONTROLLER_RTL" "$MEMORY_RTL" "$RESET_RTL" "$HOSTMUX_RTL"; do
    [[ -f "$input" ]] || {
        echo "ERROR: required P08 source missing: $input" >&2
        exit 2
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$REPORT_DIR"

# Package the exact same P03-compatible HLS compute engine used by P05/P06/P07.
bash "$HLS_DIR/run_package.sh" | tee "$BUILD_DIR/hls_package.log"
IP_REPO_DIR="$HLS_DIR/build/p03_package/ip_repo"
[[ -f "$IP_REPO_DIR/loihi_core_v2_tick/component.xml" ]] || {
    echo "ERROR: packaged loihi_core_v2_tick component.xml not found under $IP_REPO_DIR" >&2
    exit 3
}

# Re-run the already accepted P08 dispatch-controller RTL simulation as a guard
# before integrating that controller into the routed physical shell.
bash "$PROJECT_DIR/rtl/run_p08_paged_dispatch_controller_sim.sh" \
    | tee "$BUILD_DIR/p08_dispatch_rtl_sim.log"
grep -q 'PASS: p08_paged_dispatch_controller' "$BUILD_DIR/p08_dispatch_rtl_sim.log" || {
    echo "ERROR: P08 dispatch-controller RTL regression did not report PASS" >&2
    exit 3
}

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs \
      "$IP_REPO_DIR" \
      "$VIVADO_PROJECT_DIR" \
      "$EXPECTED_PART" \
      "$EXPECTED_VLNV" \
      "$CONTROLLER_RTL" \
      "$MEMORY_RTL" \
      "$RESET_RTL" \
      "$HOSTMUX_RTL" \
      "$REPORT_DIR" \
      "$JOBS" \
    2>&1 | tee "$BUILD_DIR/vivado_impl.log"

for required in \
    "$REPORT_DIR/timing_summary_post_route.rpt" \
    "$REPORT_DIR/utilization_post_route.rpt" \
    "$REPORT_DIR/utilization_hierarchical_post_route.rpt" \
    "$REPORT_DIR/memory_primitives_post_route.rpt" \
    "$REPORT_DIR/bus_skew_post_route.rpt" \
    "$REPORT_DIR/p08_post_route_metrics.txt" \
    "$REPORT_DIR/p08_post_route.dcp" \
    "$REPORT_DIR/p08_host_paged.bit" \
    "$REPORT_DIR/p08_host_paged.ltx"; do
    [[ -f "$required" ]] || {
        echo "ERROR: expected P08 implementation artifact missing: $required" >&2
        exit 4
    }
done

metric_value() {
    local key="$1"
    sed -n "s/^${key}=//p" "$REPORT_DIR/p08_post_route_metrics.txt" | tail -n 1
}

WNS="$(metric_value wns_ns)"
WHS="$(metric_value whs_ns)"
for pair in "wns_ns:$WNS" "whs_ns:$WHS"; do
    key="${pair%%:*}"
    value="${pair#*:}"
    if [[ -z "$value" || "$value" == "NA" ]]; then
        echo "ERROR: P08 post-route metric $key is unavailable" >&2
        exit 5
    fi
    if ! awk -v value="$value" 'BEGIN { exit !(value + 0 >= 0) }'; then
        echo "ERROR: P08 post-route timing failed: $key=$value" >&2
        exit 5
    fi
done

[[ "$(metric_value p08_expected_logical_backing_contexts)" == "5" ]] || {
    echo "ERROR: P08 route did not bind the expected five logical backing contexts" >&2
    exit 5
}
[[ "$(metric_value resident_context_slots)" == "3" ]] || {
    echo "ERROR: P08 route did not retain exactly three resident context slots" >&2
    exit 5
}
[[ "$(metric_value physical_engines)" == "1" ]] || {
    echo "ERROR: P08 route did not report one physical engine" >&2
    exit 5
}
[[ "$(metric_value host_paged_dispatch)" == "1" ]] || {
    echo "ERROR: P08 routed shell is not marked host-paged" >&2
    exit 5
}
[[ "$(metric_value on_fabric_cross_page_router)" == "0" ]] || {
    echo "ERROR: P08 unexpectedly introduced an on-fabric cross-page router" >&2
    exit 5
}
[[ "$(metric_value host_owns_cross_page_routing)" == "1" ]] || {
    echo "ERROR: P08 host routing ownership contract drifted" >&2
    exit 5
}
[[ "$(metric_value host_owns_global_barrier)" == "1" ]] || {
    echo "ERROR: P08 host barrier ownership contract drifted" >&2
    exit 5
}
[[ "$(metric_value logical_capacity_changed)" == "0" ]] || {
    echo "ERROR: P08 route changed the logical-capacity contract" >&2
    exit 5
}

# Require the physical memory footprint to remain within the K26 device and to
# preserve the accepted three-full-context implementation strategy.
URAM="$(metric_value uram)"
if [[ -z "$URAM" ]]; then
    echo "ERROR: P08 post-route URAM metric is unavailable" >&2
    exit 5
fi
if ! awk -v value="$URAM" 'BEGIN { exit !(value + 0 <= 64) }'; then
    echo "ERROR: P08 routed shell exceeds K26 URAM capacity: uram=$URAM" >&2
    exit 5
fi

BIT_SHA="$(sha256sum "$REPORT_DIR/p08_host_paged.bit" | awk '{print $1}')"
LTX_SHA="$(sha256sum "$REPORT_DIR/p08_host_paged.ltx" | awk '{print $1}')"

printf 'PASS: P08.4.3a routed timing wns_ns=%s whs_ns=%s\n' "$WNS" "$WHS"
printf 'PASS: P08.4.3a physical topology logical_backing=5 resident_contexts=3 physical_engines=1 host_paged=true logical_capacity_changed=false\n'
printf 'PASS: P08.4.3a routing ownership cross_page=host global_barrier=host on_fabric_cross_page_router=false\n'
printf 'PASS: P08.4.3a resources uram=%s\n' "$URAM"
printf 'PASS: P08.4.3a artifacts bitstream_sha256=%s probes_sha256=%s\n' "$BIT_SHA" "$LTX_SHA"

echo
echo '=== P08 post-route metrics ==='
cat "$REPORT_DIR/p08_post_route_metrics.txt"
echo
echo '=== P08 utilization summary ==='
grep -E '^\| (CLB LUTs|CLB Registers|Slice LUTs|Slice Registers|Block RAM Tile|URAM|DSPs)' \
    "$REPORT_DIR/utilization_post_route.rpt" || true

echo
echo '=== P08 hierarchy ==='
grep -E \
    'loihi_core_v2_tick_0|p08_paged_dispatch_controller_0|p08_context_memory_0' \
    "$REPORT_DIR/utilization_hierarchical_post_route.rpt" || true

echo
echo "P08.4.3a host-paged K26 implementation gate completed successfully."
echo "Bitstream: $REPORT_DIR/p08_host_paged.bit"
echo "Debug probes: $REPORT_DIR/p08_host_paged.ltx"
echo "Reports: $REPORT_DIR"
