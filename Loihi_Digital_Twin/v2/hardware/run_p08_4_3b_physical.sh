#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
EXPECTED_BIT_SHA="3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83"
EXPECTED_LTX_SHA="e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936"

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
VECTOR_FILE="$BUILD_DIR/p08_4_3b_physical_vectors.tcl"
MANIFEST_FILE="$BUILD_DIR/p08_4_3b_physical_manifest.json"
RESULT_FILE="$BUILD_DIR/p08_4_3b_physical_result.txt"
RAW_LOG="$BUILD_DIR/p08_4_3b_physical.log"
TCL_SCRIPT="$SCRIPT_DIR/p08_4_3b_physical_conformance.tcl"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado/Vitis 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    vivado -version >&2 || true
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
    "$CONFORMANCE_DIR/compiled_execution_conformance_manifest.json" \
    "$CONFORMANCE_DIR/compiled_execution_conformance_vectors.npz"; do
    [[ -f "$path" ]] || {
        echo "ERROR: required accepted P08 artifact missing: $path" >&2
        exit 3
    }
done

ACTUAL_BIT_SHA="$(sha256sum "$BIT_FILE" | awk '{print $1}')"
ACTUAL_LTX_SHA="$(sha256sum "$LTX_FILE" | awk '{print $1}')"
[[ "$ACTUAL_BIT_SHA" == "$EXPECTED_BIT_SHA" ]] || {
    echo "ERROR: P08.4.3b bitstream identity drifted" >&2
    echo "expected=$EXPECTED_BIT_SHA" >&2
    echo "actual=$ACTUAL_BIT_SHA" >&2
    exit 4
}
[[ "$ACTUAL_LTX_SHA" == "$EXPECTED_LTX_SHA" ]] || {
    echo "ERROR: P08.4.3b debug-probe identity drifted" >&2
    echo "expected=$EXPECTED_LTX_SHA" >&2
    echo "actual=$ACTUAL_LTX_SHA" >&2
    exit 4
}

echo "PASS: P08.4.3b frozen physical shell bitstream_sha256=$ACTUAL_BIT_SHA probes_sha256=$ACTUAL_LTX_SHA"

export PYTHONPATH="$PROJECT_DIR/src:$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO_DIR"

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/physical_conformance.py
python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_p08_4_physical_conformance.py \
    applications/mnist_v2_nxtf/tests/test_p08_4_compiled_execution_conformance.py \
    Loihi_Digital_Twin/v2/tests/test_p08_paging.py

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

python -m mnist_v2_nxtf.physical_conformance \
    --conversion-dir "$CONVERSION_DIR" \
    --conformance-dir "$CONFORMANCE_DIR" \
    --output-dir "$BUILD_DIR"

P08_4_3B_MANIFEST="$MANIFEST_FILE" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from mnist_v2_nxtf.physical_conformance import (
    EXPECTED_FINAL_EVIDENCE,
    EXPECTED_PREDICTION,
    INGRESS_NAME,
    OUTPUT_NAME,
    PHYSICAL_SCHEMA,
    PHYSICAL_SLOT,
    PHYSICAL_TIMESTEP,
)
from mnist_v2_nxtf.source_recovered_validation import (
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
)

path = Path(os.environ["P08_4_3B_MANIFEST"])
manifest = json.loads(path.read_text(encoding="utf-8"))
required = {
    "schema": PHYSICAL_SCHEMA,
    "status": "P08_4_3B_PHYSICAL_REVIEW_PENDING",
    "representative_test_index": 0,
    "representative_label": 7,
    "physical_timestep": PHYSICAL_TIMESTEP,
    "physical_slot": PHYSICAL_SLOT,
    "dispatch_sequence": [INGRESS_NAME, OUTPUT_NAME, INGRESS_NAME],
    "physical_dispatch_count": 3,
    "physical_page_replacements": 2,
    "reload_exercised": True,
    "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
    "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    "expected_final_evidence": list(EXPECTED_FINAL_EVIDENCE),
    "expected_prediction": EXPECTED_PREDICTION,
    "logical_core_count": 5,
    "resident_context_count": 3,
    "physical_engine_count": 1,
    "official_test_used_for_physical_conformance": True,
    "model_or_conversion_selection_after_test": False,
}
for key, expected in required.items():
    if manifest.get(key) != expected:
        raise SystemExit(
            f"ERROR: P08.4.3b physical manifest {key}={manifest.get(key)!r}, expected {expected!r}"
        )

ids = {int(item["logical_core_id"]) for item in manifest["contexts"]}
if ids != {0, 4}:
    raise SystemExit(f"ERROR: P08.4.3b physical contexts drifted: {sorted(ids)}")

payload = dict(manifest)
recorded = payload.pop("manifest_fingerprint", None)
recomputed = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recorded != recomputed:
    raise SystemExit("ERROR: P08.4.3b physical manifest fingerprint does not recompute")

