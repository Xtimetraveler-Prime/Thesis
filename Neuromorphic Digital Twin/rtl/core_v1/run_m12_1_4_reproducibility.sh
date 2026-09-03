#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
M12_1_3_RUNNER="$SCRIPT_DIR/run_m12_1_3_hardware_capture.sh"
M12_1_3_BUILD="$SCRIPT_DIR/build/m12_1_3"
M12_1_3_TRACE="$M12_1_3_BUILD/captures/m11_5_4_recurrent_chain_physical_trace_v1.json"
M12_1_3_LOG="$M12_1_3_BUILD/m12_1_3_hardware_capture.log"
CLOSURE_DIR="$SCRIPT_DIR/build/m12_1_4"
CAPTURE_A="$CLOSURE_DIR/m11_5_4_recurrent_chain_physical_trace_v1_run_a.json"
CAPTURE_B="$CLOSURE_DIR/m11_5_4_recurrent_chain_physical_trace_v1_run_b.json"
LOG_A="$CLOSURE_DIR/m12_1_4_run_a.log"
LOG_B="$CLOSURE_DIR/m12_1_4_run_b.log"
COMPARE="$PROJECT_DIR/examples/compare_m12_1_4_physical_captures.py"

for path in "$M12_1_3_RUNNER" "$COMPARE"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.1.4 input is missing: $path" >&2
        exit 2
    fi
done

mkdir -p "$CLOSURE_DIR"
rm -f "$CAPTURE_A" "$CAPTURE_B" "$LOG_A" "$LOG_B"

echo '=== M12.1.4 physical trace reproducibility closure ==='
echo 'This performs two independent program/reset/capture runs using the accepted M12.1.3 path.'
echo 'Keep the K26 powered and visible to Vivado; unload any stock Kria PL application first.'

echo
echo '--- M12.1.4 physical run A ---'
bash "$M12_1_3_RUNNER"
if [[ ! -s "$M12_1_3_TRACE" || ! -s "$M12_1_3_LOG" ]]; then
    echo 'ERROR: M12.1.3 run A did not leave its validated trace/log artifacts.' >&2
    exit 3
fi
cp -- "$M12_1_3_TRACE" "$CAPTURE_A"
cp -- "$M12_1_3_LOG" "$LOG_A"

echo
echo '--- M12.1.4 physical run B ---'
bash "$M12_1_3_RUNNER"
if [[ ! -s "$M12_1_3_TRACE" || ! -s "$M12_1_3_LOG" ]]; then
    echo 'ERROR: M12.1.3 run B did not leave its validated trace/log artifacts.' >&2
    exit 3
fi
cp -- "$M12_1_3_TRACE" "$CAPTURE_B"
cp -- "$M12_1_3_LOG" "$LOG_B"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$COMPARE" "$CAPTURE_A" "$CAPTURE_B"

echo
echo 'M12.1.4 repeated physical capture closure completed successfully.'
printf 'Capture A: %s\n' "$CAPTURE_A"
printf 'Capture B: %s\n' "$CAPTURE_B"
printf 'Run A log: %s\n' "$LOG_A"
printf 'Run B log: %s\n' "$LOG_B"
