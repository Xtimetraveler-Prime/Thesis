#!/usr/bin/env bash
# OWNER PC only: new passive route, independent review, UNRELEASED .bit.
# No original evidence modified; no programming, DTBO, FPGA manager or JTAG.
set -euo pipefail
if [[ "$EUID" -eq 0 ]]; then
  echo "M08_D3_2_BITGEN_REFUSED: do not run as root" >&2
  exit 2
fi
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd -P)"
if ! command -v vivado >/dev/null 2>&1; then
  echo "M08_D3_2_BITGEN_REFUSED: local Vivado 2025.2 missing" >&2
  exit 2
fi
python3 "$ROOT/scripts/m08_d3_2_passive_bitstream_gate.py" >/dev/null

# Build and route a COMPLETELY FRESH copy. Never touch 77Ols9zt or z6PIsrwZ.
OUTPUT="$(bash "$ROOT/scripts/run_m08_d3_2_passive_route_pc.sh")" || {
  printf '%s\n' "$OUTPUT"
  echo "M08_D3_2_BITGEN_REFUSED: fresh route failed; preserve evidence" >&2
  exit 2
}
printf '%s\n' "$OUTPUT"
RUN="$(printf '%s\n' "$OUTPUT" |
  sed -n 's/^M08_D3_2_PASSIVE_ROUTE_PC_REPORTS_CAPTURED_REVIEW_REQUIRED_NO_BITSTREAM_NO_BOARD=//p' |
  tail -n 1)"
case "$RUN" in
  "$HOME"/Thesis_Evidence/M08/m08_d3_2_passive_synth_*) ;;
  *) echo "M08_D3_2_BITGEN_REFUSED: wrong new run path" >&2; exit 2 ;;
esac
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt && sha256sum -c 98_route_evidence_sha256.txt)

# New review is read-only and refuses bitgen on unreviewed DRC/timing/fan topology.
python3 "$ROOT/scripts/m08_d3_2_passive_route_report_review.py" \
  --run-dir "$RUN" > "$RUN/65_prebit_pc_review.json"
mkdir "$RUN/bitstream_candidate"

# This creates only an UNRELEASED .bit on the PC. It never talks to KV260.
vivado -mode batch \
  -source "$ROOT/scripts/m08_d3_2_passive_bitstream_candidate.tcl" \
  -log "$RUN/07_passive_bitgen_vivado.log" \
  -journal "$RUN/08_passive_bitgen_vivado.jou" \
  -tclargs "$RUN/output" "$RUN/bitstream_candidate"

# Validate candidate, log, size and rereview original receipts before signing.
# Since receipt is written last, make first native audit without candidate ledger
# by using the --pre-ledger explicit option.
python3 "$ROOT/scripts/m08_d3_2_passive_bitstream_gate.py" \
  --run-dir "$RUN" --pre-ledger > "$RUN/66_pc_unreleased_bitstream_gate.json"

(
  cd "$RUN"
  sha256sum \
    07_passive_bitgen_vivado.log \
    08_passive_bitgen_vivado.jou \
    65_prebit_pc_review.json \
    66_pc_unreleased_bitstream_gate.json \
    bitstream_candidate/m08_d3_2_passive_fan_UNRELEASED.bit \
    bitstream_candidate/61_unreleased_bitstream_readback.txt \
    > 96_candidate_evidence_sha256.txt
  sha256sum -c 96_candidate_evidence_sha256.txt
)
python3 "$ROOT/scripts/m08_d3_2_passive_bitstream_gate.py" --run-dir "$RUN"
printf 'M08_D3_2_UNRELEASED_BITSTREAM_CANDIDATE_CAPTURED_NO_BOARD=%s\n' "$RUN"
