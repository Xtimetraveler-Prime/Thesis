#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/p03_2_mmio_impl"
PROJECT_XPR="$BUILD_DIR/project/loihi_twin_v3_p03_mmio_impl.xpr"
REPORT_DIR="$BUILD_DIR/reports"
RECOVERY_TCL="$SCRIPT_DIR/recover_p03_mmio_xsa.tcl"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado/Vitis 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi

[[ -f "$PROJECT_XPR" ]] || {
    echo "ERROR: existing P03.2 routed project is missing: $PROJECT_XPR" >&2
    echo "ERROR: run vivado/run_p03_mmio_impl.sh instead." >&2
    exit 3
}

mkdir -p "$REPORT_DIR"

METRICS_FILE="$REPORT_DIR/p03_2_post_route_metrics.txt"
[[ -f "$METRICS_FILE" ]] || {
    echo "ERROR: existing P03.2 post-route metrics are missing: $METRICS_FILE" >&2
    exit 4
}

metric_value() {
    local key="$1"
    sed -n "s/^${key}=//p" "$METRICS_FILE" | tail -n 1
}

WNS="$(metric_value wns_ns)"
WHS="$(metric_value whs_ns)"
for pair in "wns_ns:$WNS" "whs_ns:$WHS"; do
    key="${pair%%:*}"
    value="${pair#*:}"
    if [[ -z "$value" || "$value" == "NA" ]]; then
        echo "ERROR: recovered P03.2 metric $key is unavailable" >&2
        exit 5
    fi
    if ! awk -v value="$value" 'BEGIN { exit !(value + 0 >= 0) }'; then
        echo "ERROR: recovered P03.2 timing failed: $key=$value" >&2
        exit 5
    fi
done

for pair in     "resident_context_slots:3"     "physical_engines:1"     "p02_hp0_enabled:1"     "p02_hp0_data_width_bits:128"     "p03_hpm0_enabled:1"     "p03_hpm0_data_width_bits:32"     "p03_mmio_base:0xA4000000"     "p03_mmio_range_bytes:0x00001000"     "p03_mmio_controls_page:1"     "p03_mmio_controls_dispatch:1"     "p03_mmio_controls_resident_memory:1"; do
    key="${pair%%:*}"
    expected="${pair#*:}"
    actual="$(metric_value "$key")"
    [[ "$actual" == "$expected" ]] || {
        echo "ERROR: recovered P03.2 metric $key expected $expected, got $actual" >&2
        exit 5
    }
done

URAM="$(metric_value uram)"
if [[ -z "$URAM" ]] || ! awk -v value="$URAM" 'BEGIN { exit !(value + 0 <= 64) }'; then
    echo "ERROR: recovered P03.2 URAM capacity evidence invalid: uram=$URAM" >&2
    exit 5
fi

vivado -mode batch     -source "$RECOVERY_TCL"     -tclargs "$PROJECT_XPR" "$REPORT_DIR"     2>&1 | tee "$BUILD_DIR/xsa_recovery.log"

for required in     "$REPORT_DIR/p03_2_ps_mmio.bit"     "$REPORT_DIR/p03_2_ps_mmio.ltx"     "$REPORT_DIR/p03_2_ps_mmio.xsa"; do
    [[ -f "$required" ]] || {
        echo "ERROR: P03.2 recovered artifact missing: $required" >&2
        exit 4
    }
done

BIT_SHA="$(sha256sum "$REPORT_DIR/p03_2_ps_mmio.bit" | awk '{print $1}')"
LTX_SHA="$(sha256sum "$REPORT_DIR/p03_2_ps_mmio.ltx" | awk '{print $1}')"
XSA_SHA="$(sha256sum "$REPORT_DIR/p03_2_ps_mmio.xsa" | awk '{print $1}')"

printf 'PASS: P03.2 recovered routed timing wns_ns=%s whs_ns=%s\n' "$WNS" "$WHS"
printf 'PASS: P03.2 recovered topology resident_contexts=3 physical_engines=1 hp0=128bit hpm0=32bit\n'
printf 'PASS: P03.2 recovered MMIO map base=0xA4000000 range=0x00001000\n'
printf 'PASS: P03.2 recovered resources uram=%s\n' "$URAM"
printf 'PASS: P03.2 recovered artifacts bitstream_sha256=%s probes_sha256=%s xsa_sha256=%s\n'     "$BIT_SHA" "$LTX_SHA" "$XSA_SHA"
echo "PASS: P03.2 routed-project XSA recovery gate completed successfully."
