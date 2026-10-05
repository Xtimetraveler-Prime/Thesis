#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
ANN_DIR="$ARTIFACT_ROOT/p08_3_3_full_ann"
FINAL_DIR="$ARTIFACT_ROOT/p08_3_5c_source_recovered_conversion"
CANDIDATE_DIR="$ARTIFACT_ROOT/.p08_3_5c_source_recovered_conversion_candidate"

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
        "ERROR: P08.3.5c requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/source_backend_reconstruction.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/source_recovered_conversion.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_backend_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_source_recovered_conversion.py

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

python -m mnist_v2_nxtf.source_recovered_conversion \
    --checkpoint "$CHECKPOINT" \
    --training-manifest "$TRAINING_MANIFEST" \
    --output-dir "$CANDIDATE_DIR"

P08_3_5C_DIR="$CANDIDATE_DIR" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from loihi_twin_v2.compiler import CompiledDeployment, NetworkSpec
from mnist_v2_nxtf.source_recovered_conversion import (
    INPUT_INGRESS_MODE,
    SOFTMAX_READOUT_MODE,
    SOFTMAX_READOUT_THRESHOLD,
    SOURCE_RECOVERED_COMPILED,
    SOURCE_RECOVERED_MANIFEST,
    SOURCE_RECOVERED_NETWORK,
    SOURCE_RECOVERED_PARAMETERS,
    SOURCE_RECOVERED_SCHEMA,
    _arrays_fingerprint,
)
from mnist_v2_nxtf.source_backend_reconstruction import (
    SOURCE_BACKEND_MANIFEST,
    SOURCE_INPUT_SCALE,
)

root = Path(os.environ["P08_3_5C_DIR"])
paths = {
    "manifest": root / SOURCE_RECOVERED_MANIFEST,
    "parameters": root / SOURCE_RECOVERED_PARAMETERS,
    "network": root / SOURCE_RECOVERED_NETWORK,
    "compiled": root / SOURCE_RECOVERED_COMPILED,
    "source_manifest": root / SOURCE_BACKEND_MANIFEST,
}
for name, path in paths.items():
    if not path.is_file():
        raise SystemExit(f"ERROR: P08.3.5c missing {name}: {path}")

manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
source_manifest = json.loads(paths["source_manifest"].read_text(encoding="utf-8"))
required = {
    "schema": SOURCE_RECOVERED_SCHEMA,
    "status": "P08_3_5C_SOURCE_RECOVERED_COMPILE_REVIEW_PENDING",
    "supersedes_forward_execution_artifact": "P08_3_4_DTHIR_BLANKET_SCALE",
    "preserve_superseded_artifact_for_audit": True,
    "official_test_used": False,
    "test_examples_observed": 0,
    "classification_accuracy_evaluated": False,
    "calibration_examples": 5500,
    "input_ingress_mode": INPUT_INGRESS_MODE,
    "input_scale": SOURCE_INPUT_SCALE,
    "softmax_readout_mode": SOFTMAX_READOUT_MODE,
    "softmax_readout_threshold": SOFTMAX_READOUT_THRESHOLD,
    "softmax_output_spike_count_decoder": False,
    "logical_core_count": 5,
    "resident_context_count": 3,
    "physical_engine_count": 1,
    "neuron_count": 4218,
    "expanded_connections": 338880,
}
for key, expected in required.items():
    if manifest.get(key) != expected:
        raise SystemExit(
            f"ERROR: P08.3.5c manifest {key}={manifest.get(key)!r}, expected {expected!r}"
        )

hidden_thresholds = manifest.get("hidden_thresholds")
if hidden_thresholds != [
    int(source_manifest["layers"][0]["threshold"]),
    int(source_manifest["layers"][1]["threshold"]),
    int(source_manifest["layers"][2]["threshold"]),
]:
    raise SystemExit("ERROR: compiled hidden thresholds do not match source normalization")
if any(int(value) <= 0 for value in hidden_thresholds):
    raise SystemExit("ERROR: recovered hidden threshold is not positive")

with np.load(paths["parameters"], allow_pickle=False) as payload:
    arrays = {name: np.asarray(payload[name]) for name in payload.files}
if _arrays_fingerprint(arrays) != manifest["parameter_fingerprint"]:
    raise SystemExit("ERROR: source-recovered parameter fingerprint does not recompute")

network = NetworkSpec.read_json(paths["network"])
compiled = CompiledDeployment.read_json(paths["compiled"])
if network.fingerprint != manifest["network_fingerprint"]:
    raise SystemExit("ERROR: source-recovered network fingerprint mismatch")
if compiled.fingerprint != manifest["compiled_fingerprint"]:
    raise SystemExit("ERROR: source-recovered compiled fingerprint mismatch")
if compiled.source_fingerprint != network.fingerprint:
    raise SystemExit("ERROR: P06 compiled deployment is not bound to recovered network")
if len(compiled.logical_deployment.core_configs) != 5:
    raise SystemExit("ERROR: source-recovered deployment did not compile to five logical cores")

layer_thresholds = {}
for population in network.populations:
    layer = population.name.split("_c", 1)[0]
    layer_thresholds.setdefault(layer, set()).add(population.compartment.threshold)
expected_thresholds = {
    "conv1": {hidden_thresholds[0]},
    "conv2": {hidden_thresholds[1]},
    "conv3": {hidden_thresholds[2]},
    "conv4": {SOFTMAX_READOUT_THRESHOLD},
}
if layer_thresholds != expected_thresholds:
    raise SystemExit(
        f"ERROR: network thresholds {layer_thresholds!r} != {expected_thresholds!r}"
    )

payload = dict(manifest)
recorded = payload.pop("manifest_fingerprint", None)
recomputed = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recorded != recomputed:
    raise SystemExit("ERROR: P08.3.5c manifest fingerprint does not recompute")

print(
    "PASS: P08.3.5c gate source semantics "
    f"input_threshold={manifest['input_threshold']} "
    f"hidden_thresholds={hidden_thresholds} softmax_threshold={SOFTMAX_READOUT_THRESHOLD}"
)
print(
    "PASS: P08.3.5c gate deployment "
    "logical_cores=5 resident_contexts=3 physical_engines=1 "
    "neurons=4218 expanded=338880"
)
print(
    "PASS: P08.3.5c supersession old_p08_3_4=preserved "
    "forward_execution=source_recovered classification_accuracy_evaluated=false"
)
print(
    "PASS: P08.3.5c test lock official_test_used=false test_examples_observed=0"
)
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_DIR" "$FINAL_DIR"

echo
echo "P08.3.5c source-recovered conversion compile gate completed successfully."
echo "Candidate artifacts are in: $FINAL_DIR"
echo "Official-test evaluation remains locked; classification accuracy was not evaluated."
