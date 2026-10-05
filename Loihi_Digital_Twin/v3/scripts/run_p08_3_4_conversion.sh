#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
ANN_DIR="$ARTIFACT_ROOT/p08_3_3_full_ann"
FINAL_DIR="$ARTIFACT_ROOT/p08_3_4_conversion"
CANDIDATE_DIR="$ARTIFACT_ROOT/.p08_3_4_conversion_candidate"

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
        "ERROR: P08.3.4 conversion requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/accepted_ann.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/policy.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/conversion.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/conversion_loihi.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_policy.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_ann_contract.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_training.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_conversion.py

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

python -m mnist_v2_nxtf.conversion_loihi \
    --checkpoint "$CHECKPOINT" \
    --training-manifest "$TRAINING_MANIFEST" \
    --output-dir "$CANDIDATE_DIR"

P08_3_4_CANDIDATE_DIR="$CANDIDATE_DIR" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

from loihi_twin_v2.compiler import CompiledDeployment, NetworkSpec
from mnist_v2_nxtf.accepted_ann import (
    ACCEPTED_ANN_CHECKPOINT_SHA256,
    ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
)
from mnist_v2_nxtf.conversion_loihi import (
    CONVERSION_ARTIFACT_FILENAME,
    CONVERSION_MANIFEST_FILENAME,
    CONVERSION_SCHEMA,
    CONVERTED_NETWORK_FILENAME,
    COMPILED_DEPLOYMENT_FILENAME,
    DTHIR_PARAMETER_SCALE,
    INTEGER_THRESHOLD_SCALE,
    NORMALIZATION_PERCENTILE,
    _arrays_fingerprint,
)
from mnist_v2_nxtf.policy import CONVERSION_POLICY
from mnist_v2_nxtf.reconstruction import PROPOSED_METRICS

root = Path(os.environ["P08_3_4_CANDIDATE_DIR"])
manifest_path = root / CONVERSION_MANIFEST_FILENAME
parameters_path = root / CONVERSION_ARTIFACT_FILENAME
network_path = root / CONVERTED_NETWORK_FILENAME
compiled_path = root / COMPILED_DEPLOYMENT_FILENAME
for path in (manifest_path, parameters_path, network_path, compiled_path):
    if not path.is_file():
        raise SystemExit(f"ERROR: P08.3.4 artifact is missing: {path}")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
required = {
    "schema": CONVERSION_SCHEMA,
    "status": "P08_3_4_CONVERTED_VALIDATION_PENDING",
    "accepted_ann_checkpoint_sha256": ACCEPTED_ANN_CHECKPOINT_SHA256,
    "accepted_ann_weights_fingerprint": ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
    "official_test_used": False,
    "test_examples_observed": 0,
    "calibration_source": "training_remainder_only",
    "calibration_stride": 10,
    "calibration_examples": 5_500,
    "normalization_percentile": NORMALIZATION_PERCENTILE,
    "integer_threshold_scale": INTEGER_THRESHOLD_SCALE,
    "desired_threshold_to_input_ratio": 8,
    "dthir_parameter_scale": DTHIR_PARAMETER_SCALE,
    "dthir_scaling_status": "PROJECT_RECONSTRUCTION_SOURCE_BOUNDED_NO_ACCURACY_TUNING",
    "weight_sign_mode": "mixed",
    "weight_quantization_step": 2,
    "weight_rounding": "toward_zero",
    "weight_exponent": 0,
    "weight_range": [-256, 254],
    "reset_mode": CONVERSION_POLICY.reset_mode,
    "primary_timesteps": 100,
    "logical_core_count": 5,
    "resident_context_count": 3,
    "physical_engine_count": 1,
    "expanded_connections": PROPOSED_METRICS.expanded_connections,
    "neuron_count": PROPOSED_METRICS.neuron_count,
    "trainable_ann_parameters": PROPOSED_METRICS.trainable_parameters,
}
for key, expected in required.items():
    observed = manifest.get(key)
    if observed != expected:
        raise SystemExit(
            f"ERROR: P08.3.4 manifest field {key}={observed!r}, expected {expected!r}"
        )

if DTHIR_PARAMETER_SCALE != 64.0:
    raise SystemExit(
        f"ERROR: P08.3.4 DThIR parameter scale={DTHIR_PARAMETER_SCALE}, expected 64"
    )

lambdas = manifest.get("activation_lambdas")
if not isinstance(lambdas, list) or len(lambdas) != 5:
    raise SystemExit("ERROR: P08.3.4 must record lambda_0..lambda_4")
if any(not math.isfinite(float(value)) or float(value) <= 0.0 for value in lambdas):
    raise SystemExit(f"ERROR: invalid P08.3.4 activation lambdas: {lambdas}")

layers = manifest.get("layers")
if not isinstance(layers, list) or len(layers) != 4:
    raise SystemExit("ERROR: P08.3.4 must record four converted convolution layers")
if sum(int(layer["total_weights"]) for layer in layers) != PROPOSED_METRICS.kernel_weights:
    raise SystemExit("ERROR: converted kernel coefficient count drifted")
