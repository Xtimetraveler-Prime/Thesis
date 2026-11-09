#!/usr/bin/env bash
# M05.12d.3: attest original Vitis 2025.2 generated signed32 RTL.
# No Vivado project, board, PS, DDR, JTAG, re-synthesis or fake HLS module.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$#" -ne 1 ]]; then
  echo "Usage: bash scripts/run_m05_12d3_real_hls_contract.sh <accepted ORIGINAL M05.11c XSim evidence directory>" >&2
  exit 2
fi
for tool in git python3 sha256sum mktemp realpath; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2; exit 2; }
done
XSIM="$(realpath -e -- "$1")"
EVIDENCE_ROOT="${M05_EVIDENCE_ROOT:-$HOME/Thesis_Evidence}"
mkdir -p -- "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_12d3_real_hls_contract_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M05.12d.3 original HLS contract evidence: $OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
printf '%s\n' "$XSIM" > "$OUT/source_xsim_evidence.txt"
sha256sum "$ROOT/hls/m05_rolling/m05_rolling.cpp" \
  "$ROOT/scripts/m05_axis_regmap.py" \
  "$ROOT/scripts/m05_12d3_real_hls_contract.py" \
  "$ROOT/scripts/run_m05_12d3_real_hls_contract.sh" > "$OUT/source_sha256.txt"
python3 "$ROOT/scripts/m05_12d3_real_hls_contract.py" \
  --xsim-evidence "$XSIM" \
  --source "$ROOT/hls/m05_rolling/m05_rolling.cpp" \
  --report "$OUT/01_original_hls_contract.txt" \
  > "$OUT/02_attestation.log" 2>&1 || {
    cat "$OUT/02_attestation.log" >&2
    exit 1
  }
cat "$OUT/02_attestation.log"
grep -Fxq 'PASS: M05.12d.3 ORIGINAL generated signed32 HLS RTL port/regmap/source attestation (NO Vivado BD or hardware)' "$OUT/02_attestation.log" || {
  echo "ERROR: ORIGINAL HLS attestation PASS missing" >&2; exit 1
}
