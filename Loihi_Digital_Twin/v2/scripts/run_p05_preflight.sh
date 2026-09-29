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

echo
 echo "P05 source preflight completed successfully."
