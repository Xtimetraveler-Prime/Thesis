#!/usr/bin/env bash
# G3.3 READ ONLY: audit previously accepted HLS/G2/G3.2 artifacts; NO BOARD.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if (( $# != 7 )); then
  echo 'Usage: bash scripts/run_m06_g3_3_hls_inventory.sh <HLS cosim> <original A-E> <original D3> <original header JSON> <DWC owner> <G3.2 PASS ZIP> <v1 repository root>' >&2
  exit 2
fi
for tool in python3 git sha256sum realpath cmp tee; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2; exit 2; }
done
HLS="$(realpath -e -- "$1")"
AE="$(realpath -e -- "$2")"
D3="$(realpath -e -- "$3")"
HEADERS="$(realpath -e -- "$4")"
DWC="$(realpath -e -- "$5")"
G32="$(realpath -e -- "$6")"
REPO="$(realpath -e -- "$7")"
[[ "$REPO" == "$ROOT" ]] || { echo 'ERROR: wrong v1 repository root' >&2; exit 2; }
[[ "$(basename "$HLS")" == m06_paged_rolling_hls_cosim_* &&
   "$(basename "$AE")" == m06_original_vendor_mem_sc_xsim_* &&
   "$(basename "$D3")" == neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ &&
   "$(basename "$DWC")" == m06_g3_real_amd_dwc_* &&
   "$(basename "$HEADERS")" == 08_mem_sc_wrapper_headers_nonansi_fixed.json &&
   "$(basename "$G32")" == M06_G3_2_CORRECTED_XSIM_REVIEW_*.zip ]] || {
  echo 'ERROR: original accepted G1/G2/G3.2 evidence paths required' >&2; exit 2;
}
mkdir -p "$HOME/Thesis_Evidence"
OUT="$(mktemp -d "$HOME/Thesis_Evidence/m06_g3_3_hls_source_inventory_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc=$?
  trap - EXIT
  cd "$ROOT" || rc=3
  sha256sum scripts/m06_g3_2_connected_evidence_audit.py \
    scripts/m06_g3_3_hls_inventory.py \
    scripts/run_m06_g3_3_hls_inventory.sh \
    scripts/m06_g3_original_link_inputs.py \
    scripts/m06_g3_exact_original_pin_matrix.py \
    scripts/m06_g3_capture_dwc_ports.py \
    hls/m06_paged_rolling/m06_paged_rolling.cpp \
    hls/m06_paged_rolling/m06_paged_rolling.hpp \
    > "$OUT/source_after_sha256.txt" || rc=3
  cmp -s "$OUT/source_before_sha256.txt" "$OUT/source_after_sha256.txt" || {
    echo 'FATAL: G3.3 source modified during read-only inventory' >&2
    rc=3
  }
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M06_G3_3_HLS_INVENTORY_EVIDENCE $OUT exit=$rc"
  exit "$rc"
}
trap finish EXIT
cd "$ROOT"
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/worktree_status.txt"
printf '%s\n' "$HLS" > "$OUT/original_hls_folder.txt"
printf '%s\n' "$AE" > "$OUT/original_vendor_ae_folder.txt"
printf '%s\n' "$D3" > "$OUT/original_d3_folder.txt"
printf '%s\n' "$DWC" > "$OUT/original_dwc_folder.txt"
printf '%s\n' "$G32" > "$OUT/original_g3_2_zip_path.txt"
sha256sum "$G32" > "$OUT/original_g3_2_zip_sha256.txt"
sha256sum scripts/m06_g3_2_connected_evidence_audit.py \
  scripts/m06_g3_3_hls_inventory.py \
  scripts/run_m06_g3_3_hls_inventory.sh \
  scripts/m06_g3_original_link_inputs.py \
  scripts/m06_g3_exact_original_pin_matrix.py \
  scripts/m06_g3_capture_dwc_ports.py \
  hls/m06_paged_rolling/m06_paged_rolling.cpp \
  hls/m06_paged_rolling/m06_paged_rolling.hpp \
  > "$OUT/source_before_sha256.txt"
python3 scripts/m06_g3_2_connected_evidence_audit.py \
  --zip "$G32" --output "$OUT/00_g3_2_reaccepted.json" \
  2>&1 | tee "$OUT/02_inventory_console.log"
python3 scripts/m06_g3_3_hls_inventory.py \
  --hls-cosim "$HLS" --vendor-a-e "$AE" --repo "$ROOT" \
  --d3 "$D3" --headers "$HEADERS" --dwc "$DWC" \
  --g3-2-zip "$G32" --output "$OUT/01_g3_3_hls_interface_inventory.json" \
  2>&1 | tee -a "$OUT/02_inventory_console.log"
grep -Fq 'M06_G3_3_REAL_HLS_RTL_INVENTORY_READY NOT_CONNECTED' "$OUT/02_inventory_console.log"
echo 'M06 G3.3 source inventory PASS; actual HLS-to-AMD-XSim NOT CONNECTED'
