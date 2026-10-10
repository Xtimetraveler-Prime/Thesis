#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="loihi-digital-twin.org:hls:loihi_core_v2_tick:1.0"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v2"
TCL_SCRIPT="$SCRIPT_DIR/create_p03_mmio_impl_project.tcl"
BUILD_DIR="${P03_MMIO_BUILD_DIR:-$SCRIPT_DIR/build/p03_2c_ila_diagnostic}"
REPORT_DIR="$BUILD_DIR/reports"
VIVADO_PROJECT_DIR="$BUILD_DIR/project"
JOBS="${VIVADO_JOBS:-1}"
STAGE="${P03_MMIO_STAGE:-route}"
case "$STAGE" in
    bd|route) ;;
    *) echo "ERROR: P03_MMIO_STAGE must be bd or route, got $STAGE" >&2; exit 2 ;;
esac

CONTROLLER_RTL="$PROJECT_DIR/rtl/p08_paged_dispatch_controller.v"
MEMORY_RTL="$PROJECT_DIR/rtl/p05_context_memory_fabric.v"
RESET_RTL="$PROJECT_DIR/rtl/p04_reset_conditioner.v"
HOSTMUX_RTL="$PROJECT_DIR/rtl/p04_host_mux.v"
WALKER_RTL="$PROJECT_DIR/rtl/p02_context_page_bank_walker.v"
ARBITER_RTL="$PROJECT_DIR/rtl/p02_page_host_arbiter.v"
RANGE_GUARD_RTL="$PROJECT_DIR/rtl/p02_ddr_backing_range_guard.v"
ADAPTER_RTL="$PROJECT_DIR/rtl/p02_axi128_burst_adapter.v"
MMIO_RTL="$PROJECT_DIR/rtl/p03_ps_control_regs.v"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado/Vitis 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi

export HLS_PART="${HLS_PART:-$EXPECTED_PART}"
[[ "$HLS_PART" == "$EXPECTED_PART" ]] || {
    echo "ERROR: P03.2 is targeted to $EXPECTED_PART, got HLS_PART=$HLS_PART" >&2
    exit 2
}

if [[ -e "$BUILD_DIR" ]]; then
    echo "ERROR: diagnostic build output already exists: $BUILD_DIR" >&2
    echo "ERROR: set P03_MMIO_BUILD_DIR to a NEW path to preserve previous evidence." >&2
    exit 2
fi
mkdir -p "$REPORT_DIR"

bash "$PROJECT_DIR/scripts/run_p03_2_preflight.sh"     | tee "$BUILD_DIR/p03_2_preflight.log"

bash "$HLS_DIR/run_package.sh" | tee "$BUILD_DIR/hls_package.log"
IP_REPO_DIR="$HLS_DIR/build/p03_package/ip_repo"

vivado -mode batch     -source "$TCL_SCRIPT"     -tclargs         "$IP_REPO_DIR"         "$VIVADO_PROJECT_DIR"         "$EXPECTED_PART"         "$EXPECTED_VLNV"         "$CONTROLLER_RTL"         "$MEMORY_RTL"         "$RESET_RTL"         "$HOSTMUX_RTL"         "$WALKER_RTL"         "$ARBITER_RTL"         "$RANGE_GUARD_RTL"         "$ADAPTER_RTL"         "$MMIO_RTL"         "$REPORT_DIR"         "$JOBS"         "$STAGE"     2>&1 | tee "$BUILD_DIR/vivado_impl.log"

if [[ "$STAGE" == "bd" ]]; then
    grep -F -q "PASS: P03.2c split upstream-AXI4/downstream-native ILA block design validated." \
        "$BUILD_DIR/vivado_impl.log" || {
        echo "ERROR: P03.2c BD-only pass marker missing." >&2
        exit 4
    }
    echo "PASS: P03.2c BD-only System ILA interface validation gate completed."
    echo "Diagnostic build: $BUILD_DIR"
    exit 0
fi

for required in     "$REPORT_DIR/timing_summary_post_route.rpt"     "$REPORT_DIR/utilization_post_route.rpt"     "$REPORT_DIR/utilization_hierarchical_post_route.rpt"     "$REPORT_DIR/memory_primitives_post_route.rpt"     "$REPORT_DIR/bus_skew_post_route.rpt"     "$REPORT_DIR/p03_2_post_route_metrics.txt"     "$REPORT_DIR/p03_2_mmio_post_route.dcp"     "$REPORT_DIR/p03_2_ps_mmio.bit"     "$REPORT_DIR/p03_2_ps_mmio.ltx"     "$REPORT_DIR/p03_2_ps_mmio.xsa"; do
    [[ -f "$required" ]] || {
        echo "ERROR: expected P03.2 route artifact missing: $required" >&2
        exit 4
    }
