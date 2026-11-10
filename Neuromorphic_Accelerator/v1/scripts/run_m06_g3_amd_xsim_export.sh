#!/usr/bin/env bash
# M06 G3: official AMD XSim simulation source export, NOT simulation.
# Reuse saved real AMD 2025.2 dual-DWC scratch project READ ONLY.
# No original D3 edits; no physical DDR/JTAG/board/bitstream.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if (( $# != 1 )); then
  echo "Usage: bash scripts/run_m06_g3_amd_xsim_export.sh <successful original DWC evidence folder>" >&2
  exit 2
fi
DW="$(realpath -e -- "$1")"
if [[ "$(basename -- "$DW")" != m06_g3_real_amd_dwc_* ]]; then
  echo "ERROR: expected original successful M06 AMD DWC evidence directory" >&2
  exit 2
fi
for app in vivado git python3 sha256sum cmp find grep tee realpath; do
  command -v "$app" >/dev/null || {
    echo "ERROR: missing $app; source original Vivado 2025.2 settings64.sh" >&2
    exit 2
  }
done
VERSION="$(vivado -version 2>&1)" || exit 2
[[ "$VERSION" == *2025.2* ]] || {
  echo "ERROR: original AMD Vivado 2025.2 required" >&2
  exit 2
}
cd "$ROOT"
python3 scripts/m06_g3_amd_dwc_evidence_audit.py \
  --evidence "$DW" \
  --output "$HOME/Thesis_Evidence/m06_g3_reaudit_for_export_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"
mkdir -p "$HOME/Thesis_Evidence"
OUT="$(mktemp -d "$HOME/Thesis_Evidence/m06_g3_amd_sim_export_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  cd "$ROOT" || rc=3
  sha256sum scripts/m06_g3_export_real_dwc_xsim.tcl \
    scripts/run_m06_g3_amd_xsim_export.sh > "$OUT/source_after_sha256.txt" || rc=3
  cmp -s "$OUT/source_before_sha256.txt" "$OUT/source_after_sha256.txt" || {
    echo "FATAL: G3 XSim export script mutated during owner run" >&2
    rc=3
  }
  sha256sum -c "$DW/04_real_amd_dwc_xci_sha256.txt" \
    > "$OUT/05_owner_xci_after_check.txt" 2>&1 || {
    echo "FATAL: originally accepted AMD XCI content changed" >&2
    rc=3
  }
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M06 G3 original AMD DWC XSim EXPORT evidence: $OUT"
  echo "M06 G3 AMD XSim source export exit: $rc"
  exit "$rc"
}
trap finish EXIT
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/worktree_status.txt"
printf '%s\n' "$VERSION" > "$OUT/vivado_version.txt"
printf '%s\n' "$DW" > "$OUT/original_width_ip_folder.txt"
sha256sum scripts/m06_g3_export_real_dwc_xsim.tcl \
  scripts/run_m06_g3_amd_xsim_export.sh > "$OUT/source_before_sha256.txt"
sha256sum -c "$DW/04_real_amd_dwc_xci_sha256.txt" \
  > "$OUT/00_owner_xci_before_check.txt" 2>&1
vivado -mode batch -notrace \
  -source "$ROOT/scripts/m06_g3_export_real_dwc_xsim.tcl" \
  -tclargs "$DW" "$OUT" 2>&1 | tee "$OUT/01_vivado_export.log"
grep -Fq "M06_G3_REAL_AMD_DWC_XSIM_SOURCES_EXPORTED_NOT_CONNECTED_NOT_SIMULATED" \
  "$OUT/01_vivado_export.log" || {
    echo "ERROR: real Vivado official XSim export marker absent" >&2
    exit 1
  }
find "$OUT/exported_xsim_scripts" -type f -name '*.sh' \
  | sort > "$OUT/03_official_amd_xsim_script_paths.txt"
if [[ $(wc -l < "$OUT/03_official_amd_xsim_script_paths.txt") -lt 2 ]]; then
  echo "ERROR: fewer than two real AMD converter standalone xsim scripts" >&2
  exit 1
fi
grep -Fq 'm06_g3_read_dwc' "$OUT/03_official_amd_xsim_script_paths.txt"
grep -Fq 'm06_g3_write_dwc' "$OUT/03_official_amd_xsim_script_paths.txt"
python3 "$ROOT/scripts/m06_g3_capture_dwc_ports.py" \
  --owner-dwc "$DW" --output "$OUT/04_real_amd_dwc_port_headers.json"
echo "M06 G3 REAL AMD simulation scripts EXPORTED ONLY; no vendor XSim/connected HLS/board run"
