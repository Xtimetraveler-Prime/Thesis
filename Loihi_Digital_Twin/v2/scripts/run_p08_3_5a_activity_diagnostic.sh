#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
CONVERSION_DIR="$ARTIFACT_ROOT/p08_3_4_conversion"
DIAGNOSTIC_DIR="$ARTIFACT_ROOT/p08_3_5a_activity_diagnostic"

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
        "ERROR: P08.3.5a diagnostic requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/accepted_conversion.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/validation_snn.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/activity_diagnostic.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_p08_3_validation_snn.py \
    applications/mnist_v2_nxtf/tests/test_p08_3_activity_diagnostic.py

if [[ ! -f "$CONVERSION_DIR/conversion_manifest.json" ]]; then
    echo "ERROR: accepted P08.3.4 conversion artifact is missing: $CONVERSION_DIR" >&2
    exit 1
fi

rm -rf "$DIAGNOSTIC_DIR"
mkdir -p "$DIAGNOSTIC_DIR"

python -m mnist_v2_nxtf.activity_diagnostic \
    --conversion-dir "$CONVERSION_DIR" \
    --output-dir "$DIAGNOSTIC_DIR" \
    --examples 100

echo
echo "P08.3.5a activity diagnostic completed successfully."
echo "Diagnostic artifact: $DIAGNOSTIC_DIR/activity_diagnostic.json"
echo "No conversion/execution policy was changed by this diagnostic."
