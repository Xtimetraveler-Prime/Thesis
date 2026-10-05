#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
EXPECTED_VLNV="loihi-digital-twin.org:hls:loihi_core_v2_tick:1.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PACKAGE_CONFIG="$SCRIPT_DIR/hls_package.cfg"

require_tool() {
    local tool="$1"
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: $tool is not on PATH. Source Vivado/Vitis 2025.2 settings64.sh first." >&2
        exit 2
    }
}
require_version() {
    local tool="$1"; shift
    local out
    out="$("$tool" "$@" 2>&1 || true)"
    [[ "$out" == *"$EXPECTED_VERSION"* ]] || {
        echo "ERROR: $tool is not reporting version $EXPECTED_VERSION" >&2
        echo "$out" >&2
        exit 2
    }
}

for tool in python3 vitis vitis-run v++ vivado; do require_tool "$tool"; done
require_version vitis --version
require_version vitis-run --version
require_version v++ --version
require_version vivado -version

: "${HLS_PART:=$EXPECTED_PART}"
if [[ "$HLS_PART" != "$EXPECTED_PART" ]]; then
    echo "ERROR: P03 packaging is frozen to $EXPECTED_PART, got HLS_PART=$HLS_PART" >&2
    exit 2
fi

STAGE_ROOT="/tmp/loihi_twin_v2_hls_${UID}/p03_package"
WORK_DIR="$STAGE_ROOT/work"
BUILD_DIR="$SCRIPT_DIR/build/p03_package"
IP_REPO_DIR="$BUILD_DIR/ip_repo"
rm -rf "$STAGE_ROOT" "$BUILD_DIR"
mkdir -p "$STAGE_ROOT" "$BUILD_DIR"
cp -R "$SCRIPT_DIR/include" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/src" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/tb" "$STAGE_ROOT/"
cp "$PACKAGE_CONFIG" "$STAGE_ROOT/hls_package.cfg"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p03_hls_vectors.py" \
    --output "$STAGE_ROOT/tb/generated_p03_vectors.inc"

printf 'P03 package toolchain: Vivado/Vitis %s\n' "$EXPECTED_VERSION"
printf 'P03 package part: %s\n' "$HLS_PART"
printf 'P03 package VLNV: %s\n' "$EXPECTED_VLNV"

cd "$STAGE_ROOT"
v++ -c --mode hls \
    --config hls_package.cfg \
    --work_dir "$WORK_DIR" \
    --part "$HLS_PART" \
    2>&1 | tee "$BUILD_DIR/vpp_hls_package_synthesis.log"

vitis-run --mode hls --package \
    --config hls_package.cfg \
    --work_dir "$WORK_DIR" \
    --part "$HLS_PART" \
    2>&1 | tee "$BUILD_DIR/vitis_hls_package.log"

COMPONENT_XML="$(find "$WORK_DIR" -type f -path '*/impl/ip/component.xml' -print -quit)"
if [[ -z "$COMPONENT_XML" ]]; then
    COMPONENT_XML="$(find "$WORK_DIR" -type f -name component.xml -print -quit)"
fi
[[ -n "$COMPONENT_XML" ]] || {
    echo "ERROR: package completed but component.xml was not found under $WORK_DIR" >&2
    exit 3
}

PACKAGED_IP_DIR="$(dirname "$COMPONENT_XML")"
mkdir -p "$IP_REPO_DIR/loihi_core_v2_tick"
cp -a "$PACKAGED_IP_DIR/." "$IP_REPO_DIR/loihi_core_v2_tick/"

printf 'P03 packaged IP repository: %s\n' "$IP_REPO_DIR"
printf 'P03 packaged component: %s\n' "$IP_REPO_DIR/loihi_core_v2_tick/component.xml"
