#!/usr/bin/env bash
# M05.12d.3: NEW native grouped real AXIS cleanup, no physical FPGA.
# The previously accepted original D3 partial graph is NEVER rerun/overwritten.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$#" -ne 1 ]]; then
  echo "Usage: bash scripts/run_m05_12d3_native_axis_candidate.sh <accepted original D3 HLS contract evidence directory>" >&2
  exit 2
fi
for tool in vivado git python3 sha256sum mktemp realpath tee; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing $tool; source Vivado 2025.2" >&2; exit 2; }
done
vivado -version | grep -q 2025.2 || { echo "ERROR: real Vivado 2025.2 required" >&2; exit 2; }
CONTRACT="$(realpath -e -- "$1")"
EVIDENCE_ROOT="${M05_EVIDENCE_ROOT:-$HOME/Thesis_Evidence}"
mkdir -p -- "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_12d3_native_axis_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M05.12d.3 NEW genuine native AXIS PS/PL graph candidate evidence: $OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
printf '%s\n' "$CONTRACT" > "$OUT/source_hls_contract_evidence.txt"
sha256sum \
  "$ROOT/hls/m05_rolling/m05_rolling.cpp" \
  "$ROOT/scripts/m05_12d3_real_hls_contract.py" \
  "$ROOT/scripts/m05_12d3_hls_connected_preflight.py" \
  "$ROOT/scripts/m05_12d3_native_axis_candidate.tcl" \
  "$ROOT/scripts/m05_12d3_native_axis_candidate_audit.py" \
  "$ROOT/scripts/run_m05_12d3_native_axis_candidate.sh" \
  "$ROOT/rtl/m05_12/m05_12d_axis_shell_ref.v" \
  "$ROOT/rtl/m05_11/m05_11_stream_shell.v" \
  > "$OUT/source_sha256.txt"
python3 "$ROOT/scripts/m05_12d3_hls_connected_preflight.py" \
  --contract-evidence "$CONTRACT" \
  --source "$ROOT/hls/m05_rolling/m05_rolling.cpp" \
  --output "$OUT/01_hls_preflight.txt" 2>&1 | tee "$OUT/01_hls_preflight.log"
RTL_DIR="$(sed -n 's/^RTL_DIRECTORY|//p' "$OUT/01_hls_preflight.txt")"
if [[ -z "$RTL_DIR" || ! -f "$RTL_DIR/m05_rolling_replay.v" ]]; then
  echo "ERROR: authenticated Vitis-generated RTL directory not found" >&2; exit 1
fi
cd "$OUT"
vivado -mode batch -nojournal -nolog \
  -source "$ROOT/scripts/m05_12d3_native_axis_candidate.tcl" \
  -tclargs "$ROOT" "$OUT/02_native_axis_graph.txt" "$RTL_DIR" "$OUT/05_read_only_address_inventory.txt" \
  2>&1 | tee "$OUT/03_vivado.log"
grep -Fxq 'PASS: M05.12d.3 genuine HLS grouped native AXIS connected (CANDIDATE: NO ADDR/BD-VALIDATION/DDR)' "$OUT/03_vivado.log" || {
  echo "ERROR: required genuine Vivado original HLS integration marker missing" >&2
  exit 1
}
# Vivado's BD 41-1306 warning indicates interface pins were overridden.
# It was present in prior genuinely passing scalar integration evidence:
# this new interface-level graph MUST NOT generate that warning again.
if grep -Fq 'WARNING: [BD 41-1306]' "$OUT/03_vivado.log"; then
  echo "ERROR: native AXIS interface warning BD 41-1306 persists; do not accept" >&2
  exit 1
fi
python3 "$ROOT/scripts/m05_12d3_native_axis_candidate_audit.py" \
  --report "$OUT/02_native_axis_graph.txt" \
  --inventory "$OUT/05_read_only_address_inventory.txt" 2>&1 | tee "$OUT/04_independent_audit.log"
