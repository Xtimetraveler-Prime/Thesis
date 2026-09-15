#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd -- "$APP_DIR/../.." && pwd)"
CORE_DIR="$REPO_ROOT/Neuromorphic Digital Twin"
VENV="${MNIST_12_VENV:-$REPO_ROOT/.venv-mnist-catalyst}"
CATALYST_DIR="${MNIST_12_CATALYST_DIR:-$CORE_DIR/build/m13_1/catalyst-n1}"
PYTHON="${PYTHON:-python3}"

"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install -e "$CORE_DIR"
"$VENV/bin/python" -m pip install -e "$APP_DIR"

bash "$CORE_DIR/scripts/fetch_m13_1_catalyst.sh" "$CATALYST_DIR"

PYTHONPATH="$CATALYST_DIR/sdk:$CORE_DIR/src:$APP_DIR${PYTHONPATH:+:$PYTHONPATH}" \
"$VENV/bin/python" - <<'PY'
from pathlib import Path
import neurocore
import mnist_app
import neuromorphic_twin
from neurocore.constants import NEURONS_PER_CORE, POOL_DEPTH

if int(NEURONS_PER_CORE) != 1024:
    raise SystemExit(f"ERROR: pinned Catalyst SDK NEURONS_PER_CORE={NEURONS_PER_CORE}, expected 1024")
if int(POOL_DEPTH) != 32768:
    raise SystemExit(f"ERROR: pinned Catalyst SDK POOL_DEPTH={POOL_DEPTH}, expected 32768")
print(f"MNIST-12 Catalyst environment PASS: NEURONS_PER_CORE={NEURONS_PER_CORE} POOL_DEPTH={POOL_DEPTH}")
PY

echo "Activate with: source '$VENV/bin/activate'"
echo "For Catalyst runs export: PYTHONPATH='$CATALYST_DIR/sdk:$CORE_DIR/src:$APP_DIR'"
