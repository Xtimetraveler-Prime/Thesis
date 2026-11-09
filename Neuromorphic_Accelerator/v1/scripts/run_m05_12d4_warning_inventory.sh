#!/usr/bin/env bash
# M05.12d.4 D4.1 ONLY: read original 2025.2 output products; never rerun D3.
# Deliberate exit 3 = inventory written but unresolved AXI gate is BLOCKED.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED="neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/run_m05_12d4_warning_inventory.sh <ORIGINAL_D3_IP_OUTPUT_EVIDENCE>" >&2
  exit 2
fi
for tool in git python3 sha256sum realpath mktemp tee; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing tool $tool" >&2; exit 2; }
done
ORIGINAL="$(realpath -e -- "$1")"
if [[ ! -d "$ORIGINAL" || "$(basename "$ORIGINAL")" != "$EXPECTED" ]]; then
  echo "ERROR: only the exact ORIGINAL owner D3 evidence is accepted" >&2
  exit 2
fi
EVIDENCE_ROOT="${M05_EVIDENCE_ROOT:-$HOME/Thesis_Evidence}"
mkdir -p -- "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_12d4_warning_inventory_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  printf 'D4.1 immutable independent inventory: %s (3=protocol unresolved, 2=invalid input)\n' "$OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
printf '%s\n' "$ORIGINAL" > "$OUT/01_source_original_d3_path.txt"
sha256sum \
  "$ROOT/scripts/m05_12d4_warning_inventory.py" \
  "$ROOT/scripts/m05_12d3_ip_output_audit.py" \
  "$ROOT/scripts/run_m05_12d4_warning_inventory.sh" \
  "$ORIGINAL/03_vivado.log" \
  "$ORIGINAL/15_ip_output_width_readback.txt" \
  "$ORIGINAL/16_ip_output_sha256_manifest.txt" \
  "$ORIGINAL/source_sha256.txt" \
  "$ORIGINAL/07_full_bd_validation.txt" \
  > "$OUT/source_sha256.txt"
# No writes in ORIGINAL. Never infer protocol acceptance from previous D3 exit0.
set +e
python3 "$ROOT/scripts/m05_12d4_warning_inventory.py" \
  --original-d3 "$ORIGINAL" \
  --output "$OUT/02_warning_inventory.json" \
  2>&1 | tee "$OUT/03_independent_inventory.log"
audit_rc="${PIPESTATUS[0]}"
set -e
if [[ "$audit_rc" -eq 3 ]]; then
  echo "D4.1 provenance verified; attribution/AXI semantics remain BLOCKED."
elif [[ "$audit_rc" -ne 0 ]]; then
  echo "D4.1 warning inventory validation FAILED; preserve original and new evidence." >&2
fi
exit "$audit_rc"
