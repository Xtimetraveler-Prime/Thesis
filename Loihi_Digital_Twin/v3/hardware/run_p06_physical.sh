#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
P05_REPORT_DIR="$PROJECT_DIR/vivado/build/p05_impl/reports"
BIT_FILE="${P06_BIT_FILE:-$P05_REPORT_DIR/p05_virtualized.bit}"
LTX_FILE="${P06_LTX_FILE:-$P05_REPORT_DIR/p05_virtualized.ltx}"
HW_SERVER_URL="${HW_SERVER_URL:-localhost:3121}"
BUILD_DIR="$SCRIPT_DIR/build/p06_physical"
NETWORK_FILE="$BUILD_DIR/network.json"
DEPLOYMENT_FILE="$BUILD_DIR/deployment.json"
REPORT_FILE="$BUILD_DIR/mapping_report.json"
FPGA_REPORT_FILE="$BUILD_DIR/fpga_report.json"
VECTOR_FILE="$BUILD_DIR/p06_physical_vectors.tcl"
RESULT_FILE="$BUILD_DIR/p06_physical_result.txt"
TCL_SCRIPT="$SCRIPT_DIR/p06_physical_conformance.tcl"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi
command -v sha256sum >/dev/null 2>&1 || {
    echo "ERROR: sha256sum is not on PATH" >&2
    exit 2
}
for artifact in "$BIT_FILE" "$LTX_FILE"; do
    [[ -f "$artifact" ]] || {
        echo "ERROR: required accepted P05 hardware artifact missing: $artifact" >&2
        echo "Run the accepted P05 implementation flow or set P06_BIT_FILE/P06_LTX_FILE." >&2
        exit 3
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p06_demo_network.py" \
    --output "$NETWORK_FILE"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/scripts/compile_p06.py" \
    "$NETWORK_FILE" \
    --output "$DEPLOYMENT_FILE" \
    --report "$REPORT_FILE" \
    --fpga-report "$FPGA_REPORT_FILE" \
    --compartments-per-core 2

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p06_physical_vectors.py" \
    "$DEPLOYMENT_FILE" \
    --output "$VECTOR_FILE"

printf 'P06 physical bitstream (accepted P05 shell): %s\n' "$BIT_FILE"
printf 'P06 physical probes: %s\n' "$LTX_FILE"
printf 'P06 compiled deployment: %s\n' "$DEPLOYMENT_FILE"
printf 'P06 hardware server: %s\n' "$HW_SERVER_URL"

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$VECTOR_FILE" "$RESULT_FILE" "$HW_SERVER_URL" \
    2>&1 | tee "$BUILD_DIR/p06_physical.log"

[[ -f "$RESULT_FILE" ]] || {
    echo "ERROR: P06 physical run did not produce $RESULT_FILE" >&2
    exit 4
}
grep -q '^result=PASS$' "$RESULT_FILE" || {
    echo "ERROR: P06 physical result is not PASS" >&2
    cat "$RESULT_FILE" >&2
    exit 5
}

DEPLOYMENT_FINGERPRINT="$(
    PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python3 - "$DEPLOYMENT_FILE" <<'PY'
from loihi_twin_v2 import CompiledDeployment
import sys
print(CompiledDeployment.read_json(sys.argv[1]).fingerprint)
PY
)"
if ! grep -q "^deployment_fingerprint=${DEPLOYMENT_FINGERPRINT}$" "$RESULT_FILE"; then
    echo "ERROR: P06 physical result fingerprint does not match compiled deployment" >&2
    exit 6
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="$SCRIPT_DIR/evidence/p06_physical_${STAMP}"
mkdir -p "$EVIDENCE_DIR"
cp "$RESULT_FILE" "$EVIDENCE_DIR/"
cp "$BUILD_DIR/p06_physical.log" "$EVIDENCE_DIR/"
cp "$NETWORK_FILE" "$EVIDENCE_DIR/"
cp "$DEPLOYMENT_FILE" "$EVIDENCE_DIR/"
cp "$REPORT_FILE" "$EVIDENCE_DIR/"
cp "$FPGA_REPORT_FILE" "$EVIDENCE_DIR/"
cp "$VECTOR_FILE" "$EVIDENCE_DIR/"
for report in \
    p05_post_route_metrics.txt \
    timing_summary_post_route.rpt \
    utilization_post_route.rpt \
    bus_skew_post_route.rpt \
    drc_post_route.rpt \
    methodology_post_route.rpt; do
    if [[ -f "$P05_REPORT_DIR/$report" ]]; then
        cp "$P05_REPORT_DIR/$report" "$EVIDENCE_DIR/"
    fi
done
{
    printf 'bitstream=%s\n' "$BIT_FILE"
    printf 'debug_probes=%s\n' "$LTX_FILE"
    printf 'compiled_deployment=%s\n' "$DEPLOYMENT_FILE"
    sha256sum "$BIT_FILE" "$LTX_FILE" "$DEPLOYMENT_FILE" "$NETWORK_FILE"
} > "$EVIDENCE_DIR/artifact_sha256.txt"

echo
echo '=== P06 physical result ==='
cat "$RESULT_FILE"
echo
echo "P06 mapped-deployment physical conformance gate completed successfully."
echo "Build evidence: $BUILD_DIR"
echo "Archived evidence: $EVIDENCE_DIR"
