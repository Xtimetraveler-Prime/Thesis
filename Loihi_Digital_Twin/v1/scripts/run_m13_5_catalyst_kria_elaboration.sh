#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATALYST="${1:-$ROOT/build/m13_1/catalyst-n1}"
OUT="${2:-$ROOT/build/m13_5/kria-elaboration}"

command -v python3 >/dev/null
command -v iverilog >/dev/null

major="$(iverilog -V 2>&1 | sed -n 's/^Icarus Verilog version \([0-9][0-9]*\).*/\1/p' | head -n1)"
if [[ -z "$major" || "$major" -lt 12 ]]; then
  echo "ERROR: M13.5 requires Icarus Verilog >=12; observed: $(iverilog -V 2>&1 | head -n1)" >&2
  exit 2
fi

cd "$ROOT"
PYTHONPATH=src python3 examples/validate_m13_5_hardware_manifest.py --catalyst-checkout "$CATALYST"

mkdir -p "$OUT"
rtl="$CATALYST/rtl"
kria="$CATALYST/fpga/kria"
files=(
  "$rtl/sram.v"
  "$rtl/spike_fifo.v"
  "$rtl/async_fifo.v"
  "$rtl/uart_tx.v"
  "$rtl/uart_rx.v"
  "$rtl/scalable_core_v2.v"
  "$rtl/neuromorphic_mesh.v"
  "$rtl/async_noc_mesh.v"
  "$rtl/async_router.v"
  "$rtl/sync_tree.v"
  "$rtl/chip_link.v"
  "$rtl/host_interface.v"
  "$rtl/axi_uart_bridge.v"
  "$rtl/neuromorphic_top.v"
  "$kria/kria_neuromorphic.v"
)

iverilog -g2012 -DSIMULATION -s kria_neuromorphic -o "$OUT/kria_neuromorphic.vvp" "${files[@]}" 2>&1 | tee "$OUT/iverilog.log"

git -C "$CATALYST" diff --quiet --
git -C "$CATALYST" diff --cached --quiet --

echo "M13.5 Catalyst Kria RTL elaboration PASS: commit=1806bb4b4114 part=xczu5ev-sfvc784-2-i top=kria_neuromorphic iverilog_major=$major files=${#files[@]}"
