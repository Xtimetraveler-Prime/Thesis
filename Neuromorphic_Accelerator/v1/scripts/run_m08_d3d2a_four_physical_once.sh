#!/usr/bin/env bash
# D3.D.2A one-shot owner JTAG programming and four-neuron M02 parity.
# NO automatic retry, NO board/PS/DDR write outside bounded PL JTAG AXI.
# Original D3.D.1 and D3.C evidence/bitstreams are never modified.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
    echo 'usage: run_m08_d3d2a_four_physical_once.sh <accepted-new-four-neuron-native-dir>' >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
RUN="$(realpath -- "$1")"
if [[ ! -d "$BASE" || -L "$BASE" || ! -d "$RUN" || -L "$RUN" ||
      "$RUN" != "$BASE"/m08_d3d2a_four_* ]]; then
    echo 'M08_D3D2A_HW_STOP: invalid owner native evidence path' >&2
    exit 2
fi
if [[ "$(id -u)" -eq 0 ]]; then
    echo 'M08_D3D2A_HW_STOP: do not run as root' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1 ||
   ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_D3D2A_HW_STOP: source genuine Vivado 2025.2' >&2
    exit 2
fi
# Strict ORIGINAL native report/bitstream gate: 7 vendor-only scoped DRC
# warnings, exact pinned owner SHA/size, source copies, timing, receipts.
python3 "$ROOT/scripts/m08_d3d2a_four_gate.py" --run-dir "$RUN"
BIT="$RUN/bitstream_candidate/m08_d3d2a_four_lif_jtag_UNRELEASED.bit"
EXPECTED_SHA="3c213c1271f48106495203d008d7f46619f8f079549117e404fca11fd3179411"
if [[ ! -f "$BIT" || -L "$BIT" ||
      "$(stat -c '%s' "$BIT")" != 7797843 ||
      "$(sha256sum "$BIT" | awk '{print $1}')" != "$EXPECTED_SHA" ]]; then
    echo 'M08_D3D2A_HW_STOP: native FPGA candidate not pinned owner bitstream' >&2
    exit 2
fi
if [[ "${M08_D3D2A_ALLOW_PROGRAM:-}" != YES ]]; then
    echo 'M08_D3D2A_HW_STOP: explicitly set M08_D3D2A_ALLOW_PROGRAM=YES' >&2
    exit 2
fi

HW="$(mktemp -d "$BASE/m08_d3d2a_four_HW_XXXXXXXX")"
echo "M08_D3D2A_NEW_PC_HW_EVIDENCE=$HW"
# Only the independent host oracle writes this golden input file.
python3 "$ROOT/scripts/m08_d3d2a_four_vectors.py" --out "$HW/10_m02_golden.txt"
cp -- "$ROOT/scripts/m08_d3d2a_four_readback_once.tcl" "$HW/00_executed_source.tcl"
export M08_D3D2A_BIT="$BIT"
export M08_D3D2A_EXPECTED_SHA="$EXPECTED_SHA"
export M08_D3D2A_RESULT="$HW/80_neural_parity_readback.txt"
export M08_D3D2A_VECTORS="$HW/10_m02_golden.txt"

set +e
timeout --signal=TERM --kill-after=15s 300s     vivado -mode batch         -source "$HW/00_executed_source.tcl"         -log "$HW/01_jtag_neuron.log"         -journal "$HW/02_jtag_neuron.jou"
RC=$?
set -e
printf 'vivado_physical_exit=%s\n' "$RC" > "$HW/03_exit.txt"
(
    cd "$HW"
    if [[ "$RC" -eq 0 && -s 80_neural_parity_readback.txt ]] &&
       grep -Fxq 'result=TWO_HARDWARE_FOUR_NEURON_FIXTURES_MATCHED_M02'            80_neural_parity_readback.txt &&
       [[ "$(grep -c '^fixture=.* hardware=PASS$' 80_neural_parity_readback.txt)" -eq 2 ]]; then
        sha256sum 00_executed_source.tcl 01_jtag_neuron.log 02_jtag_neuron.jou             03_exit.txt 10_m02_golden.txt 80_neural_parity_readback.txt             > 99_evidence_sha256.txt
        sha256sum -c 99_evidence_sha256.txt
        python3 "$ROOT/scripts/m08_d3d2a_four_physical_audit.py"             --run-dir "$RUN" --hw-dir "$HW"
        echo 'M08_D3D2A_HARDWARE_FOUR_NEURON_M02_PARITY_SUCCEEDED'
    else
        # Even if the FPGA operation failed, preserve the only original
        # program attempt, log, Tcl, origin vector file and exit code.
        sha256sum 00_executed_source.tcl 01_jtag_neuron.log 02_jtag_neuron.jou             03_exit.txt 10_m02_golden.txt > 99_evidence_sha256.txt
        echo "M08_D3D2A_HW_STOP_NO_RETRY: $HW" >&2
        exit 3
    fi
)
echo "M08_D3D2A_HARDWARE_RESULT_DIR=$HW"
