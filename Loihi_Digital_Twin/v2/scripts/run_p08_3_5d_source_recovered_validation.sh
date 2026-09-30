#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
CONVERSION_DIR="$ARTIFACT_ROOT/p08_3_5c_source_recovered_conversion"
FINAL_DIR="$ARTIFACT_ROOT/p08_3_5d_source_recovered_validation"
CANDIDATE_DIR="$ARTIFACT_ROOT/.p08_3_5d_source_recovered_validation_candidate"

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
        "ERROR: P08.3.5d requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/accepted_ann.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/source_backend_reconstruction.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/source_recovered_conversion.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/source_recovered_validation.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_backend_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_recovered_conversion.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_recovered_validation.py

if [[ ! -d "$CONVERSION_DIR" ]]; then
    echo "ERROR: accepted P08.3.5c conversion directory is missing: $CONVERSION_DIR" >&2
    exit 1
fi

for required in \
    source_recovered_conversion_manifest.json \
    source_recovered_parameters.npz \
    source_recovered_network.json \
    source_recovered_compiled_deployment.json; do
    if [[ ! -f "$CONVERSION_DIR/$required" ]]; then
        echo "ERROR: accepted P08.3.5c artifact is missing: $CONVERSION_DIR/$required" >&2
        exit 1
    fi
done

rm -rf "$CANDIDATE_DIR"
mkdir -p "$CANDIDATE_DIR"

python -m mnist_v2_nxtf.source_recovered_validation \
    --conversion-dir "$CONVERSION_DIR" \
    --output-dir "$CANDIDATE_DIR" \
    --batch-size 128

P08_3_5C_DIR="$CONVERSION_DIR" P08_3_5D_DIR="$CANDIDATE_DIR" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from loihi_twin_v2.compiler import CompiledDeployment, NetworkSpec
from mnist_v2_nxtf.source_recovered_conversion import (
    SOURCE_RECOVERED_COMPILED,
    SOURCE_RECOVERED_NETWORK,
)
from mnist_v2_nxtf.source_recovered_validation import (
    ACCEPTED_HIDDEN_THRESHOLDS,
    ACCEPTED_INPUT_THRESHOLD,
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
    VALIDATION_EXAMPLES,
    VALIDATION_MANIFEST,
    VALIDATION_RESULTS,
    VALIDATION_SCHEMA,
    VALIDATION_TIMESTEPS,
    _results_fingerprint,
)

conversion_root = Path(os.environ["P08_3_5C_DIR"])
root = Path(os.environ["P08_3_5D_DIR"])
manifest_path = root / VALIDATION_MANIFEST
results_path = root / VALIDATION_RESULTS
if not manifest_path.is_file():
    raise SystemExit(f"ERROR: P08.3.5d manifest is missing: {manifest_path}")
if not results_path.is_file():
    raise SystemExit(f"ERROR: P08.3.5d results are missing: {results_path}")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
required = {
    "schema": VALIDATION_SCHEMA,
    "status": "P08_3_5D_SOURCE_RECOVERED_VALIDATION_REVIEW_PENDING",
    "official_test_used": False,
    "test_examples_observed": 0,
    "validation_examples": VALIDATION_EXAMPLES,
    "timesteps": VALIDATION_TIMESTEPS,
    "input_scale": 255,
    "input_threshold": ACCEPTED_INPUT_THRESHOLD,
    "hidden_thresholds": list(ACCEPTED_HIDDEN_THRESHOLDS),
    "softmax_readout_mode": "final_membrane_voltage_argmax",
    "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
    "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    "accuracy_acceptance_threshold": None,
    "post_conversion_accuracy_tuning": False,
    "classification_accuracy_evaluated": True,
    "classification_selection_source": "frozen_validation_partition_measurement_only",
    "validation_input_scaling_scope": "full_5000_validation_corpus_once_before_batching",
}
for key, expected in required.items():
    if manifest.get(key) != expected:
        raise SystemExit(
            f"ERROR: P08.3.5d manifest {key}={manifest.get(key)!r}, expected {expected!r}"
        )

accuracy = float(manifest["accuracy"])
ann_reference = float(manifest["ann_validation_reference_accuracy"])
delta = float(manifest["ann_minus_snn_validation_accuracy"])
if not 0.0 <= accuracy <= 1.0:
    raise SystemExit(f"ERROR: invalid P08.3.5d accuracy {accuracy}")
if abs(ann_reference - 0.992600) > 5e-7:
    raise SystemExit(f"ERROR: accepted ANN validation reference drifted: {ann_reference}")
if abs((ann_reference - accuracy) - delta) > 1e-12:
    raise SystemExit("ERROR: ANN-minus-SNN validation delta does not recompute")
if int(manifest["correct"]) != round(accuracy * VALIDATION_EXAMPLES):
    raise SystemExit("ERROR: correct-count and validation accuracy disagree")

