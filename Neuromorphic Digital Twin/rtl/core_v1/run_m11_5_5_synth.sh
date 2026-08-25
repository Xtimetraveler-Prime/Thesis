#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v1"
IP_REPO_DIR="$HLS_DIR/build/m11_4/ip_repo"
LOCAL_BUILD_DIR="$SCRIPT_DIR/build/m11_5_5"
VIVADO_PROJECT_DIR="$LOCAL_BUILD_DIR/vivado_project"
REPORT_DIR="$LOCAL_BUILD_DIR/reports"
LOG_FILE="$LOCAL_BUILD_DIR/m11_5_5_synth_vivado.log"

STAGE_ROOT="/tmp/neuromorphic_twin_rtl_${UID}/m11_5_5_synth"
DECODER_RTL="$STAGE_ROOT/m08_weight_decoder_v1.sv"
PHASE_B_RTL="$STAGE_ROOT/phase_b_synapse_accumulator_v1.sv"
NEURON_RTL="$STAGE_ROOT/neuron_array_controller_v1.sv"
INTEGRATED_RTL="$STAGE_ROOT/integrated_core_controller_v1.sv"
ROUTE_RTL="$STAGE_ROOT/recurrent_route_queue_v1.sv"
RECURRENT_RTL="$STAGE_ROOT/recurrent_integrated_core_controller_v1.sv"
RECURRENT_BD_RTL="$STAGE_ROOT/recurrent_integrated_core_controller_bd_v1.v"
TIMING_XDC="$STAGE_ROOT/m11_5_5_timing.xdc"
VIVADO_TCL="$STAGE_ROOT/create_m11_5_5_project.tcl"

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
    echo "ERROR: M11.5.5 is frozen to $EXPECTED_PART, but HLS_PART=$HLS_PART" >&2
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
    "$SCRIPT_DIR/recurrent_integrated_core_controller_bd_v1.v"
    "$SCRIPT_DIR/vivado/m11_5_5_timing.xdc"
    "$SCRIPT_DIR/vivado/create_m11_5_5_project.tcl"
)
for path in "${SOURCE_FILES[@]}"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: missing M11.5.5 source file: $path" >&2
        exit 3
    fi
done

rm -rf "$LOCAL_BUILD_DIR" "$STAGE_ROOT"
mkdir -p "$LOCAL_BUILD_DIR" "$REPORT_DIR" "$STAGE_ROOT"
cp "$SCRIPT_DIR/m08_weight_decoder_v1.sv" "$DECODER_RTL"
cp "$SCRIPT_DIR/phase_b_synapse_accumulator_v1.sv" "$PHASE_B_RTL"
cp "$SCRIPT_DIR/neuron_array_controller_v1.sv" "$NEURON_RTL"
cp "$SCRIPT_DIR/integrated_core_controller_v1.sv" "$INTEGRATED_RTL"
cp "$SCRIPT_DIR/recurrent_route_queue_v1.sv" "$ROUTE_RTL"
cp "$SCRIPT_DIR/recurrent_integrated_core_controller_v1.sv" "$RECURRENT_RTL"
cp "$SCRIPT_DIR/recurrent_integrated_core_controller_bd_v1.v" "$RECURRENT_BD_RTL"
cp "$SCRIPT_DIR/vivado/m11_5_5_timing.xdc" "$TIMING_XDC"
cp "$SCRIPT_DIR/vivado/create_m11_5_5_project.tcl" "$VIVADO_TCL"

printf 'M11.5.5 toolchain: Vivado %s\n' "$EXPECTED_VERSION"
printf 'M11.5.5 target part: %s\n' "$EXPECTED_PART"
printf 'M11.5.5 packaged HLS IP: %s\n' "$EXPECTED_VLNV"
printf 'M11.5.5 no-space staging directory: %s\n' "$STAGE_ROOT"

echo
echo '=== M11.5.5 trace-capable complete-core synthesis ==='
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
    "$TIMING_XDC" \
    "$REPORT_DIR" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M11.5.5 trace-capable block design validated successfully." \
    "M11.5.5 synthesis reports generated successfully."; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: Vivado returned without expected marker: $marker" >&2
        exit 4
    fi
done

PROJECT_FILE="$VIVADO_PROJECT_DIR/neuromorphic_twin_m11_5_5.xpr"
DCP_FILE="$REPORT_DIR/neuromorphic_twin_m11_5_5_synth.dcp"
REQUIRED_REPORTS=(
    "$REPORT_DIR/utilization.rpt"
    "$REPORT_DIR/utilization_hierarchical.rpt"
    "$REPORT_DIR/ram_utilization.rpt"
    "$REPORT_DIR/ram_utilization.csv"
    "$REPORT_DIR/timing_summary_synth.rpt"
    "$REPORT_DIR/setup_paths_synth.rpt"
    "$REPORT_DIR/hold_paths_synth.rpt"
    "$REPORT_DIR/methodology_synth.rpt"
    "$REPORT_DIR/clocks.rpt"
)
if [[ ! -f "$PROJECT_FILE" || ! -f "$DCP_FILE" ]]; then
    echo "ERROR: synthesis completed without expected project/checkpoint artifacts." >&2
    exit 4
fi
for report in "${REQUIRED_REPORTS[@]}"; do
    if [[ ! -s "$report" ]]; then
        echo "ERROR: required M11.5.5 report is missing or empty: $report" >&2
        exit 4
    fi
done

# A synthesis run is not a usable physical boundary merely because Vivado
# completed. Reject any profile that exceeds the selected K26's available CLB
# LUT, register, block-RAM tile, DSP, or URAM capacity. This specifically guards
# against the first M11.5.5 profile, which synthesized but required 147% of the
# device CLB LUTs.
python3 - "$REPORT_DIR/utilization.rpt" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

report = Path(sys.argv[1])
lines = report.read_text(encoding="utf-8", errors="replace").splitlines()


def row(prefix: str) -> tuple[int, int]:
    for line in lines:
        if not line.lstrip().startswith("|"):
            continue
        fields = [field.strip() for field in line.strip().strip("|").split("|")]
        if not fields or not fields[0].startswith(prefix):
            continue
        # Standard Vivado utilization table columns:
        # Site Type | Used | Fixed | Prohibited | Available | Util%
        if len(fields) < 5:
            continue
        try:
            return int(fields[1]), int(fields[4])
        except ValueError:
            continue
    raise SystemExit(f"ERROR: could not locate utilization row: {prefix}")

checks = (
    ("CLB LUTs", "CLB_LUT"),
    ("CLB Registers", "CLB_REG"),
    ("Block RAM Tile", "BRAM_TILE"),
    ("DSPs", "DSP"),
    ("URAM", "URAM"),
)

summaries: list[str] = []
failed = False
for prefix, label in checks:
    used, available = row(prefix)
    summaries.append(f"{label}={used}/{available}")
    if used > available:
        print(
            f"ERROR: M11.5.5 physical resource overflow: "
            f"{label} used={used} available={available}",
            file=sys.stderr,
        )
        failed = True

if failed:
    raise SystemExit(5)

print("M11.5.5 resource capacity check passed: " + ", ".join(summaries))
PY

echo
echo 'M11.5.5 complete-core synthesis and reporting completed successfully.'
printf 'Vivado project: %s\n' "$PROJECT_FILE"
printf 'Synthesized checkpoint: %s\n' "$DCP_FILE"
printf 'Report directory: %s\n' "$REPORT_DIR"
printf 'Log: %s\n' "$LOG_FILE"
