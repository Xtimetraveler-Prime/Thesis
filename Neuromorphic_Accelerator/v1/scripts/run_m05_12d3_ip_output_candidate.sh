#!/usr/bin/env bash
# M05.12d.3: separate offline 4-DMA HP0 DDR_LOW mapping and OCM exclusion.
# No board/PS/DDR/JTAG, no bitstream; preserve every prior owner proof.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$#" -ne 2 ]]; then
  echo "Usage: bash scripts/run_m05_12d3_ip_output_candidate.sh <ACCEPTED_ORIGINAL_HLS_CONTRACT_DIR> <EXPLICIT_SIX_BANK_OFFLINE_MAP_FILE>" >&2
  exit 2
fi
for tool in vivado git python3 sha256sum mktemp realpath tee; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing $tool; source genuine Vivado 2025.2" >&2; exit 2; }
done
vivado -version | grep -q '2025.2' || { echo "ERROR: owner Vivado 2025.2 required" >&2; exit 2; }
CONTRACT="$(realpath -e -- "$1")"
PLAN="$(realpath -e -- "$2")"
EVIDENCE_ROOT="${M05_EVIDENCE_ROOT:-$HOME/Thesis_Evidence}"
mkdir -p -- "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_12d3_ip_output_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M05.12d.3 owner file-backed Vivado BD/IP generation offline trial: $OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
printf '%s\n' "$CONTRACT" > "$OUT/source_hls_contract_evidence.txt"
printf '%s\n' "$PLAN" > "$OUT/source_explicit_control_plan.txt"
sha256sum \
  "$PLAN" \
  "$ROOT/hls/m05_rolling/m05_rolling.cpp" \
  "$ROOT/scripts/m05_12d3_real_hls_contract.py" \
  "$ROOT/scripts/m05_12d3_hls_connected_preflight.py" \
  "$ROOT/scripts/m05_12d3_address_validate_candidate.tcl" \
  "$ROOT/scripts/m05_12d3_dma_memory_trial.py" \
  "$ROOT/scripts/m05_12d3_dma_memory_audit.py" \
  "$ROOT/scripts/m05_12d3_ip_output_trial.py" \
  "$ROOT/scripts/m05_12d3_ip_output_audit.py" \
  "$ROOT/scripts/run_m05_12d3_ip_output_candidate.sh" \
  "$ROOT/scripts/run_m05_12d3_dma_memory_candidate.sh" \
  "$ROOT/scripts/m05_12d3_hls_clock_annotation.py" \
  "$ROOT/scripts/m05_12d3_address_validate_audit.py" \
  "$ROOT/scripts/run_m05_12d3_address_validate_candidate.sh" \
  "$ROOT/scripts/m05_12d3_native_axis_candidate_audit.py" \
  "$ROOT/rtl/m05_12/m05_12d_axis_shell_ref.v" \
  "$ROOT/rtl/m05_11/m05_11_stream_shell.v" \
  > "$OUT/source_sha256.txt"
python3 "$ROOT/scripts/m05_12d3_address_validate_audit.py" \
  --plan "$PLAN" --plan-only 2>&1 | tee "$OUT/00_offline_plan_admission.log"
python3 "$ROOT/scripts/m05_12d3_hls_connected_preflight.py" \
  --contract-evidence "$CONTRACT" \
  --source "$ROOT/hls/m05_rolling/m05_rolling.cpp" \
  --output "$OUT/01_hls_preflight.txt" 2>&1 | tee "$OUT/01_hls_preflight.log"
RTL_DIR="$(sed -n 's/^RTL_DIRECTORY|//p' "$OUT/01_hls_preflight.txt")"
if [[ -z "$RTL_DIR" || ! -f "$RTL_DIR/m05_rolling_replay.v" ]]; then
  echo "ERROR: actual authenticated original Vitis HLS RTL missing" >&2
  exit 1
fi
# Create only a DERIVED annotation-only clock-interface top inside fresh
# owner evidence. The original source remains SHA-authenticated and untouched.
# This is not an HLS resynthesis, neural RTL patch, or physical clock.
HLS_ANNOTATED_TOP="$OUT/09_hls_clock_annotated_top.v"
python3 "$ROOT/scripts/m05_12d3_hls_clock_annotation.py" \
  --original-top "$RTL_DIR/m05_rolling_replay.v" \
  --derived-top "$HLS_ANNOTATED_TOP" \
  --manifest "$OUT/09_hls_clock_annotation_manifest.txt" \
  --frequency-hz 96968727 2>&1 | tee "$OUT/09_hls_clock_annotation_stage.log"
sha256sum "$HLS_ANNOTATED_TOP" >> "$OUT/source_sha256.txt"
IP_TCL="$OUT/14_ip_output_trial_generated.tcl"
python3 "$ROOT/scripts/m05_12d3_ip_output_trial.py" \
  --base-tcl "$ROOT/scripts/m05_12d3_address_validate_candidate.tcl" \
  --derived-tcl "$IP_TCL" \
  --manifest "$OUT/14_ip_output_trial_source_manifest.txt" \
  2>&1 | tee "$OUT/14_ip_output_trial_stage.log"
