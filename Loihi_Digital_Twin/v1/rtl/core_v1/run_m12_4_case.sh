#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[0-9]+$ ]]; then
    echo "usage: $0 <case-id 0..21>" >&2
    exit 2
fi
CASE_ID="$1"
if (( CASE_ID < 0 || CASE_ID > 21 )); then
    echo "ERROR: M12.4 case ID must be in 0..21; got $CASE_ID" >&2
    exit 2
fi

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m12_4"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
GOLDEN_DIR="$BUILD_DIR/golden"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_4.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_4.ltx"
METADATA="$GOLDEN_DIR/hardware_cases.tsv"
CAPTURE_TCL="$SCRIPT_DIR/vivado/capture_m12_4_broad.tcl"
CASE_VALIDATOR="$PROJECT_DIR/examples/validate_m12_4_physical_case.py"
TARGET_DIR="$BUILD_DIR/targeted_case_$(printf '%02d' "$CASE_ID")"
TARGET_METADATA="$TARGET_DIR/hardware_case.tsv"
TARGET_CAPTURE_DIR="$TARGET_DIR/capture"
TARGET_REPORT="$TARGET_DIR/case.report.json"
TARGET_LOG="$TARGET_DIR/hardware.log"

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
for path in "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_TCL" "$CASE_VALIDATOR"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.4 targeted-case input is missing: $path" >&2
        echo "Run bash run_m12_4_bitstream.sh successfully first." >&2
        exit 3
    fi
done

rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_CAPTURE_DIR"
{
    head -n 1 "$METADATA"
    awk -F '\t' -v id="$CASE_ID" '$1 == id { print; found=1 } END { if (!found) exit 2 }' "$METADATA"
} > "$TARGET_METADATA"

CASE_NAME="$(awk -F '\t' 'NR==2 {print $2}' "$TARGET_METADATA")"
CASE_SEED="$(awk -F '\t' 'NR==2 {print $4}' "$TARGET_METADATA")"
CASE_HASH="$(awk -F '\t' 'NR==2 {print $5}' "$TARGET_METADATA")"
PHYSICAL="$TARGET_CAPTURE_DIR/$(printf '%02d' "$CASE_ID")-${CASE_NAME}.physical.json"

echo "=== M12.4 targeted physical case $CASE_ID: $CASE_NAME ==="
echo "seed=$CASE_SEED"
echo "configuration_sha256=$CASE_HASH"

vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$TARGET_METADATA" "$TARGET_CAPTURE_DIR" \
    2>&1 | tee "$TARGET_LOG"

if [[ ! -s "$PHYSICAL" ]]; then
    echo "ERROR: M12.4 targeted physical artifact was not produced: $PHYSICAL" >&2
    exit 4
fi

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$CASE_VALIDATOR" \
    --case-id "$CASE_ID" \
    --physical "$PHYSICAL" \
    --report "$TARGET_REPORT"

echo 'M12.4 targeted physical rerun completed successfully.'
printf 'Physical trace: %s\n' "$PHYSICAL"
printf 'Differential report: %s\n' "$TARGET_REPORT"
printf 'Hardware log: %s\n' "$TARGET_LOG"
