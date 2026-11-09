#!/usr/bin/env bash
# ONE owner read-only M05 D4: D4.2 risk and D4.3 vendor-model discovery.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ $# -ne 3 ]]; then
  echo "Usage: bash scripts/run_m05_12d4_protocol_gate.sh <ORIGINAL_D3> <D4_1_INVENTORY> <D4_1B_READONLY_BD>" >&2
  exit 2
fi
for tool in git python3 vivado sha256sum mktemp realpath tee cmp; do
  command -v "$tool" >/dev/null || { echo "M05 D4 requires $tool" >&2; exit 2; }
done
vivado -version | grep -Fq '2025.2' || { echo "Expected Vivado 2025.2" >&2; exit 2; }
ORIGINAL="$(realpath -e -- "$1")"
D4_OLD="$(realpath -e -- "$2")"
D4_BD="$(realpath -e -- "$3")"
if [[ "$(basename "$ORIGINAL")" != 'neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ' ||
      "$(basename "$D4_OLD")" != neuromorphic_v1_m05_12d4_warning_inventory_* ||
      "$(basename "$D4_BD")" != neuromorphic_v1_m05_12d4_readonly_bd_* ||
      "$ORIGINAL" == "$D4_BD" || "$ORIGINAL" == "$D4_OLD" || "$D4_BD" == "$D4_OLD" ]]; then
  echo "M05 D4 requires three DISTINCT accepted evidence folders" >&2
  exit 2
fi
EVIDENCE_ROOT="$HOME/Thesis_Evidence"
mkdir -p -- "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_12d4_protocol_gate_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  printf 'Original read-only M05 D4 protocol evidence: %s\n' "$OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
printf '%s\n' "$ORIGINAL" > "$OUT/00_original_d3_path.txt"
printf '%s\n' "$D4_OLD" > "$OUT/00_prior_d4_inventory_path.txt"
printf '%s\n' "$D4_BD" > "$OUT/00_prior_d4_bd_path.txt"
if command -v xsim >/dev/null; then
  echo "XSIM_EXECUTABLE|PRESENT|NOT_INVOKED" > "$OUT/00_simulator_availability.txt"
else
  echo "XSIM_EXECUTABLE|UNAVAILABLE|NOT_INVOKED" > "$OUT/00_simulator_availability.txt"
fi
SOURCES=(
  "$ROOT/scripts/m05_12d4_protocol_risk.py"
  "$ROOT/scripts/m05_12d4_axi_byte_oracle.py"
  "$ROOT/scripts/m05_12d4_vendor_sim_feasibility.tcl"
  "$ROOT/scripts/m05_12d4_vendor_sim_readback_audit.py"
  "$ROOT/scripts/run_m05_12d4_protocol_gate.sh"
  "$ORIGINAL/03_vivado.log"
  "$ORIGINAL/07_full_bd_validation.txt"
  "$ORIGINAL/11_dma_hp0_memory_readback.txt"
  "$ORIGINAL/12_independent_dma_hp0_memory_audit.log"
  "$ORIGINAL/16_ip_output_sha256_manifest.txt"
  "$ORIGINAL/13_file_backed_project/m05_d3_output_products.xpr"
  "$ORIGINAL/13_file_backed_project/m05_d3_output_products.srcs/sources_1/bd/m05_12d3_real_signed32_hls_six_control_address_candidate/m05_12d3_real_signed32_hls_six_control_address_candidate.bd"
  "$D4_OLD/02_warning_inventory.json"
  "$D4_BD/03_bd_interface_properties.txt"
  "$D4_BD/04_vivado_readonly.log"
  "$D4_BD/05_generated_hierarchy_hints.json"
  "$D4_BD/06_independent_bd_audit.json"
  "$D4_BD/source_sha256.txt"
  "$D4_BD/07_source_sha256_after.txt"
)
sha256sum "${SOURCES[@]}" > "$OUT/source_sha256.txt"
# Exact previous evidence and original 382 generated IP SHAs checked BEFORE Vivado.
set +e
python3 "$ROOT/scripts/m05_12d4_protocol_risk.py" \
  --original-d3 "$ORIGINAL" --d4-inventory "$D4_OLD" --d4-bd "$D4_BD" \
  --output "$OUT/02_original_axi_risk.json" \
  2>&1 | tee "$OUT/01_original_risk_audit.log"
risk_rc=$?
set -e
if [[ "$risk_rc" -ne 3 ]]; then
  echo "D4.2 original provenance/risk FAILED; vendor query not attempted" >&2
  exit 2
fi
cd -- "$OUT"
set +e
vivado -mode batch -nojournal -nolog \
  -source "$ROOT/scripts/m05_12d4_vendor_sim_feasibility.tcl" \
  -tclargs "$ORIGINAL" "$OUT/04_vendor_sim_sources.txt" "$OUT" \
  2>&1 | tee "$OUT/03_vivado_sim_discovery.log"
vendor_rc=$?
set -e
sha256sum "${SOURCES[@]}" > "$OUT/08_source_sha256_after.txt"
if ! cmp -s "$OUT/source_sha256.txt" "$OUT/08_source_sha256_after.txt"; then
  echo "ERROR: original owner source/XPR/BD/independent evidence changed" >&2
  exit 2
fi
if [[ "$vendor_rc" -ne 0 ]]; then
  echo "D4.3 original Vivado source discovery failed (rc=$vendor_rc)" >&2
  exit 2
fi
set +e
python3 "$ROOT/scripts/m05_12d4_vendor_sim_readback_audit.py" \
  --original-d3 "$ORIGINAL" --d4-inventory "$D4_OLD" --d4-bd "$D4_BD" \
  --model-report "$OUT/04_vendor_sim_sources.txt" \
  --vivado-log "$OUT/03_vivado_sim_discovery.log" \
  --output "$OUT/06_model_discovery_audit.json" \
  2>&1 | tee "$OUT/05_model_discovery_audit.log"
vendor_audit_rc=$?
set -e
if [[ "$vendor_audit_rc" -ne 3 ]]; then
  echo "D4.3 genuine read-only model discovery independent audit FAILED" >&2
  exit 2
fi
# Reaudit ALL 382 original generated file hashes AFTER Vivado (not just XPR).
set +e
python3 "$ROOT/scripts/m05_12d4_protocol_risk.py" \
  --original-d3 "$ORIGINAL" --d4-inventory "$D4_OLD" --d4-bd "$D4_BD" \
  --output "$OUT/07_post_original_axi_risk.json" \
  2>&1 | tee "$OUT/07_post_original_risk_audit.log"
post_rc=$?
set -e
if [[ "$post_rc" -ne 3 ]] || ! cmp -s "$OUT/02_original_axi_risk.json" "$OUT/07_post_original_axi_risk.json"; then
  echo "ERROR: post-query 382-file original evidence changed or risk review failed" >&2
  exit 2
fi
echo "M05 D4.2 ORIGINAL WARNING REVIEW and D4.3 VENDOR MODEL DISCOVERY COMPLETE; AXI functional protocol still BLOCKED"
exit 3