sha256sum "$IP_TCL" >> "$OUT/source_sha256.txt"
cd "$OUT"
# Validation may legitimately fail even after all six address ranges passed.
# Always preserve genuine stdout, partial graph/inventory and validation state
# and run independent audits where evidence files exist.
set +e
vivado -mode batch -nojournal -nolog \
  -source "$IP_TCL" \
  -tclargs "$ROOT" "$OUT/02_native_axis_graph.txt" "$RTL_DIR" "$PLAN" \
  "$OUT/06_real_ps_control_address_readback.txt" "$OUT/07_full_bd_validation.txt" \
  "$OUT/05_read_only_address_inventory.txt" "$HLS_ANNOTATED_TOP" \
  "$OUT/11_dma_hp0_memory_readback.txt" \
  "$OUT/15_ip_output_width_readback.txt" "$OUT/13_file_backed_project" \
  2>&1 | tee "$OUT/03_vivado.log"
vivado_rc="${PIPESTATUS[0]}"
set -e
graph_rc=1
if [[ -s "$OUT/02_native_axis_graph.txt" && -s "$OUT/05_read_only_address_inventory.txt" ]]; then
  set +e
  python3 "$ROOT/scripts/m05_12d3_native_axis_candidate_audit.py" \
    --report "$OUT/02_native_axis_graph.txt" \
    --inventory "$OUT/05_read_only_address_inventory.txt" \
    2>&1 | tee "$OUT/04_independent_original_graph_audit.log"
  graph_rc="${PIPESTATUS[0]}"
  set -e
fi
addr_rc=1
if [[ -s "$OUT/06_real_ps_control_address_readback.txt" && -s "$OUT/07_full_bd_validation.txt" ]]; then
  set +e
  python3 "$ROOT/scripts/m05_12d3_address_validate_audit.py" \
    --plan "$PLAN" \
    --mapped "$OUT/06_real_ps_control_address_readback.txt" \
    --validation "$OUT/07_full_bd_validation.txt" \
    --hls-original-contract "$CONTRACT/01_original_hls_contract.txt" \
    2>&1 | tee "$OUT/08_independent_address_validation_audit.log"
  addr_rc="${PIPESTATUS[0]}"
  set -e
fi
dma_rc=1
if [[ -s "$OUT/11_dma_hp0_memory_readback.txt" && -s "$OUT/07_full_bd_validation.txt" ]]; then
  set +e
  python3 "$ROOT/scripts/m05_12d3_dma_memory_audit.py" \
    --memory-report "$OUT/11_dma_hp0_memory_readback.txt" \
    --validation "$OUT/07_full_bd_validation.txt" \
    --vivado-log "$OUT/03_vivado.log" \
    2>&1 | tee "$OUT/12_independent_dma_hp0_memory_audit.log"
  dma_rc="${PIPESTATUS[0]}"
  set -e
fi
ip_rc=1
if [[ -s "$OUT/15_ip_output_width_readback.txt" ]]; then
  set +e
  python3 "$ROOT/scripts/m05_12d3_ip_output_audit.py" \
    --evidence-dir "$OUT" --width-report "$OUT/15_ip_output_width_readback.txt" \
    --vivado-log "$OUT/03_vivado.log" \
    --generated-manifest "$OUT/16_ip_output_sha256_manifest.txt" \
    2>&1 | tee "$OUT/17_independent_ip_output_audit.log"
  ip_rc="${PIPESTATUS[0]}"
  set -e
fi
if grep -Fq 'WARNING: [BD 41-1306]' "$OUT/03_vivado.log"; then
  echo "ERROR: owner-native AXI4-Stream pin override warning returned" >&2
  exit 1
fi
if [[ "$vivado_rc" -ne 0 || "$graph_rc" -ne 0 || "$addr_rc" -ne 0 || "$dma_rc" -ne 0 || "$ip_rc" -ne 0 ]]; then
  echo "INCOMPLETE: M05.12d.3 generated output trial Vivado=$vivado_rc graph=$graph_rc controls=$addr_rc dma=$dma_rc generated=$ip_rc" >&2
  exit 1
fi
grep -Fxq 'PASS: M05.12d.3 file-backed Vivado BD/IP outputs generated and original DMA/full-BD passed (NO SYNTHESIS/BITSTREAM/BOARD)' "$OUT/03_vivado.log" || {
  echo "ERROR: genuine full BD PASS marker missing" >&2
  exit 1
}
echo "PASS: M05.12d.3 file-backed Vivado generated BD output products, 256/128 endpoint widths, all four independent audits (NO SYNTHESIS/BOARD/DDR)"
