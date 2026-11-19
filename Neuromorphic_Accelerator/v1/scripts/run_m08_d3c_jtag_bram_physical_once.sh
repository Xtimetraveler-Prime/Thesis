#!/usr/bin/env bash
# EXPLICIT physical one-shot JTAG link experiment: no Linux/SSH dependency.
# Never call until fresh native Vivado 2025.2 image is verified and physical setup ready.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
    echo 'usage: run_m08_d3c_jtag_bram_physical_once.sh <fresh-native-D3C-run>' >&2
    exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN="$(realpath -- "$1")"
BASE="$HOME/Thesis_Evidence/M08"
if [[ "$RUN" != "$BASE"/m08_d3c_jtag_link_* || ! -d "$RUN" ]]; then
    echo 'M08_D3C_HW_STOP: unexpected candidate directory' >&2
    exit 2
fi
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
    echo 'M08_D3C_HW_STOP: PC evidence base unavailable' >&2
    exit 2
fi
if ! command -v vivado >/dev/null 2>&1 ||
   ! vivado -version | grep -Eq '^Vivado v2025\.2'; then
    echo 'M08_D3C_HW_STOP: expected Vivado 2025.2 not active' >&2
    exit 2
fi
python3 "$ROOT/scripts/m08_d3c_jtag_bram_gate.py" --run-dir "$RUN"
BIT="$RUN/bitstream_candidate/m08_d3c_jtag_bram_UNRELEASED.bit"
if [[ ! -f "$BIT" || -L "$BIT" ]]; then
    echo 'M08_D3C_HW_STOP: missing/symlinked new bit' >&2
    exit 2
fi
if [[ "$USER" == root ]]; then
    echo 'M08_D3C_HW_STOP: do not run as root' >&2
    exit 2
fi
if [[ "${M08_D3C_ALLOW_PROGRAM:-}" != YES ]]; then
    echo 'M08_D3C_HW_STOP: export M08_D3C_ALLOW_PROGRAM=YES explicitly' >&2
    exit 2
fi
TEST="$(mktemp -d "$BASE/m08_d3c_jtag_HW_XXXXXXXX")"
echo "M08_D3C_NEW_PC_HW_EVIDENCE=$TEST"
export M08_D3C_BIT="$BIT"
export M08_D3C_EXPECTED_SHA
M08_D3C_EXPECTED_SHA="$(sha256sum "$BIT" | cut -d ' ' -f1)"
export M08_D3C_RESULT="$TEST/80_four_word_readback.txt"
set +e
timeout --signal=TERM --kill-after=15s 240s \
  vivado -mode batch \
    -source "$ROOT/scripts/m08_d3c_jtag_bram_readback_once.tcl" \
    -log "$TEST/01_jtag_run.log" \
    -journal "$TEST/02_jtag_run.jou"
RC=$?
set -e
printf 'vivado_physical_exit=%s\n' "$RC" > "$TEST/03_exit.txt"
(
    cd "$TEST"
    cp "$ROOT/scripts/m08_d3c_jtag_bram_readback_once.tcl" 00_executed_source.tcl
    if [[ "$RC" -eq 0 && -s 80_four_word_readback.txt ]] &&
       grep -q 'result=FOUR_BRAM_WORDS_WRITTEN_READ_AND_MATCHED' 80_four_word_readback.txt; then
        sha256sum 00_executed_source.tcl 01_jtag_run.log 02_jtag_run.jou \
          03_exit.txt 80_four_word_readback.txt > 99_evidence_sha256.txt
        sha256sum -c 99_evidence_sha256.txt
        echo 'M08_D3C_HARDWARE_FOUR_WORD_BRAM_READBACK_SUCCEEDED'
    else
        sha256sum 00_executed_source.tcl 01_jtag_run.log 02_jtag_run.jou \
          03_exit.txt > 99_evidence_sha256.txt
        echo 'M08_D3C_HW_STOP_NO_RETRY: preserve logs, inspect UART/JTAG/clock' >&2
        exit 3
    fi
)
echo "M08_D3C_HARDWARE_RESULT_DIR=$TEST"
