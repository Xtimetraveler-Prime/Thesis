#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="neuromorphic-twin.org:hls:neuron_step_v1:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PACKAGE_CONFIG="$SCRIPT_DIR/hls_package.cfg"
VIVADO_TCL="$SCRIPT_DIR/vivado/create_m11_4_project.tcl"

require_tool() {
    local tool="$1"
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool is not on PATH. Source the Vitis/Vivado 2025.2 settings64.sh first." >&2
        exit 2
    fi
}

require_version() {
    local tool="$1"
    shift
    local version_output
    version_output="$("$tool" "$@" 2>&1 || true)"
    if [[ "$version_output" != *"$EXPECTED_VERSION"* ]]; then
        echo "ERROR: $tool is not reporting version $EXPECTED_VERSION." >&2
        echo "$version_output" >&2
        exit 2
    fi
}

for tool in python3 vitis vitis-run v++ vivado; do
    require_tool "$tool"
done

require_version vitis --version
require_version vitis-run --version
require_version v++ --version
require_version vivado -version

if [[ -z "${HLS_PART:-}" ]]; then
    echo "ERROR: HLS_PART is not set. For M11.4 use: export HLS_PART='$EXPECTED_PART'" >&2
    exit 2
fi

if [[ "$HLS_PART" != "$EXPECTED_PART" ]]; then
    echo "ERROR: M11.4 is frozen to target part $EXPECTED_PART, but HLS_PART=$HLS_PART" >&2
    exit 2
fi

if [[ ! -f "$PACKAGE_CONFIG" ]]; then
    echo "ERROR: missing package config: $PACKAGE_CONFIG" >&2
    exit 2
fi
if [[ ! -f "$VIVADO_TCL" ]]; then
    echo "ERROR: missing Vivado Tcl project script: $VIVADO_TCL" >&2
    exit 2
fi

STAGE_ROOT="/tmp/neuromorphic_twin_hls_${UID}/m11_4"
WORK_DIR="$STAGE_ROOT/work"
LOCAL_BUILD_DIR="$SCRIPT_DIR/build/m11_4"
IP_REPO_DIR="$LOCAL_BUILD_DIR/ip_repo"
VIVADO_PROJECT_DIR="$LOCAL_BUILD_DIR/vivado_project"

rm -rf "$STAGE_ROOT" "$LOCAL_BUILD_DIR"
mkdir -p "$STAGE_ROOT" "$LOCAL_BUILD_DIR"
cp -R "$SCRIPT_DIR/include" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/src" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/tb" "$STAGE_ROOT/"
cp "$PACKAGE_CONFIG" "$STAGE_ROOT/hls_package.cfg"

# Keep synthesis reproducible from the same source tree and make the generated
# M11.2 include available if the tool inspects the testbench during packaging.
PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_m11_hls_vectors.py" \
    --output "$STAGE_ROOT/tb/generated_m11_2_vectors.inc"

printf 'M11.4 toolchain: Vitis/Vivado %s\n' "$EXPECTED_VERSION"
printf 'M11.4 target part: %s\n' "$HLS_PART"
printf 'M11.4 packaged IP VLNV: %s\n' "$EXPECTED_VLNV"
printf 'M11.4 staging directory: %s\n' "$STAGE_ROOT"

cd "$STAGE_ROOT"

echo
echo '=== M11.4 HLS synthesis for packaging ==='
v++ -c --mode hls \
    --config hls_package.cfg \
    --work_dir "$WORK_DIR" \
    --part "$HLS_PART" \
    2>&1 | tee "$LOCAL_BUILD_DIR/vpp_hls_package_synthesis.log"

echo
echo '=== M11.4 package Vivado IP ==='
vitis-run --mode hls --package \
    --config hls_package.cfg \
    --work_dir "$WORK_DIR" \
    --part "$HLS_PART" \
    2>&1 | tee "$LOCAL_BUILD_DIR/vitis_hls_package.log"

COMPONENT_XML="$(find "$WORK_DIR" -type f -path '*/impl/ip/component.xml' -print -quit)"
if [[ -z "$COMPONENT_XML" ]]; then
    COMPONENT_XML="$(find "$WORK_DIR" -type f -name component.xml -print -quit)"
fi
if [[ -z "$COMPONENT_XML" ]]; then
    echo "ERROR: package completed but no packaged IP component.xml was found under $WORK_DIR" >&2
    exit 3
fi

PACKAGED_IP_DIR="$(dirname "$COMPONENT_XML")"
mkdir -p "$IP_REPO_DIR/neuron_step_v1"
cp -a "$PACKAGED_IP_DIR/." "$IP_REPO_DIR/neuron_step_v1/"

IP_ZIP="$(find "$STAGE_ROOT" -type f -name '*.zip' -print -quit)"
if [[ -n "$IP_ZIP" ]]; then
    cp "$IP_ZIP" "$LOCAL_BUILD_DIR/neuron_step_v1_ip.zip"
    printf 'Packaged IP ZIP: %s\n' "$LOCAL_BUILD_DIR/neuron_step_v1_ip.zip"
else
    echo "WARNING: package succeeded but no ZIP was found; continuing with the unzipped impl/ip repository." >&2
fi

printf 'Vivado IP repository: %s\n' "$IP_REPO_DIR"

echo
echo '=== M11.4 create Vivado project and block design ==='
vivado -mode batch \
    -source "$VIVADO_TCL" \
    -tclargs "$IP_REPO_DIR" "$VIVADO_PROJECT_DIR" "$EXPECTED_PART" "$EXPECTED_VLNV" \
    2>&1 | tee "$LOCAL_BUILD_DIR/vivado_project_create.log"

PROJECT_FILE="$(find "$VIVADO_PROJECT_DIR" -maxdepth 2 -type f -name '*.xpr' -print -quit)"
BD_FILE="$(find "$VIVADO_PROJECT_DIR" -type f -name 'neuromorphic_twin_core.bd' -print -quit)"

if [[ -z "$PROJECT_FILE" ]]; then
    echo "ERROR: Vivado returned success but no .xpr project file was found." >&2
    exit 4
fi
if [[ -z "$BD_FILE" ]]; then
    echo "ERROR: Vivado returned success but neuromorphic_twin_core.bd was not found." >&2
    exit 4
fi

echo
echo 'M11.4 packaging and Vivado project creation completed successfully.'
printf 'Vivado project: %s\n' "$PROJECT_FILE"
printf 'Block design: %s\n' "$BD_FILE"
printf 'Generated evidence/logs: %s\n' "$LOCAL_BUILD_DIR"
