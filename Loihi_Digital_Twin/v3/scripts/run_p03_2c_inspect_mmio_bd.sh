#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
XPR="$V3_DIR/vivado/build/p03_2_mmio_impl/project/loihi_twin_v3_p03_mmio_impl.xpr"
command -v vivado >/dev/null 2>&1 || { echo "ERROR: vivado not on PATH" >&2; exit 2; }
[[ -f "$XPR" ]] || { echo "ERROR: P03.2 Vivado project missing: $XPR" >&2; exit 2; }
cd "$V3_DIR"
vivado -mode batch -source vivado/p03_2c_inspect_mmio_bd.tcl -tclargs "$XPR"
