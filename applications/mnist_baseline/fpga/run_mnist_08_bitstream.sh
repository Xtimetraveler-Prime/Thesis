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
LOCAL_BUILD_DIR="$APP_DIR/build/mnist-08"
VIVADO_PROJECT_DIR="$LOCAL_BUILD_DIR/vivado_project"
REPORT_DIR="$LOCAL_BUILD_DIR/reports"
ARTIFACT_DIR="$LOCAL_BUILD_DIR/artifacts"
GOLDEN_DIR="$LOCAL_BUILD_DIR/golden"
LOG_FILE="$LOCAL_BUILD_DIR/mnist_08_vivado.log"
JOBS="${MNIST_08_JOBS:-4}"

STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/mnist_08"
DECODER_RTL="$STAGE_ROOT/m08_weight_decoder_v1.sv"
PHASE_B_RTL="$STAGE_ROOT/phase_b_synapse_accumulator_v1.sv"
NEURON_RTL="$STAGE_ROOT/neuron_array_controller_v1.sv"
INTEGRATED_RTL="$STAGE_ROOT/integrated_core_controller_v1.sv"
ROUTE_RTL="$STAGE_ROOT/recurrent_route_queue_v1.sv"
RECURRENT_RTL="$STAGE_ROOT/recurrent_integrated_core_controller_v1.sv"
BRIDGE_RTL="$STAGE_ROOT/m12_trace_read_bridge_v1.sv"
CAPTURE_RTL="$STAGE_ROOT/m12_3_multitick_capture_controller_v1.sv"
CAPTURE_BD_RTL="$STAGE_ROOT/m12_3_multitick_capture_controller_bd_v1.v"
CAPTURE_VECTORS="$STAGE_ROOT/generated_m12_3_multitick_cases.svh"
VIVADO_TCL="$STAGE_ROOT/create_m12_3_project.tcl"

require_tool() {
    local tool="$1"
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool is not on PATH." >&2
        exit 2
    fi
}
require_tool vivado
require_tool python3

