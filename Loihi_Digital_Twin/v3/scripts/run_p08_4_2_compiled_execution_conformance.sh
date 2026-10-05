#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
CONVERSION_DIR="$ARTIFACT_ROOT/p08_3_5c_source_recovered_conversion"
OFFICIAL_TEST_DIR="$ARTIFACT_ROOT/p08_4_1_official_test"
OFFICIAL_TEST_MANIFEST="$OFFICIAL_TEST_DIR/official_test_evaluation_manifest.json"
FINAL_DIR="$ARTIFACT_ROOT/p08_4_2_compiled_execution_conformance"
CANDIDATE_DIR="$ARTIFACT_ROOT/.p08_4_2_compiled_execution_conformance_candidate"

export PYTHONPATH="$PROJECT_DIR/src:$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO_DIR"

python - <<'PY'
missing = []
for module in ("numpy", "pytest", "tensorflow"):
    try:
        __import__(module)
    except ImportError:
        missing.append(module)
if missing:
    raise SystemExit(
        "ERROR: P08.4.2 requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/accepted_official_test.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/compiled_execution_conformance.py

python -m pytest -q \
    Loihi_Digital_Twin/v2/tests/test_p08_paging.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_recovered_conversion.py \
    applications/mnist_v2_nxtf/tests/test_p08_4_official_test_evaluation.py \
    applications/mnist_v2_nxtf/tests/test_p08_4_compiled_execution_conformance.py

if [[ ! -f "$OFFICIAL_TEST_MANIFEST" ]]; then
    echo "ERROR: accepted P08.4.1 official-test manifest is missing: $OFFICIAL_TEST_MANIFEST" >&2
    exit 1
fi

P08_4_1_MANIFEST="$OFFICIAL_TEST_MANIFEST" python - <<'PY'
import os
from mnist_v2_nxtf.accepted_official_test import validate_accepted_official_test_manifest

manifest = validate_accepted_official_test_manifest(os.environ["P08_4_1_MANIFEST"])
print(
    "PASS: P08.4.2 accepted P08.4.1 binding "
    f"ann={float(manifest['ann_accuracy']):.6f} "
    f"snn={float(manifest['snn_accuracy']):.6f} "
    "selection_decisions_after_test=0"
)
PY

for path in \
    "$CONVERSION_DIR/source_recovered_conversion_manifest.json" \
    "$CONVERSION_DIR/source_recovered_parameters.npz" \
    "$CONVERSION_DIR/source_recovered_compiled_deployment.json"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required accepted P08.3.5c artifact is missing: $path" >&2
        exit 1
    fi
done

rm -rf "$CANDIDATE_DIR"
mkdir -p "$CANDIDATE_DIR"

python -m mnist_v2_nxtf.compiled_execution_conformance \
    --conversion-dir "$CONVERSION_DIR" \
    --output-dir "$CANDIDATE_DIR"

P08_4_2_DIR="$CANDIDATE_DIR" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from mnist_v2_nxtf.compiled_execution_conformance import (
    CONFORMANCE_MANIFEST,
    CONFORMANCE_SCHEMA,
    CONFORMANCE_TIMESTEPS,
    CONFORMANCE_VECTORS,
    REPRESENTATIVE_SELECTION_RULE,
    REPRESENTATIVE_TEST_INDEX,
)
from mnist_v2_nxtf.source_recovered_validation import (
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
)

root = Path(os.environ["P08_4_2_DIR"])
manifest_path = root / CONFORMANCE_MANIFEST
vectors_path = root / CONFORMANCE_VECTORS
for path in (manifest_path, vectors_path):
    if not path.is_file():
        raise SystemExit(f"ERROR: P08.4.2 missing artifact: {path}")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
required = {
    "schema": CONFORMANCE_SCHEMA,
    "status": "P08_4_2_COMPILED_EXECUTION_REVIEW_PENDING",
    "representative_test_index": REPRESENTATIVE_TEST_INDEX,
    "representative_selection_rule": REPRESENTATIVE_SELECTION_RULE,
    "timesteps": CONFORMANCE_TIMESTEPS,
    "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
    "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    "logical_core_count": 5,
    "resident_context_count": 3,
    "physical_engine_count": 1,
    "normalized_trace_invariant": True,
    "compiled_evidence_matches_source_simulator": True,
    "official_test_used_for_conformance": True,
    "model_or_conversion_selection_after_test": False,
}
for key, expected in required.items():
    if manifest.get(key) != expected:
        raise SystemExit(
            f"ERROR: P08.4.2 manifest {key}={manifest.get(key)!r}, expected {expected!r}"
        )

runs = {item["mode"]: item for item in manifest["runs"]}
if set(runs) != {"unpaged_reference", "paged_forward", "paged_reverse"}:
    raise SystemExit("ERROR: P08.4.2 execution modes drifted")
trace_ids = {item["trace_fingerprint"] for item in runs.values()}
if len(trace_ids) != 1:
    raise SystemExit("ERROR: normalized trace differs across legal execution orders")
expected_evidence = manifest["vector_final_evidence"]
for name, item in runs.items():
    if item["final_evidence"] != expected_evidence:
        raise SystemExit(f"ERROR: {name} final evidence differs from source simulator")
    if int(item["prediction"]) != int(manifest["vector_prediction"]):
        raise SystemExit(f"ERROR: {name} prediction differs from source simulator")
for name in ("paged_forward", "paged_reverse"):
    if int(runs[name]["page_loads"]) <= 0 or int(runs[name]["evictions"]) <= 0:
        raise SystemExit(f"ERROR: {name} did not exercise paging")

with np.load(vectors_path, allow_pickle=False) as vectors:
    if tuple(vectors["input_spikes"].shape) != (100, 784):
        raise SystemExit("ERROR: saved input-spike schedule shape drifted")
    if vectors["vector_evidence"].tolist() != expected_evidence:
        raise SystemExit("ERROR: saved vector evidence differs from manifest")

payload = dict(manifest)
recorded = payload.pop("manifest_fingerprint", None)
recomputed = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recorded != recomputed:
    raise SystemExit("ERROR: P08.4.2 manifest fingerprint does not recompute")

print(
    "PASS: P08.4.2 gate exact conformance "
    f"prediction={manifest['vector_prediction']} "
    f"trace={next(iter(trace_ids))} evidence_match=true"
)
print(
    "PASS: P08.4.2 gate paging "
    f"forward_loads={runs['paged_forward']['page_loads']} "
    f"reverse_loads={runs['paged_reverse']['page_loads']} "
    "logical_cores=5 resident_contexts=3 physical_engines=1"
)
print(
    "PASS: P08.4.2 gate identities "
    f"parameters={manifest['parameter_fingerprint']} "
    f"network={manifest['network_fingerprint']} compiled={manifest['compiled_fingerprint']}"
)
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_DIR" "$FINAL_DIR"

echo
echo "P08.4.2 exact compiled execution conformance gate completed successfully."
echo "Accepted candidate artifacts are in: $FINAL_DIR"
echo "The representative test frame was fixed by index; no model/conversion selection followed P08.4.1."
