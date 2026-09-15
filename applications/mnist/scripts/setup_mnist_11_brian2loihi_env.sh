#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd -- "$APP_DIR/../.." && pwd)"
CORE_DIR="$REPO_ROOT/Neuromorphic Digital Twin"
VENV="${MNIST_11_VENV:-$REPO_ROOT/.venv-mnist-brian2loihi}"
PYTHON="${PYTHON:-python3}"

"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install -e "$CORE_DIR[compare]"
"$VENV/bin/python" -m pip install -e "$APP_DIR"

"$VENV/bin/python" - <<'PY'
from importlib.metadata import version
import brian2
import brian2_loihi
import neuromorphic_twin
import mnist_app

expected = {
    "numpy": "1.26.4",
    "brian2": "2.9.0",
    "brian2-loihi": "0.5.2",
}
for package, wanted in expected.items():
    actual = version(package)
    if actual != wanted:
        raise SystemExit(f"ERROR: {package}={actual}, expected {wanted}")
print("MNIST-11 environment PASS:", ", ".join(f"{p}={version(p)}" for p in expected))
PY

echo "Activate with: source '$VENV/bin/activate'"
