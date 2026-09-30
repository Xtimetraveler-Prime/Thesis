#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
FINAL_DIR="$ARTIFACT_ROOT/p08_3_3_full_ann"
CANDIDATE_DIR="$ARTIFACT_ROOT/.p08_3_3_full_ann_candidate"

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
        "ERROR: P08.3.3 full training requires the dedicated .venv-p08 "
        "environment (missing: %s). From the repository root run:\n"
        "  source .venv-p08/bin/activate\n"
        "  python -m pip install -e Loihi_Digital_Twin/v2\n"
        "  python -m pip install -e 'applications/mnist_v2_nxtf[train,test]'"
        % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/data.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/ann.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/policy.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/training.py

# Re-run the inexpensive contract tests before beginning the real training job.
python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_policy.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_ann_contract.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_training.py

mkdir -p "$ARTIFACT_ROOT"
rm -rf "$CANDIDATE_DIR"
mkdir -p "$CANDIDATE_DIR"

# Train once under the frozen full policy. The smoke gate already established
# deterministic replay of the machinery; repeating a 55k/5k run is not required.
python -m mnist_v2_nxtf.training \
    --output-dir "$CANDIDATE_DIR" \
    2>&1 | tee "$CANDIDATE_DIR/training.log"

P08_3_3_CANDIDATE_DIR="$CANDIDATE_DIR" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import tensorflow as tf

from mnist_v2_nxtf.ann import EXPECTED_ANN_PARAMETERS
from mnist_v2_nxtf.policy import ANN_POLICY

SANITY_FLOOR = 0.95
root = Path(os.environ["P08_3_3_CANDIDATE_DIR"])
manifest_path = root / "training_manifest.json"
checkpoint_path = root / "selected_ann.keras"

if not manifest_path.is_file():
    raise SystemExit("ERROR: P08.3.3 training manifest was not created")
if not checkpoint_path.is_file():
    raise SystemExit("ERROR: P08.3.3 selected checkpoint was not created")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

required = {
    "schema": "p08-ann-training-v1",
    "mode": "full-55k-5k",
    "official_test_used": False,
    "selection_source": "fixed_validation_split_only",
    "train_examples": 55_000,
    "validation_examples": 5_000,
    "test_examples_observed": 0,
    "model_parameters": EXPECTED_ANN_PARAMETERS,
    "max_epochs": ANN_POLICY.max_epochs,
    "early_stopping_patience": ANN_POLICY.early_stopping_patience,
    "checkpoint_metric": ANN_POLICY.checkpoint_metric,
    "checkpoint_mode": ANN_POLICY.checkpoint_mode,
}
for key, expected in required.items():
    observed = manifest.get(key)
    if observed != expected:
        raise SystemExit(
            f"ERROR: P08.3.3 manifest field {key}={observed!r}, expected {expected!r}"
        )

history = manifest.get("history")
if not isinstance(history, list) or not history:
    raise SystemExit("ERROR: P08.3.3 manifest has no training history")
if manifest.get("epochs_ran") != len(history):
    raise SystemExit("ERROR: P08.3.3 epochs_ran does not match history length")
if not 1 <= len(history) <= ANN_POLICY.max_epochs:
    raise SystemExit("ERROR: P08.3.3 history length is outside frozen epoch policy")

for record in history:
    for key in ("loss", "accuracy", "val_loss", "val_accuracy"):
        if not math.isfinite(float(record[key])):
            raise SystemExit(f"ERROR: non-finite P08.3.3 metric {key}={record[key]}")

# Recompute the frozen validation-only checkpoint ordering.
best = min(
    history,
    key=lambda r: (-float(r["val_accuracy"]), float(r["val_loss"]), int(r["epoch"])),
)
if int(manifest["best_epoch"]) != int(best["epoch"]):
    raise SystemExit("ERROR: selected epoch is not the frozen validation optimum")
if not math.isclose(float(manifest["best_val_accuracy"]), float(best["val_accuracy"]), rel_tol=0, abs_tol=1e-12):
    raise SystemExit("ERROR: best validation accuracy does not match selected history record")
