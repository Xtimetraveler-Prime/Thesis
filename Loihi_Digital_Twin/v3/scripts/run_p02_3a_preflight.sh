#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$V3_DIR"

PYTHONPATH="$V3_DIR/src" python -m pytest     tests/test_p02_ddr_abi.py     tests/test_p02_ddr_backing.py     -q | tee /tmp/v3_p02_3a_pytest.log

if grep -Eq 'failed|error|ERROR|FAIL' /tmp/v3_p02_3a_pytest.log; then
    echo "ERROR: P02 Python focused gate failed." >&2
    exit 3
fi

bash "$V3_DIR/rtl/run_p02_context_page_bank_walker_sim.sh"

echo "PASS: P02.3a preflight completed successfully."
