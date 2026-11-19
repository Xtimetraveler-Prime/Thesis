#!/usr/bin/env bash
# Offline owner PC ONLY: fresh native KV260 JTAG AXI -> BRAM candidate.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
    echo 'M08_D3C_STOP: PC M08 evidence base missing/symlinked' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1; then
    echo 'M08_D3C_STOP: source Vivado 2025.2 settings64.sh first' >&2
    exit 2
fi
if ! vivado -version | grep -Eq '^Vivado v2025\.2'; then
    echo 'M08_D3C_STOP: Vivado version not 2025.2' >&2
    exit 2
fi
python3 "$ROOT/scripts/m08_d3c_jtag_bram_gate.py" --source-only
RUN="$(mktemp -d "$BASE/m08_d3c_jtag_link_XXXXXXXX")"
echo "M08_D3C_FRESH_PC_EVIDENCE_DIR=$RUN"
set +e
vivado -mode batch \
    -source "$ROOT/scripts/m08_d3c_jtag_bram_build.tcl" \
    -tclargs "$RUN" \
    -log "$RUN/00_vivado.log" \
    -journal "$RUN/01_vivado.jou"
RC=$?
set -e
printf 'vivado_build_exit=%s\n' "$RC" > "$RUN/02_vivado_exit.txt"
if [[ "$RC" -ne 0 ]]; then
    echo "M08_D3C_NATIVE_BUILD_FAILED_PC_ONLY: $RUN" >&2
    exit "$RC"
fi
FILES=(
    00_vivado.log 01_vivado.jou 02_vivado_exit.txt
    reports/10_fan_a12.xdc
    reports/20_route_drc.rpt
    reports/21_route_timing.rpt
    reports/22_route_utilization.rpt
    reports/23_route_clocks.rpt
    reports/30_native_result.txt
    bitstream_candidate/m08_d3c_jtag_bram_UNRELEASED.bit
)
for name in "$(printf '%s\n' "00_vivado.log" "01_vivado.jou" "02_vivado_exit.txt" \
    "reports/10_fan_a12.xdc" "reports/20_route_drc.rpt" "reports/21_route_timing.rpt" \
    "reports/22_route_utilization.rpt" "reports/23_route_clocks.rpt" \
    "reports/30_native_result.txt" "bitstream_candidate/m08_d3c_jtag_bram_UNRELEASED.bit")"; do
    : "$name"
done
(
    cd "$RUN"
    sha256sum "00_vivado.log" "01_vivado.jou" "02_vivado_exit.txt" \
        "reports/10_fan_a12.xdc" "reports/20_route_drc.rpt" "reports/21_route_timing.rpt" \
        "reports/22_route_utilization.rpt" "reports/23_route_clocks.rpt" \
        "reports/30_native_result.txt" "bitstream_candidate/m08_d3c_jtag_bram_UNRELEASED.bit" \
        > 99_evidence_sha256.txt
    sha256sum -c 99_evidence_sha256.txt
)
python3 "$ROOT/scripts/m08_d3c_jtag_bram_gate.py" --run-dir "$RUN"
echo "M08_D3C_PC_NATIVE_BRAM_CANDIDATE_UNRELEASED=$RUN"
