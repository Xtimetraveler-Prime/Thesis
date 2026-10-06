#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$V3_DIR/vivado/build/p02_4b_paging_stress"
FIXTURE_DIR="$BUILD_DIR/fixture"
LOG_DIR="$BUILD_DIR/logs"
RESULT_FILE="$BUILD_DIR/p02_4b_paging_stress_result.txt"

P02_IMPL_REPORT_DIR="${P02_IMPL_REPORT_DIR:-$V3_DIR/vivado/build/p02_ddr_impl/reports}"
BIT_FILE="${P02_BIT_FILE:-$P02_IMPL_REPORT_DIR/p02_ddr_paged.bit}"
LTX_FILE="${P02_LTX_FILE:-$P02_IMPL_REPORT_DIR/p02_ddr_paged.ltx}"
XSDB_SERVER_URL="${P02_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
VIVADO_SERVER_URL="${P02_VIVADO_SERVER_URL:-localhost:3121}"

EXPECTED_BIT_SHA="0d96ae6af0cc313ccbd8f9c802aeb0c8c7946bfeabaca3152ef5c7b9d2b23f26"
EXPECTED_LTX_SHA="f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe"

for tool in python xsdb vivado sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required P02.4b paging-stress tool missing: $tool" >&2
        exit 2
    }
done

[[ "$(sha256sum "$BIT_FILE" | awk '{print $1}')" == "$EXPECTED_BIT_SHA" ]] || {
    echo "ERROR: paging-stress bitstream identity drifted" >&2
    exit 2
}
[[ "$(sha256sum "$LTX_FILE" | awk '{print $1}')" == "$EXPECTED_LTX_SHA" ]] || {
    echo "ERROR: paging-stress probes identity drifted" >&2
    exit 2
}

rm -rf "$BUILD_DIR"
mkdir -p "$FIXTURE_DIR" "$LOG_DIR"

cd "$V3_DIR"
PYTHONPATH="$V3_DIR/src" python scripts/p02_4b_ring_fixture.py generate     --output-dir "$FIXTURE_DIR"     | tee "$LOG_DIR/fixture_generate.log"

xsdb vivado/p02_4b_xsdb_prepare.tcl     "$FIXTURE_DIR" "$XSDB_SERVER_URL"     | tee "$LOG_DIR/xsdb_prepare.log"

vivado -mode batch     -source vivado/p02_4b_paging_stress.tcl     -tclargs         "$BIT_FILE"         "$LTX_FILE"         "$FIXTURE_DIR/p02_4b_vectors.tcl"         "$RESULT_FILE"         "$VIVADO_SERVER_URL"     2>&1 | tee "$LOG_DIR/paging_stress.log"

grep -q '^result=PASS$' "$RESULT_FILE"
grep -q 'PASS: P02.4b paging-only stress reproduced exact pre-failure transfer sequence without compute'     "$LOG_DIR/paging_stress.log"

echo "PASS: P02.4b paging-only physical stress gate completed."
echo "IMPORTANT: reboot the KV260 before normal Linux use."
