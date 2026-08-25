#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
HLS_DIR="$PROJECT_DIR/hls/core_v1"
IP_REPO_DIR="$HLS_DIR/build/m11_4/ip_repo"
LOCAL_BUILD_DIR="$SCRIPT_DIR/build/m11_5_2_real_ip"
VIVADO_PROJECT_DIR="$LOCAL_BUILD_DIR/vivado_project"
VECTOR_FILE="$LOCAL_BUILD_DIR/generated_m11_5_2_vectors.svh"
VIVADO_TCL="$SCRIPT_DIR/vivado/create_m11_5_2_project.tcl"
CONTROLLER_RTL="$SCRIPT_DIR/neuron_array_controller_v1.sv"
CONTROLLER_BD_RTL="$SCRIPT_DIR/neuron_array_controller_bd_v1.sv"
TB_FILE="$SCRIPT_DIR/tb/tb_neuromorphic_twin_m11_5_2.sv"
LOG_FILE="$LOCAL_BUILD_DIR/m11_5_2_real_ip_vivado.log"
PASS_MARKER="M11.5.2 real packaged-IP integration passed:"

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
    echo "ERROR: M11.5.2 is frozen to $EXPECTED_PART, but HLS_PART=$HLS_PART" >&2
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

for path in "$VIVADO_TCL" "$CONTROLLER_RTL" "$CONTROLLER_BD_RTL" "$TB_FILE"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: missing M11.5.2 source file: $path" >&2
        exit 3
    fi
done

rm -rf "$LOCAL_BUILD_DIR"
mkdir -p "$LOCAL_BUILD_DIR"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_m11_5_2_vectors.py" \
    --output "$VECTOR_FILE"

printf 'M11.5.2 toolchain: Vivado %s\n' "$EXPECTED_VERSION"
printf 'M11.5.2 target part: %s\n' "$EXPECTED_PART"
printf 'M11.5.2 packaged HLS IP: %s\n' "$EXPECTED_VLNV"
printf 'M11.5.2 IP repository: %s\n' "$IP_REPO_DIR"

echo
echo '=== M11.5.2 controller + real packaged HLS IP ==='
vivado -mode batch \
    -source "$VIVADO_TCL" \
    -tclargs \
    "$IP_REPO_DIR" \
    "$VIVADO_PROJECT_DIR" \
    "$EXPECTED_PART" \
    "$EXPECTED_VLNV" \
    "$CONTROLLER_RTL" \
    "$CONTROLLER_BD_RTL" \
    "$TB_FILE" \
    "$VECTOR_FILE" \
    2>&1 | tee "$LOG_FILE"

if ! grep -Fq "$PASS_MARKER" "$LOG_FILE"; then
    echo "ERROR: Vivado returned without the M11.5.2 real-IP pass marker." >&2
    exit 4
fi

PROJECT_FILE="$VIVADO_PROJECT_DIR/neuromorphic_twin_m11_5_2.xpr"
BD_FILE="$(find "$VIVADO_PROJECT_DIR" -type f -name 'neuromorphic_twin_m11_5_2.bd' -print -quit)"
if [[ ! -f "$PROJECT_FILE" ]]; then
    echo "ERROR: real-IP simulation passed but the expected .xpr was not found." >&2
    exit 4
fi
if [[ -z "$BD_FILE" ]]; then
    echo "ERROR: real-IP simulation passed but the expected block design was not found." >&2
    exit 4
fi

echo
echo 'M11.5.2 controller + real packaged HLS IP simulation completed successfully.'
printf 'Vivado project: %s\n' "$PROJECT_FILE"
printf 'Block design: %s\n' "$BD_FILE"
printf 'Log: %s\n' "$LOG_FILE"
