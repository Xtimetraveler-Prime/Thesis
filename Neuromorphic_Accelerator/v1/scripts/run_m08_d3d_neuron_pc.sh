#!/usr/bin/env bash
# Offline owner PC ONLY: first real LIF compute-bearing KV260 JTAG image.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
    echo 'M08_D3D_STOP: PC M08 evidence base missing/symlinked' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1; then
    echo 'M08_D3D_STOP: source Vivado 2025.2 settings64.sh first' >&2
    exit 2
fi
if ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_D3D_STOP: Vivado version not 2025.2' >&2
    exit 2
fi
python3 "$ROOT/scripts/m08_d3d_neuron_gate.py" --source-only
RUN="$(mktemp -d "$BASE/m08_d3d_neuron_XXXXXXXX")"
echo "M08_D3D_FRESH_PC_EVIDENCE_DIR=$RUN"
set +e
vivado -mode batch \
    -log "$RUN/00_vivado.log" \
    -journal "$RUN/01_vivado.jou" \
    -source "$ROOT/scripts/m08_d3d_neuron_build.tcl" \
    -tclargs "$RUN"
RC=$?
set -e
printf 'vivado_build_exit=%s\n' "$RC" > "$RUN/02_vivado_exit.txt"
if [[ "$RC" -ne 0 ]]; then
    echo "M08_D3D_NATIVE_BUILD_FAILED_PC_ONLY: $RUN" >&2
    exit "$RC"
fi
for name in "00_vivado.log" "01_vivado.jou" "02_vivado_exit.txt" \
    "reports/10_fan_a12.xdc" "reports/11_fabric_por.v" "reports/12_lif_axil.v" "reports/20_route_drc.rpt" "reports/21_route_timing.rpt" \
    "reports/22_route_utilization.rpt" "reports/23_route_clocks.rpt" \
    "reports/30_native_result.txt" "bitstream_candidate/m08_d3d_lif_jtag_UNRELEASED.bit"; do
    if [[ ! -s "$RUN/$name" || -L "$RUN/$name" ]]; then
        echo "M08_D3D_MISSING_NATIVE_EVIDENCE: $RUN/$name" >&2
        exit 3
    fi
done
(
    cd "$RUN"
    sha256sum "00_vivado.log" "01_vivado.jou" "02_vivado_exit.txt" \
        "reports/10_fan_a12.xdc" "reports/11_fabric_por.v" "reports/12_lif_axil.v" "reports/20_route_drc.rpt" "reports/21_route_timing.rpt" \
        "reports/22_route_utilization.rpt" "reports/23_route_clocks.rpt" \
        "reports/30_native_result.txt" "bitstream_candidate/m08_d3d_lif_jtag_UNRELEASED.bit" \
        > 99_evidence_sha256.txt
    sha256sum -c 99_evidence_sha256.txt
)
python3 "$ROOT/scripts/m08_d3d_neuron_gate.py" --run-dir "$RUN"
echo "M08_D3D_PC_NATIVE_NEURON_CANDIDATE_UNRELEASED=$RUN"