stage_totals = np.asarray(manifest["stage_total_spikes"], dtype=np.int64)
stage_active = np.asarray(manifest["stage_active_examples"], dtype=np.int64)
if stage_totals.shape != (4,) or stage_active.shape != (4,):
    raise SystemExit("ERROR: P08.3.5d stage activity shape drifted")
if np.any(stage_totals <= 0):
    raise SystemExit(f"ERROR: source-recovered activity died in a stage: {stage_totals.tolist()}")
if np.any(stage_active <= 0) or np.any(stage_active > VALIDATION_EXAMPLES):
    raise SystemExit(f"ERROR: invalid active-example counts: {stage_active.tolist()}")

with np.load(results_path, allow_pickle=False) as payload:
    labels = np.asarray(payload["labels"], dtype=np.int64)
    predictions = np.asarray(payload["predictions"], dtype=np.int64)
    evidence = np.asarray(payload["final_evidence"], dtype=np.int64)
    confusion = np.asarray(payload["confusion_matrix"], dtype=np.int64)
    class_accuracy = np.asarray(payload["class_accuracy"], dtype=np.float64)
    saved_totals = np.asarray(payload["stage_total_spikes"], dtype=np.int64)
    saved_active = np.asarray(payload["stage_active_examples"], dtype=np.int64)

if labels.shape != (VALIDATION_EXAMPLES,) or predictions.shape != (VALIDATION_EXAMPLES,):
    raise SystemExit("ERROR: P08.3.5d prediction array shape drifted")
if evidence.shape != (VALIDATION_EXAMPLES, 10):
    raise SystemExit(f"ERROR: P08.3.5d evidence shape drifted: {evidence.shape}")
if confusion.shape != (10, 10) or int(confusion.sum()) != VALIDATION_EXAMPLES:
    raise SystemExit("ERROR: P08.3.5d confusion matrix is incomplete")
if class_accuracy.shape != (10,) or np.any(~np.isfinite(class_accuracy)):
    raise SystemExit("ERROR: P08.3.5d class-accuracy vector is invalid")
if not np.array_equal(saved_totals, stage_totals) or not np.array_equal(saved_active, stage_active):
    raise SystemExit("ERROR: P08.3.5d activity manifest/result arrays disagree")

observed_accuracy = float(np.count_nonzero(labels == predictions) / VALIDATION_EXAMPLES)
if abs(observed_accuracy - accuracy) > 1e-12:
    raise SystemExit("ERROR: P08.3.5d stored predictions do not reproduce accuracy")
if _results_fingerprint(labels, predictions) != manifest["prediction_fingerprint"]:
    raise SystemExit("ERROR: P08.3.5d prediction fingerprint does not recompute")
if _results_fingerprint(evidence) != manifest["evidence_fingerprint"]:
    raise SystemExit("ERROR: P08.3.5d evidence fingerprint does not recompute")

# Re-verify that the exact compiled artifact evaluated above is the accepted
# P08.3.5c graph, not merely a manifest claiming those identities.
network = NetworkSpec.read_json(conversion_root / SOURCE_RECOVERED_NETWORK)
compiled = CompiledDeployment.read_json(conversion_root / SOURCE_RECOVERED_COMPILED)
if network.fingerprint != ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT:
    raise SystemExit("ERROR: P08.3.5d source network fingerprint drifted")
if compiled.fingerprint != ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT:
    raise SystemExit("ERROR: P08.3.5d compiled deployment fingerprint drifted")
if compiled.source_fingerprint != network.fingerprint:
    raise SystemExit("ERROR: P08.3.5d compiled deployment is detached from its source network")

payload = dict(manifest)
recorded_manifest_fingerprint = payload.pop("manifest_fingerprint", None)
recomputed_manifest_fingerprint = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recorded_manifest_fingerprint != recomputed_manifest_fingerprint:
    raise SystemExit("ERROR: P08.3.5d manifest fingerprint does not recompute")

print(
    "PASS: P08.3.5d gate measurement "
    f"examples=5000 timesteps=100 accuracy={accuracy:.6f} "
    f"ann_reference={ann_reference:.6f} delta={delta:.6f}"
)
print(
    "PASS: P08.3.5d gate activity "
    f"stage_total_spikes={stage_totals.tolist()} "
    f"stage_active_examples={stage_active.tolist()}"
)
print(
    "PASS: P08.3.5d gate readout "
    f"ties={manifest['ties']} all_equal={manifest['all_equal_evidence_examples']} "
    f"zero={manifest['zero_evidence_examples']} "
    f"range=[{manifest['evidence_min']},{manifest['evidence_max']}]"
)
print(
    "PASS: P08.3.5d gate identities "
    f"parameters={ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT} "
    f"network={network.fingerprint} compiled={compiled.fingerprint}"
)
print(
    "PASS: P08.3.5d test lock official_test_used=false "
    "test_examples_observed=0 accuracy_threshold=none post_conversion_tuning=false"
)
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_DIR" "$FINAL_DIR"

echo
echo "P08.3.5d source-recovered validation gate completed successfully."
echo "Validation artifacts are in: $FINAL_DIR"
echo "Official-test evaluation remains locked pending acceptance of this validation result."
