#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m12_3"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
GOLDEN_DIR="$BUILD_DIR/golden"
CAPTURE_DIR="$BUILD_DIR/captures"
DIFF_DIR="$BUILD_DIR/differential_reports"
REPLAY_DIR="$BUILD_DIR/reset_replay"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_3.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_3.ltx"
METADATA="$GOLDEN_DIR/hardware_cases.tsv"
REPLAY_METADATA="$BUILD_DIR/reset_replay_case.tsv"
CAPTURE_TCL="$SCRIPT_DIR/vivado/capture_m12_3_multitick.tcl"
SUITE_VALIDATOR="$PROJECT_DIR/examples/validate_m12_3_physical_suite.py"
CASE_VALIDATOR="$PROJECT_DIR/examples/validate_m12_3_physical_case.py"
REPLAY_VALIDATOR="$PROJECT_DIR/examples/validate_m12_3_reset_replay.py"
LOG_FILE="$BUILD_DIR/m12_3_hardware_suite.log"
REPLAY_LOG="$BUILD_DIR/m12_3_reset_replay.log"
REPLAY_CASE_ID=2
REPLAY_CASE_NAME="two-neuron-recurrent-loop"

if ! command -v vivado >/dev/null 2>&1; then
    echo "ERROR: vivado is not on PATH. Source the Vivado 2025.2 settings64.sh first." >&2
    exit 2
fi
VIVADO_VERSION="$(vivado -version 2>&1 || true)"
if [[ "$VIVADO_VERSION" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: vivado is not reporting version $EXPECTED_VERSION." >&2
    echo "$VIVADO_VERSION" >&2
    exit 2
fi
for path in \
    "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_TCL" \
    "$SUITE_VALIDATOR" "$CASE_VALIDATOR" "$REPLAY_VALIDATOR"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.3 hardware-suite input is missing: $path" >&2
        echo "Run bash run_m12_3_bitstream.sh successfully first." >&2
        exit 3
    fi
done

rm -rf "$CAPTURE_DIR" "$DIFF_DIR" "$REPLAY_DIR"
mkdir -p "$CAPTURE_DIR" "$DIFF_DIR" "$REPLAY_DIR"

echo '=== M12.3 exact physical multi-tick/recurrent directed suite ==='
echo 'The board must be powered and visible to Vivado Hardware Manager, with PS pl_clk0 running.'
echo 'On stock Kria Linux, unload any active starter-kit PL application first if it owns the PL.'

vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_DIR" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M12.3 bitstream programmed successfully." \
    "M12.3 PL clock heartbeat advanced:" \
    "M12.3 local capture reset released through VIO." \
    "M12.3 captured physical case 9 complete:" \
    "M12.3 physical directed multi-tick suite capture completed successfully: cases=10 ticks=40"; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: physical run returned without expected M12.3 marker: $marker" >&2
        exit 4
    fi
done

mapfile -t physical_files < <(find "$CAPTURE_DIR" -maxdepth 1 -type f -name '*.physical.json' -print | sort)
if [[ "${#physical_files[@]}" -ne 10 ]]; then
    echo "ERROR: M12.3 expected 10 physical JSON artifacts; found ${#physical_files[@]}." >&2
    exit 4
fi

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$SUITE_VALIDATOR" \
    --physical-dir "$CAPTURE_DIR" \
    --report-dir "$DIFF_DIR"

if [[ ! -s "$DIFF_DIR/suite_report.json" ]]; then
    echo "ERROR: M12.3 suite differential report was not created." >&2
    exit 5
fi

# Reset/replay closure: execute the six-tick recurrent-loop anchor again through
# a separate Hardware Manager programming/reset session. The second run must
# independently match Python and reproduce the first run's typed tick sequence.
{
    head -n 1 "$METADATA"
    awk -F '\t' -v id="$REPLAY_CASE_ID" '$1 == id { print; found=1 } END { if (!found) exit 2 }' "$METADATA"
} > "$REPLAY_METADATA"

vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$REPLAY_METADATA" "$REPLAY_DIR" \
    2>&1 | tee "$REPLAY_LOG"

FIRST_REPLAY_ANCHOR="$CAPTURE_DIR/02-${REPLAY_CASE_NAME}.physical.json"
SECOND_REPLAY_ANCHOR="$REPLAY_DIR/02-${REPLAY_CASE_NAME}.physical.json"
REPLAY_CASE_REPORT="$DIFF_DIR/02-${REPLAY_CASE_NAME}.replay.report.json"
for path in "$FIRST_REPLAY_ANCHOR" "$SECOND_REPLAY_ANCHOR"; do
    if [[ ! -s "$path" ]]; then
        echo "ERROR: M12.3 reset/replay artifact missing: $path" >&2
        exit 6
    fi
done

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$CASE_VALIDATOR" \
    --case-id "$REPLAY_CASE_ID" \
    --physical "$SECOND_REPLAY_ANCHOR" \
    --report "$REPLAY_CASE_REPORT"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$REPLAY_VALIDATOR" \
    --first "$FIRST_REPLAY_ANCHOR" \
    --replay "$SECOND_REPLAY_ANCHOR"

echo
echo 'M12.3 physical multi-tick/recurrent suite completed successfully.'
printf 'Physical traces: %s\n' "$CAPTURE_DIR"
printf 'Differential reports: %s\n' "$DIFF_DIR"
printf 'Reset/replay trace: %s\n' "$SECOND_REPLAY_ANCHOR"
printf 'Hardware log: %s\n' "$LOG_FILE"
printf 'Reset/replay log: %s\n' "$REPLAY_LOG"
