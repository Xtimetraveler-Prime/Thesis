#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TMP_DIR="$V3_DIR/vivado/build/p02_4b_preflight"

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR/fixture" "$TMP_DIR/dumps"

cd "$V3_DIR"

PYTHONPATH="$V3_DIR/src" python -m pytest     tests/test_p02_ddr_abi.py     tests/test_p02_ddr_backing.py     tests/test_p02_physical_fixture.py     tests/test_p02_4b_ring_fixture.py     -q | tee "$TMP_DIR/pytest.log"

PYTHONPATH="$V3_DIR/src" python scripts/p02_4b_ring_fixture.py generate     --output-dir "$TMP_DIR/fixture"     | tee "$TMP_DIR/generate.log"

for core in 0 1 2 3 4; do
    cp "$TMP_DIR/fixture/core${core}_expected.bin"        "$TMP_DIR/dumps/core${core}_after.bin"
done

PYTHONPATH="$V3_DIR/src" python scripts/p02_4b_ring_fixture.py verify     --fixture-dir "$TMP_DIR/fixture"     --dump-dir "$TMP_DIR/dumps"     | tee "$TMP_DIR/verify.log"

bash -n scripts/run_p02_4b_five_over_three.sh

python - "$V3_DIR" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
paths = (
    "vivado/p02_4b_xsdb_prepare.tcl",
    "vivado/p02_4b_xsdb_dump.tcl",
    "vivado/p02_4b_five_over_three.tcl",
)
for relative in paths:
    text = (root / relative).read_text(encoding="utf-8")
    for left, right in (("{", "}"), ("[", "]")):
        if text.count(left) != text.count(right):
            raise SystemExit(f"FAIL: unbalanced {left}{right} delimiters in {relative}")

runtime = (root / "vivado/p02_4b_five_over_three.tcl").read_text(encoding="utf-8")
required = (
    "p02b_page_transfer 1 1",
    "p02b_page_transfer 0 0",
    "P02B_EVENT_COUNT",
    "p02b_decode_packet",
    "authoritative_backing=k26-ddr",
    "completed_dispatches=35",
)
for token in required:
    if token not in runtime:
        raise SystemExit(f"FAIL: P02.4b runtime contract missing {token!r}")

print("PASS: P02.4b Tcl/runtime contract preflight")
PY

grep -q "PASS: P02.4b five-over-three golden fixture generated" "$TMP_DIR/generate.log"
grep -q "PASS: P02.4b all five DDR backing records match golden final images" "$TMP_DIR/verify.log"

echo "PASS: P02.4b software preflight completed successfully."
