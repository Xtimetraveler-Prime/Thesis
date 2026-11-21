#!/usr/bin/env bash
# D3.D.2E M32Q STAGED/NOT RELEASED: new EXACT owner-image inspector MUST return 0 first.
# image, only after read-only original 12-SHA/DRC/timing native gate exit 0.
# User must separately confirm independent cooling, UART, stable exclusive
# JTAG and stock recovery. One owner-authorized physical run, NO AUTO RETRY.
# Revalidate all 12 immutable native SHA files, exact DRC, RTL, 100MHz timing,
# original image digest BEFORE generating physical evidence or opening JTAG.
# Owner confirms independent ACTIVE cooling, UART capture, stock recovery,
# stable exclusive JTAG, and explicit one-shot program consent manually.
# Exactly one Tcl program_hw_devices invocation; NEVER retry automatically.
# No PS/DDR/Linux MMIO, no flash, SD writes or D3.D.2D image reuse.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
    echo 'usage: run_m08_d3d2e_queue_physical_once.sh <new-original-accepted-native-dir>' >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
NATIVE="$(realpath -- "$1")"
if [[ ! -d "$BASE" || -L "$BASE" || ! -d "$NATIVE" || -L "$NATIVE" ||
      "$NATIVE" != "$BASE/m08_d3d2e_queue_GFz0SbiC" || "$(id -u)" -eq 0 ]]; then
    echo 'M08_D3D2E_HW_STOP: noncanonical native folder or root' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1 ||
   ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_D3D2E_HW_STOP: expected genuine Vivado 2025.2' >&2
    exit 2
fi
# Exact original owner image provenance, seven JTAG/XSDB warnings, bitstream
# SHA and timing are independently verified by the native checker BEFORE any
# physical receipt directory or JTAG operation.
# This is the NEW first-original exact DRC/timing acceptance gate, released only after
# all exact owner report hashes and warning pins are independently reviewed.
# DO NOT bypass this line; stop before creating an HW folder or opening JTAG.
python3 "$ROOT/scripts/m08_d3d2e_queue_exact_native_accept.py" --run-dir "$NATIVE"
EXPECTED_SHA="2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc"
EXPECTED_SIZE=7797844
BIT="$NATIVE/bitstream_candidate/m08_d3d2e_queue_lif_jtag_UNRELEASED.bit"
if [[ ! -f "$BIT" || -L "$BIT" ||
      "$(stat -c '%s' "$BIT")" != "$EXPECTED_SIZE" ||
      "$(sha256sum "$BIT" | awk '{print $1}')" != "$EXPECTED_SHA" ]]; then
    echo 'M08_D3D2E_HW_STOP: no exact reviewed first-original M32Q candidate' >&2
    exit 2
fi
if [[ "${M08_D3D2E_ALLOW_PROGRAM:-}" != YES ||
      "${M08_D3D2E_PREFLIGHT_CONFIRMED:-}" != YES ]]; then
    echo 'M08_D3D2E_HW_STOP: owner must confirm independent active cooling, UART logging, recovery, stable single-owner JTAG and arm M08_D3D2E_ALLOW_PROGRAM=YES M08_D3D2E_PREFLIGHT_CONFIRMED=YES' >&2
    exit 2
fi
# No GUI Hardware Manager / independent hw_server on the same JTAG cable.
# Unique evidence dir, exclusive fresh name; no failed attempt overwritten.
HW="$(mktemp -d "$BASE/m08_d3d2e_queue_HW_XXXXXXXX")"
echo "M08_D3D2E_NEW_PC_HW_EVIDENCE=$HW"
python3 "$ROOT/scripts/m08_d3d2d_event_vectors.py" --out "$HW/10_m06_tickqueue_golden.hex"
cp -- "$ROOT/scripts/m08_d3d2e_queue_readback_once.tcl" "$HW/00_executed_source.tcl"
export M08_D3D2E_BIT="$BIT"
export M08_D3D2E_EXPECTED_SHA="$EXPECTED_SHA"
export M08_D3D2E_VECTORS="$HW/10_m06_tickqueue_golden.hex"
export M08_D3D2E_RESULT="$HW/80_m06_tickqueue_hw_parity.txt"
set +e
timeout --signal=TERM --kill-after=15s 600s \
    vivado -mode batch -source "$HW/00_executed_source.tcl" \
    -log "$HW/01_jtag_m06.log" -journal "$HW/02_jtag_m06.jou"
RC=$?
set -e
printf 'vivado_physical_exit=%s\n' "$RC" > "$HW/03_exit.txt"
(
    cd "$HW"
    if [[ "$RC" -eq 0 && -s 80_m06_tickqueue_hw_parity.txt ]] &&
        grep -Fxq 'result=ONE_ORIGINAL_M06_32X4_QUEUED_EVENT_SERVICE_AND_RECURRENT_HARDWARE_PARITY' \
            80_m06_tickqueue_hw_parity.txt &&
        [[ "$(grep -c '^neuron=[0-9]* external_currents=.* voltages=.* mask=.* synaptic_currents=' \
            80_m06_tickqueue_hw_parity.txt)" -eq 32 ]]; then
        sha256sum 00_executed_source.tcl 01_jtag_m06.log 02_jtag_m06.jou \
            03_exit.txt 10_m06_tickqueue_golden.hex 80_m06_tickqueue_hw_parity.txt \
            >99_evidence_sha256.txt
        sha256sum -c 99_evidence_sha256.txt
        python3 "$ROOT/scripts/m08_d3d2e_queue_physical_audit.py" \
            --run-dir "$NATIVE" --hw-dir "$HW"
        echo 'M08_D3D2E_HARDWARE_M06_32X4_QUEUE_SERVICE_AND_RECURRENT_PARITY_SUCCEEDED'
    else
        for f in 00_executed_source.tcl 01_jtag_m06.log 02_jtag_m06.jou \
                 03_exit.txt 10_m06_tickqueue_golden.hex 80_m06_tickqueue_hw_parity.txt; do
            [[ ! -f "$f" ]] || sha256sum "$f"
        done >99_evidence_sha256.txt
        echo "M08_D3D2E_HW_STOP_NO_RETRY: preserve original $HW" >&2
        exit 3
    fi
)
echo "M08_D3D2E_HARDWARE_RESULT_DIR=$HW"