done

metric_value() {
    local key="$1"
    sed -n "s/^${key}=//p" "$REPORT_DIR/p03_2_post_route_metrics.txt" | tail -n 1
}

WNS="$(metric_value wns_ns)"
WHS="$(metric_value whs_ns)"
for pair in "wns_ns:$WNS" "whs_ns:$WHS"; do
    key="${pair%%:*}"
    value="${pair#*:}"
    if [[ -z "$value" || "$value" == "NA" ]]; then
        echo "ERROR: P03.2 post-route metric $key is unavailable" >&2
        exit 5
    fi
    if ! awk -v value="$value" 'BEGIN { exit !(value + 0 >= 0) }'; then
        echo "ERROR: P03.2 post-route timing failed: $key=$value" >&2
        exit 5
    fi
done

for pair in     "resident_context_slots:3"     "physical_engines:1"     "logical_capacity_changed:0"     "p02_hp0_enabled:1"     "p02_hp0_data_width_bits:128"     "p02_axi_burst_beats:16"     "p02_axi_burst_bytes:256"     "p02_ddr_range_guard:1"     "p02_page_walker:1"     "p02_page_host_arbiter:1"     "p02_host_controls_page_command:0"     "p03_hpm0_enabled:1"     "p03_hpm0_data_width_bits:32"     "p03_hpm0_transport:axi_protocol_converter"     "p03_hpm0_system_ila:1"     "p03_hpm0_ila_slots:1"     "p03_mmio_native_ila:1"     "p03_mmio_native_probes:7"     "p03_mmio_base:0xA4000000"     "p03_mmio_range_bytes:0x00001000"     "p03_mmio_controls_page:1"     "p03_mmio_controls_dispatch:1"     "p03_mmio_controls_resident_memory:1"     "p03_ps_runtime_implemented:0"; do
    key="${pair%%:*}"
    expected="${pair#*:}"
    actual="$(metric_value "$key")"
    [[ "$actual" == "$expected" ]] || {
        echo "ERROR: P03.2 route metric $key expected $expected, got $actual" >&2
        exit 5
    }
done

URAM="$(metric_value uram)"
if [[ -z "$URAM" ]] || ! awk -v value="$URAM" 'BEGIN { exit !(value + 0 <= 64) }'; then
    echo "ERROR: P03.2 routed shell exceeds or lacks K26 URAM capacity evidence: uram=$URAM" >&2
    exit 5
fi

BIT_SHA="$(sha256sum "$REPORT_DIR/p03_2_ps_mmio.bit" | awk '{print $1}')"
LTX_SHA="$(sha256sum "$REPORT_DIR/p03_2_ps_mmio.ltx" | awk '{print $1}')"
XSA_SHA="$(sha256sum "$REPORT_DIR/p03_2_ps_mmio.xsa" | awk '{print $1}')"

printf 'PASS: P03.2 routed timing wns_ns=%s whs_ns=%s
' "$WNS" "$WHS"
printf 'PASS: P03.2 physical topology resident_contexts=3 physical_engines=1 hp0=128bit hpm0=32bit
'
printf 'PASS: P03.2 MMIO map base=0xA4000000 range=0x00001000
'
printf 'PASS: P03.2 command ownership page=ps-mmio dispatch=ps-mmio resident-memory=ps-mmio
'
printf 'PASS: P03.2 resources uram=%s
' "$URAM"
printf 'PASS: P03.2 artifacts bitstream_sha256=%s probes_sha256=%s xsa_sha256=%s
' "$BIT_SHA" "$LTX_SHA" "$XSA_SHA"

echo
echo '=== P03.2 post-route metrics ==='
cat "$REPORT_DIR/p03_2_post_route_metrics.txt"

echo
echo "PASS: P03.2 routed PS-MMIO implementation gate completed successfully."
echo "Bitstream: $REPORT_DIR/p03_2_ps_mmio.bit"
echo "Debug probes: $REPORT_DIR/p03_2_ps_mmio.ltx"
echo "Fixed XSA: $REPORT_DIR/p03_2_ps_mmio.xsa"
echo "Reports: $REPORT_DIR"
