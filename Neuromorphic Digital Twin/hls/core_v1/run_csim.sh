#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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

echo "M11 toolchain: Vitis/Vivado $EXPECTED_VERSION"
echo "HLS target part: $HLS_PART"

rm -rf build/csim

vitis-run --mode hls --csim \
    --config hls_config.cfg \
    --work_dir build/csim \
    --part "$HLS_PART"
