#!/usr/bin/env bash
# D3.D.2C M06 32-neuron — staged single-owner-authorized KV260 JTAG test.
# CURRENTLY HARD BLOCKED until original NEW owner image is reviewed and its
# SHA256 (and exact new DRC/timing hierarchy) are recorded in *new* gate.
# NO D3.D.2B prior image reuse and NO automatic retry on any failure.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
    echo 'usage: run_m08_d3d2c_m06_physical_once.sh <new-original-accepted-native-dir>' >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/Thesis_Evidence/M08"
NATIVE="$(realpath -- "$1")"
if [[ ! -d "$BASE" || -L "$BASE" || ! -d "$NATIVE" || -L "$NATIVE" ||
      "$NATIVE" != "$BASE"/m08_d3d2c_m06_* || "$(id -u)" -eq 0 ]]; then
    echo 'M08_D3D2C_HW_STOP: noncanonical native folder or root' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1 ||
   ! vivado -version | grep -Eq '^[Vv]ivado v2025\.2([[:space:]]|$)'; then
    echo 'M08_D3D2C_HW_STOP: expected genuine Vivado 2025.2' >&2
    exit 2
fi
# Always returns 2 in current stage, even with valid new native evidence.
# It may be modified ONLY after independent original owner DRC/timing/image
# review with image-specific SHA, exact warning paths and mutation tests.
python3 "$ROOT/scripts/m08_d3d2c_m06_native_review.py" --run-dir "$NATIVE"
EXPECTED_SHA="UNREVIEWED_M08_D3D2C_OWNER_IMAGE"
if [[ ! "$EXPECTED_SHA" =~ ^[a-f0-9]{64}$ ]]; then
    echo 'M08_D3D2C_HW_STOP_NO_RELEASE: first owner image NOT accepted' >&2
    exit 2
fi
BIT="$NATIVE/bitstream_candidate/m08_d3d2c_m06_lif_jtag_UNRELEASED.bit"
if [[ ! -f "$BIT" || -L "$BIT" ||
      "$(sha256sum "$BIT" | awk '{print $1}')" != "$EXPECTED_SHA" ]]; then
    echo 'M08_D3D2C_HW_STOP: no exact reviewed original M06 candidate' >&2
    exit 2
fi
if [[ "${M08_D3D2C_ALLOW_PROGRAM:-}" != YES ]]; then
    echo 'M08_D3D2C_HW_STOP: explicit owner M08_D3D2C_ALLOW_PROGRAM=YES needed' >&2
    exit 2
fi
HW="$(mktemp -d "$BASE/m08_d3d2c_m06_HW_XXXXXXXX")"
echo "M08_D3D2C_NEW_PC_HW_EVIDENCE=$HW"
python3 "$ROOT/scripts/m08_d3d2c_m06_vectors.py" --out "$HW/10_m06_32x4_golden.hex"
cp -- "$ROOT/scripts/m08_d3d2c_m06_readback_once.tcl" "$HW/00_executed_source.tcl"
export M08_D3D2C_BIT="$BIT"
export M08_D3D2C_EXPECTED_SHA="$EXPECTED_SHA"
export M08_D3D2C_VECTORS="$HW/10_m06_32x4_golden.hex"
export M08_D3D2C_RESULT="$HW/80_m06_32x4_hw_parity.txt"
set +e
timeout --signal=TERM --kill-after=15s 600s \
    vivado -mode batch -source "$HW/00_executed_source.tcl" \
    -log "$HW/01_jtag_m06.log" -journal "$HW/02_jtag_m06.jou"
RC=$?
set -e
printf 'vivado_physical_exit=%s\n' "$RC" > "$HW/03_exit.txt"
(
    cd "$HW"
    if [[ "$RC" -eq 0 && -s 80_m06_32x4_hw_parity.txt ]] &&
        grep -Fxq 'result=ONE_ORIGINAL_M06_32X4_RECURRENT_HARDWARE_PARITY' \
            80_m06_32x4_hw_parity.txt &&
        [[ "$(grep -c '^neuron=[0-9]* voltages=.* mask=.* synaptic_currents=' \
            80_m06_32x4_hw_parity.txt)" -eq 32 ]]; then
        sha256sum 00_executed_source.tcl 01_jtag_m06.log 02_jtag_m06.jou \
            03_exit.txt 10_m06_32x4_golden.hex 80_m06_32x4_hw_parity.txt \
            >99_evidence_sha256.txt
        sha256sum -c 99_evidence_sha256.txt
        python3 "$ROOT/scripts/m08_d3d2c_m06_physical_audit.py" \
            --run-dir "$NATIVE" --hw-dir "$HW"
        echo 'M08_D3D2C_HARDWARE_M06_32X4_RECURRENT_M02_PARITY_SUCCEEDED'
    else
        for f in 00_executed_source.tcl 01_jtag_m06.log 02_jtag_m06.jou \
                 03_exit.txt 10_m06_32x4_golden.hex 80_m06_32x4_hw_parity.txt; do
            [[ ! -f "$f" ]] || sha256sum "$f"
        done >99_evidence_sha256.txt
        echo "M08_D3D2C_HW_STOP_NO_RETRY: preserve original $HW" >&2
        exit 3
    fi
)
echo "M08_D3D2C_HARDWARE_RESULT_DIR=$HW"
