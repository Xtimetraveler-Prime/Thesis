#!/usr/bin/env bash
# M08 D3.2 OWNER PC ONLY: fresh passive synthesis then route_design, NO .bit.
set -euo pipefail
if [[ "$EUID" -eq 0 ]]; then
    echo "M08_D3_2_ROUTE_REJECTED: do not run as root" >&2
    exit 2
fi
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd -P)"
if ! command -v vivado >/dev/null 2>&1; then
    echo "M08_D3_2_ROUTE_REJECTED: Vivado 2025.2 unavailable" >&2
    exit 2
fi
python3 "$ROOT/scripts/m08_d3_2_passive_route_gate.py" >/dev/null
# The existing synth runner creates a FRESH, isolated Vivado project. Do not
# copy/modify the original accepted D3.1 run or previous z6PIsrwZ evidence.
SYNTH_OUTPUT="$(bash "$ROOT/scripts/run_m08_d3_2_passive_synth_pc.sh")" || {
    printf '%s\n' "$SYNTH_OUTPUT"
    echo "M08_D3_2_ROUTE_REJECTED: passive synthesis did not complete" >&2
    exit 2
}
printf '%s\n' "$SYNTH_OUTPUT"
RUN="$(printf '%s\n' "$SYNTH_OUTPUT" | sed -n 's/^M08_D3_2_PASSIVE_PC_SYNTH_ONLY_RECORDED_NOT_ROUTED_NO_BITSTREAM_NO_BOARD=//p' | tail -n 1)"
case "$RUN" in
    "$HOME"/Thesis_Evidence/M08/m08_d3_2_passive_synth_*) ;;
    *) echo "M08_D3_2_ROUTE_REJECTED: fresh synthesis run path invalid" >&2; exit 2 ;;
esac
if [[ ! -f "$RUN/99_evidence_sha256.txt" ]]; then
    echo "M08_D3_2_ROUTE_REJECTED: original synthesis evidence ledger absent" >&2
    exit 2
fi
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
vivado -mode batch     -source "$ROOT/scripts/m08_d3_2_passive_route_only.tcl"     -log "$RUN/05_passive_route_vivado.log"     -journal "$RUN/06_passive_route_vivado.jou"     -tclargs "$RUN/output"
python3 "$ROOT/scripts/m08_d3_2_passive_route_gate.py" --native-run-dir "$RUN"     > "$RUN/50_pc_route_evidence_review.json"
# New SECOND ledger: keep the original 99 synthesis receipt unchanged.
(
    cd "$RUN"
    sha256sum         05_passive_route_vivado.log         06_passive_route_vivado.jou         output/40_passive_route_readback.txt         output/41_passive_route_timing.rpt         output/42_passive_route_drc.rpt         output/43_passive_route_utilization.rpt         output/44_passive_route_clocks.rpt         50_pc_route_evidence_review.json         > 98_route_evidence_sha256.txt
    sha256sum -c 98_route_evidence_sha256.txt
)
printf 'M08_D3_2_PASSIVE_ROUTE_PC_REPORTS_CAPTURED_REVIEW_REQUIRED_NO_BITSTREAM_NO_BOARD=%s\n' "$RUN"
