#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
ANN_DIR="$ARTIFACT_ROOT/p08_3_3_full_ann"
FINAL_DIR="$ARTIFACT_ROOT/p08_3_5b_source_semantics"
CANDIDATE_DIR="$ARTIFACT_ROOT/.p08_3_5b_source_semantics_candidate"

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
        "ERROR: P08.3.5b requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/accepted_ann.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/policy.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/source_backend_reconstruction.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_p08_3_policy.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_ann_contract.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_backend_reconstruction.py

CHECKPOINT="$ANN_DIR/selected_ann.keras"
TRAINING_MANIFEST="$ANN_DIR/training_manifest.json"
if [[ ! -f "$CHECKPOINT" ]]; then
    echo "ERROR: accepted P08.3.3 checkpoint is missing: $CHECKPOINT" >&2
    exit 1
fi
if [[ ! -f "$TRAINING_MANIFEST" ]]; then
    echo "ERROR: accepted P08.3.3 training manifest is missing: $TRAINING_MANIFEST" >&2
    exit 1
fi

rm -rf "$CANDIDATE_DIR"
mkdir -p "$CANDIDATE_DIR"

python -m mnist_v2_nxtf.source_backend_reconstruction \
    --checkpoint "$CHECKPOINT" \
    --training-manifest "$TRAINING_MANIFEST" \
    --output-dir "$CANDIDATE_DIR" \
    --examples 100

P08_3_5B_DIR="$CANDIDATE_DIR" python - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

from mnist_v2_nxtf.source_backend_reconstruction import (
    SOURCE_ACTIVATION_PERCENTILE,
    SOURCE_BACKEND_MANIFEST,
    SOURCE_BACKEND_SCHEMA,
    SOURCE_INPUT_SCALE,
    SOURCE_PARAM_PERCENTILE,
)

root = Path(os.environ["P08_3_5B_DIR"])
manifest_path = root / SOURCE_BACKEND_MANIFEST
if not manifest_path.is_file():
    raise SystemExit(f"ERROR: P08.3.5b manifest is missing: {manifest_path}")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

required = {
    "schema": SOURCE_BACKEND_SCHEMA,
    "official_test_used": False,
    "test_examples_observed": 0,
    "calibration_examples": 5500,
    "param_percentile": SOURCE_PARAM_PERCENTILE,
    "activation_percentile": SOURCE_ACTIVATION_PERCENTILE,
    "desired_threshold_to_input_ratio": 8,
    "input_mode": "NxTF_BIAS_FRAME_RECONSTRUCTION",
    "input_scale": SOURCE_INPUT_SCALE,
    "hidden_thresholds_are_per_layer": True,
    "softmax_output_uses_ordinary_spike_threshold": False,
    "normalization_origin": "RECOVERED_PUBLIC_INTEL_NXTF_BACKEND",
    "fpga_execution_adaptation": "hard_reset_project_profile",
}
for key, expected in required.items():
    if manifest.get(key) != expected:
        raise SystemExit(
            f"ERROR: P08.3.5b manifest {key}={manifest.get(key)!r}, expected {expected!r}"
        )

if int(manifest["input_threshold"]) <= 0:
    raise SystemExit("ERROR: source-recovered input threshold is nonpositive")
layers = manifest.get("layers")
if not isinstance(layers, list) or len(layers) != 4:
    raise SystemExit("ERROR: P08.3.5b expected four convolution layer records")
for index, layer in enumerate(layers, start=1):
    if int(layer["weight_clipped"]) or int(layer["bias_clipped"]):
        raise SystemExit(f"ERROR: source normalization clipped parameters in conv{index}")
    if index < 4:
        if layer["softmax_readout"]:
            raise SystemExit(f"ERROR: hidden conv{index} marked as softmax")
        if layer["threshold"] is None or int(layer["threshold"]) <= 0:
            raise SystemExit(f"ERROR: hidden conv{index} has no calibrated threshold")
        if layer["slope"] is None or float(layer["slope"]) <= 0:
            raise SystemExit(f"ERROR: hidden conv{index} has no positive propagated slope")
    else:
        if not layer["softmax_readout"]:
            raise SystemExit("ERROR: conv4 must retain recovered softmax-readout status")
        if layer["threshold"] is not None:
            raise SystemExit("ERROR: source-recovered softmax output should skip ordinary threshold")

activity = manifest.get("activity_preflight")
if not isinstance(activity, dict):
    raise SystemExit("ERROR: P08.3.5b activity preflight is missing")
if activity.get("classification_accuracy_evaluated") is not False:
    raise SystemExit("ERROR: P08.3.5b must not evaluate classification accuracy")
if activity.get("first_dead_stage") is not None:
    raise SystemExit(
        f"ERROR: source-recovered hidden path is still dead at {activity['first_dead_stage']}"
    )
for key in ("input_spikes", "conv1_spikes", "conv2_spikes", "conv3_spikes"):
    if int(activity.get(key, 0)) <= 0:
        raise SystemExit(f"ERROR: P08.3.5b expected positive {key}")
if int(activity.get("softmax_evidence_nonzero_examples", 0)) <= 0:
    raise SystemExit("ERROR: recovered softmax readout produced no nonzero evidence")
if int(activity.get("softmax_evidence_distinct_examples", 0)) <= 0:
    raise SystemExit("ERROR: recovered softmax readout produced no class-distinguishing evidence")

thresholds = [manifest["input_threshold"]] + [layer["threshold"] for layer in layers[:3]]
print(
    "PASS: P08.3.5b source semantics verified "
    f"thresholds={thresholds} fixed_threshold_512=false blanket_scale_64=false"
)
print(
    "PASS: P08.3.5b activity propagation "
    f"input={activity['input_spikes']} conv1={activity['conv1_spikes']} "
    f"conv2={activity['conv2_spikes']} conv3={activity['conv3_spikes']} "
    f"first_dead_stage={activity['first_dead_stage']}"
)
print(
    "PASS: P08.3.5b softmax readout preflight "
    f"nonzero_examples={activity['softmax_evidence_nonzero_examples']} "
    f"distinct_examples={activity['softmax_evidence_distinct_examples']}"
)
print(
    "PASS: P08.3.5b test lock official_test_used=false test_examples_observed=0 "
    "classification_accuracy_evaluated=false"
)
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_DIR" "$FINAL_DIR"

echo
echo "P08.3.5b source-recovered NxTF semantics preflight completed successfully."
echo "Candidate source-semantics artifacts are in: $FINAL_DIR"
echo "This gate does not evaluate SNN classification accuracy and does not unlock the official test set."
