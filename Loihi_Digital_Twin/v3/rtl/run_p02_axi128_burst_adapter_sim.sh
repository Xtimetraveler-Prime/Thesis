#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/p02_axi128_burst_adapter_sim"
TOP="test_p02_axi128_burst_adapter"

command -v xvlog >/dev/null 2>&1 || {
    echo "ERROR: xvlog is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}
command -v xelab >/dev/null 2>&1 || {
    echo "ERROR: xelab is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}
command -v xsim >/dev/null 2>&1 || {
    echo "ERROR: xsim is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

xvlog     "$SCRIPT_DIR/p02_axi128_burst_adapter.v"     "$SCRIPT_DIR/tb/test_p02_axi128_burst_adapter.v"     2>&1 | tee xvlog.log

xelab "$TOP" -s p02_axi128_burst_adapter_sim     2>&1 | tee xelab.log

xsim p02_axi128_burst_adapter_sim -runall     2>&1 | tee xsim.log

grep -q 'PASS: p02_axi128_burst_adapter' xsim.log || {
    echo "ERROR: P02.3b1 AXI burst-adapter PASS marker not found." >&2
    exit 3
}
if grep -q 'FAIL:' xsim.log; then
    echo "ERROR: P02.3b1 AXI burst-adapter simulation emitted FAIL." >&2
    exit 3
fi

echo "PASS: P02.3b1 AXI burst-adapter simulation completed successfully."
