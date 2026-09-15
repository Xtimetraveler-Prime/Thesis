#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd -- "$APP_DIR/../.." && pwd)"
PROJECT_DIR="$REPO_ROOT/Neuromorphic Digital Twin"
CORE_RTL="$PROJECT_DIR/rtl/core_v1"
HLS_DIR="$PROJECT_DIR/hls/core_v1"
IP_REPO_DIR="$HLS_DIR/build/m11_4/ip_repo"
LOCAL_BUILD_DIR="$APP_DIR/build/mnist-10"
VIVADO_PROJECT_DIR="$LOCAL_BUILD_DIR/vivado_project"
REPORT_DIR="$LOCAL_BUILD_DIR/reports"
ARTIFACT_DIR="$LOCAL_BUILD_DIR/artifacts"
LOG_FILE="$LOCAL_BUILD_DIR/mnist_10_vivado.log"
JOBS="${MNIST_10_JOBS:-4}"

STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/mnist_10"
DECODER_RTL="$STAGE_ROOT/m08_weight_decoder_v1.sv"
PHASE_B_RTL="$STAGE_ROOT/phase_b_synapse_accumulator_v1.sv"
NEURON_RTL="$STAGE_ROOT/neuron_array_controller_v1.sv"
INTEGRATED_RTL="$STAGE_ROOT/integrated_core_controller_v1.sv"
ROUTE_RTL="$STAGE_ROOT/recurrent_route_queue_v1.sv"
RECURRENT_RTL="$STAGE_ROOT/recurrent_integrated_core_controller_v1.sv"
BRIDGE_RTL="$STAGE_ROOT/m12_trace_read_bridge_v1.sv"
CAPTURE_RTL="$STAGE_ROOT/m12_5_characterization_capture_controller_v1.sv"
CAPTURE_BD_RTL="$STAGE_ROOT/m12_5_characterization_capture_controller_bd_v1.v"
CAPTURE_VECTORS="$STAGE_ROOT/generated_m12_3_multitick_cases.svh"
VIVADO_TCL="$STAGE_ROOT/create_m12_5_project.tcl"

for tool in vivado python3; do
    command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: $tool is not on PATH." >&2; exit 2; }
done
VIVADO_VERSION="$(vivado -version 2>&1 || true)"
[[ "$VIVADO_VERSION" == *"$EXPECTED_VERSION"* ]] || { echo "ERROR: Vivado $EXPECTED_VERSION required." >&2; exit 2; }
if [[ -n "${HLS_PART:-}" && "$HLS_PART" != "$EXPECTED_PART" ]]; then
    echo "ERROR: MNIST-10 is frozen to $EXPECTED_PART, but HLS_PART=$HLS_PART" >&2
    exit 2
fi
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: MNIST_10_JOBS must be positive." >&2; exit 2; }
[[ -f "$IP_REPO_DIR/neuron_step_v1/component.xml" ]] || {
    echo "ERROR: packaged neuron_step_v1 IP missing; run Neuromorphic Digital Twin/hls/core_v1/run_m11_4.sh first." >&2
    exit 3
}

rm -rf "$VIVADO_PROJECT_DIR" "$REPORT_DIR" "$ARTIFACT_DIR" "$STAGE_ROOT"
mkdir -p "$REPORT_DIR" "$ARTIFACT_DIR" "$STAGE_ROOT"
cp "$CORE_RTL/m08_weight_decoder_v1.sv" "$DECODER_RTL"
cp "$CORE_RTL/phase_b_synapse_accumulator_v1.sv" "$PHASE_B_RTL"
cp "$CORE_RTL/neuron_array_controller_v1.sv" "$NEURON_RTL"
cp "$CORE_RTL/integrated_core_controller_v1.sv" "$INTEGRATED_RTL"
cp "$CORE_RTL/recurrent_route_queue_v1.sv" "$ROUTE_RTL"
cp "$CORE_RTL/recurrent_integrated_core_controller_v1.sv" "$RECURRENT_RTL"
cp "$CORE_RTL/m12_trace_read_bridge_v1.sv" "$BRIDGE_RTL"
cp "$CORE_RTL/m12_5_characterization_capture_controller_bd_v1.v" "$CAPTURE_BD_RTL"
cp "$CORE_RTL/vivado/create_m12_5_project.tcl" "$VIVADO_TCL"

