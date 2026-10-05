#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"

export PYTHONPATH="$PROJECT_DIR/src:$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
export TF_CPP_MIN_LOG_LEVEL="${TF_CPP_MIN_LOG_LEVEL:-2}"
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
        "ERROR: P08.3.2 preflight requires the dedicated .venv-p08 training "
        "environment (missing: %s). From the repository root run:\n"
        "  source .venv-p08/bin/activate\n"
        "  python -m pip install -e Loihi_Digital_Twin/v2\n"
        "  python -m pip install -e 'applications/mnist_v2_nxtf[train,test]'"
        % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/config.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/data.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/policy.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/ann.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/training.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_2_paging.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_policy.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_ann_contract.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_training.py \
    Loihi_Digital_Twin/v2/tests/test_p08_paging.py

SMOKE_ROOT="/tmp/p08_3_2_training_smoke"
rm -rf "$SMOKE_ROOT"
mkdir -p "$SMOKE_ROOT/run_a" "$SMOKE_ROOT/run_b"

python -m mnist_v2_nxtf.training \
    --smoke \
    --output-dir "$SMOKE_ROOT/run_a" \
    | tee "$SMOKE_ROOT/run_a.log"

python -m mnist_v2_nxtf.training \
    --smoke \
    --output-dir "$SMOKE_ROOT/run_b" \
    | tee "$SMOKE_ROOT/run_b.log"

python - <<'PY'
import hashlib
import json
from pathlib import Path

root = Path("/tmp/p08_3_2_training_smoke")
a = json.loads((root / "run_a" / "training_manifest.json").read_text())
b = json.loads((root / "run_b" / "training_manifest.json").read_text())

for manifest in (a, b):
    assert manifest["schema"] == "p08-ann-training-v1"
    assert manifest["mode"] == "deterministic-smoke"
    assert manifest["official_test_used"] is False
    assert manifest["selection_source"] == "fixed_validation_split_only"
    assert manifest["test_examples_observed"] == 0
    assert manifest["train_examples"] == 80
    assert manifest["validation_examples"] == 20
    assert manifest["model_parameters"] == 7006
    assert manifest["max_epochs"] == 1
    assert manifest["epochs_ran"] == 1
    assert manifest["best_epoch"] == 1
    assert len(manifest["checkpoint_sha256"]) == 64
    assert len(manifest["selected_weights_fingerprint"]) == 64
    assert len(manifest["manifest_fingerprint"]) == 64

    checkpoint = root / ("run_a" if manifest is a else "run_b") / manifest["checkpoint_filename"]
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    assert digest == manifest["checkpoint_sha256"]

# Determinism is checked at the semantic tensor/metric boundary rather than the
# .keras archive byte boundary, because ZIP/container metadata may differ.
for field in (
    "dataset_fingerprint",
    "split_fingerprint",
    "selected_weights_fingerprint",
    "best_epoch",
    "best_val_accuracy",
    "best_val_loss",
    "history",
):
    assert a[field] == b[field], f"deterministic smoke mismatch for {field}"

print(
    "PASS: P08.3.2 deterministic smoke replay "
    f"weights={a['selected_weights_fingerprint']} "
    f"val_accuracy={a['best_val_accuracy']:.6f} "
    f"val_loss={a['best_val_loss']:.6f}"
)
print(
    "PASS: P08.3.2 test lock "
    "official_test_used=false test_examples_observed=0 selection=fixed_validation_split_only"
)
PY

echo
echo "P08.3.2 deterministic training-pipeline preflight completed successfully."
echo "This gate uses synthetic smoke data only; it does not load MNIST or run full ANN training."
echo "After independent acceptance, the frozen 55k/5k ANN training run may begin."
