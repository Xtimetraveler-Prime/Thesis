#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_VERSION="2025.2"
STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m11_5_3"
SNAPSHOT="m11_5_3_phase_b_sim"

for tool in vivado xvlog xelab xsim; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required Vivado tool '$tool' was not found in PATH" >&2
        exit 1
    fi
done

if ! vivado -version 2>/dev/null | head -n 1 | grep -F "$EXPECTED_VERSION" >/dev/null; then
    echo "ERROR: M11.5 requires Vivado $EXPECTED_VERSION" >&2
    vivado -version | head -n 4 >&2 || true
    exit 1
fi

rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE_ROOT/tb"
cp "$SCRIPT_DIR/m08_weight_decoder_v1.sv" "$STAGE_ROOT/"
cp "$SCRIPT_DIR/phase_b_synapse_accumulator_v1.sv" "$STAGE_ROOT/"
cp "$SCRIPT_DIR/tb/tb_phase_b_synapse_accumulator_v1.sv" "$STAGE_ROOT/tb/"

cd "$STAGE_ROOT"

xvlog --sv \
    m08_weight_decoder_v1.sv \
    phase_b_synapse_accumulator_v1.sv \
    tb/tb_phase_b_synapse_accumulator_v1.sv

xelab tb_phase_b_synapse_accumulator_v1 \
    -snapshot "$SNAPSHOT" \
    -debug typical

xsim "$SNAPSHOT" -runall

echo
echo "M11.5.3 standalone Phase-B RTL simulation completed successfully."
echo "Staged simulation directory: $STAGE_ROOT"
