#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
ANN_DIR="$ARTIFACT_ROOT/p08_3_3_full_ann"
CONVERSION_DIR="$ARTIFACT_ROOT/p08_3_5c_source_recovered_conversion"
FINAL_DIR="$ARTIFACT_ROOT/p08_4_1_official_test"
CANDIDATE_DIR="$ARTIFACT_ROOT/.p08_4_1_official_test_candidate"

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
        "ERROR: P08.4.1 requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/official_test_evaluation.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_backend_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_recovered_conversion.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_recovered_validation.py \
    applications/mnist_v2_nxtf/tests/test_p08_4_official_test_evaluation.py

CHECKPOINT="$ANN_DIR/selected_ann.keras"
TRAINING_MANIFEST="$ANN_DIR/training_manifest.json"
CONVERSION_MANIFEST="$CONVERSION_DIR/source_recovered_conversion_manifest.json"
CONVERSION_PARAMETERS="$CONVERSION_DIR/source_recovered_parameters.npz"

for path in "$CHECKPOINT" "$TRAINING_MANIFEST" "$CONVERSION_MANIFEST" "$CONVERSION_PARAMETERS"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required accepted P08.3 artifact is missing: $path" >&2
        exit 1
    fi
done

rm -rf "$CANDIDATE_DIR"
mkdir -p "$CANDIDATE_DIR"

python -m mnist_v2_nxtf.official_test_evaluation \
    --checkpoint "$CHECKPOINT" \
    --training-manifest "$TRAINING_MANIFEST" \
    --conversion-dir "$CONVERSION_DIR" \
    --output-dir "$CANDIDATE_DIR"

P08_4_1_DIR="$CANDIDATE_DIR" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from mnist_v2_nxtf.official_test_evaluation import (
    OFFICIAL_TEST_EXAMPLES,
    OFFICIAL_TEST_MANIFEST,
    OFFICIAL_TEST_RESULTS,
    OFFICIAL_TEST_SCHEMA,
)
from mnist_v2_nxtf.source_recovered_validation import (
    ACCEPTED_HIDDEN_THRESHOLDS,
    ACCEPTED_INPUT_THRESHOLD,
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
    _results_fingerprint,
)
from mnist_v2_nxtf.accepted_ann import (
    ACCEPTED_ANN_CHECKPOINT_SHA256,
    ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
)

root = Path(os.environ["P08_4_1_DIR"])
manifest_path = root / OFFICIAL_TEST_MANIFEST
results_path = root / OFFICIAL_TEST_RESULTS
if not manifest_path.is_file():
    raise SystemExit(f"ERROR: P08.4.1 manifest missing: {manifest_path}")
if not results_path.is_file():
    raise SystemExit(f"ERROR: P08.4.1 results missing: {results_path}")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
required = {
    "schema": OFFICIAL_TEST_SCHEMA,
    "status": "P08_4_1_OFFICIAL_TEST_REVIEW_PENDING",
    "p08_3_acceptance_status": "P08_3_ACCEPTED_OFFICIAL_TEST_UNLOCKED",
    "official_test_used": True,
    "test_examples_observed": 10000,
    "evaluation_only_no_selection": True,
    "selection_decisions_after_test": 0,
    "post_test_training": False,
    "post_test_conversion_tuning": False,
    "post_test_threshold_tuning": False,
    "post_test_decoder_tuning": False,
    "post_test_timestep_tuning": False,
    "timesteps": 100,
    "test_input_scaling_scope": "full_10000_official_test_corpus_once_before_batching",
    "input_scale": 255,
    "input_threshold": ACCEPTED_INPUT_THRESHOLD,
    "hidden_thresholds": list(ACCEPTED_HIDDEN_THRESHOLDS),
    "accepted_ann_checkpoint_sha256": ACCEPTED_ANN_CHECKPOINT_SHA256,
    "accepted_ann_weights_fingerprint": ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
    "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
    "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    "accuracy_acceptance_threshold": None,
}
for key, expected in required.items():
    if manifest.get(key) != expected:
        raise SystemExit(
            f"ERROR: P08.4.1 manifest {key}={manifest.get(key)!r}, expected {expected!r}"
        )

for key in ("ann_accuracy", "snn_accuracy"):
    value = float(manifest[key])
    if not np.isfinite(value) or not (0.0 <= value <= 1.0):
        raise SystemExit(f"ERROR: P08.4.1 invalid {key}={value}")
if abs(
    float(manifest["ann_minus_snn_accuracy"])
    - (float(manifest["ann_accuracy"]) - float(manifest["snn_accuracy"]))
) > 1e-12:
    raise SystemExit("ERROR: P08.4.1 ANN-SNN accuracy delta does not recompute")

with np.load(results_path, allow_pickle=False) as payload:
    labels = np.asarray(payload["labels"], dtype=np.int64)
    ann_predictions = np.asarray(payload["ann_predictions"], dtype=np.int64)
    snn_predictions = np.asarray(payload["snn_predictions"], dtype=np.int64)
    evidence = np.asarray(payload["snn_final_evidence"], dtype=np.int64)
    ann_confusion = np.asarray(payload["ann_confusion_matrix"], dtype=np.int64)
    snn_confusion = np.asarray(payload["snn_confusion_matrix"], dtype=np.int64)
    stage_total_spikes = np.asarray(payload["stage_total_spikes"], dtype=np.int64)
    stage_active_examples = np.asarray(payload["stage_active_examples"], dtype=np.int64)

