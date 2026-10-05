#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${TMPDIR:-/tmp}/loihi_twin_v2_p03_host_bridge_${UID:-0}"
SNAPSHOT="p03_host_bridge_tb"

for tool in xvlog xelab xsim; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: $tool is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
        exit 2
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

xvlog \
    "$SCRIPT_DIR/p03_memory_host_bridge.v" \
    "$SCRIPT_DIR/p03_run_monitor.v" \
    "$SCRIPT_DIR/tb/test_p03_memory_host_bridge.v"

xelab test_p03_memory_host_bridge \
    -s "$SNAPSHOT" \
    -debug typical

xsim "$SNAPSHOT" -runall

echo "P03 host bridge XSim gate completed successfully."
