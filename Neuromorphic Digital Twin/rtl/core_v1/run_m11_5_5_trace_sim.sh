#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v1"
IP_REPO_DIR="$HLS_DIR/build/m11_4/ip_repo"
LOCAL_BUILD_DIR="$SCRIPT_DIR/build/m11_5_5_trace"
VIVADO_PROJECT_DIR="$LOCAL_BUILD_DIR/vivado_project"
LOG_FILE="$LOCAL_BUILD_DIR/m11_5_5_trace_vivado.log"

STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m11_5_5_trace"
DECODER_RTL="$STAGE_ROOT/m08_weight_decoder_v1.sv"
PHASE_B_RTL="$STAGE_ROOT/phase_b_synapse_accumulator_v1.sv"
NEURON_RTL="$STAGE_ROOT/neuron_array_controller_v1.sv"
INTEGRATED_RTL="$STAGE_ROOT/integrated_core_controller_v1.sv"
ROUTE_RTL="$STAGE_ROOT/recurrent_route_queue_v1.sv"
RECURRENT_RTL="$STAGE_ROOT/recurrent_integrated_core_controller_v1.sv"
RECURRENT_BD_RTL="$STAGE_ROOT/recurrent_integrated_core_controller_bd_v1.v"
TB_FILE="$STAGE_ROOT/tb_neuromorphic_twin_m11_5_5_trace.sv"
M54_INCLUDE="$STAGE_ROOT/generated_m11_5_4_integrated_vectors.svh"
M55_INCLUDE="$STAGE_ROOT/generated_m11_5_5_trace_vectors.svh"
VIVADO_TCL="$STAGE_ROOT/create_m11_5_5_trace_project.tcl"

require_tool() {
    local tool="$1"
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool is not on PATH. Source the Vivado 2025.2 settings64.sh first." >&2
        exit 2
    fi
}

require_tool python3
require_tool vivado

VIVADO_VERSION="$(vivado -version 2>&1 || true)"
if [[ "$VIVADO_VERSION" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: vivado is not reporting version $EXPECTED_VERSION." >&2
    echo "$VIVADO_VERSION" >&2
    exit 2
fi
if [[ -n "${HLS_PART:-}" && "$HLS_PART" != "$EXPECTED_PART" ]]; then
    echo "ERROR: M11.5.5 is frozen to $EXPECTED_PART, but HLS_PART=$HLS_PART" >&2
    exit 2
fi
if [[ ! -f "$IP_REPO_DIR/neuron_step_v1/component.xml" ]]; then
    echo "ERROR: missing M11.4 packaged neuron_step_v1 IP:" >&2
    echo "  $IP_REPO_DIR/neuron_step_v1/component.xml" >&2
    echo "Recreate it with: export HLS_PART='$EXPECTED_PART'; cd '$HLS_DIR'; bash run_m11_4.sh" >&2
    exit 3
fi

rm -rf "$LOCAL_BUILD_DIR" "$STAGE_ROOT"
mkdir -p "$LOCAL_BUILD_DIR" "$STAGE_ROOT"
cp "$SCRIPT_DIR/m08_weight_decoder_v1.sv" "$DECODER_RTL"
cp "$SCRIPT_DIR/phase_b_synapse_accumulator_v1.sv" "$PHASE_B_RTL"
cp "$SCRIPT_DIR/neuron_array_controller_v1.sv" "$NEURON_RTL"
cp "$SCRIPT_DIR/integrated_core_controller_v1.sv" "$INTEGRATED_RTL"
cp "$SCRIPT_DIR/recurrent_route_queue_v1.sv" "$ROUTE_RTL"
cp "$SCRIPT_DIR/recurrent_integrated_core_controller_v1.sv" "$RECURRENT_RTL"
cp "$SCRIPT_DIR/recurrent_integrated_core_controller_bd_v1.v" "$RECURRENT_BD_RTL"
cp "$SCRIPT_DIR/tb/tb_neuromorphic_twin_m11_5_5_trace.sv" "$TB_FILE"
cp "$SCRIPT_DIR/vivado/create_m11_5_5_trace_project.tcl" "$VIVADO_TCL"

(
    cd "$PROJECT_DIR"
    python3 examples/generate_m11_5_4_integrated_vectors.py --output "$M54_INCLUDE"
    python3 examples/generate_m11_5_5_trace_vectors.py --output "$M55_INCLUDE"
)

printf 'M11.5.5 trace toolchain: Vivado %s\n' "$EXPECTED_VERSION"
printf 'M11.5.5 target part: %s\n' "$EXPECTED_PART"
printf 'M11.5.5 packaged HLS IP: %s\n' "$EXPECTED_VLNV"
printf 'M11.5.5 no-space staging directory: %s\n' "$STAGE_ROOT"

echo
echo '=== M11.5.5 trace snapshot + real packaged HLS IP ==='
vivado -mode batch \
    -source "$VIVADO_TCL" \
    -tclargs \
    "$IP_REPO_DIR" \
    "$VIVADO_PROJECT_DIR" \
    "$EXPECTED_PART" \
    "$EXPECTED_VLNV" \
    "$DECODER_RTL" \
    "$PHASE_B_RTL" \
    "$NEURON_RTL" \
    "$INTEGRATED_RTL" \
    "$ROUTE_RTL" \
    "$RECURRENT_RTL" \
    "$RECURRENT_BD_RTL" \
    "$TB_FILE" \
    "$M54_INCLUDE" \
    "$M55_INCLUDE" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M11.5.5 trace real-HLS block design validated successfully." \
    "M11.5.5 trace snapshot + real-HLS recurrent regression passed: ticks=4, neurons=3, tag=0x4d353554" \
    "M11.5.5 trace real-HLS Vivado simulation flow completed."; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: Vivado returned without expected M11.5.5 trace marker: $marker" >&2
        exit 4
    fi
done

echo
echo 'M11.5.5 trace snapshot + real packaged HLS IP simulation completed successfully.'
printf 'Vivado project: %s\n' "$VIVADO_PROJECT_DIR/neuromorphic_twin_m11_5_5_trace.xpr"
printf 'Log: %s\n' "$LOG_FILE"
