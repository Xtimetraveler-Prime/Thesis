#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="${1:-/tmp/v3_p03_2c_ila_capture}"
READ_ADDR="${P03_ILA_READ_ADDR:-0xA4000004}"
HW_SERVER_URL="${P03_HW_SERVER_URL:-localhost:3121}"
XSDB_SERVER_URL="${P03_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
LTX="${P03_ILA_LTX:-$V3_DIR/vivado/build/p03_2c_ila_diagnostic/reports/p03_2_ps_mmio.ltx}"
ARMED_MARKER="$OUT_DIR/armed.marker"
VIVADO_LOG="$OUT_DIR/vivado_ila_capture.log"
READ_LOG="$OUT_DIR/xsdb_single_read.log"
HALT_LOG="$OUT_DIR/xsdb_halt.log"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado/Vitis 2025.2 settings64.sh first." >&2
    exit 2
}
command -v xsdb >/dev/null 2>&1 || {
    echo "ERROR: xsdb is not on PATH. Source Vitis 2025.2 settings64.sh first." >&2
    exit 2
}
[[ -f "$LTX" ]] || {
    echo "ERROR: P03.2c System ILA probes file missing: $LTX" >&2
    exit 2
}

if [[ -e "$OUT_DIR" ]]; then
    echo "ERROR: ILA capture output already exists: $OUT_DIR" >&2
    echo "ERROR: select a NEW output directory to preserve previous evidence." >&2
    exit 2
fi
mkdir -p "$OUT_DIR"

cd "$V3_DIR"

# Freeze Linux/processor activity before arming the HPM0 read trigger.
xsdb vivado/p03_2c_xsdb_halt_a53.tcl "$XSDB_SERVER_URL" | tee "$HALT_LOG"

vivado -mode batch \
    -source vivado/p03_2c_ila_capture.tcl \
    -tclargs "$OUT_DIR" "$ARMED_MARKER" "$LTX" "$HW_SERVER_URL" \
    >"$VIVADO_LOG" 2>&1 &
VIVADO_PID=$!

cleanup() {
    if kill -0 "$VIVADO_PID" 2>/dev/null; then
        kill "$VIVADO_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

for _ in $(seq 1 120); do
    if [[ -f "$ARMED_MARKER" ]]; then
        break
    fi
    if ! kill -0 "$VIVADO_PID" 2>/dev/null; then
        echo "ERROR: Vivado ILA capture exited before arming." >&2
        cat "$VIVADO_LOG" >&2
        exit 3
    fi
    sleep 0.25
done

if [[ ! -f "$ARMED_MARKER" ]]; then
    echo "ERROR: timed out waiting for P03.2c ILA to arm." >&2
    cat "$VIVADO_LOG" >&2
    exit 3
fi

echo "PASS: P03.2c System ILA armed; issuing single physical read at $READ_ADDR"

xsdb vivado/p03_2c_xsdb_single_mmio_read.tcl "$READ_ADDR" "$XSDB_SERVER_URL" \
    | tee "$READ_LOG"

wait "$VIVADO_PID"
trap - EXIT

grep -E "P03_2C_ILA_|PASS:|ERROR:|CRITICAL WARNING" "$VIVADO_LOG" || true

for required in \
    "$OUT_DIR/p03_2c_hpm0_capture.ila" \
    "$OUT_DIR/p03_2c_hpm0_capture.csv" \
    "$OUT_DIR/p03_2c_hpm0_capture.vcd" \
    "$OUT_DIR/p03_2c_mmio_slave_capture.ila" \
    "$OUT_DIR/p03_2c_mmio_slave_capture.csv" \
    "$OUT_DIR/p03_2c_mmio_slave_capture.vcd"; do
    [[ -s "$required" ]] || {
        echo "ERROR: expected ILA capture artifact missing/empty: $required" >&2
        exit 4
    }
done

echo "PASS: P03.2c upstream AXI4 and downstream AXI4-Lite read-channel ILA artifacts written to $OUT_DIR"
echo "IMPORTANT: Cortex-A53 cores were halted. Reboot the KV260 after this diagnostic; do not resume Linux."