VIVADO_VERSION="$(vivado -version 2>&1 || true)"
if [[ "$VIVADO_VERSION" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: vivado is not reporting version $EXPECTED_VERSION." >&2
    echo "$VIVADO_VERSION" >&2
    exit 2
fi
if [[ -n "${HLS_PART:-}" && "$HLS_PART" != "$EXPECTED_PART" ]]; then
    echo "ERROR: MNIST-08 is frozen to $EXPECTED_PART, but HLS_PART=$HLS_PART" >&2
    exit 2
fi
if [[ ! "$JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: MNIST_08_JOBS must be a positive integer; got '$JOBS'." >&2
    exit 2
fi
if [[ ! -f "$IP_REPO_DIR/neuron_step_v1/component.xml" ]]; then
    echo "ERROR: packaged neuron_step_v1 IP not found at $IP_REPO_DIR." >&2
    echo "Recreate it first with Neuromorphic Digital Twin/hls/core_v1/run_m11_4.sh." >&2
    exit 3
fi

SOURCE_FILES=(
    "$CORE_RTL/m08_weight_decoder_v1.sv"
    "$CORE_RTL/phase_b_synapse_accumulator_v1.sv"
    "$CORE_RTL/neuron_array_controller_v1.sv"
    "$CORE_RTL/integrated_core_controller_v1.sv"
    "$CORE_RTL/recurrent_route_queue_v1.sv"
    "$CORE_RTL/recurrent_integrated_core_controller_v1.sv"
    "$CORE_RTL/m12_trace_read_bridge_v1.sv"
    "$CORE_RTL/m12_3_multitick_capture_controller_v1.sv"
    "$CORE_RTL/m12_3_multitick_capture_controller_bd_v1.v"
    "$CORE_RTL/vivado/create_m12_3_project.tcl"
    "$CORE_RTL/check_m11_6_resources.py"
    "$APP_DIR/scripts/generate_fpga_corpus.py"
    "$APP_DIR/mnist_app/fpga_corpus_shell.py"
)
for path in "${SOURCE_FILES[@]}"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: missing MNIST-08 source file: $path" >&2
        exit 3
    fi
done

rm -rf "$LOCAL_BUILD_DIR" "$STAGE_ROOT"
mkdir -p "$REPORT_DIR" "$ARTIFACT_DIR" "$GOLDEN_DIR" "$STAGE_ROOT"
cp "$CORE_RTL/m08_weight_decoder_v1.sv" "$DECODER_RTL"
cp "$CORE_RTL/phase_b_synapse_accumulator_v1.sv" "$PHASE_B_RTL"
cp "$CORE_RTL/neuron_array_controller_v1.sv" "$NEURON_RTL"
cp "$CORE_RTL/integrated_core_controller_v1.sv" "$INTEGRATED_RTL"
cp "$CORE_RTL/recurrent_route_queue_v1.sv" "$ROUTE_RTL"
cp "$CORE_RTL/recurrent_integrated_core_controller_v1.sv" "$RECURRENT_RTL"
cp "$CORE_RTL/m12_trace_read_bridge_v1.sv" "$BRIDGE_RTL"
cp "$CORE_RTL/m12_3_multitick_capture_controller_bd_v1.v" "$CAPTURE_BD_RTL"
cp "$CORE_RTL/vivado/create_m12_3_project.tcl" "$VIVADO_TCL"

PYTHONPATH="$APP_DIR:$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 - "$CORE_RTL/m12_3_multitick_capture_controller_v1.sv" "$CAPTURE_RTL" <<'PY'
from pathlib import Path
import sys
from mnist_app.fpga_corpus_shell import write_patched_capture_controller
write_patched_capture_controller(Path(sys.argv[1]), Path(sys.argv[2]))
PY

PYTHONPATH="$APP_DIR:$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$APP_DIR/scripts/generate_fpga_corpus.py" \
    --frozen-root "$APP_DIR/frozen/mnist-v1" \
    --output-dir "$GOLDEN_DIR" \
    --sv-output "$CAPTURE_VECTORS"

if grep -Eq 'M12_3_EXPECTED|RECURRENT_SCHEDULE|RECURRENT_EVENTS' "$CAPTURE_VECTORS"; then
    echo "ERROR: generated MNIST-08 FPGA include contains forbidden golden/recurrent schedule arrays." >&2
    exit 3
fi
for required_token in M12_3_CASE_PROFILE_IDS M12_3_EXTERNAL_ROWS; do
    if ! grep -Fq "$required_token" "$CAPTURE_VECTORS"; then
        echo "ERROR: generated MNIST-08 include is missing $required_token." >&2
        exit 3
    fi
done
if ! grep -Fq 'static_image_id = M12_3_CASE_PROFILE_IDS[active_case_id]' "$CAPTURE_RTL"; then
    echo "ERROR: MNIST-08 staged capture controller did not receive shared-profile patch." >&2
    exit 3
fi
if ! grep -Fq 'M12_3_EXTERNAL_ROWS[' "$CAPTURE_RTL"; then
    echo "ERROR: MNIST-08 staged capture controller did not receive packed-event patch." >&2
    exit 3
fi

printf 'MNIST-08 toolchain: Vivado %s\n' "$EXPECTED_VERSION"
printf 'MNIST-08 target part: %s\n' "$EXPECTED_PART"
printf 'MNIST-08 packaged HLS IP: %s\n' "$EXPECTED_VLNV"
printf 'MNIST-08 implementation jobs: %s\n' "$JOBS"
printf 'MNIST-08 source images: 30\n'
printf 'MNIST-08 physical cases: 60\n'
printf 'MNIST-08 committed ticks: 960\n'

echo
echo '=== MNIST-08 routed corpus implementation + bitstream ==='
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
    "$BRIDGE_RTL" \
    "$CAPTURE_RTL" \
    "$CAPTURE_BD_RTL" \
    "$CAPTURE_VECTORS" \
    "$REPORT_DIR" \
    "$ARTIFACT_DIR" \
    "$JOBS" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M12.3 physical trace-capture block design validated successfully." \
    "M12.3 implementation completed successfully." \
    "M12.3 routed timing check passed:" \
    "M12.3 bitstream generated successfully."; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: Vivado returned without expected capture-shell marker: $marker" >&2
        exit 4
    fi
done

M12_BIT="$ARTIFACT_DIR/neuromorphic_twin_m12_3.bit"
M12_LTX="$ARTIFACT_DIR/neuromorphic_twin_m12_3.ltx"
M12_XSA="$ARTIFACT_DIR/neuromorphic_twin_m12_3.xsa"
M12_DCP="$ARTIFACT_DIR/neuromorphic_twin_m12_3_routed.dcp"
for artifact in "$M12_BIT" "$M12_LTX" "$M12_XSA" "$M12_DCP"; do
    if [[ ! -s "$artifact" ]]; then
        echo "ERROR: required MNIST-08 implementation artifact missing: $artifact" >&2
        exit 4
    fi
done

cp "$M12_BIT" "$ARTIFACT_DIR/neuromorphic_twin_mnist_08.bit"
cp "$M12_LTX" "$ARTIFACT_DIR/neuromorphic_twin_mnist_08.ltx"
cp "$M12_XSA" "$ARTIFACT_DIR/neuromorphic_twin_mnist_08.xsa"
cp "$M12_DCP" "$ARTIFACT_DIR/neuromorphic_twin_mnist_08_routed.dcp"

if [[ ! -s "$GOLDEN_DIR/manifest.json" || ! -s "$GOLDEN_DIR/hardware_cases.tsv" ]]; then
    echo "ERROR: MNIST-08 golden corpus bundle is incomplete." >&2
    exit 4
fi
python3 "$CORE_RTL/check_m11_6_resources.py" \
    "$REPORT_DIR/utilization_impl.rpt" \
    "$REPORT_DIR/ram_utilization_impl.rpt"

echo
echo 'MNIST-08 routed corpus bitstream flow completed successfully.'
printf 'Bitstream: %s\n' "$ARTIFACT_DIR/neuromorphic_twin_mnist_08.bit"
printf 'Debug probes: %s\n' "$ARTIFACT_DIR/neuromorphic_twin_mnist_08.ltx"
printf 'Golden manifest: %s\n' "$GOLDEN_DIR/manifest.json"
printf 'Reports: %s\n' "$REPORT_DIR"
printf 'Log: %s\n' "$LOG_FILE"
