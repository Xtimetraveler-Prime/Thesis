#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/p05_virtualized_controller_sim"
TOP="test_p05_virtualized_controller"

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

xvlog \
    "$SCRIPT_DIR/p04_packet_memory_streamer.v" \
    "$SCRIPT_DIR/p05_virtualized_controller.v" \
    "$SCRIPT_DIR/tb/test_p05_virtualized_controller.v" \
    2>&1 | tee xvlog.log

xelab "$TOP" -s p05_virtualized_controller_sim \
    2>&1 | tee xelab.log

xsim p05_virtualized_controller_sim -runall \
    2>&1 | tee xsim.log

grep -q 'PASS: P05 virtualized controller directed test completed successfully.' xsim.log || {
    echo "ERROR: P05 virtualized controller PASS marker not found." >&2
    exit 3
}
if grep -q 'FAIL:' xsim.log; then
    echo "ERROR: P05 virtualized controller simulation emitted FAIL." >&2
    exit 3
fi

echo "P05 virtualized controller simulation gate completed successfully."
