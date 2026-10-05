#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="loihi-digital-twin.org:hls:loihi_core_v2_tick:1.0"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v2"
TCL_SCRIPT="$SCRIPT_DIR/create_p02_ddr_impl_project.tcl"
BUILD_DIR="$SCRIPT_DIR/build/p02_ddr_synth"
REPORT_DIR="$BUILD_DIR/reports"
VIVADO_PROJECT_DIR="$BUILD_DIR/project"
JOBS="${VIVADO_JOBS:-4}"

CONTROLLER_RTL="$PROJECT_DIR/rtl/p08_paged_dispatch_controller.v"
MEMORY_RTL="$PROJECT_DIR/rtl/p05_context_memory_fabric.v"
RESET_RTL="$PROJECT_DIR/rtl/p04_reset_conditioner.v"
HOSTMUX_RTL="$PROJECT_DIR/rtl/p04_host_mux.v"
WALKER_RTL="$PROJECT_DIR/rtl/p02_context_page_bank_walker.v"
ARBITER_RTL="$PROJECT_DIR/rtl/p02_page_host_arbiter.v"
RANGE_GUARD_RTL="$PROJECT_DIR/rtl/p02_ddr_backing_range_guard.v"
ADAPTER_RTL="$PROJECT_DIR/rtl/p02_axi128_burst_adapter.v"

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
    echo "ERROR: P02.3b2 is targeted to $EXPECTED_PART, got HLS_PART=$HLS_PART" >&2
    exit 2
fi

for input in     "$TCL_SCRIPT"     "$CONTROLLER_RTL"     "$MEMORY_RTL"     "$RESET_RTL"     "$HOSTMUX_RTL"     "$WALKER_RTL"     "$ARBITER_RTL"     "$RANGE_GUARD_RTL"     "$ADAPTER_RTL"; do
    [[ -f "$input" ]] || {
        echo "ERROR: required P02.3b2 source missing: $input" >&2
        exit 2
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$REPORT_DIR"

bash "$PROJECT_DIR/scripts/run_p02_3b2_preflight.sh"     | tee "$BUILD_DIR/p02_3b2_preflight.log"

bash "$HLS_DIR/run_package.sh" | tee "$BUILD_DIR/hls_package.log"
IP_REPO_DIR="$HLS_DIR/build/p03_package/ip_repo"
[[ -f "$IP_REPO_DIR/loihi_core_v2_tick/component.xml" ]] || {
    echo "ERROR: packaged loihi_core_v2_tick component.xml not found under $IP_REPO_DIR" >&2
    exit 3
}

vivado -mode batch     -source "$TCL_SCRIPT"     -tclargs       "$IP_REPO_DIR"       "$VIVADO_PROJECT_DIR"       "$EXPECTED_PART"       "$EXPECTED_VLNV"       "$CONTROLLER_RTL"       "$MEMORY_RTL"       "$RESET_RTL"       "$HOSTMUX_RTL"       "$WALKER_RTL"       "$ARBITER_RTL"       "$RANGE_GUARD_RTL"       "$ADAPTER_RTL"       "$REPORT_DIR"       "$JOBS"       synth     2>&1 | tee "$BUILD_DIR/vivado_synth.log"

grep -q 'P02.3b2 HP0 DDR-paged one-engine / three-resident-context block design validated successfully.'     "$BUILD_DIR/vivado_synth.log" || {
    echo "ERROR: P02.3b2 block-design validation marker was not found" >&2
    exit 4
}

for required in     "$REPORT_DIR/timing_summary_post_synth.rpt"     "$REPORT_DIR/utilization_post_synth.rpt"     "$REPORT_DIR/utilization_hierarchical_post_synth.rpt"     "$REPORT_DIR/p02_post_synth_metrics.txt"     "$REPORT_DIR/p02_ddr_post_synth.dcp"; do
    [[ -f "$required" ]] || {
        echo "ERROR: expected P02.3b2 synthesis artifact missing: $required" >&2
        exit 4
    }
done

metric_value() {
    local key="$1"
    sed -n "s/^${key}=//p" "$REPORT_DIR/p02_post_synth_metrics.txt" | tail -n 1
}

for pair in     "resident_context_slots:3"     "physical_engines:1"     "logical_capacity_changed:0"     "p02_ddr_backing_base:0x40000000"     "p02_ddr_backing_bytes:0x04000000"     "p02_ddr_record_bytes:0x00080000"     "p02_ddr_logical_capacity:128"     "p02_hp0_enabled:1"     "p02_hp0_data_width_bits:128"     "p02_axi_burst_beats:16"     "p02_axi_burst_bytes:256"     "p02_ddr_range_guard:1"     "p02_page_walker:1"     "p02_page_host_arbiter:1"     "p02_ps_runtime_implemented:0"; do
    key="${pair%%:*}"
    expected="${pair#*:}"
    actual="$(metric_value "$key")"
    [[ "$actual" == "$expected" ]] || {
        echo "ERROR: P02.3b2 synthesis metric $key expected $expected, got $actual" >&2
        exit 5
    }
done

URAM="$(metric_value uram)"
if [[ -z "$URAM" ]]; then
    echo "ERROR: P02.3b2 synthesis URAM metric is unavailable" >&2
    exit 5
fi
if ! awk -v value="$URAM" 'BEGIN { exit !(value + 0 <= 64) }'; then
    echo "ERROR: P02.3b2 synthesis exceeds K26 URAM capacity: uram=$URAM" >&2
    exit 5
fi

echo
echo '=== P02.3b2 synthesis metrics ==='
cat "$REPORT_DIR/p02_post_synth_metrics.txt"

echo
echo '=== P02.3b2 synthesis utilization summary ==='
grep -E '^\| (CLB LUTs|CLB Registers|Slice LUTs|Slice Registers|Block RAM Tile|URAM|DSPs)'     "$REPORT_DIR/utilization_post_synth.rpt" || true

echo
echo '=== P02.3b2 synthesis hierarchy ==='
grep -E     'loihi_core_v2_tick_0|p08_context_memory_0|p02_context_page_bank_walker_0|p02_page_host_arbiter_0|p02_axi128_burst_adapter_0|p02_hp0_smartconnect_0'     "$REPORT_DIR/utilization_hierarchical_post_synth.rpt" || true

echo
echo "PASS: P02.3b2 HP0 integration synthesis gate completed successfully."
echo "Reports: $REPORT_DIR"
