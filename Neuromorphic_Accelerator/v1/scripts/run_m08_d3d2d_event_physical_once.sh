#!/usr/bin/env bash
# D3.D.2D M06 raw-event — FIRST new FPGA test STAGED AND HARD BLOCKED.
# NO new original DRC/timing/bitstream signoff exists. DO NOT RUN ON BOARD.
# Revalidate all 12 immutable native SHA files, exact DRC, RTL, 100MHz timing,
# original image digest BEFORE generating physical evidence or opening JTAG.
# Owner confirms independent ACTIVE cooling, UART capture, stock recovery,
# stable exclusive JTAG, and explicit one-shot program consent manually.
# Exactly one Tcl program_hw_devices invocation; NEVER retry automatically.
# No PS/DDR/Linux MMIO, no flash, SD writes or D3.D.2B image reuse.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
    echo 'usage: run_m08_d3d2d_event_physical_once.sh <new-original-accepted-native-dir>' >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
NATIVE="$(realpath -- "$1")"
if [[ ! -d "$BASE" || -L "$BASE" || ! -d "$NATIVE" || -L "$NATIVE" ||
      "$NATIVE" != "$BASE"/m08_d3d2d_event_* || "$(id -u)" -eq 0 ]]; then
    echo 'M08_D3D2D_HW_STOP: noncanonical native folder or root' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1 ||
   ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_D3D2D_HW_STOP: expected genuine Vivado 2025.2' >&2
    exit 2
fi
# NEW first-owner native DRC/timing/bitstream must be reviewed separately.
# Its first-image native gate ALWAYS exits 2. No physical programming now.
python3 "$ROOT/scripts/m08_d3d2d_event_native_review.py" --run-dir "$NATIVE"
EXPECTED_SHA="UNREVIEWED_M08_D3D2D_NEW_IMAGE"
EXPECTED_SIZE=0  # Unreviewed first image: HARD STOP, NEVER force to zero-size bit
BIT="$NATIVE/bitstream_candidate/m08_d3d2d_event_lif_jtag_UNRELEASED.bit"
if [[ ! -f "$BIT" || -L "$BIT" ||
      "$(stat -c '%s' "$BIT")" != "$EXPECTED_SIZE" ||
      "$(sha256sum "$BIT" | awk '{print $1}')" != "$EXPECTED_SHA" ]]; then
    echo 'M08_D3D2D_HW_STOP: no exact reviewed original M06 candidate' >&2
    exit 2
fi
if [[ "${M08_D3D2D_ALLOW_PROGRAM:-}" != YES ||
      "${M08_D3D2D_PREFLIGHT_CONFIRMED:-}" != YES ]]; then
    echo 'M08_D3D2D_HW_STOP: owner must confirm independent active cooling, UART logging, recovery, stable single-owner JTAG and arm M08_D3D2D_ALLOW_PROGRAM=YES M08_D3D2D_PREFLIGHT_CONFIRMED=YES' >&2
    exit 2
fi
# No GUI Hardware Manager / independent hw_server on the same JTAG cable.
# Unique evidence dir, exclusive fresh name; no failed attempt overwritten.
HW="$(mktemp -d "$BASE/m08_d3d2d_event_HW_XXXXXXXX")"
echo "M08_D3D2D_NEW_PC_HW_EVIDENCE=$HW"
python3 "$ROOT/scripts/m08_d3d2d_event_vectors.py" --out "$HW/10_m06_raw17_golden.hex"
cp -- "$ROOT/scripts/m08_d3d2d_event_readback_once.tcl" "$HW/00_executed_source.tcl"
export M08_D3D2D_BIT="$BIT"
export M08_D3D2D_EXPECTED_SHA="$EXPECTED_SHA"
export M08_D3D2D_VECTORS="$HW/10_m06_raw17_golden.hex"
export M08_D3D2D_RESULT="$HW/80_m06_raw17_hw_parity.txt"
set +e
timeout --signal=TERM --kill-after=15s 600s \
    vivado -mode batch -source "$HW/00_executed_source.tcl" \
    -log "$HW/01_jtag_m06.log" -journal "$HW/02_jtag_m06.jou"
RC=$?
set -e
printf 'vivado_physical_exit=%s\n' "$RC" > "$HW/03_exit.txt"
(
    cd "$HW"
    if [[ "$RC" -eq 0 && -s 80_m06_raw17_hw_parity.txt ]] &&
        grep -Fxq 'result=ONE_ORIGINAL_M06_32X4_RAW_EVENT_AND_RECURRENT_HARDWARE_PARITY' \
            80_m06_raw17_hw_parity.txt &&
        [[ "$(grep -c '^neuron=[0-9]* external_currents=.* voltages=.* mask=.* synaptic_currents=' \
            80_m06_raw17_hw_parity.txt)" -eq 32 ]]; then
        sha256sum 00_executed_source.tcl 01_jtag_m06.log 02_jtag_m06.jou \
            03_exit.txt 10_m06_raw17_golden.hex 80_m06_raw17_hw_parity.txt \
            >99_evidence_sha256.txt
        sha256sum -c 99_evidence_sha256.txt
        python3 "$ROOT/scripts/m08_d3d2d_event_physical_audit.py" \
            --run-dir "$NATIVE" --hw-dir "$HW"
        echo 'M08_D3D2D_HARDWARE_M06_32X4_RAW_EVENT_AND_RECURRENT_PARITY_SUCCEEDED'
    else
        for f in 00_executed_source.tcl 01_jtag_m06.log 02_jtag_m06.jou \
                 03_exit.txt 10_m06_raw17_golden.hex 80_m06_raw17_hw_parity.txt; do
            [[ ! -f "$f" ]] || sha256sum "$f"
        done >99_evidence_sha256.txt
        echo "M08_D3D2D_HW_STOP_NO_RETRY: preserve original $HW" >&2
        exit 3
    fi
)
echo "M08_D3D2D_HARDWARE_RESULT_DIR=$HW"
