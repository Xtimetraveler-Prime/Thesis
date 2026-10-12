#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$V3_DIR/vivado/build/p03_ps_control_regs_sim"

for tool in iverilog vvp; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: $tool is required for P03.2a MMIO regression" >&2
        exit 2
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

iverilog -g2012 -Wall     -o "$BUILD_DIR/test_p03_ps_control_regs.vvp"     "$V3_DIR/rtl/p03_ps_control_regs.v"     "$V3_DIR/rtl/tb/test_p03_ps_control_regs.v"

vvp "$BUILD_DIR/test_p03_ps_control_regs.vvp"     | tee "$BUILD_DIR/test.log"

grep -q '^PASS: p03_ps_control_regs$' "$BUILD_DIR/test.log"
echo "PASS: P03.2a AXI-Lite control-register simulation completed successfully."
