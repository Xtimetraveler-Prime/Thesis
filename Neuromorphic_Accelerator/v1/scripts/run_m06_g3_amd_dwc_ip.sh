#!/usr/bin/env bash
# M06 G3: generate ONLY genuine AMD Vivado 2025.2 AXI Data Width Converter
# scratch IP output products (32-bit SI, 256-bit MI, one READ/one WRITE).
# NO original D3/IP modification, board, JTAG, bitstream or PS DDR.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if (($# != 0)); then
  echo "Usage: bash scripts/run_m06_g3_amd_dwc_ip.sh (no arguments)" >&2
  exit 2
fi
for app in vivado git realpath sha256sum find tee python3 grep; do
  command -v "$app" >/dev/null 2>&1 || {
    echo "ERROR: missing $app; source Vivado 2025.2 settings64.sh" >&2
    exit 2
  }
done
VERSION="$(vivado -version 2>&1)" || {
  echo "ERROR: Vivado -version did not execute" >&2
  exit 2
}
if [[ "$VERSION" != *2025.2* ]]; then
  echo "ERROR: only original Vivado 2025.2 is accepted: $VERSION" >&2
  exit 2
fi
mkdir -p "$HOME/Thesis_Evidence"
OUT="$(mktemp -d "$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  local rc="$?"
  trap - EXIT
  cd "$ROOT" || rc=3
  sha256sum scripts/m06_g3_generate_amd_dwc.tcl \
    scripts/m06_g3_xci_path.tcl \
    scripts/run_m06_g3_amd_dwc_ip.sh > "$OUT/source_after_sha256.txt" || rc=3
  cmp -s "$OUT/source_before_sha256.txt" "$OUT/source_after_sha256.txt" || {
    echo "FATAL: G3 generator source mutated during original Vivado run" >&2
    rc=3
  }
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  find "$OUT/new_scratch_project" -type f -name '*.xci' -print 2>/dev/null \
    | sort > "$OUT/03_real_amd_dwc_xci_paths.txt" || true
  if [[ -s "$OUT/03_real_amd_dwc_xci_paths.txt" ]]; then
    while IFS= read -r f; do sha256sum "$f"; done \
      < "$OUT/03_real_amd_dwc_xci_paths.txt" \
      > "$OUT/04_real_amd_dwc_xci_sha256.txt" || rc=3
  fi
  printf 'genuine_vendor_converter_status=%s\n' \
    "$([[ "$rc" == 0 ]] && echo GENERATED_ONLY || echo FAILED)" \
    > "$OUT/scope.txt"
  echo "M06 G3 original AMD 32:256 width-IP preparation evidence: $OUT"
  echo "M06 G3 width-IP preparation exit: $rc"
  exit "$rc"
}
trap finish EXIT

cd "$ROOT"
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/worktree_status.txt"
printf '%s\n' "$VERSION" > "$OUT/vivado_version.txt"
sha256sum scripts/m06_g3_generate_amd_dwc.tcl \
  scripts/m06_g3_xci_path.tcl \
  scripts/run_m06_g3_amd_dwc_ip.sh > "$OUT/source_before_sha256.txt"

# All generated products are outside the repository in a NEW unique folder.
# Do not source or touch the immutable D3 original AMD SmartConnect project.
vivado -mode batch -notrace \
  -source "$ROOT/scripts/m06_g3_generate_amd_dwc.tcl" \
  -tclargs "$OUT" 2>&1 | tee "$OUT/01_vivado_amd_dwc.log"

grep -Fq "M06_G3_REAL_AMD_DWC_IP_GENERATED_NOT_CONNECTED" \
  "$OUT/01_vivado_amd_dwc.log" || {
  echo "ERROR: genuine Vivado IP output marker absent" >&2
  exit 1
}
if [[ ! -s "$OUT/02_amd_dwc_configuration.tsv" ]]; then
  echo "ERROR: original AMD IP parameter readback missing" >&2
  exit 1
fi
python3 "$ROOT/scripts/m06_g3_amd_dwc_evidence_audit.py" \
  --evidence "$OUT" --pre-finalize \
  --output "$OUT/05_unverified_pre_finalize_review.json"
echo "PASS: original AMD 2025.2 DWC 32:256 output products GENERATED ONLY"
echo "      HLS/SmartConnect integration, 64:32 address guard and vendor XSim NOT RUN"
