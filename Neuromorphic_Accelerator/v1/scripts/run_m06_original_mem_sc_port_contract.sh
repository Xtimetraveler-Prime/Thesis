#!/usr/bin/env bash
# M06: exact original read-only Vivado 2025.2 port capture for vendor BFM.
# No warning inventory, generate_target, simulation PASS, or board operations.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/run_m06_original_mem_sc_port_contract.sh <ACCEPTED_ORIGINAL_D3_DIR>" >&2
  exit 2
fi
for tool in git python3 vivado sha256sum mktemp realpath tee cmp; do
  command -v "$tool" >/dev/null || { echo "requires $tool" >&2; exit 2; }
done
vivado -version | grep -Fq '2025.2' || { echo "Vivado 2025.2 required" >&2; exit 2; }
ORIG="$(realpath -e -- "$1")"
[[ "$(basename "$ORIG")" == "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ" ]] || {
  echo "Only accepted original D3 XPR/BD source supported" >&2; exit 2;
}
[[ -f "$ORIG/result.txt" ]] && grep -Fxq 'exit_status=0' "$ORIG/result.txt" || {
  echo "Original D3 does not carry exit_status=0" >&2; exit 2;
}
XPR="$ORIG/13_file_backed_project/m05_d3_output_products.xpr"
DESIGN=m05_12d3_real_signed32_hls_six_control_address_candidate
BD="$ORIG/13_file_backed_project/m05_d3_output_products.srcs/sources_1/bd/$DESIGN/$DESIGN.bd"
MANIFEST="$ORIG/16_ip_output_sha256_manifest.txt"
for item in "$XPR" "$BD" "$MANIFEST"; do
  [[ -f "$item" ]] || { echo "Missing original file $item" >&2; exit 2; }
done
mkdir -p -- "$HOME/Thesis_Evidence"
OUT="$(mktemp -d "$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  local rc=$?
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  printf 'M06 original vendor read-only port evidence: %s\n' "$OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
printf '%s\n' "$ORIG" > "$OUT/00_original_d3_path.txt"
sha256sum "$ROOT/scripts/m06_original_mem_sc_ports.tcl" \
  "$ROOT/scripts/m06_original_mem_sc_contract_audit.py" \
  "$ROOT/scripts/run_m06_original_mem_sc_port_contract.sh" \
  "$XPR" "$BD" "$MANIFEST" > "$OUT/01_original_source_sha256.txt"
cd "$OUT"
set +e
vivado -mode batch -nojournal -nolog \
  -source "$ROOT/scripts/m06_original_mem_sc_ports.tcl" \
  -tclargs "$ORIG" "$OUT/02_original_mem_sc_ports.txt" \
  2>&1 | tee "$OUT/03_vivado_readonly.log"
vivado_rc=$?
set -e
sha256sum "$ROOT/scripts/m06_original_mem_sc_ports.tcl" \
  "$ROOT/scripts/m06_original_mem_sc_contract_audit.py" \
  "$ROOT/scripts/run_m06_original_mem_sc_port_contract.sh" \
  "$XPR" "$BD" "$MANIFEST" > "$OUT/04_original_source_after_sha256.txt"
if ! cmp -s "$OUT/01_original_source_sha256.txt" "$OUT/04_original_source_after_sha256.txt"; then
  echo "ERROR: original critical XPR/BD/manifest or tool source changed" >&2
  exit 2
fi
if [[ "$vivado_rc" -ne 0 ]]; then
  echo "ERROR: original vendor source/port query failed: Vivado rc=$vivado_rc" >&2
  exit 2
fi
python3 "$ROOT/scripts/m06_original_mem_sc_contract_audit.py" \
  --original "$ORIG" \
  --report "$OUT/02_original_mem_sc_ports.txt" \
  --vivado-log "$OUT/03_vivado_readonly.log" \
  --output "$OUT/05_sim_bfm_contract_summary.json" | tee "$OUT/05_audit.log"
echo "PASS: original vendor XSim-BFM ports CAPTURED; functional XSim NOT RUN; no warning inventory; NO BOARD"
