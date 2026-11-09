#!/usr/bin/env bash
# M05.12d.1 offline PL-only AXIS connected graph. NO BOARD/PS/DDR/SYNTH.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ "$#" -gt 1 || ( "$#" -eq 1 && "$1" != "--help" ) ]]; then
  echo "Usage: bash scripts/run_m05_12d1_axis_graph.sh [--help]" >&2; exit 2
fi
if [[ "$#" -eq 1 ]]; then
  echo "M05.12d.1 genuine Vivado offline AXIS connectivity; NO BOARD/PS/DDR"; exit 0
fi
for tool in vivado git python3 sha256sum mktemp tee; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing $tool; source Vivado 2025.2" >&2; exit 2; }
done
vivado -version | grep -q '2025.2' || { echo "ERROR: Vivado 2025.2 required" >&2; exit 2; }
EVIDENCE_ROOT="$HOME/Thesis_Evidence"
if [[ -v M05_EVIDENCE_ROOT ]]; then
  if [[ -n "$M05_EVIDENCE_ROOT" ]]; then EVIDENCE_ROOT="$M05_EVIDENCE_ROOT"; fi
fi
mkdir -p "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_12d1_axis_graph_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  local rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M05.12d.1 offline Vivado stream graph evidence: $OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
sha256sum "$ROOT/scripts/run_m05_12d1_axis_graph.sh" "$ROOT/scripts/m05_12d1_axis_graph.tcl" "$ROOT/scripts/m05_12d1_axis_graph_audit.py" "$ROOT/rtl/m05_12/m05_12d_axis_shell_ref.v" "$ROOT/rtl/m05_11/m05_11_stream_shell.v" > "$OUT/source_sha256.txt"
cd "$OUT"
vivado -mode batch -nojournal -nolog \
  -source "$ROOT/scripts/m05_12d1_axis_graph.tcl" \
  -tclargs "$ROOT" "$OUT/01_axis_links.txt" \
  2>&1 | tee "$OUT/02_vivado.log"
grep -Fxq "PASS: M05.12d.1 genuine offline DMA-to-shell four AXIS nets (PARTIAL PL BD, NO PS/DDR)" "$OUT/02_vivado.log" || {
  echo "ERROR: Vivado AXIS connectivity PASS marker absent" >&2; exit 1
}
python3 "$ROOT/scripts/m05_12d1_axis_graph_audit.py" --report "$OUT/01_axis_links.txt" \
  2>&1 | tee "$OUT/03_independent_audit.log"
