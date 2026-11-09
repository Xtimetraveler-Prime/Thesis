#!/usr/bin/env bash
# M05.12b: READ-ONLY Vivado IP-catalog probe. NO BOARD / NO BITSTREAM.
# Creates an IN-MEMORY scratch project only; never opens an existing design.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ "$#" -gt 1 || ( "$#" -eq 1 && "$1" != "--help" ) ]]; then
  echo "Usage: bash scripts/run_m05_12_ip_catalog.sh [--help]" >&2
  exit 2
fi
if [[ "$#" -eq 1 ]]; then
  echo "Offline Vivado 2025.2 K26 AXI DMA IP-catalog probe; NO BOARD."
  exit 0
fi
for tool in vivado git sha256sum mktemp tee; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: missing $tool (source Vivado 2025.2 settings64.sh)" >&2
    exit 2
  }
done
vivado -version | grep -q '2025.2' || {
  echo "ERROR: Vivado 2025.2 is required" >&2
  exit 2
}
ROOT_EVIDENCE="$HOME/Thesis_Evidence"
if [[ -v M05_EVIDENCE_ROOT ]]; then
  if [[ -n "$M05_EVIDENCE_ROOT" ]]; then
    ROOT_EVIDENCE="$M05_EVIDENCE_ROOT"
  fi
fi
mkdir -p "$ROOT_EVIDENCE"
OUT="$(mktemp -d "$ROOT_EVIDENCE/neuromorphic_v1_m05_12_ip_catalog_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M05.12 IP catalog-only evidence: $OUT"
  exit "$rc"
}
trap finish EXIT
git -C "$ROOT" rev-parse HEAD > "$OUT/commit.txt"
git -C "$ROOT" status --porcelain=v1 > "$OUT/working_tree_status.txt"
sha256sum "$ROOT/scripts/run_m05_12_ip_catalog.sh" \
          "$ROOT/scripts/m05_12_ip_catalog.tcl" > "$OUT/source_sha256.txt"
cd "$OUT"
# Tcl creates only an in-memory, unconnected catalog instance.
# No synthesis, placement, exported design, physical memory, or device access.
vivado -mode batch -nojournal -nolog \
  -source "$ROOT/scripts/m05_12_ip_catalog.tcl" \
  -tclargs "$OUT/capabilities.txt" \
  2>&1 | tee "$OUT/01_catalog.log"
grep -Fq "PASS: M05.12 K26 Vivado AXI DMA IP catalog-only inspection" \
  "$OUT/01_catalog.log" || {
  echo "ERROR: Vivado IP-catalog PASS marker missing" >&2
  exit 1
}
test -s "$OUT/capabilities.txt" || {
  echo "ERROR: missing catalog capability transcript" >&2
  exit 1
}
