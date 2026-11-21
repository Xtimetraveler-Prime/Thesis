#!/usr/bin/env bash
# M08.4 ONLY: FIRST NEW original owner PC Vivado 2025.2 candidate.
# NO BOARD / JTAG / DDR / Linux device access. Not image-signoff.
# Preserve ALL accepted and failed original-native evidence directories.
set -euo pipefail
if [[ "$(id -u)" -eq 0 ]]; then
    echo "M08_4_PC_REFUSED_ROOT_OWNER" >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
    echo "M08_4_PC_EVIDENCE_BASE_MISSING_OR_SYMLINKED" >&2
    exit 2
fi
command -v vivado >/dev/null 2>&1 || {
    echo 'M08_4_PC_NEEDS_REAL_VIVADO_2025_2_SETTINGS64' >&2
    exit 2
}
vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)' || {
    echo 'M08_4_PC_REQUIRES_VIVADO_2025_2' >&2
    exit 2
}
# Real RTL tests must not be skipped; this is a compute-bearing candidate.
command -v iverilog >/dev/null 2>&1 || {
    echo 'M08_4_PC_REQUIRES_REAL_IVERILOG' >&2
    exit 2
}
command -v vvp >/dev/null 2>&1 || {
    echo 'M08_4_PC_REQUIRES_REAL_VVP' >&2
    exit 2
}
export PYTHONDONTWRITEBYTECODE=1
python3 "$ROOT/scripts/m08_paged_m06_lif_source_gate.py" --source-only
(
    cd "$ROOT"
    python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif.py' -v
    python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif_fail_closed.py' -v
)
# Only real source/Icarus success creates new original owner evidence.
RUN="$(mktemp -d "$BASE/m08_paged_m06_lif_XXXXXXXX")"
echo "M08_4_FIRST_NEW_OWNER_OFFLINE_CANDIDATE_DIR=$RUN"
set +e
vivado -mode batch \
    -log "$RUN/00_vivado.log" \
    -journal "$RUN/01_vivado.jou" \
    -source "$ROOT/scripts/m08_paged_m06_lif_build.tcl" \
    -tclargs "$RUN"
RC=$?
set -e
printf 'vivado_build_exit=%s\n' "$RC" > "$RUN/02_vivado_exit.txt"
if [[ "$RC" -ne 0 ]]; then
    echo "M08_4_FIRST_OWNER_NATIVE_FAILED_OFFLINE_KEEP_ORIGINAL=$RUN" >&2
    exit "$RC"
fi
FILES=(
    00_vivado.log
    01_vivado.jou
    02_vivado_exit.txt
    reports/10_fan_a12.xdc
    reports/11_fabric_por.v
    reports/12_paged_lif_shell.v
    reports/13_paged_lif_engine.v
    reports/14_paged_axil_control.sv
    reports/15_paged_host_page_bank.sv
    reports/20_route_drc.rpt
    reports/21_route_timing.rpt
    reports/22_route_utilization.rpt
    reports/23_route_clocks.rpt
    reports/30_native_result.txt
    bitstream_candidate/m08_paged_m06_lif_jtag_UNRELEASED.bit
)
for rel in "${FILES[@]}"; do
    if [[ ! -s "$RUN/$rel" || -L "$RUN/$rel" ]]; then
        echo "M08_4_FIRST_OWNER_NATIVE_MISSING=$RUN/$rel" >&2
        exit 3
    fi
done
(
    cd "$RUN"
    sha256sum "${FILES[@]}" > 99_evidence_sha256.txt
    sha256sum -c 99_evidence_sha256.txt
)
echo "M08_4_FIRST_OWNER_ROUTED_BITSTREAM_NEW_IMAGE_REVIEW_REQUIRED=$RUN"
echo "M08_4_NO_BOARD_NO_JTAG_NO_DDR_NO_RELEASE"
# Deliberately ALWAYS exits 2 even if the first original new bitstream
# is genuine. Share exact image DRC/timing/warnings/source hash then create
# a distinct image-specific gate. NEVER inherit older M32Q bit acceptance.
python3 "$ROOT/scripts/m08_paged_m06_lif_native_review.py" --run-dir "$RUN"
