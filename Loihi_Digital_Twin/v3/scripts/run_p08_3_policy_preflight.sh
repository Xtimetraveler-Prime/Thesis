#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"

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
        "ERROR: P08.3.1 policy preflight requires the dedicated .venv-p08 "
        "training environment (missing: %s). From the repository root run:\n"
        "  source .venv-p08/bin/activate\n"
        "  python -m pip install --upgrade pip\n"
        "  python -m pip install -e Loihi_Digital_Twin/v2\n"
        "  python -m pip install -e 'applications/mnist_v2_nxtf[train,test]'"
        % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/config.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/reconstruction.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/data.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/policy.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/ann.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_2_paging.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_policy.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_ann_contract.py \
    Loihi_Digital_Twin/v2/tests/test_p08_paging.py

python - <<'PY'
from mnist_v2_nxtf import TOPOLOGY_STATUS
from mnist_v2_nxtf.ann import EXPECTED_ANN_PARAMETERS, build_ann, compile_ann
from mnist_v2_nxtf.policy import (
    ANN_POLICY,
    CONVERSION_POLICY,
    OFFICIAL_TEST_POLICY,
    POLICY_STATUS,
    validate_frozen_policy,
)

assert TOPOLOGY_STATUS == "P08_2_PAGING_ACCEPTED_P08_3_POLICY_FROZEN"
assert POLICY_STATUS == "P08_3_1_TRAINING_CONVERSION_POLICY_FROZEN"
assert OFFICIAL_TEST_POLICY == "LOCKED_UNTIL_P08_3_CHECKPOINT_AND_CONVERSION_FREEZE"
validate_frozen_policy()

model = build_ann()
compile_ann(model)
assert model.count_params() == EXPECTED_ANN_PARAMETERS == 7006

print(
    "PASS: P08.3.1 ANN policy "
    f"filters={ANN_POLICY.topology_filters} params={model.count_params()} "
    f"batch={ANN_POLICY.batch_size} max_epochs={ANN_POLICY.max_epochs} "
    f"dropout={ANN_POLICY.dropout_rate}"
)
print(
    "PASS: P08.3.1 conversion policy "
    f"timesteps={CONVERSION_POLICY.primary_timesteps} "
    f"weight_bits={CONVERSION_POLICY.weight_bits} "
    f"bias_bits={CONVERSION_POLICY.bias_bits} "
    f"threshold={CONVERSION_POLICY.threshold_mantissa} "
    f"reset={CONVERSION_POLICY.reset_mode}"
)
print(f"PASS: official MNIST test policy={OFFICIAL_TEST_POLICY}")
PY

echo
echo "P08.3.1 training/conversion policy preflight completed successfully."
echo "This gate does not train the ANN and does not load the official MNIST test split."
echo "After independent acceptance, P08.3.2 may train/select using only the 55k/5k train-validation boundary."
