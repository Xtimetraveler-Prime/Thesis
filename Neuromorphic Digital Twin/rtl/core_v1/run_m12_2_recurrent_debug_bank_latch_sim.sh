#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_VERSION="2025.2"
STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m12_2_recurrent_debug_bank_latch"
SNAPSHOT="m12_2_recurrent_debug_bank_latch_sim"
PASS_MARKER="M12.2 recurrent debug bank-latch regression passed:"

for tool in vivado xvlog xelab xsim; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required Vivado tool '$tool' was not found in PATH" >&2
        exit 1
    fi
done

if ! vivado -version 2>/dev/null | head -n 1 | grep -F "$EXPECTED_VERSION" >/dev/null; then
    echo "ERROR: M12.2 debug-bank regression requires Vivado $EXPECTED_VERSION" >&2
    vivado -version | head -n 4 >&2 || true
    exit 1
fi

rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE_ROOT/tb"
cp "$SCRIPT_DIR/recurrent_route_queue_v1.sv" "$STAGE_ROOT/"
cp "$SCRIPT_DIR/tb/tb_m12_2_recurrent_debug_bank_latch.sv" "$STAGE_ROOT/tb/"

cd "$STAGE_ROOT"

xvlog --sv \
    recurrent_route_queue_v1.sv \
    tb/tb_m12_2_recurrent_debug_bank_latch.sv \
    2>&1 | tee compile.log

xelab tb_m12_2_recurrent_debug_bank_latch \
    -snapshot "$SNAPSHOT" \
    -debug typical \
    2>&1 | tee elaborate.log

xsim "$SNAPSHOT" -runall 2>&1 | tee simulate.log

if ! grep -Fq "$PASS_MARKER" simulate.log; then
    echo "ERROR: XSIM returned without the M12.2 debug-bank latch pass marker." >&2
    exit 2
fi

echo
echo "M12.2 recurrent debug-bank latch RTL simulation completed successfully."
echo "Staged simulation directory: $STAGE_ROOT"
