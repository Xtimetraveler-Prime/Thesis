#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v1"
IP_REPO_DIR="$HLS_DIR/build/m11_4/ip_repo"
LOCAL_BUILD_DIR="$SCRIPT_DIR/build/m12_2"
VIVADO_PROJECT_DIR="$LOCAL_BUILD_DIR/vivado_project"
REPORT_DIR="$LOCAL_BUILD_DIR/reports"
ARTIFACT_DIR="$LOCAL_BUILD_DIR/artifacts"
GOLDEN_DIR="$LOCAL_BUILD_DIR/golden"
LOG_FILE="$LOCAL_BUILD_DIR/m12_2_vivado.log"
JOBS="${M12_2_JOBS:-4}"

STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m12_2"
DECODER_RTL="$STAGE_ROOT/m08_weight_decoder_v1.sv"
PHASE_B_RTL="$STAGE_ROOT/phase_b_synapse_accumulator_v1.sv"
NEURON_RTL="$STAGE_ROOT/neuron_array_controller_v1.sv"
INTEGRATED_RTL="$STAGE_ROOT/integrated_core_controller_v1.sv"
ROUTE_RTL="$STAGE_ROOT/recurrent_route_queue_v1.sv"
RECURRENT_RTL="$STAGE_ROOT/recurrent_integrated_core_controller_v1.sv"
BRIDGE_RTL="$STAGE_ROOT/m12_trace_read_bridge_v1.sv"
CAPTURE_RTL="$STAGE_ROOT/m12_2_single_tick_capture_controller_v1.sv"
CAPTURE_BD_RTL="$STAGE_ROOT/m12_2_single_tick_capture_controller_bd_v1.v"
CAPTURE_VECTORS="$STAGE_ROOT/generated_m12_2_single_tick_cases.svh"
VIVADO_TCL="$STAGE_ROOT/create_m12_2_project.tcl"

