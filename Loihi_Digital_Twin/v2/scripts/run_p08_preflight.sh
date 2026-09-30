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
for module in ("numpy", "pytest"):
    try:
        __import__(module)
    except ImportError:
        missing.append(module)
if missing:
    raise SystemExit(
        "ERROR: P08 preflight requires the dedicated .venv-p08 application "
        "environment (missing: %s). From the repository root run:\n"
        "  python3.12 -m venv .venv-p08\n"
        "  source .venv-p08/bin/activate\n"
        "  python -m pip install --upgrade pip\n"
        "  python -m pip install -e Loihi_Digital_Twin/v2\n"
        "  python -m pip install -e 'applications/mnist_v2_nxtf[test]'"
        % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/config.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/data.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/reconstruction.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/structural.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    Loihi_Digital_Twin/v2/tests/test_p06_compiler.py \
    Loihi_Digital_Twin/v2/tests/test_p05_hardware_image.py

python - <<'PY'
from mnist_v2_nxtf import PRIMARY_TIMESTEPS, TOPOLOGY_STATUS
from mnist_v2_nxtf.reconstruction import PROPOSED_METRICS, RECONSTRUCTION_STATUS

assert TOPOLOGY_STATUS == "UNFROZEN_NXTF_EMULATION_REALIGN"
assert PRIMARY_TIMESTEPS == 100
print(
    "PASS: P08 NxTF-emulation scaffold "
    f"topology_status={TOPOLOGY_STATUS} primary_timesteps={PRIMARY_TIMESTEPS}"
)
print(
    "PASS: P08.1 source-bounded reconstruction proposal "
    f"status={RECONSTRUCTION_STATUS} filters={PROPOSED_METRICS.filters} "
    f"neurons={PROPOSED_METRICS.neuron_count} "
    f"params={PROPOSED_METRICS.trainable_parameters} "
    f"expanded={PROPOSED_METRICS.expanded_connections}"
)
PY

echo
echo "P08.1 source-reconstruction preflight completed successfully."
echo "The topology is still proposed/unfrozen; do not train or evaluate the test set yet."