if labels.shape != (OFFICIAL_TEST_EXAMPLES,):
    raise SystemExit(f"ERROR: P08.4.1 labels shape drifted: {labels.shape}")
if ann_predictions.shape != labels.shape or snn_predictions.shape != labels.shape:
    raise SystemExit("ERROR: P08.4.1 prediction shape drifted")
if evidence.shape != (OFFICIAL_TEST_EXAMPLES, 10):
    raise SystemExit(f"ERROR: P08.4.1 evidence shape drifted: {evidence.shape}")
if ann_confusion.shape != (10, 10) or snn_confusion.shape != (10, 10):
    raise SystemExit("ERROR: P08.4.1 confusion matrix shape drifted")
if int(ann_confusion.sum()) != OFFICIAL_TEST_EXAMPLES or int(snn_confusion.sum()) != OFFICIAL_TEST_EXAMPLES:
    raise SystemExit("ERROR: P08.4.1 confusion matrix count drifted")

ann_correct = int(np.count_nonzero(ann_predictions == labels))
snn_correct = int(np.count_nonzero(snn_predictions == labels))
if ann_correct != int(manifest["ann_correct"]):
    raise SystemExit("ERROR: P08.4.1 ANN correct count does not recompute")
if snn_correct != int(manifest["snn_correct"]):
    raise SystemExit("ERROR: P08.4.1 SNN correct count does not recompute")
if abs(ann_correct / OFFICIAL_TEST_EXAMPLES - float(manifest["ann_accuracy"])) > 1e-12:
    raise SystemExit("ERROR: P08.4.1 ANN accuracy does not recompute")
if abs(snn_correct / OFFICIAL_TEST_EXAMPLES - float(manifest["snn_accuracy"])) > 1e-12:
    raise SystemExit("ERROR: P08.4.1 SNN accuracy does not recompute")

if _results_fingerprint(labels) != manifest["labels_fingerprint"]:
    raise SystemExit("ERROR: P08.4.1 labels fingerprint does not recompute")
if _results_fingerprint(labels, ann_predictions) != manifest["ann_prediction_fingerprint"]:
    raise SystemExit("ERROR: P08.4.1 ANN prediction fingerprint does not recompute")
if _results_fingerprint(labels, snn_predictions) != manifest["snn_prediction_fingerprint"]:
    raise SystemExit("ERROR: P08.4.1 SNN prediction fingerprint does not recompute")
if _results_fingerprint(evidence) != manifest["snn_evidence_fingerprint"]:
    raise SystemExit("ERROR: P08.4.1 SNN evidence fingerprint does not recompute")

if stage_total_spikes.shape != (4,) or stage_active_examples.shape != (4,):
    raise SystemExit("ERROR: P08.4.1 activity vector shape drifted")
if np.any(stage_total_spikes[1:] <= 0):
    raise SystemExit("ERROR: P08.4.1 one or more hidden stages produced no spikes")
if np.any(stage_active_examples <= 0):
    raise SystemExit("ERROR: P08.4.1 one or more stages had no active examples")
if list(stage_total_spikes.astype(int)) != manifest["stage_total_spikes"]:
    raise SystemExit("ERROR: P08.4.1 stage spike totals do not match manifest")
if list(stage_active_examples.astype(int)) != manifest["stage_active_examples"]:
    raise SystemExit("ERROR: P08.4.1 active-example totals do not match manifest")

payload = dict(manifest)
recorded = payload.pop("manifest_fingerprint", None)
recomputed = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recorded != recomputed:
    raise SystemExit("ERROR: P08.4.1 manifest fingerprint does not recompute")

print(
    "PASS: P08.4.1 gate accuracy "
    f"examples=10000 ann={manifest['ann_accuracy']:.6f} "
    f"snn={manifest['snn_accuracy']:.6f} delta={manifest['ann_minus_snn_accuracy']:.6f}"
)
print(
    "PASS: P08.4.1 gate SNN activity "
    f"stage_total_spikes={manifest['stage_total_spikes']} "
    f"stage_active_examples={manifest['stage_active_examples']}"
)
print(
    "PASS: P08.4.1 gate SNN readout "
    f"ties={manifest['snn_ties']} all_equal={manifest['snn_all_equal_evidence_examples']} "
    f"zero={manifest['snn_zero_evidence_examples']} "
    f"range=[{manifest['snn_evidence_min']},{manifest['snn_evidence_max']}]"
)
print(
    "PASS: P08.4.1 gate identities "
    f"ann={manifest['accepted_ann_weights_fingerprint']} "
    f"parameters={manifest['parameter_fingerprint']} "
    f"network={manifest['network_fingerprint']} compiled={manifest['compiled_fingerprint']}"
)
print(
    "PASS: P08.4.1 gate test-use boundary official_test_used=true "
    "test_examples_observed=10000 selection_decisions_after_test=0 post_test_tuning=false"
)
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_DIR" "$FINAL_DIR"

echo
echo "P08.4.1 frozen ANN/SNN official test evaluation gate completed successfully."
echo "Accepted candidate artifacts are in: $FINAL_DIR"
echo "Official test results are observational only; no post-test tuning is permitted."
