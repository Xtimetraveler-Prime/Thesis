#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TMP_DIR="$V3_DIR/vivado/build/p02_4_preflight"

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR/fixture"

cd "$V3_DIR"

PYTHONPATH="$V3_DIR/src" python -m pytest     tests/test_p02_ddr_abi.py     tests/test_p02_ddr_backing.py     tests/test_p02_physical_fixture.py     -q | tee "$TMP_DIR/pytest.log"

python scripts/p02_4_fixture.py generate     --output-dir "$TMP_DIR/fixture"     > "$TMP_DIR/generate.log"

python scripts/p02_4_fixture.py verify     --fixture-dir "$TMP_DIR/fixture"     --source-dump "$TMP_DIR/fixture/source_core0.bin"     --full-dump "$TMP_DIR/fixture/full_expected_core126.bin"     --mutable-dump "$TMP_DIR/fixture/mutable_expected_core127.bin"     > "$TMP_DIR/verify.log"

bash -n scripts/run_p02_4_physical_roundtrip.sh

python - "$V3_DIR" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
for relative in (
    "vivado/p02_4_xsdb_prepare.tcl",
    "vivado/p02_4_xsdb_dump.tcl",
    "vivado/p02_4_vio_roundtrip.tcl",
):
    text = (root / relative).read_text(encoding="utf-8")
    # Lightweight delimiter sanity for Tcl source before the real XSDB/Vivado run.
    for left, right in (("{", "}"), ("[", "]")):
        if text.count(left) != text.count(right):
            raise SystemExit(f"FAIL: unbalanced {left}{right} delimiters in {relative}")
print("PASS: P02.4 Tcl source delimiter preflight")
PY

grep -q "PASS: P02.4 deterministic DDR fixture generated" "$TMP_DIR/generate.log"
grep -q "PASS: P02.4 physical DDR round-trip dumps match expected records" "$TMP_DIR/verify.log"

echo "PASS: P02.4a software preflight completed successfully."
