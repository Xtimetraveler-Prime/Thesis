#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_DIR/vivado/build/p05_impl/reports"
BIT_FILE="${P05_BIT_FILE:-$REPORT_DIR/p05_virtualized.bit}"
LTX_FILE="${P05_LTX_FILE:-$REPORT_DIR/p05_virtualized.ltx}"
HW_SERVER_URL="${HW_SERVER_URL:-localhost:3121}"
BUILD_DIR="$SCRIPT_DIR/build/p05_physical"
VECTOR_FILE="$BUILD_DIR/p05_physical_vectors.tcl"
RESULT_FILE="$BUILD_DIR/p05_physical_result.txt"
TCL_SCRIPT="$SCRIPT_DIR/p05_physical_conformance.tcl"

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
command -v sha256sum >/dev/null 2>&1 || {
    echo "ERROR: sha256sum is not on PATH" >&2
    exit 2
}

for artifact in "$BIT_FILE" "$LTX_FILE"; do
    [[ -f "$artifact" ]] || {
        echo "ERROR: required P05 hardware artifact missing: $artifact" >&2
        echo "Run vivado/run_p05_impl.sh successfully first." >&2
        exit 3
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p05_physical_vectors.py" \
    --output "$VECTOR_FILE"

printf 'P05 physical bitstream: %s\n' "$BIT_FILE"
printf 'P05 physical probes: %s\n' "$LTX_FILE"
printf 'P05 hardware server: %s\n' "$HW_SERVER_URL"

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$VECTOR_FILE" "$RESULT_FILE" "$HW_SERVER_URL" \
    2>&1 | tee "$BUILD_DIR/p05_physical.log"

[[ -f "$RESULT_FILE" ]] || {
    echo "ERROR: P05 physical run did not produce $RESULT_FILE" >&2
    exit 4
}
grep -q '^result=PASS$' "$RESULT_FILE" || {
    echo "ERROR: P05 physical result is not PASS" >&2
    cat "$RESULT_FILE" >&2
    exit 5
}

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="$SCRIPT_DIR/evidence/p05_physical_${STAMP}"
mkdir -p "$EVIDENCE_DIR"
cp "$RESULT_FILE" "$EVIDENCE_DIR/"
cp "$BUILD_DIR/p05_physical.log" "$EVIDENCE_DIR/"
cp "$VECTOR_FILE" "$EVIDENCE_DIR/"
for report in \
    p05_post_route_metrics.txt \
    timing_summary_post_route.rpt \
    utilization_post_route.rpt \
    utilization_hierarchical_post_route.rpt \
    memory_primitives_post_route.rpt \
    bus_skew_post_route.rpt \
    drc_post_route.rpt \
    methodology_post_route.rpt; do
    if [[ -f "$REPORT_DIR/$report" ]]; then
        cp "$REPORT_DIR/$report" "$EVIDENCE_DIR/"
    fi
done
{
    printf 'bitstream=%s\n' "$BIT_FILE"
    printf 'debug_probes=%s\n' "$LTX_FILE"
    sha256sum "$BIT_FILE" "$LTX_FILE"
} > "$EVIDENCE_DIR/artifact_sha256.txt"

echo
echo '=== P05 physical result ==='
cat "$RESULT_FILE"
echo
echo "P05 physical virtualization conformance gate completed successfully."
echo "Build evidence: $BUILD_DIR"
echo "Archived evidence: $EVIDENCE_DIR"
