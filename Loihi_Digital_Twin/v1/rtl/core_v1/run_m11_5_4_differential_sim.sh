#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
EXPECTED_VERSION="2025.2"
STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m11_5_4_differential"
SNAPSHOT="m11_5_4_recurrent_differential_sim"
VECTOR_FILE="$STAGE_ROOT/generated_m11_5_4_vectors.svh"
SIM_LOG="$STAGE_ROOT/xsim.log"
PASS_MARKER="M11.5.4 Python/RTL routing differential passed:"

for tool in python3 vivado xvlog xelab xsim; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required tool '$tool' was not found in PATH" >&2
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
cp "$SCRIPT_DIR/recurrent_route_queue_v1.sv" "$STAGE_ROOT/"
cp "$SCRIPT_DIR/tb/tb_recurrent_route_queue_differential_v1.sv" "$STAGE_ROOT/tb/"

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python3 "$ROOT_DIR/examples/generate_m11_5_4_vectors.py" \
    --output "$VECTOR_FILE"

cd "$STAGE_ROOT"

xvlog --sv -i . \
    recurrent_route_queue_v1.sv \
    tb/tb_recurrent_route_queue_differential_v1.sv

xelab tb_recurrent_route_queue_differential_v1 \
    -snapshot "$SNAPSHOT" \
    -debug typical

xsim "$SNAPSHOT" -runall | tee "$SIM_LOG"

if ! grep -Fq "$PASS_MARKER" "$SIM_LOG"; then
    echo "ERROR: XSIM returned without the M11.5.4 differential pass marker." >&2
    exit 1
fi

echo
echo "M11.5.4 Python-to-RTL routing differential simulation completed successfully."
echo "Staged simulation directory: $STAGE_ROOT"
echo "Generated vectors: $VECTOR_FILE"
echo "Log: $SIM_LOG"
