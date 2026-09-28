#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m12_2"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
PROBE_DIR="$BUILD_DIR/case07_probe"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2.ltx"
CAPTURE_TCL="$SCRIPT_DIR/vivado/capture_m12_2_single_tick.tcl"
VALIDATOR="$PROJECT_DIR/examples/validate_m12_2_physical_case.py"
METADATA="$PROBE_DIR/case07_only.tsv"
PHYSICAL="$PROBE_DIR/07-threshold-over-refractory-entry.physical.json"
REPORT="$PROBE_DIR/07-threshold-over-refractory-entry.report.json"
LOG_FILE="$PROBE_DIR/case07_hardware.log"

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
for path in "$BIT_FILE" "$LTX_FILE" "$CAPTURE_TCL" "$VALIDATOR"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.2 case-07 probe input is missing: $path" >&2
        echo "Rebuild M12.2 first with: bash run_m12_2_bitstream.sh" >&2
        exit 3
    fi
done

rm -rf "$PROBE_DIR"
mkdir -p "$PROBE_DIR"
printf 'case_id\tcase_name\tneuron_count\n7\tthreshold-over-refractory-entry\t1\n' > "$METADATA"

echo '=== M12.2 targeted physical probe: case 07 only ==='
echo 'This programs the M12.2 bitstream and executes case 07 as the first/only case.'

vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$METADATA" "$PROBE_DIR" \
    2>&1 | tee "$LOG_FILE"

if [[ ! -s "$PHYSICAL" ]]; then
    echo "ERROR: targeted case-07 physical artifact was not created: $PHYSICAL" >&2
    exit 4
fi

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$VALIDATOR" \
    --case-id 7 \
    --physical "$PHYSICAL" \
    --report "$REPORT"

echo
echo 'M12.2 targeted case-07 physical probe completed successfully.'
printf 'Physical trace: %s\n' "$PHYSICAL"
printf 'Differential report: %s\n' "$REPORT"
printf 'Hardware log: %s\n' "$LOG_FILE"
