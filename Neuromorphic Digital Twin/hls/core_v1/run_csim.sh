#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
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
    local version_output
    version_output="$("$tool" "$@" 2>&1 || true)"
    if [[ "$version_output" != *"$EXPECTED_VERSION"* ]]; then
        echo "ERROR: $tool is not reporting version $EXPECTED_VERSION." >&2
        echo "$version_output" >&2
        exit 2
    fi
}

require_tool python3
require_tool vitis
require_tool vitis-run
require_tool v++
require_tool vivado

require_version vitis --version
require_version vitis-run --version
require_version v++ --version
require_version vivado -version

if [[ -z "${HLS_PART:-}" ]]; then
    cat >&2 <<'EOF'
ERROR: HLS_PART is not set.
Set it to the exact FPGA part used by the target Vivado project, for example:

    export HLS_PART='<exact-part-name>'

If you already have the board's Vivado project open, run this in the Vivado Tcl console:

    get_property PART [current_project]
EOF
    exit 2
fi

# Vitis HLS 2025.2 rejects project/solution paths containing spaces. The
# repository intentionally contains "Neuromorphic Digital Twin", so stage the
# HLS component under /tmp. The staged copy is recreated on every invocation.
STAGE_ROOT="/tmp/neuromorphic_twin_hls_${UID}/m11_core_csim"
WORK_DIR="$STAGE_ROOT/work"

rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE_ROOT"
cp -R "$SCRIPT_DIR/include" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/src" "$STAGE_ROOT/"
cp -R "$SCRIPT_DIR/tb" "$STAGE_ROOT/"
cp "$SCRIPT_DIR/hls_config.cfg" "$STAGE_ROOT/"

# M11.2: generate the differential corpus from the frozen Python FPGA-v1
# golden model directly into the staged testbench directory. The generated
# file is intentionally not checked into the repository.
PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_m11_hls_vectors.py" \
    --output "$STAGE_ROOT/tb/generated_m11_2_vectors.inc"

printf 'M11 toolchain: Vitis/Vivado %s\n' "$EXPECTED_VERSION"
printf 'HLS target part: %s\n' "$HLS_PART"
printf 'HLS staging directory: %s\n' "$STAGE_ROOT"

cd "$STAGE_ROOT"

vitis-run --mode hls --csim \
    --config hls_config.cfg \
    --work_dir "$WORK_DIR" \
    --part "$HLS_PART"
