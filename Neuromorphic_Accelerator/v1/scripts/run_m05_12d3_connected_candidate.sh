#!/usr/bin/env bash
# M05.12d.3 original offline connected K26 PS + 4 DMA + shell graph.
# No physical FPGA/JTAG, no PS DDR boot or buffers, no HLS fake/mock.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ "$#" -gt 1 || ( "$#" -eq 1 && "$1" != "--help" ) ]]; then
  echo "Usage: bash scripts/run_m05_12d3_connected_candidate.sh [--help]" >&2; exit 2
fi
if [[ "$#" -eq 1 ]]; then
  echo "M05.12d.3 offline connected PS/DMA/shell graph; NO BOARD/DDR/HLS"; exit 0
fi
for tool in vivado git python3 sha256sum mktemp tee; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing $tool; source Vivado 2025.2" >&2; exit 2; }
done
vivado -version | grep -q '2025.2' || { echo "ERROR: Vivado 2025.2 required" >&2; exit 2; }
EVIDENCE_ROOT="$HOME/Thesis_Evidence"
if [[ -v M05_EVIDENCE_ROOT && -n "$M05_EVIDENCE_ROOT" ]]; then EVIDENCE_ROOT="$M05_EVIDENCE_ROOT"; fi
mkdir -p "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_12d3_connected_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M05.12d.3 original offline connected-candidate evidence: $OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
sha256sum "$ROOT/scripts/run_m05_12d3_connected_candidate.sh" \
  "$ROOT/scripts/m05_12d3_connected_candidate.tcl" \
  "$ROOT/scripts/m05_12d3_connected_candidate_audit.py" \
  "$ROOT/rtl/m05_12/m05_12d_axis_shell_ref.v" \
  "$ROOT/rtl/m05_11/m05_11_stream_shell.v" \
  > "$OUT/source_sha256.txt"
cd "$OUT"
vivado -mode batch -nojournal -nolog \
  -source "$ROOT/scripts/m05_12d3_connected_candidate.tcl" \
  -tclargs "$ROOT" "$OUT/01_connected_graph.txt" 2>&1 | tee "$OUT/02_vivado.log"
grep -Fxq "PASS: M05.12d.3 offline PS/PL four-DMA control/memory/stream/clock graph (PARTIAL: NO HLS/ADDR/DDR)" "$OUT/02_vivado.log" || {
  echo "ERROR: actual Vivado partial PS/PL graph PASS missing" >&2; exit 1
}
python3 "$ROOT/scripts/m05_12d3_connected_candidate_audit.py" \
  --report "$OUT/01_connected_graph.txt" 2>&1 | tee "$OUT/03_independent_audit.log"
