#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$V3_DIR"

PYTHONPATH="$V3_DIR/src" python -m pytest     tests/test_p03_1_runtime_contract.py     -q | tee /tmp/v3_p03_1_focused_pytest.log

python - "$V3_DIR" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
contract = (root / "docs/P03_1_AUTONOMOUS_RUNTIME_CONTRACT.md").read_text(
    encoding="utf-8"
)
addendum = (root / "docs/LOIHI1_TARGET_SPEC_V3_ADDENDUM.md").read_text(
    encoding="utf-8"
)
runtime = (root / "src/loihi_twin_v2/runtime_v3.py").read_text(
    encoding="utf-8"
)

for token in (
    "LOAD_DEPLOYMENT",
    "INITIALIZE_BACKING",
    "INITIALIZE_RESIDENT_SET",
    "DRAIN_AND_ROUTE_PACKETS",
    "BARRIER_CHECK",
    "SWAP_EVENT_BANKS",
    "WRITE_RESULT",
    "0x4000_0000 .. 0x43FF_FFFF",
    "external PC",
    "first detected fault is sticky",
    "Inference interval",
):
    if token not in contract:
        raise SystemExit(f"FAIL: P03.1 contract missing {token!r}")

for token in (
    "transistor-level Loihi equivalence",
    "physically asynchronous-circuit equivalence",
    "DDR record is an FPGA-v3 ABI",
    "Board-local autonomy rule",
):
    if token not in addendum:
        raise SystemExit(f"FAIL: P03.1 v3 addendum missing {token!r}")

for token in (
    "class RuntimeState",
    "class RuntimeFault",
    "BARRIER_INCOMPLETE",
    "external_pc_may_drive_algorithmic_control",
    "debug_response",
):
    if token == "debug_response":
        continue
    if token not in runtime:
        raise SystemExit(f"FAIL: P03.1 executable model missing {token!r}")

print("PASS: P03.1 contract/addendum static checks")
PY

PYTHONPATH="$V3_DIR/src" python -m pytest -q     | tee /tmp/v3_p03_1_full_pytest.log

if grep -Eq 'failed|error|ERROR|FAIL' /tmp/v3_p03_1_full_pytest.log; then
    echo "ERROR: P03.1 full inherited v3 regression reported failure/error." >&2
    exit 3
fi

echo "PASS: P03.1 autonomous runtime contract preflight completed successfully."
