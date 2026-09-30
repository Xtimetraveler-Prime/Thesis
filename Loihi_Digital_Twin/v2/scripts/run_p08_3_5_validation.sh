#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
CONVERSION_DIR="$ARTIFACT_ROOT/p08_3_4_conversion"
FINAL_DIR="$ARTIFACT_ROOT/p08_3_5_validation"
CANDIDATE_DIR="$ARTIFACT_ROOT/.p08_3_5_validation_candidate"

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
        "ERROR: P08.3.5 requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/accepted_conversion.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/validation_snn.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_policy.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_ann_contract.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_training.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_conversion.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_validation_snn.py

if [[ ! -d "$CONVERSION_DIR" ]]; then
    echo "ERROR: accepted P08.3.4 conversion directory is missing: $CONVERSION_DIR" >&2
    exit 1
fi

rm -rf "$CANDIDATE_DIR"
mkdir -p "$CANDIDATE_DIR"

python -m mnist_v2_nxtf.validation_snn \
    --conversion-dir "$CONVERSION_DIR" \
    --output-dir "$CANDIDATE_DIR" \
    --batch-size 500

P08_3_5_CANDIDATE_DIR="$CANDIDATE_DIR" python - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from mnist_v2_nxtf.accepted_conversion import (
    ACCEPTED_COMPILED_FINGERPRINT,
    ACCEPTED_CONVERSION_FINGERPRINT,
    ACCEPTED_NETWORK_FINGERPRINT,
)
from mnist_v2_nxtf.validation_snn import (
    RATE_ENCODER,
    VALIDATION_MANIFEST_FILENAME,
    VALIDATION_PREDICTIONS_FILENAME,
    VALIDATION_SCHEMA,
    _arrays_fingerprint,
)

root = Path(os.environ["P08_3_5_CANDIDATE_DIR"])
manifest_path = root / VALIDATION_MANIFEST_FILENAME
predictions_path = root / VALIDATION_PREDICTIONS_FILENAME
if not manifest_path.is_file() or not predictions_path.is_file():
    raise SystemExit("ERROR: P08.3.5 validation artifacts are incomplete")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
required = {
    "schema": VALIDATION_SCHEMA,
    "status": "P08_3_5_VALIDATION_MEASURED_REVIEW_PENDING",
    "official_test_used": False,
    "test_examples_observed": 0,
    "validation_examples": 5000,
    "accepted_conversion_fingerprint": ACCEPTED_CONVERSION_FINGERPRINT,
    "accepted_network_fingerprint": ACCEPTED_NETWORK_FINGERPRINT,
    "accepted_compiled_fingerprint": ACCEPTED_COMPILED_FINGERPRINT,
    "timesteps": 100,
    "pipeline_flush_timesteps": 0,
    "input_encoder": RATE_ENCODER,
    "decoder": "argmax_total_output_spike_count",
    "decoder_tie_break": "lowest_class_index",
    "accuracy_acceptance_threshold": None,
    "accuracy_policy": "measurement_only_no_post_conversion_tuning_threshold",
}
for key, expected in required.items():
    if manifest.get(key) != expected:
        raise SystemExit(
            f"ERROR: P08.3.5 manifest field {key}={manifest.get(key)!r}, "
            f"expected {expected!r}"
        )

accuracy = float(manifest["snn_validation_accuracy"])
if not 0.0 <= accuracy <= 1.0:
    raise SystemExit(f"ERROR: invalid P08.3.5 validation accuracy: {accuracy}")
if int(manifest["total_output_spikes"]) <= 0:
    raise SystemExit("ERROR: converted SNN produced no output spikes on validation set")

with np.load(predictions_path, allow_pickle=False) as payload:
    labels = np.asarray(payload["labels"])
    predictions = np.asarray(payload["predictions"])
    counts = np.asarray(payload["output_spike_counts"])
    confusion = np.asarray(payload["confusion_matrix"])
if labels.shape != (5000,) or predictions.shape != (5000,):
    raise SystemExit("ERROR: P08.3.5 prediction vector shape drifted")
if counts.shape != (5000, 10) or confusion.shape != (10, 10):
    raise SystemExit("ERROR: P08.3.5 output-count/confusion shape drifted")
if int(confusion.sum()) != 5000:
    raise SystemExit("ERROR: P08.3.5 confusion matrix does not cover all validation examples")
observed = _arrays_fingerprint(labels, predictions, counts, confusion)
if observed != manifest["predictions_fingerprint"]:
    raise SystemExit("ERROR: P08.3.5 predictions fingerprint does not recompute")

print(
    "PASS: P08.3.5 full validation artifact "
    f"examples=5000 timesteps=100 accuracy={accuracy:.6f} "
    f"ann_minus_snn={float(manifest['ann_minus_snn_accuracy']):.6f}"
)
print(
    "PASS: P08.3.5 activity diagnostics "
    f"total_spikes={manifest['total_output_spikes']} "
    f"silent={manifest['silent_examples']} ties={manifest['tie_examples']}"
)
print(
    "PASS: P08.3.5 measurement policy accuracy_threshold=none "
    "post_conversion_tuning=false"
)
print(
    "PASS: P08.3.5 test lock official_test_used=false "
    "test_examples_observed=0 validation_examples=5000"
)
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_DIR" "$FINAL_DIR"

echo
echo "P08.3.5 validation-only SNN gate completed successfully."
echo "Validation artifacts are in: $FINAL_DIR"
echo "Official-test evaluation remains locked pending review of this measured SNN result."