if not math.isclose(float(manifest["best_val_loss"]), float(best["val_loss"]), rel_tol=0, abs_tol=1e-12):
    raise SystemExit("ERROR: best validation loss does not match selected history record")

best_val_accuracy = float(manifest["best_val_accuracy"])
if best_val_accuracy < SANITY_FLOOR:
    raise SystemExit(
        "ERROR: frozen P08.3.3 ANN failed the predeclared engineering sanity floor: "
        f"val_accuracy={best_val_accuracy:.6f} floor={SANITY_FLOOR:.6f}"
    )

# Validate the checkpoint byte hash recorded by training.py.
digest = hashlib.sha256()
with checkpoint_path.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
checkpoint_sha256 = digest.hexdigest()
if checkpoint_sha256 != manifest.get("checkpoint_sha256"):
    raise SystemExit("ERROR: checkpoint SHA-256 does not match manifest")

# Validate the tensor-level fingerprint independently of archive metadata.
def array_identity(array: np.ndarray) -> bytes:
    value = np.ascontiguousarray(array)
    header = json.dumps(
        {"shape": value.shape, "dtype": str(value.dtype)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return header + b"\0" + value.tobytes(order="C")

selected = tf.keras.models.load_model(checkpoint_path)
if selected.count_params() != EXPECTED_ANN_PARAMETERS:
    raise SystemExit("ERROR: reloaded selected ANN parameter count drifted")
weights_digest = hashlib.sha256()
for weight in selected.get_weights():
    weights_digest.update(array_identity(weight))
weights_fingerprint = weights_digest.hexdigest()
if weights_fingerprint != manifest.get("selected_weights_fingerprint"):
    raise SystemExit("ERROR: selected ANN tensor fingerprint does not match manifest")

# The manifest fingerprint excludes only its own fingerprint field.
payload = dict(manifest)
recorded_manifest_fingerprint = payload.pop("manifest_fingerprint", None)
recomputed_manifest_fingerprint = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recomputed_manifest_fingerprint != recorded_manifest_fingerprint:
    raise SystemExit("ERROR: training manifest fingerprint does not recompute")

gate = {
    "schema": "p08-ann-training-gate-v1",
    "result": "PASS",
    "sanity_floor": SANITY_FLOOR,
    "best_epoch": int(manifest["best_epoch"]),
    "epochs_ran": int(manifest["epochs_ran"]),
    "best_val_accuracy": best_val_accuracy,
    "best_val_loss": float(manifest["best_val_loss"]),
    "checkpoint_sha256": checkpoint_sha256,
    "selected_weights_fingerprint": weights_fingerprint,
    "manifest_fingerprint": recorded_manifest_fingerprint,
    "split_fingerprint": manifest["split_fingerprint"],
    "dataset_fingerprint": manifest["dataset_fingerprint"],
    "official_test_used": False,
    "test_examples_observed": 0,
    "selection_source": "fixed_validation_split_only",
}
(root / "gate_result.json").write_text(
    json.dumps(gate, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

print(
    "PASS: P08.3.3 full ANN training "
    f"epochs={gate['epochs_ran']} best_epoch={gate['best_epoch']} "
    f"val_accuracy={gate['best_val_accuracy']:.6f} "
    f"val_loss={gate['best_val_loss']:.6f} sanity_floor={SANITY_FLOOR:.2f}"
)
print(
    "PASS: P08.3.3 selected artifact "
    f"weights_fingerprint={weights_fingerprint} "
    f"checkpoint_sha256={checkpoint_sha256}"
)
print(
    "PASS: P08.3.3 test lock official_test_used=false "
    "test_examples_observed=0 selection=fixed_validation_split_only"
)
PY

# Promote the fully validated candidate atomically enough for the local workflow.
rm -rf "$FINAL_DIR"
mv "$CANDIDATE_DIR" "$FINAL_DIR"

echo
echo "P08.3.3 full ANN training gate completed successfully."
echo "Accepted-candidate artifacts are in: $FINAL_DIR"
echo "Do not evaluate the official MNIST test split yet; conversion is still pending."
