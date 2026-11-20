#!/usr/bin/env bash
# D3.D.1 physical one-shot JTAG neural test; NEVER run until new genuine native
# Vivado image hash/timing/DRC and KV260 recovery/cooling/UART are reviewed.
# This is explicit owner programming. No automatic reprogramming or retry.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
    echo 'usage: run_m08_d3d_neuron_physical_once.sh <new-accepted-D3D-native-run>' >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN="$(realpath -- "$1")"
BASE="$HOME/Thesis_Evidence/M08"
if [[ "$RUN" != "$BASE"/m08_d3d_neuron_* || ! -d "$RUN" ||
      ! -d "$BASE" || -L "$BASE" || -L "$RUN" ]]; then
    echo 'M08_D3D_HW_STOP: unexpected/missing/symlinked new neural evidence' >&2
    exit 2
fi
if [[ "$(id -u)" -eq 0 ]]; then
    echo 'M08_D3D_HW_STOP: do not run as root' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1 ||
   ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_D3D_HW_STOP: expected genuine Vivado 2025.2' >&2
    exit 2
fi
# Independent source/native audit before even arming JTAG.
python3 "$ROOT/scripts/m08_d3d_neuron_gate.py" --run-dir "$RUN"
BIT="$RUN/bitstream_candidate/m08_d3d_lif_jtag_UNRELEASED.bit"
if [[ ! -f "$BIT" || -L "$BIT" ]]; then
    echo 'M08_D3D_HW_STOP: no new verified LIF bitstream' >&2
    exit 2
fi
if [[ "${M08_D3D_ALLOW_PROGRAM:-}" != YES ]]; then
    echo 'M08_D3D_HW_STOP: explicitly set M08_D3D_ALLOW_PROGRAM=YES' >&2
    exit 2
fi
TEST="$(mktemp -d "$BASE/m08_d3d_neuron_HW_XXXXXXXX")"
echo "M08_D3D_NEW_PC_HW_EVIDENCE=$TEST"
# Generate independent M02 dense+queued *goldens*, not HW result values.
python3 "$ROOT/scripts/m08_d3d_neuron_vectors.py" --out "$TEST/10_m02_golden.txt"
export M08_D3D_BIT="$BIT"
export M08_D3D_EXPECTED_SHA
M08_D3D_EXPECTED_SHA="$(sha256sum "$BIT" | cut -d ' ' -f1)"
export M08_D3D_RESULT="$TEST/80_neural_parity_readback.txt"
export M08_D3D_VECTORS="$TEST/10_m02_golden.txt"
set +e
timeout --signal=TERM --kill-after=15s 300s \
    vivado -mode batch \
        -source "$ROOT/scripts/m08_d3d_neuron_readback_once.tcl" \
        -log "$TEST/01_jtag_neuron.log" \
        -journal "$TEST/02_jtag_neuron.jou"
RC=$?
set -e
printf 'vivado_physical_exit=%s\n' "$RC" > "$TEST/03_exit.txt"
(
    cd "$TEST"
    cp "$ROOT/scripts/m08_d3d_neuron_readback_once.tcl" 00_executed_source.tcl
    if [[ "$RC" -eq 0 && -s 80_neural_parity_readback.txt ]] &&
       grep -Fxq 'result=FOUR_HARDWARE_NEURON_FIXTURES_MATCHED_M02' \
           80_neural_parity_readback.txt &&
       [[ "$(grep -c '^fixture=.* hardware=PASS$' 80_neural_parity_readback.txt)" -eq 4 ]]; then
        sha256sum 00_executed_source.tcl 01_jtag_neuron.log 02_jtag_neuron.jou \
           03_exit.txt 10_m02_golden.txt 80_neural_parity_readback.txt \
           > 99_evidence_sha256.txt
        sha256sum -c 99_evidence_sha256.txt
        # Independent read-only verdict requires complete per-tick physical
        # parity against the separately computed existing M02 reference.
        python3 "$ROOT/scripts/m08_d3d_neuron_physical_audit.py" \
            --run-dir "$RUN" --hw-dir "$TEST"
        echo 'M08_D3D_HARDWARE_M02_LIF_FOUR_FIXTURE_PARITY_SUCCEEDED'
    else
        sha256sum 00_executed_source.tcl 01_jtag_neuron.log 02_jtag_neuron.jou \
           03_exit.txt 10_m02_golden.txt > 99_evidence_sha256.txt
        echo 'M08_D3D_HW_STOP_NO_RETRY: preserve evidence, UART and recovery state' >&2
        exit 3
    fi
)
echo "M08_D3D_HARDWARE_RESULT_DIR=$TEST"
