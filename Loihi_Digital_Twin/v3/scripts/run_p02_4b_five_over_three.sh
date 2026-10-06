#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

BUILD_DIR="$V3_DIR/vivado/build/p02_4b_five_over_three"
FIXTURE_DIR="$BUILD_DIR/fixture"
DUMP_DIR="$BUILD_DIR/dumps"
LOG_DIR="$BUILD_DIR/logs"
RESULT_FILE="$BUILD_DIR/p02_4b_result.txt"

P02_IMPL_REPORT_DIR="${P02_IMPL_REPORT_DIR:-$V3_DIR/vivado/build/p02_ddr_impl/reports}"
BIT_FILE="${P02_BIT_FILE:-$P02_IMPL_REPORT_DIR/p02_ddr_paged.bit}"
LTX_FILE="${P02_LTX_FILE:-$P02_IMPL_REPORT_DIR/p02_ddr_paged.ltx}"

XSDB_SERVER_URL="${P02_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
VIVADO_SERVER_URL="${P02_VIVADO_SERVER_URL:-localhost:3121}"

EXPECTED_BIT_SHA="e9c3fb490f726a1169ed4b7f0c330f5806961c6471e2b13f63f5e042e97421b1"
EXPECTED_LTX_SHA="f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe"

for tool in python xsdb vivado sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required P02.4b tool is not on PATH: $tool" >&2
        exit 2
    }
done

for artifact in "$BIT_FILE" "$LTX_FILE"; do
    [[ -f "$artifact" ]] || {
        echo "ERROR: accepted P02.3b2 artifact missing: $artifact" >&2
        exit 2
    }
done

BIT_SHA="$(sha256sum "$BIT_FILE" | awk '{print $1}')"
LTX_SHA="$(sha256sum "$LTX_FILE" | awk '{print $1}')"
[[ "$BIT_SHA" == "$EXPECTED_BIT_SHA" ]] || {
    echo "ERROR: P02.4b bitstream identity drifted: $BIT_SHA" >&2
    exit 2
}
[[ "$LTX_SHA" == "$EXPECTED_LTX_SHA" ]] || {
    echo "ERROR: P02.4b probes identity drifted: $LTX_SHA" >&2
    exit 2
}

rm -rf "$BUILD_DIR"
mkdir -p "$FIXTURE_DIR" "$DUMP_DIR" "$LOG_DIR"

cd "$V3_DIR"

PYTHONPATH="$V3_DIR/src" python scripts/p02_4b_ring_fixture.py generate     --output-dir "$FIXTURE_DIR"     | tee "$LOG_DIR/fixture_generate.log"

cat <<'EOF'
P02.4b HARDWARE NOTE:
  The test halts the visible Cortex-A53 cores before provisioning the project
  DDR window. Linux will stop responding. Reboot the KV260 after the run rather
  than resuming that Linux instance.
EOF

xsdb vivado/p02_4b_xsdb_prepare.tcl     "$FIXTURE_DIR" "$XSDB_SERVER_URL"     | tee "$LOG_DIR/xsdb_prepare.log"

vivado -mode batch     -source vivado/p02_4b_five_over_three.tcl     -tclargs         "$BIT_FILE"         "$LTX_FILE"         "$FIXTURE_DIR/p02_4b_vectors.tcl"         "$RESULT_FILE"         "$VIVADO_SERVER_URL"     2>&1 | tee "$LOG_DIR/physical.log"

[[ -f "$RESULT_FILE" ]] || {
    echo "ERROR: P02.4b physical runtime did not produce $RESULT_FILE" >&2
    exit 3
}
grep -q '^result=PASS$' "$RESULT_FILE" || {
    echo "ERROR: P02.4b physical result is not PASS" >&2
    cat "$RESULT_FILE" >&2
    exit 3
}
for expected in     'logical_core_count=5'     'resident_context_count=3'     'physical_engine_count=1'     'timesteps=7'     'completed_dispatches=35'     'barriers=7'     'authoritative_backing=k26-ddr'; do
    grep -q "^${expected}$" "$RESULT_FILE" || {
        echo "ERROR: P02.4b result missing $expected" >&2
        exit 3
    }
done

xsdb vivado/p02_4b_xsdb_dump.tcl     "$DUMP_DIR" "$XSDB_SERVER_URL"     | tee "$LOG_DIR/xsdb_dump.log"

PYTHONPATH="$V3_DIR/src" python scripts/p02_4b_ring_fixture.py verify     --fixture-dir "$FIXTURE_DIR"     --dump-dir "$DUMP_DIR"     | tee "$LOG_DIR/fixture_verify.log"

for marker in     "PASS: P02.4b five-over-three golden fixture generated"     "PASS: P02.4b five authoritative DDR backing records provisioned and byte-verified by physical readback"     "PASS: P02.4b initial residency logical={0 1 2} physical_slots=3"     "PASS: P02.4b five-over-three physical execution completed with K26 DDR authoritative"     "PASS: P02.4b five final DDR backing records dumped"     "PASS: P02.4b all five DDR backing records match golden final images"; do
    grep -R -F -q "$marker" "$LOG_DIR" || {
        echo "ERROR: missing P02.4b acceptance marker: $marker" >&2
        exit 4
    }
done

echo
echo "=== P02.4b physical result ==="
cat "$RESULT_FILE"
echo
echo "PASS: P02.4b five-logical-core / three-resident-context DDR-backed gate completed successfully."
echo "Evidence directory: $BUILD_DIR"
echo "IMPORTANT: reboot the KV260 before resuming normal Linux use."
