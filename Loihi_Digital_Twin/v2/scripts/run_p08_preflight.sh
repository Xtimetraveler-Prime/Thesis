#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
BUILD_DIR="$PROJECT_DIR/build/p08_preflight"

export PYTHONPATH="$PROJECT_DIR/src:$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO_DIR"

# P08's structural mapping probe uses NumPy arrays even before TensorFlow
# training begins. Keep that dependency out of the long-lived .venv-v2
# environment and require the dedicated P08 application environment instead.
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
        "  python -m pip install -e 'applications/mnist_v2_nxtf[train,test]'"
        % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/config.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/data.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/topology.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/training.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/conversion.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/inference.py \
    applications/mnist_v2_nxtf/scripts/train_candidate.py \
    applications/mnist_v2_nxtf/scripts/convert_candidate.py \
    applications/mnist_v2_nxtf/scripts/audit_candidate.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_candidate_mapping.py \
    Loihi_Digital_Twin/v2/tests/test_p06_compiler.py \
    Loihi_Digital_Twin/v2/tests/test_p05_hardware_image.py

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
python applications/mnist_v2_nxtf/scripts/audit_candidate.py \
    --output "$BUILD_DIR/p08_candidate_mapping.json"

python - "$BUILD_DIR/p08_candidate_mapping.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text())
assert payload["schema"] == "p08-candidate-mapping-audit-v1"
assert payload["topology"]["total_spiking_neurons"] == 2058
assert payload["topology"]["trainable_weights"] == 7796
assert payload["logical_core_count"] == 3
assert payload["physical_engine_count"] == 1
assert payload["logical_capacity_changed"] is False
assert payload["connection_sharing"]["expanded_connections"] == 81800
assert payload["connection_sharing"]["stored_shared_parameters"] == 10076
assert payload["static_route_estimate"] == {"total": 1772, "local": 812, "remote": 960}
print(
    "PASS: P08 candidate artifact pipeline "
    "neurons=2058 weights=7796 logical_cores=3 physical_engines=1 "
    "expanded=81800 stored=10076 local_routes=812 remote_routes=960"
)
PY

echo
echo "P08 source/mapping preflight completed successfully."
echo "Artifacts: $BUILD_DIR"
