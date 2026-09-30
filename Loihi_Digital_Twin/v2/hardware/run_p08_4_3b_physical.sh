#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_BIT_SHA="3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83"
EXPECTED_LTX_SHA="e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936"
EXPECTED_COMPILED="5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
CONVERSION_DIR="$ARTIFACT_ROOT/p08_3_5c_source_recovered_conversion"
CONFORMANCE_DIR="$ARTIFACT_ROOT/p08_4_2_compiled_execution_conformance"
P08_REPORT_DIR="$PROJECT_DIR/vivado/build/p08_impl/reports"
BIT_FILE="${P08_4_3B_BIT_FILE:-$P08_REPORT_DIR/p08_host_paged.bit}"
LTX_FILE="${P08_4_3B_LTX_FILE:-$P08_REPORT_DIR/p08_host_paged.ltx}"
HW_SERVER_URL="${HW_SERVER_URL:-localhost:3121}"
BUILD_DIR="$SCRIPT_DIR/build/p08_4_3b_physical"
VECTOR_FILE="$BUILD_DIR/p08_4_3b_vectors.tcl"
VECTOR_SUMMARY="$BUILD_DIR/p08_4_3b_vector_summary.json"
RESULT_FILE="$BUILD_DIR/p08_4_3b_physical_result.txt"
RAW_LOG="$BUILD_DIR/p08_4_3b_physical.log"
TCL_SCRIPT="$SCRIPT_DIR/p08_4_3b_physical_conformance.tcl"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado/Vitis 2025.2 settings64.sh first." >&2
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
for path in "$BIT_FILE" "$LTX_FILE" "$TCL_SCRIPT"; do
    [[ -f "$path" ]] || {
        echo "ERROR: required P08.4.3b physical input missing: $path" >&2
        exit 3
    }
done
for path in \
    "$CONVERSION_DIR/source_recovered_compiled_deployment.json" \
    "$CONFORMANCE_DIR/compiled_execution_conformance_manifest.json"; do
    [[ -f "$path" ]] || {
        echo "ERROR: required accepted P08 artifact missing: $path" >&2
        exit 3
    }
done

actual_bit_sha="$(sha256sum "$BIT_FILE" | awk '{print $1}')"
actual_ltx_sha="$(sha256sum "$LTX_FILE" | awk '{print $1}')"
[[ "$actual_bit_sha" == "$EXPECTED_BIT_SHA" ]] || {
    echo "ERROR: P08.4.3a bitstream identity drifted: $actual_bit_sha" >&2
    exit 4
}
[[ "$actual_ltx_sha" == "$EXPECTED_LTX_SHA" ]] || {
    echo "ERROR: P08.4.3a probes identity drifted: $actual_ltx_sha" >&2
    exit 4
}
echo "PASS: P08.4.3b accepted shell bitstream_sha256=$actual_bit_sha probes_sha256=$actual_ltx_sha"

export PYTHONPATH="$PROJECT_DIR/src:$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO_DIR"
python - <<'PY'
missing = []
for module in ("numpy", "tensorflow"):
    try:
        __import__(module)
    except ImportError:
        missing.append(module)
