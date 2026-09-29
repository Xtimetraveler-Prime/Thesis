#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_DIR/vivado/build/p04_impl/reports"
BIT_FILE="${P04_BIT_FILE:-$REPORT_DIR/p04_two_core.bit}"
LTX_FILE="${P04_LTX_FILE:-$REPORT_DIR/p04_two_core.ltx}"
HW_SERVER_URL="${HW_SERVER_URL:-localhost:3121}"
BUILD_DIR="$SCRIPT_DIR/build/p04_physical"
VECTOR_FILE="$BUILD_DIR/p04_physical_vectors.tcl"
RESULT_FILE="$BUILD_DIR/p04_physical_result.txt"
TCL_SCRIPT="$SCRIPT_DIR/p04_physical_conformance.tcl"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi
command -v python3 >/dev/null 2>&1 || {
    echo "ERROR: python3 is not on PATH" >&2
    exit 2
}

for artifact in "$BIT_FILE" "$LTX_FILE"; do
    [[ -f "$artifact" ]] || {
        echo "ERROR: required P04 hardware artifact missing: $artifact" >&2
        echo "Run vivado/run_p04_impl.sh successfully first." >&2
        exit 3
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p04_physical_vectors.py" \
    --output "$VECTOR_FILE"

printf 'P04 physical bitstream: %s\n' "$BIT_FILE"
printf 'P04 physical probes: %s\n' "$LTX_FILE"
printf 'P04 hardware server: %s\n' "$HW_SERVER_URL"

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$VECTOR_FILE" "$RESULT_FILE" "$HW_SERVER_URL" \
    2>&1 | tee "$BUILD_DIR/p04_physical.log"

[[ -f "$RESULT_FILE" ]] || {
    echo "ERROR: P04 physical run did not produce $RESULT_FILE" >&2
    exit 4
}
grep -q '^result=PASS$' "$RESULT_FILE" || {
    echo "ERROR: P04 physical result is not PASS" >&2
    cat "$RESULT_FILE" >&2
    exit 5
}

echo
echo '=== P04 physical result ==='
cat "$RESULT_FILE"
echo
echo "P04 physical conformance gate completed successfully."
echo "Evidence: $BUILD_DIR"
