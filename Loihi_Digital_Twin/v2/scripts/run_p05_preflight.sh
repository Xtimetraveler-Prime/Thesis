#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

python -m pytest -q \
    tests/test_virtualization.py \
    tests/test_p05_hardware_image.py \
    tests/test_multicore_architecture.py

bash rtl/run_p05_virtualized_controller_sim.sh

TMP_VECTORS="$(mktemp)"
trap 'rm -f "$TMP_VECTORS"' EXIT
PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 examples/generate_p05_physical_vectors.py --output "$TMP_VECTORS"
grep -q 'name logical_id_ring' "$TMP_VECTORS"
grep -q 'name local_remote_fanin' "$TMP_VECTORS"
grep -q 'set P05_CONTEXTS 3' "$TMP_VECTORS"

echo
echo "P05 source preflight completed successfully."
