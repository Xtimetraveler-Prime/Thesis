#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_PART="xck26-sfvc784-2LV-c"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

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
    local output
    output="$("$tool" "$@" 2>&1 || true)"
    if [[ "$output" != *"$EXPECTED_VERSION"* ]]; then
        echo "ERROR: $tool is not reporting version $EXPECTED_VERSION." >&2
        echo "$output" >&2
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
    echo "ERROR: HLS_PART is not set. Use: export HLS_PART='$EXPECTED_PART'" >&2
    exit 2
fi
if [[ "$HLS_PART" != "$EXPECTED_PART" ]]; then
    echo "ERROR: P03 is targeted to $EXPECTED_PART, but HLS_PART=$HLS_PART" >&2
    exit 2
fi

STAGE_ROOT="/tmp/loihi_twin_v2_hls_${UID}/p03_core_csim"
WORK_DIR="$STAGE_ROOT/work"
rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE_ROOT"
cp -R "$SCRIPT_DIR/include" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/src" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/tb" "$STAGE_ROOT/"
cp "$SCRIPT_DIR/hls_config.cfg" "$STAGE_ROOT/"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p03_hls_vectors.py" \
    --output "$STAGE_ROOT/tb/generated_p03_vectors.inc"

printf 'P03 toolchain: Vitis/Vivado %s\n' "$EXPECTED_VERSION"
printf 'P03 target part: %s\n' "$HLS_PART"
printf 'P03 staging directory: %s\n' "$STAGE_ROOT"

cd "$STAGE_ROOT"
vitis-run --mode hls --csim \
    --config hls_config.cfg \
    --work_dir "$WORK_DIR" \
    --part "$HLS_PART"

echo 'P03 HLS C simulation completed successfully.'
