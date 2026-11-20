#!/usr/bin/env bash
# M08 D3.D.2B: one owner-authorized JTAG attempt for new routed synapses.
# The new native image is NOT accepted until an independent original DRC/SHA
# review. No automatic retry on ANY failed board operation.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
    echo 'usage: run_m08_d3d2b_synaptic_physical_once.sh <new-accepted-native-dir>' >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
NATIVE="$(realpath -- "$1")"
if [[ ! -d "$BASE" || -L "$BASE" || ! -d "$NATIVE" || -L "$NATIVE" ||
      "$NATIVE" != "$BASE"/m08_d3d2b_synaptic_* || "$(id -u)" -eq 0 ]]; then
    echo 'M08_D3D2B_HW_STOP: invalid original evidence path / root user' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1 ||
   ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_D3D2B_HW_STOP: expected genuine Vivado 2025.2' >&2
    exit 2
fi
# Strict new ORIGINAL image + 12-file SHA + DRC/timing and RTL source gate,
# not a previous generation's image/waiver. This must PASS before any JTAG.
python3 "$ROOT/scripts/m08_d3d2b_synaptic_gate.py" --run-dir "$NATIVE"
BIT="$NATIVE/bitstream_candidate/m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit"
if [[ ! -f "$BIT" || -L "$BIT" ]]; then
    echo 'M08_D3D2B_HW_STOP: native synapse bitstream missing' >&2
    exit 2
fi
if [[ "${M08_D3D2B_ALLOW_PROGRAM:-}" != YES ]]; then
    echo 'M08_D3D2B_HW_STOP: explicit M08_D3D2B_ALLOW_PROGRAM=YES needed' >&2
    exit 2
fi
HW="$(mktemp -d "$BASE/m08_d3d2b_synaptic_HW_XXXXXXXX")"
echo "M08_D3D2B_NEW_PC_HW_EVIDENCE=$HW"
python3 "$ROOT/scripts/m08_d3d2b_synaptic_vectors.py" --out "$HW/10_m02_golden.txt"
cp -- "$ROOT/scripts/m08_d3d2b_synaptic_readback_once.tcl" "$HW/00_executed_source.tcl"
export M08_D3D2B_BIT="$BIT"
export M08_D3D2B_EXPECTED_SHA
M08_D3D2B_EXPECTED_SHA="$(sha256sum "$BIT" | awk '{print $1}')"
export M08_D3D2B_VECTORS="$HW/10_m02_golden.txt"
export M08_D3D2B_RESULT="$HW/80_synaptic_parity_readback.txt"
set +e
timeout --signal=TERM --kill-after=15s 300s     vivado -mode batch         -source "$HW/00_executed_source.tcl"         -log "$HW/01_jtag_synaptic.log"         -journal "$HW/02_jtag_synaptic.jou"
RC=$?
set -e
printf 'vivado_physical_exit=%s\n' "$RC" > "$HW/03_exit.txt"
(
    cd "$HW"
    if [[ "$RC" -eq 0 && -s 80_synaptic_parity_readback.txt ]] &&
       grep -Fxq 'result=TWO_FOUR_NEURON_RECURRENT_SYNAPSE_FIXTURES_MATCHED_M02'            80_synaptic_parity_readback.txt &&
       [[ "$(grep -c '^fixture=.* hardware=PASS$' 80_synaptic_parity_readback.txt)" -eq 2 ]]; then
        sha256sum 00_executed_source.tcl 01_jtag_synaptic.log 02_jtag_synaptic.jou             03_exit.txt 10_m02_golden.txt 80_synaptic_parity_readback.txt             > 99_evidence_sha256.txt
        sha256sum -c 99_evidence_sha256.txt
        python3 "$ROOT/scripts/m08_d3d2b_synaptic_physical_audit.py"             --run-dir "$NATIVE" --hw-dir "$HW"
        echo 'M08_D3D2B_HARDWARE_RECURRENT_SYNAPSE_M02_PARITY_SUCCEEDED'
    else
        sha256sum 00_executed_source.tcl 01_jtag_synaptic.log 02_jtag_synaptic.jou             03_exit.txt 10_m02_golden.txt > 99_evidence_sha256.txt
        echo "M08_D3D2B_HW_STOP_NO_RETRY: preserve original run $HW" >&2
        exit 3
    fi
)
echo "M08_D3D2B_HARDWARE_RESULT_DIR=$HW"
