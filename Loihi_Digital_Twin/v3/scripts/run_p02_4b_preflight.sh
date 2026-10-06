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

prepare = (root / "vivado/p02_4b_xsdb_prepare.tcl").read_text(encoding="utf-8")
dump = (root / "vivado/p02_4b_xsdb_dump.tcl").read_text(encoding="utf-8")

shared_physical_target_tokens = (
    "p02b_select_physical_memory_target",
    "foreach candidate {PSU APU}",
    "physical DDR access target",
    "mrd -bin -file",
)
for label, text in (("prepare", prepare), ("dump", dump)):
    for token in shared_physical_target_tokens:
        if token not in text:
            raise SystemExit(
                f"FAIL: P02.4b XSDB {label} script missing physical-target contract {token!r}"
            )

prepare_only_tokens = (
    "p02_binary_files_equal",
    "physical DDR readback mismatch",
    "byte-verified by physical readback",
)
for token in prepare_only_tokens:
    if token not in prepare:
        raise SystemExit(
            f"FAIL: P02.4b XSDB prepare script missing readback-verification contract {token!r}"
        )

if "verify -data" in prepare:
    raise SystemExit("FAIL: P02.4b prepare script still uses context-dependent verify -data")

print("PASS: P02.4b XSDB physical PSU/APU memory-target preflight")
print("PASS: P02.4b physical DDR binary-readback verification preflight")

runtime = (root / "vivado/p02_4b_five_over_three.tcl").read_text(encoding="utf-8")
required = (
    "p02b_page_transfer 1 1",
    "p02b_page_transfer 0 0",
    "P02B_EVENT_COUNT",
    "p02b_decode_packet",
    "authoritative_backing=k26-ddr",
    'p02b_expect "completed dispatches" [p02b_p08_input 8] 35',
    'puts $result "completed_dispatches=$P02B_DISPATCHES"',
    "debug idle before page",
    "debug idle before dispatch",
    "start_blocked",
    "p02b_verify_static_resident_image",
    "p02b_verify_initial_resident_image",
    "external event readback",
    "p02b_host_response_snapshot",
    "ACK/RVALID/ERROR/RDATA must be sampled from one VIO refresh",
)
for token in required:
    if token not in runtime:
        raise SystemExit(f"FAIL: P02.4b runtime contract missing {token!r}")

manifest = __import__("json").loads((root / "vivado/build/p02_4b_preflight/fixture/manifest.json").read_text(encoding="utf-8"))
expected_manifest = {
    "schema": "p02-4b-five-over-three-ring-v1",
    "logical_core_count": 5,
    "resident_context_count": 3,
    "physical_engine_count": 1,
    "timesteps": 7,
    "dispatch_count": 35,
    "expected_packet_count_total": 30,
    "authoritative_backing": "k26-ddr",
    "trace_fingerprint": "9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac",
    "manifest_fingerprint": "15288f1f6245c39a98167f610802d9146debfc6e3266981eb4bcd5245a1c975d",
}
for key, expected in expected_manifest.items():
    actual = manifest.get(key)
    if actual != expected:
        raise SystemExit(
            f"FAIL: P02.4b frozen manifest {key}={actual!r}, expected {expected!r}"
        )
print("PASS: P02.4b frozen golden manifest preflight")

print("PASS: P02.4b Tcl/runtime contract preflight")
PY

grep -q "PASS: P02.4b five-over-three golden fixture generated" "$TMP_DIR/generate.log"
grep -q "PASS: P02.4b all five DDR backing records match golden final images" "$TMP_DIR/verify.log"

echo "PASS: P02.4b software preflight completed successfully."