PYTHONPATH="$APP_DIR:$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 - "$SCRIPT_DIR/mnist_09_runtime_controller_v1.sv" "$CAPTURE_RTL" <<'PY'
from pathlib import Path
import sys
from mnist_app.characterization_runtime import write_timing_runtime_controller
write_timing_runtime_controller(Path(sys.argv[1]), Path(sys.argv[2]))
PY

PYTHONPATH="$APP_DIR:$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$APP_DIR/scripts/generate_runtime_profiles.py" \
    --frozen-root "$APP_DIR/frozen/mnist-v1" \
    --sv-output "$CAPTURE_VECTORS"

if grep -Eq 'M12_3_EXPECTED|M12_3_EXTERNAL_(COUNTS|ROWS|EVENTS)[[:space:]]*\[|RECURRENT_SCHEDULE' "$CAPTURE_VECTORS"; then
    echo "ERROR: MNIST-10 static include unexpectedly contains runtime/golden event data." >&2
    exit 3
fi
if ! grep -Fq 'observed_last_tick_cycles <= tick_cycle_counter' "$CAPTURE_RTL"; then
    echo "ERROR: passive MNIST-10 cycle counter was not staged." >&2
    exit 3
fi

printf 'MNIST-10 toolchain: Vivado %s\n' "$EXPECTED_VERSION"
printf 'MNIST-10 target part: %s\n' "$EXPECTED_PART"
printf 'MNIST-10 runtime: same frozen profiles and host-streamed events as MNIST-09\n'
printf 'MNIST-10 timing witness: passive M12.5 tick_start -> tick_done PL-cycle counter\n'

echo
echo '=== MNIST-10 characterized reusable runtime implementation + bitstream ==='
vivado -mode batch \
    -source "$VIVADO_TCL" \
    -tclargs \
    "$IP_REPO_DIR" "$VIVADO_PROJECT_DIR" "$EXPECTED_PART" "$EXPECTED_VLNV" \
    "$DECODER_RTL" "$PHASE_B_RTL" "$NEURON_RTL" "$INTEGRATED_RTL" \
    "$ROUTE_RTL" "$RECURRENT_RTL" "$BRIDGE_RTL" "$CAPTURE_RTL" \
    "$CAPTURE_BD_RTL" "$CAPTURE_VECTORS" "$REPORT_DIR" "$ARTIFACT_DIR" "$JOBS" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M12.5 physical trace-capture block design validated successfully." \
    "M12.5 implementation completed successfully." \
    "M12.5 routed timing check passed:" \
    "M12.5 bitstream generated successfully."; do
    grep -Fq "$marker" "$LOG_FILE" || { echo "ERROR: missing implementation marker: $marker" >&2; exit 4; }
done

for ext in bit ltx xsa; do
    src="$ARTIFACT_DIR/neuromorphic_twin_m12_5.$ext"
    [[ -s "$src" ]] || { echo "ERROR: missing characterization artifact: $src" >&2; exit 4; }
    cp "$src" "$ARTIFACT_DIR/neuromorphic_twin_mnist_10.$ext"
done
src_dcp="$ARTIFACT_DIR/neuromorphic_twin_m12_5_routed.dcp"
[[ -s "$src_dcp" ]] || { echo "ERROR: missing routed DCP." >&2; exit 4; }
cp "$src_dcp" "$ARTIFACT_DIR/neuromorphic_twin_mnist_10_routed.dcp"
python3 "$CORE_RTL/check_m11_6_resources.py" "$REPORT_DIR/utilization_impl.rpt" "$REPORT_DIR/ram_utilization_impl.rpt"

echo
echo 'MNIST-10 characterized runtime bitstream completed successfully.'
printf 'Bitstream: %s\n' "$ARTIFACT_DIR/neuromorphic_twin_mnist_10.bit"
printf 'Debug probes: %s\n' "$ARTIFACT_DIR/neuromorphic_twin_mnist_10.ltx"
printf 'Reports: %s\n' "$REPORT_DIR"
printf 'Log: %s\n' "$LOG_FILE"