for layer in layers:
    w_min = int(layer["integer_weight_min"])
    w_max = int(layer["integer_weight_max"])
    b_min = int(layer["integer_bias_min"])
    b_max = int(layer["integer_bias_max"])
    if w_min < CONVERSION_POLICY.signed_weight_min or w_max > CONVERSION_POLICY.signed_weight_max:
        raise SystemExit(f"ERROR: integer weight overflow survived gate in {layer['name']}")
    if b_min < CONVERSION_POLICY.signed_bias_min or b_max > CONVERSION_POLICY.signed_bias_max:
        raise SystemExit(f"ERROR: integer bias overflow survived gate in {layer['name']}")

with np.load(parameters_path, allow_pickle=False) as payload:
    arrays = {name: np.asarray(payload[name]) for name in payload.files}
for name, array in arrays.items():
    if name.endswith("_kernel_integer") and np.any(array.astype(np.int64) % 2 != 0):
        raise SystemExit(f"ERROR: non-step-2 Loihi mixed-sign weight survived in {name}")
observed_conversion_fingerprint = _arrays_fingerprint(arrays)
if observed_conversion_fingerprint != manifest.get("conversion_fingerprint"):
    raise SystemExit("ERROR: converted parameter fingerprint does not recompute")

network = NetworkSpec.read_json(network_path)
compiled = CompiledDeployment.read_json(compiled_path)
if network.fingerprint != manifest.get("converted_network_fingerprint"):
    raise SystemExit("ERROR: converted network fingerprint does not match manifest")
if compiled.fingerprint != manifest.get("compiled_deployment_fingerprint"):
    raise SystemExit("ERROR: compiled deployment fingerprint does not match manifest")
if compiled.source_fingerprint != network.fingerprint:
    raise SystemExit("ERROR: P06 deployment source fingerprint is not the converted network")
if len(compiled.logical_deployment.core_configs) != 5:
    raise SystemExit("ERROR: converted P06 deployment did not map to five logical cores")

payload = dict(manifest)
recorded_manifest_fingerprint = payload.pop("manifest_fingerprint", None)
recomputed_manifest_fingerprint = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recomputed_manifest_fingerprint != recorded_manifest_fingerprint:
    raise SystemExit("ERROR: P08.3.4 conversion manifest fingerprint does not recompute")

gate = {
    "schema": "p08-ann-to-snn-conversion-gate-v3-dthir",
    "result": "PASS",
    "accepted_ann_checkpoint_sha256": ACCEPTED_ANN_CHECKPOINT_SHA256,
    "accepted_ann_weights_fingerprint": ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
    "calibration_examples": 5_500,
    "activation_lambdas": lambdas,
    "conversion_fingerprint": observed_conversion_fingerprint,
    "converted_network_fingerprint": network.fingerprint,
    "compiled_deployment_fingerprint": compiled.fingerprint,
    "logical_core_count": 5,
    "resident_context_count": 3,
    "physical_engine_count": 1,
    "official_test_used": False,
    "test_examples_observed": 0,
    "normalization_percentile": NORMALIZATION_PERCENTILE,
    "integer_threshold_scale": INTEGER_THRESHOLD_SCALE,
    "desired_threshold_to_input_ratio": 8,
    "dthir_parameter_scale": DTHIR_PARAMETER_SCALE,
    "dthir_scaling_status": "PROJECT_RECONSTRUCTION_SOURCE_BOUNDED_NO_ACCURACY_TUNING",
    "weight_sign_mode": "mixed",
    "weight_quantization_step": 2,
    "weight_rounding": "toward_zero",
    "weight_range": [-256, 254],
    "integer_clipping": False,
}
(root / "gate_result.json").write_text(
    json.dumps(gate, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

ranges = ",".join(
    f"{layer['name']}=W[{layer['integer_weight_min']},{layer['integer_weight_max']}]"
    f"/B[{layer['integer_bias_min']},{layer['integer_bias_max']}]"
    for layer in layers
)
print(
    "PASS: P08.3.4 conversion artifact "
    f"calibration_examples=5500 percentile={NORMALIZATION_PERCENTILE:g} "
    f"threshold_mantissa={INTEGER_THRESHOLD_SCALE} dthir=8 parameter_scale={DTHIR_PARAMETER_SCALE:g}"
)
print(
    "PASS: P08.3.4 Loihi mixed-sign weights "
    "range=[-256,254] step=2 rounding=toward_zero exponent=0 clipping=false"
)
print(f"PASS: P08.3.4 integer ranges {ranges} clipping=false")
print(
    "PASS: P08.3.4 converted deployment "
    f"logical_cores=5 resident_contexts=3 physical_engines=1 "
    f"expanded={PROPOSED_METRICS.expanded_connections}"
)
print(
    "PASS: P08.3.4 artifact identities "
    f"conversion={observed_conversion_fingerprint} "
    f"network={network.fingerprint} compiled={compiled.fingerprint}"
)
print(
    "PASS: P08.3.4 test lock official_test_used=false "
    "test_examples_observed=0 validation_accuracy_not_evaluated=true"
)
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_DIR" "$FINAL_DIR"

echo
echo "P08.3.4 ANN-to-SNN conversion gate completed successfully."
echo "Accepted conversion artifacts are in: $FINAL_DIR"
echo "Official-test evaluation remains locked. The next gate will measure validation-only SNN behavior at 100 timesteps."