if missing:
    raise SystemExit(
        "ERROR: P08.4.3b requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY
python -m py_compile applications/mnist_v2_nxtf/mnist_v2_nxtf/physical_conformance_vectors.py

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
python -m mnist_v2_nxtf.physical_conformance_vectors \
    --conversion-dir "$CONVERSION_DIR" \
    --conformance-dir "$CONFORMANCE_DIR" \
    --output "$VECTOR_FILE" \
    --summary "$VECTOR_SUMMARY"

P08B_VECTOR_SUMMARY="$VECTOR_SUMMARY" EXPECTED_COMPILED="$EXPECTED_COMPILED" python - <<'PY'
import json
import os
from pathlib import Path
summary = json.loads(Path(os.environ["P08B_VECTOR_SUMMARY"]).read_text(encoding="utf-8"))
required = {
    "schema": "p08-4-3b-physical-dispatch-vector-v1",
    "compiled_fingerprint": os.environ["EXPECTED_COMPILED"],
    "test_index": 0,
    "label": 7,
    "timestep": 99,
    "target_logical_core": 4,
    "resident_slot": 0,
    "decoy_logical_core": 0,
    "selection_decisions_after_test": 0,
}
for key, expected in required.items():
    if summary.get(key) != expected:
        raise SystemExit(f"ERROR: P08.4.3b vector {key}={summary.get(key)!r}, expected {expected!r}")
if summary.get("expected_evidence") != [-284, -1203, 104, 109, -2253, -599, -2659, 1446, -436, -63]:
    raise SystemExit("ERROR: P08.4.3b accepted evidence vector drifted")
if int(summary.get("event_count", -1)) < 0 or int(summary.get("event_count", 0)) > 4096:
    raise SystemExit("ERROR: P08.4.3b event count exceeds hardware contract")
print(
    "PASS: P08.4.3b frozen dispatch corpus "
    f"test_index={summary['test_index']} label={summary['label']} timestep={summary['timestep']} "
    f"logical_core={summary['target_logical_core']} events={summary['event_count']} "
    f"compartments={summary['compartment_count']} synapses={summary['synapse_count']} routes={summary['route_count']}"
)
PY

printf 'P08.4.3b bitstream: %s\n' "$BIT_FILE"
printf 'P08.4.3b probes: %s\n' "$LTX_FILE"
printf 'P08.4.3b hardware server: %s\n' "$HW_SERVER_URL"

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$VECTOR_FILE" "$RESULT_FILE" "$HW_SERVER_URL" \
    2>&1 | tee "$RAW_LOG"

[[ -f "$RESULT_FILE" ]] || {
    echo "ERROR: P08.4.3b hardware harness did not produce $RESULT_FILE" >&2
    exit 5
}
grep -q '^result=PASS$' "$RESULT_FILE" || {
    echo "ERROR: P08.4.3b physical result is not PASS" >&2
    cat "$RESULT_FILE" >&2
    exit 6
}
grep -q "^compiled_fingerprint=$EXPECTED_COMPILED$" "$RESULT_FILE" || {
    echo "ERROR: P08.4.3b physical result compiled identity drifted" >&2
    exit 6
}
for expected in \
    'test_index=0' \
    'label=7' \
    'timestep=99' \
    'resident_slot=0' \
    'evicted_logical_core=0' \
    'loaded_logical_core=4' \
    'state_trace_exact_match=1' \
    'packet_exact_match=1' \
    'evidence_exact_match=1' \
    'model_or_conversion_selection_after_test=0'; do
    grep -q "^${expected}$" "$RESULT_FILE" || {
        echo "ERROR: P08.4.3b result missing ${expected}" >&2
        exit 6
    }
done
grep -q '^evidence=-284 -1203 104 109 -2253 -599 -2659 1446 -436 -63$' "$RESULT_FILE" || {
    echo "ERROR: P08.4.3b physical evidence vector drifted" >&2
    exit 6
}

echo "PASS: P08.4.3b result exact state_trace=true packets=true evidence=true compiled=$EXPECTED_COMPILED"
echo "PASS: P08.4.3b physical evidence [-284,-1203,104,109,-2253,-599,-2659,1446,-436,-63] prediction=7"
echo "PASS: P08.4.3b test-use boundary selection_decisions_after_test=0"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="$SCRIPT_DIR/evidence/p08_4_3b_physical_${STAMP}"
mkdir -p "$EVIDENCE_DIR"
cp "$RESULT_FILE" "$RAW_LOG" "$VECTOR_FILE" "$VECTOR_SUMMARY" "$EVIDENCE_DIR/"
cp "$P08_REPORT_DIR/p08_post_route_metrics.txt" "$EVIDENCE_DIR/" 2>/dev/null || true
{
    printf 'bitstream=%s\n' "$BIT_FILE"
    printf 'debug_probes=%s\n' "$LTX_FILE"
    printf 'compiled_fingerprint=%s\n' "$EXPECTED_COMPILED"
    sha256sum "$BIT_FILE" "$LTX_FILE" "$VECTOR_FILE" "$VECTOR_SUMMARY"
} > "$EVIDENCE_DIR/artifact_sha256.txt"

echo
echo '=== P08.4.3b physical result ==='
cat "$RESULT_FILE"
echo
echo "P08.4.3b physical MNIST conformance gate completed successfully."
echo "Build evidence: $BUILD_DIR"
echo "Archived evidence: $EVIDENCE_DIR"
