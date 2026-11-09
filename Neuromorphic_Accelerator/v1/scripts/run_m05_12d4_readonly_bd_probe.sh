#!/usr/bin/env bash
# D4.1b: read-only original 2025.2 project inspection. NO hardware.
# This is deliberately NOT another HLS preflight or D3 output generation.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ $# -ne 2 ]]; then
  echo "Usage: bash scripts/run_m05_12d4_readonly_bd_probe.sh <ORIGINAL_D3_DIR> <ACCEPTED_D4_1_INVENTORY_DIR>" >&2
  exit 2
fi
for tool in git python3 vivado sha256sum mktemp realpath tee cmp; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing tool $tool" >&2; exit 2; }
done
vivado -version | grep -q '2025.2' || { echo "ERROR: genuine Vivado 2025.2 required" >&2; exit 2; }
ORIGINAL="$(realpath -e -- "$1")"
PREVIOUS="$(realpath -e -- "$2")"
if [[ "$(basename "$ORIGINAL")" != "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ" ]]; then
  echo "ERROR: exact immutable original D3 directory required" >&2
  exit 2
fi
if [[ "$(basename "$PREVIOUS")" != neuromorphic_v1_m05_12d4_warning_inventory_* ]]; then
  echo "ERROR: genuine prior D4 warning-inventory directory required" >&2
  exit 2
fi
EVIDENCE_ROOT="$HOME/Thesis_Evidence"
mkdir -p -- "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_12d4_readonly_bd_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M05 D4.1b original read-only Vivado property evidence: $OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
printf '%s\n' "$ORIGINAL" > "$OUT/00_original_d3_path.txt"
printf '%s\n' "$PREVIOUS" > "$OUT/00_previous_d4_path.txt"
sha256sum \
  "$ROOT/scripts/m05_12d4_readonly_bd_properties.tcl" \
  "$ROOT/scripts/m05_12d4_readonly_bd_audit.py" \
  "$ROOT/scripts/m05_12d4_generated_hierarchy_index.py" \
  "$ROOT/scripts/run_m05_12d4_readonly_bd_probe.sh" \
  "$ORIGINAL/03_vivado.log" \
  "$ORIGINAL/11_dma_hp0_memory_readback.txt" \
  "$ORIGINAL/12_independent_dma_hp0_memory_audit.log" \
  "$ORIGINAL/16_ip_output_sha256_manifest.txt" \
  "$ORIGINAL/13_file_backed_project/m05_d3_output_products.xpr" \
  "$ORIGINAL/13_file_backed_project/m05_d3_output_products.srcs/sources_1/bd/m05_12d3_real_signed32_hls_six_control_address_candidate/m05_12d3_real_signed32_hls_six_control_address_candidate.bd" \
  "$PREVIOUS/02_warning_inventory.json" > "$OUT/source_sha256.txt"
# Validate original evidence BEFORE any tool opens it. This report remains
# provisional until original-file invariance is rechecked AFTER Vivado too.
set +e
python3 "$ROOT/scripts/m05_12d4_generated_hierarchy_index.py" \
  --original-d3 "$ORIGINAL" --previous-d4 "$PREVIOUS/02_warning_inventory.json" \
  --output "$OUT/05_generated_hierarchy_hints.json" \
  2>&1 | tee "$OUT/01_original_hierarchy_index.log"
index_rc=$?
set -e
if [[ "$index_rc" -ne 3 ]]; then
  echo "ERROR: original D3 hash or previous D4 provenance failed (index=$index_rc)" >&2
  exit 2
fi
cd -- "$OUT"
set +e
vivado -mode batch -nojournal -nolog \
  -source "$ROOT/scripts/m05_12d4_readonly_bd_properties.tcl" \
  -tclargs "$ORIGINAL" "$OUT/03_bd_interface_properties.txt" "$OUT" \
  2>&1 | tee "$OUT/04_vivado_readonly.log"
vivado_rc=$?
set -e
# Rehash exact original XPR/BD and vendor logs and compare D3 original
# snapshots taken at startup, regardless of failure or success.
sha256sum \
  "$ROOT/scripts/m05_12d4_readonly_bd_properties.tcl" \
  "$ROOT/scripts/m05_12d4_readonly_bd_audit.py" \
  "$ROOT/scripts/m05_12d4_generated_hierarchy_index.py" \
  "$ROOT/scripts/run_m05_12d4_readonly_bd_probe.sh" \
  "$ORIGINAL/03_vivado.log" \
  "$ORIGINAL/11_dma_hp0_memory_readback.txt" \
  "$ORIGINAL/12_independent_dma_hp0_memory_audit.log" \
  "$ORIGINAL/16_ip_output_sha256_manifest.txt" \
  "$ORIGINAL/13_file_backed_project/m05_d3_output_products.xpr" \
  "$ORIGINAL/13_file_backed_project/m05_d3_output_products.srcs/sources_1/bd/m05_12d3_real_signed32_hls_six_control_address_candidate/m05_12d3_real_signed32_hls_six_control_address_candidate.bd" \
  "$PREVIOUS/02_warning_inventory.json" > "$OUT/07_source_sha256_after.txt"
if ! cmp -s "$OUT/source_sha256.txt" "$OUT/07_source_sha256_after.txt"; then
  echo "ERROR: unexpected original source/XPR/BD or evidence hash change; preserve all evidence" >&2
  exit 2
fi
if [[ "$vivado_rc" -ne 0 ]]; then
  echo "D4.1b read-only Vivado query BLOCKED/FAILED (Vivado=$vivado_rc); preserve evidence" >&2
  exit 2
fi
set +e
python3 "$ROOT/scripts/m05_12d4_readonly_bd_audit.py" \
  --original-d3 "$ORIGINAL" --previous-d4 "$PREVIOUS/02_warning_inventory.json" \
  --bd-report "$OUT/03_bd_interface_properties.txt" \
  --vivado-log "$OUT/04_vivado_readonly.log" \
  --output "$OUT/06_independent_bd_audit.json" \
  2>&1 | tee "$OUT/06_independent_bd_audit.log"
audit_rc=$?
set -e
if [[ "$audit_rc" -ne 3 ]]; then
  echo "D4.1b independent original property audit FAIL (rc=$audit_rc)" >&2
  exit 2
fi
echo "D4.1b ORIGINAL read-only endpoint property proof captured; generated AXI behavior remains BLOCKED."
exit 3
