#!/usr/bin/env bash
# Offline owner PC ONLY: NEW 32-neuron RAW EVENT M32E v5 candidate. NO BOARD.
# Historical D3.D.2C original physical image and evidence are immutable.
# No hardware programming, no original evidence overwrite, no Vivado reuse.
# A successful bitgen is NOT native signoff: first new DRC/timing/image
# report needs separate original-owner review and an exact-image allowlist.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
    echo 'M08_D3D2D_STOP: PC M08 evidence base missing/symlinked' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1; then
    echo 'M08_D3D2D_STOP: source Vivado 2025.2 settings64.sh first' >&2
    exit 2
fi
if ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_D3D2D_STOP: Vivado version not 2025.2' >&2
    exit 2
fi
python3 "$ROOT/scripts/m08_d3d2d_event_gate.py" --source-only
RUN="$(mktemp -d "$BASE/m08_d3d2d_event_XXXXXXXX")"
echo "M08_D3D2D_FRESH_PC_EVIDENCE_DIR=$RUN"
set +e
vivado -mode batch \
    -log "$RUN/00_vivado.log" \
    -journal "$RUN/01_vivado.jou" \
    -source "$ROOT/scripts/m08_d3d2d_event_build.tcl" \
    -tclargs "$RUN"
RC=$?
set -e
printf 'vivado_build_exit=%s\n' "$RC" > "$RUN/02_vivado_exit.txt"
if [[ "$RC" -ne 0 ]]; then
    echo "M08_D3D2D_NATIVE_BUILD_FAILED_PC_ONLY: $RUN" >&2
    exit "$RC"
fi
for name in "00_vivado.log" "01_vivado.jou" "02_vivado_exit.txt" \
    "reports/10_fan_a12.xdc" "reports/11_fabric_por.v" "reports/12_synaptic_lif_axil.v" "reports/20_route_drc.rpt" "reports/21_route_timing.rpt" \
    "reports/22_route_utilization.rpt" "reports/23_route_clocks.rpt" \
    "reports/30_native_result.txt" "bitstream_candidate/m08_d3d2d_event_lif_jtag_UNRELEASED.bit"; do
    if [[ ! -s "$RUN/$name" || -L "$RUN/$name" ]]; then
        echo "M08_D3D2D_MISSING_NATIVE_EVIDENCE: $RUN/$name" >&2
        exit 3
    fi
done
(
    cd "$RUN"
    sha256sum "00_vivado.log" "01_vivado.jou" "02_vivado_exit.txt" \
        "reports/10_fan_a12.xdc" "reports/11_fabric_por.v" "reports/12_synaptic_lif_axil.v" "reports/20_route_drc.rpt" "reports/21_route_timing.rpt" \
        "reports/22_route_utilization.rpt" "reports/23_route_clocks.rpt" \
        "reports/30_native_result.txt" "bitstream_candidate/m08_d3d2d_event_lif_jtag_UNRELEASED.bit" \
        > 99_evidence_sha256.txt
    sha256sum -c 99_evidence_sha256.txt
)
echo "M08_D3D2D_PC_NATIVE_IMAGE_NEW_DRC_REVIEW_REQUIRED=$RUN"
echo "M08_D3D2D_NO_BOARD_NO_JTAG_NO_IMAGE_RELEASE"
python3 "$ROOT/scripts/m08_d3d2d_event_native_review.py" --run-dir "$RUN"