require_tool() {
    local tool="$1"
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool is not on PATH. Source the Vivado 2025.2 settings64.sh first." >&2
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
    echo "ERROR: M12.2 is frozen to $EXPECTED_PART, but HLS_PART=$HLS_PART" >&2
    exit 2
fi
if [[ ! "$JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: M12_2_JOBS must be a positive integer; got '$JOBS'." >&2
    exit 2
fi

if [[ ! -f "$IP_REPO_DIR/neuron_step_v1/component.xml" ]]; then
    echo "ERROR: the M11.4 packaged neuron_step_v1 IP repository was not found:" >&2
    echo "  $IP_REPO_DIR/neuron_step_v1/component.xml" >&2
    echo "Recreate it once with:" >&2
    echo "  export HLS_PART='$EXPECTED_PART'" >&2
    echo "  cd '$HLS_DIR'" >&2
    echo "  bash run_m11_4.sh" >&2
    exit 3
fi

SOURCE_FILES=(
    "$SCRIPT_DIR/m08_weight_decoder_v1.sv"
    "$SCRIPT_DIR/phase_b_synapse_accumulator_v1.sv"
    "$SCRIPT_DIR/neuron_array_controller_v1.sv"
    "$SCRIPT_DIR/integrated_core_controller_v1.sv"
    "$SCRIPT_DIR/recurrent_route_queue_v1.sv"
    "$SCRIPT_DIR/recurrent_integrated_core_controller_v1.sv"
    "$SCRIPT_DIR/m12_trace_read_bridge_v1.sv"
    "$SCRIPT_DIR/m12_2_single_tick_capture_controller_v1.sv"
    "$SCRIPT_DIR/m12_2_single_tick_capture_controller_bd_v1.v"
    "$SCRIPT_DIR/vivado/create_m12_2_project.tcl"
    "$SCRIPT_DIR/check_m11_6_resources.py"
    "$PROJECT_DIR/examples/generate_m12_2_single_tick_corpus.py"
)
for path in "${SOURCE_FILES[@]}"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: missing M12.2 source file: $path" >&2
        exit 3
    fi
done

rm -rf "$LOCAL_BUILD_DIR" "$STAGE_ROOT"
mkdir -p "$LOCAL_BUILD_DIR" "$REPORT_DIR" "$ARTIFACT_DIR" "$GOLDEN_DIR" "$STAGE_ROOT"
cp "$SCRIPT_DIR/m08_weight_decoder_v1.sv" "$DECODER_RTL"
cp "$SCRIPT_DIR/phase_b_synapse_accumulator_v1.sv" "$PHASE_B_RTL"
cp "$SCRIPT_DIR/neuron_array_controller_v1.sv" "$NEURON_RTL"
cp "$SCRIPT_DIR/integrated_core_controller_v1.sv" "$INTEGRATED_RTL"
cp "$SCRIPT_DIR/recurrent_route_queue_v1.sv" "$ROUTE_RTL"
cp "$SCRIPT_DIR/recurrent_integrated_core_controller_v1.sv" "$RECURRENT_RTL"
cp "$SCRIPT_DIR/m12_trace_read_bridge_v1.sv" "$BRIDGE_RTL"
cp "$SCRIPT_DIR/m12_2_single_tick_capture_controller_v1.sv" "$CAPTURE_RTL"
cp "$SCRIPT_DIR/m12_2_single_tick_capture_controller_bd_v1.v" "$CAPTURE_BD_RTL"
cp "$SCRIPT_DIR/vivado/create_m12_2_project.tcl" "$VIVADO_TCL"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_m12_2_single_tick_corpus.py" \
    --output-dir "$GOLDEN_DIR" \
    --sv-output "$CAPTURE_VECTORS"

if grep -Fq 'M12_2_EXPECTED' "$CAPTURE_VECTORS"; then
    echo "ERROR: generated M12.2 FPGA include contains forbidden golden-output arrays." >&2
    exit 3
fi

printf 'M12.2 toolchain: Vivado %s\n' "$EXPECTED_VERSION"
printf 'M12.2 target part: %s\n' "$EXPECTED_PART"
printf 'M12.2 packaged HLS IP: %s\n' "$EXPECTED_VLNV"
printf 'M12.2 implementation jobs: %s\n' "$JOBS"
printf 'M12.2 directed cases: 16\n'
printf 'M12.2 no-space staging directory: %s\n' "$STAGE_ROOT"

echo
echo '=== M12.2 routed implementation + bitstream ==='
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
    "M12.2 physical trace-capture block design validated successfully." \
    "M12.2 implementation completed successfully." \
    "M12.2 routed timing check passed:" \
    "M12.2 bitstream generated successfully."; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: Vivado returned without expected M12.2 marker: $marker" >&2
        exit 4
    fi
done

BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2.ltx"
XSA_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2.xsa"
DCP_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2_routed.dcp"
REQUIRED_REPORTS=(
    "$REPORT_DIR/utilization_impl.rpt"
    "$REPORT_DIR/utilization_hierarchical_impl.rpt"
    "$REPORT_DIR/ram_utilization_impl.rpt"
    "$REPORT_DIR/ram_utilization_impl.csv"
    "$REPORT_DIR/timing_summary_impl.rpt"
    "$REPORT_DIR/setup_paths_impl.rpt"
    "$REPORT_DIR/hold_paths_impl.rpt"
    "$REPORT_DIR/route_status_impl.rpt"
    "$REPORT_DIR/methodology_impl.rpt"
    "$REPORT_DIR/drc_impl.rpt"
    "$REPORT_DIR/clocks_impl.rpt"
)
for artifact in "$BIT_FILE" "$LTX_FILE" "$XSA_FILE" "$DCP_FILE"; do
    if [[ ! -s "$artifact" ]]; then
        echo "ERROR: required M12.2 artifact is missing or empty: $artifact" >&2
        exit 4
    fi
done
for report in "${REQUIRED_REPORTS[@]}"; do
    if [[ ! -s "$report" ]]; then
        echo "ERROR: required M12.2 report is missing or empty: $report" >&2
        exit 4
    fi
done
if [[ ! -s "$GOLDEN_DIR/manifest.json" ]]; then
    echo "ERROR: M12.2 golden corpus manifest is missing." >&2
    exit 4
fi

python3 "$SCRIPT_DIR/check_m11_6_resources.py" \
    "$REPORT_DIR/utilization_impl.rpt" \
    "$REPORT_DIR/ram_utilization_impl.rpt"

echo
echo 'M12.2 routed bitstream flow completed successfully.'
printf 'Bitstream: %s\n' "$BIT_FILE"
printf 'Debug probes: %s\n' "$LTX_FILE"
printf 'Golden corpus: %s\n' "$GOLDEN_DIR/manifest.json"
printf 'Hardware handoff: %s\n' "$XSA_FILE"
printf 'Routed checkpoint: %s\n' "$DCP_FILE"
printf 'Reports: %s\n' "$REPORT_DIR"
printf 'Log: %s\n' "$LOG_FILE"