print(
    "PASS: P08.4.3b corpus gate "
    f"timestep={manifest['physical_timestep']} slot={manifest['physical_slot']} "
    f"sequence={manifest['dispatch_sequence']}"
)
print(
    "PASS: P08.4.3b corpus evidence "
    f"prediction={manifest['expected_prediction']} evidence={manifest['expected_final_evidence']}"
)
PY

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$VECTOR_FILE" "$RESULT_FILE" "$HW_SERVER_URL" \
    2>&1 | tee "$RAW_LOG"

[[ -f "$RESULT_FILE" ]] || {
    echo "ERROR: P08.4.3b physical harness did not produce $RESULT_FILE" >&2
    exit 5
}
grep -q '^result=PASS$' "$RESULT_FILE" || {
    echo "ERROR: P08.4.3b physical result is not PASS" >&2
    cat "$RESULT_FILE" >&2
    exit 5
}

P08_4_3B_RESULT="$RESULT_FILE" python - <<'PY'
from __future__ import annotations

import os
from pathlib import Path

from mnist_v2_nxtf.physical_conformance import EXPECTED_FINAL_EVIDENCE, EXPECTED_PREDICTION
from mnist_v2_nxtf.source_recovered_validation import (
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
)

path = Path(os.environ["P08_4_3B_RESULT"])
lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
kv = {}
dispatches = []
for line in lines:
    if line.startswith("dispatch="):
        dispatches.append(line)
    elif "=" in line:
        key, value = line.split("=", 1)
        kv[key] = value

if kv.get("result") != "PASS":
    raise SystemExit("ERROR: P08.4.3b result is not PASS")
if len(dispatches) != 3:
    raise SystemExit(f"ERROR: P08.4.3b expected 3 dispatch records, got {len(dispatches)}")
if kv.get("parameter_fingerprint") != ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT:
    raise SystemExit("ERROR: P08.4.3b parameter identity drifted")
if kv.get("network_fingerprint") != ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT:
    raise SystemExit("ERROR: P08.4.3b network identity drifted")
if kv.get("compiled_fingerprint") != ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT:
    raise SystemExit("ERROR: P08.4.3b compiled identity drifted")
if int(kv.get("prediction", "-1")) != EXPECTED_PREDICTION:
    raise SystemExit("ERROR: P08.4.3b physical prediction drifted")
actual_evidence = tuple(int(value) for value in kv.get("evidence", "").split())
if actual_evidence != EXPECTED_FINAL_EVIDENCE:
    raise SystemExit(
        f"ERROR: P08.4.3b physical evidence drifted: {actual_evidence} != {EXPECTED_FINAL_EVIDENCE}"
    )
if kv.get("context_reload_exact") != "1":
    raise SystemExit("ERROR: P08.4.3b did not record exact context reload")
if kv.get("page_replacements") != "2":
    raise SystemExit("ERROR: P08.4.3b page replacement count drifted")
if kv.get("model_or_conversion_selection_after_test") != "0":
    raise SystemExit("ERROR: P08.4.3b test-use boundary drifted")

print(
    "PASS: P08.4.3b result gate "
    f"dispatches={len(dispatches)} replacements={kv['page_replacements']} reload_exact=true"
)
print(
    "PASS: P08.4.3b physical evidence gate "
    f"prediction={kv['prediction']} evidence={list(actual_evidence)} exact_match=true"
)
PY

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="$SCRIPT_DIR/evidence/p08_4_3b_physical_${STAMP}"
mkdir -p "$EVIDENCE_DIR"
cp "$RESULT_FILE" "$EVIDENCE_DIR/"
cp "$RAW_LOG" "$EVIDENCE_DIR/"
cp "$VECTOR_FILE" "$EVIDENCE_DIR/"
cp "$MANIFEST_FILE" "$EVIDENCE_DIR/"
for report in \
    p08_post_route_metrics.txt \
    timing_summary_post_route.rpt \
    utilization_post_route.rpt \
    bus_skew_post_route.rpt \
    drc_post_route.rpt \
    methodology_post_route.rpt; do
    if [[ -f "$P08_REPORT_DIR/$report" ]]; then
        cp "$P08_REPORT_DIR/$report" "$EVIDENCE_DIR/"
    fi
done
{
    printf 'bitstream=%s\n' "$BIT_FILE"
    printf 'debug_probes=%s\n' "$LTX_FILE"
    printf 'physical_manifest=%s\n' "$MANIFEST_FILE"
    printf 'p08_4_2_conformance=%s\n' "$CONFORMANCE_DIR"
    sha256sum "$BIT_FILE" "$LTX_FILE" "$MANIFEST_FILE" "$VECTOR_FILE" "$RESULT_FILE"
} > "$EVIDENCE_DIR/artifact_sha256.txt"

echo
echo '=== P08.4.3b physical result ==='
cat "$RESULT_FILE"
echo
echo "P08.4.3b representative K26 physical conformance gate completed successfully."
echo "Build evidence: $BUILD_DIR"
echo "Archived evidence: $EVIDENCE_DIR"
