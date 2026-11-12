#!/usr/bin/env bash
# M08.2b guarded original-bitstream programming. PC VS Code terminal ONLY.
# Does not modify original M08/Loihi evidence, board firmware, fan or PS MMIO.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(cd -- "$HERE/.." && pwd)"
EXPECTED="170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf"
if [[ "$#" -ne 1 || "$1" != /* || ! -f "$1" || -L "$1" ]]; then
  echo "ERROR: pass absolute ORIGINAL M08 .bit pathname (regular non-symlink file)" >&2
  exit 2
fi
BIT="$1"
if [[ "$(basename -- "$BIT")" != "05_m08_safe_page.bit" ||
      "$(stat -c %s -- "$BIT")" != "7797831" ]]; then
  echo "ERROR: wrong M08 original bitstream basename/size" >&2
  exit 2
fi
if [[ ! -v M08_ALLOW_PROGRAM || ! -v M08_APPROVED_MODE ]]; then
  echo "ERROR: explicit operator approvals missing; no hardware action" >&2
  exit 2
fi
if [[ "$M08_ALLOW_PROGRAM" != YES || "$M08_APPROVED_MODE" != ISOLATED_JTAG ]]; then
  echo "ERROR: M08_ALLOW_PROGRAM=YES and M08_APPROVED_MODE=ISOLATED_JTAG required" >&2
  exit 2
fi
if [[ ! -v M08_BOARD_REVIEW_FILE ]]; then
  echo "ERROR: M08_BOARD_REVIEW_FILE required with real boot/fan/PL evidence" >&2
  exit 2
fi
REVIEW="$M08_BOARD_REVIEW_FILE"
if [[ ! -f "$REVIEW" || -L "$REVIEW" || ! -s "$REVIEW" ]]; then
  echo "ERROR: owner reviewed physical-state file missing/empty/symlink" >&2
  exit 2
fi
# Attestation is an operator decision; it is not automated proof of cooling.
for required in \
  "mode=ISOLATED_JTAG" \
  "linux_pl_ownership=NONE_CONFIRMED" \
  "fan_cooling=INDEPENDENT_VERIFIED" \
  "active_pl_replacement=APPROVED" \
  "operator_authorization=YES"; do
  if [[ "$(grep -Fxc -- "$required" "$REVIEW" || true)" != 1 ]]; then
    echo "ERROR: missing/ambiguous signed-off review item: $required" >&2
    exit 2
  fi
done
command -v vivado >/dev/null || {
  echo "ERROR: source genuine Vivado 2025.2 settings64.sh in VS Code terminal" >&2
  exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *2025.2* ]]; then
  echo "ERROR: Vivado version mismatch; nothing programmed" >&2
  exit 2
fi
ACTUAL="$(sha256sum -- "$BIT" | cut -d ' ' -f1)"
if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "ERROR: original .bit SHA256 mismatch; no programming" >&2
  exit 2
fi
BASE="$HOME/Thesis_Evidence/M08"
if [[ -v M08_EVIDENCE_BASE ]]; then BASE="$M08_EVIDENCE_BASE"; fi
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
  echo "ERROR: owner must provide an existing trusted evidence parent" >&2
  exit 2
fi
DIR="$(mktemp -d "$BASE/m08_2b_physical_program_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
printf 'M08_PROGRAM_EVIDENCE_DIR=%s\n' "$DIR"
cp -- "$REVIEW" "$DIR/01_board_review.txt"
# Program a newly copied, locally SHA-verified snapshot, NOT a mutable source
# pathname.  Keep the owner ORIGINAL bitstream strictly untouched.
cp -- "$BIT" "$DIR/05_m08_safe_page.bit"
FROZEN_SHA="$(sha256sum -- "$DIR/05_m08_safe_page.bit" | cut -d ' ' -f1)"
if [[ "$FROZEN_SHA" != "$EXPECTED" ]] ||
   ! cmp -s -- "$REVIEW" "$DIR/01_board_review.txt"; then
  echo "M08_PROGRAM_NOT_ACCEPTED_COPY_CHANGED preserve=$DIR" >&2
  exit 2
fi
# Tcl must review the same immutable-evidence snapshot as the operator saw.
export M08_BOARD_REVIEW_FILE="$DIR/01_board_review.txt"
printf 'original_bitstream=%s\nsha256=%s\nbytes=7797831\n' "$BIT" "$ACTUAL" > "$DIR/00_input_identity.txt"
printf 'source_head=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unavailable)" >> "$DIR/00_input_identity.txt"
set +e
vivado -mode batch -nojournal -nolog \
  -source "$HERE/m08_kv260_program_oneshot.tcl" \
  -tclargs "$DIR/05_m08_safe_page.bit" "$DIR/03_program_result.txt" \
  > "$DIR/02_vivado_program.log" 2>&1
RC=$?
set -e
printf 'vivado_exit_status=%s\n' "$RC" > "$DIR/04_run_status.txt"
AFTER="$(sha256sum -- "$BIT" | cut -d ' ' -f1)"
printf 'bitstream_sha256_after=%s\n' "$AFTER" >> "$DIR/04_run_status.txt"
(
  cd "$DIR"
  sha256sum -- 00_input_identity.txt 01_board_review.txt \
     02_vivado_program.log 04_run_status.txt > 05_evidence_sha256.txt
  sha256sum -- 05_m08_safe_page.bit >> 05_evidence_sha256.txt
  if [[ -f 03_program_result.txt ]]; then
    sha256sum -- 03_program_result.txt >> 05_evidence_sha256.txt
  fi
)
if (( RC != 0 )); then
  echo "M08_PROGRAM_NOT_ACCEPTED_VIVADO_FAILED exit=$RC original=$DIR" >&2
  exit "$RC"
fi
if [[ "$AFTER" != "$EXPECTED" ||
      ! -f "$DIR/03_program_result.txt" ]] ||
   ! grep -Fxq "result=PROGRAMMED_ONLY_NO_PS_AXI_PROOF" "$DIR/03_program_result.txt" ||
   ! grep -Fxq "device=xck26_0" "$DIR/03_program_result.txt" ||
   ! grep -Fxq "bitstream_sha256=$EXPECTED" "$DIR/03_program_result.txt" ||
   ! grep -Fq "M08_JTAG_PROGRAMMED_BITSTREAM_NO_PS_AXI_READBACK" "$DIR/02_vivado_program.log"; then
  echo "M08_PROGRAM_NOT_ACCEPTED_INCONSISTENT_RESULT preserve=$DIR" >&2
  exit 3
fi
echo "M08_PROGRAMMED_ONLY_NO_PS_AXI_READBACK"
echo "M08_PROGRAM_EVIDENCE_DIR=$DIR"
