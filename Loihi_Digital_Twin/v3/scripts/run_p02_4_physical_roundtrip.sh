#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

BUILD_DIR="$V3_DIR/vivado/build/p02_4_physical"
FIXTURE_DIR="$BUILD_DIR/fixture"
DUMP_DIR="$BUILD_DIR/dumps"
LOG_DIR="$BUILD_DIR/logs"

P02_IMPL_REPORT_DIR="${P02_IMPL_REPORT_DIR:-$V3_DIR/vivado/build/p02_ddr_impl/reports}"
BIT_FILE="${P02_BIT_FILE:-$P02_IMPL_REPORT_DIR/p02_ddr_paged.bit}"
LTX_FILE="${P02_LTX_FILE:-$P02_IMPL_REPORT_DIR/p02_ddr_paged.ltx}"

XSDB_SERVER_URL="${P02_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
VIVADO_SERVER_URL="${P02_VIVADO_SERVER_URL:-localhost:3121}"

EXPECTED_BIT_SHA="e9c3fb490f726a1169ed4b7f0c330f5806961c6471e2b13f63f5e042e97421b1"
EXPECTED_LTX_SHA="f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe"

for tool in python xsdb vivado sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required P02.4 tool is not on PATH: $tool" >&2
        exit 2
    }
done

for artifact in "$BIT_FILE" "$LTX_FILE"; do
    [[ -f "$artifact" ]] || {
        echo "ERROR: accepted P02.3b2 artifact missing: $artifact" >&2
        echo "Re-run the accepted P02.3b2 route gate or set P02_BIT_FILE/P02_LTX_FILE." >&2
        exit 2
    }
done

BIT_SHA="$(sha256sum "$BIT_FILE" | awk '{print $1}')"
LTX_SHA="$(sha256sum "$LTX_FILE" | awk '{print $1}')"
[[ "$BIT_SHA" == "$EXPECTED_BIT_SHA" ]] || {
    echo "ERROR: P02.4 bitstream is not the accepted P02.3b2 artifact." >&2
    echo "expected=$EXPECTED_BIT_SHA" >&2
    echo "actual=$BIT_SHA" >&2
    exit 2
}
[[ "$LTX_SHA" == "$EXPECTED_LTX_SHA" ]] || {
    echo "ERROR: P02.4 probes file is not the accepted P02.3b2 artifact." >&2
    echo "expected=$EXPECTED_LTX_SHA" >&2
    echo "actual=$LTX_SHA" >&2
    exit 2
}

rm -rf "$BUILD_DIR"
mkdir -p "$FIXTURE_DIR" "$DUMP_DIR" "$LOG_DIR"

cd "$V3_DIR"

python scripts/p02_4_fixture.py generate     --output-dir "$FIXTURE_DIR"     | tee "$LOG_DIR/fixture_generate.log"

cat <<'EOF'
P02.4 HARDWARE NOTE:
  The next step halts all visible Cortex-A53 cores before writing the reserved
  DDR backing window. If Linux is running on the board, its console/network
  activity will stop. Do not resume that Linux instance after the experiment;
  reboot the board when this acceptance run is complete.
EOF

xsdb vivado/p02_4_xsdb_prepare.tcl     "$FIXTURE_DIR" "$XSDB_SERVER_URL"     | tee "$LOG_DIR/xsdb_prepare.log"

vivado -mode batch     -source vivado/p02_4_vio_roundtrip.tcl     -tclargs "$BIT_FILE" "$LTX_FILE" "$VIVADO_SERVER_URL"     2>&1 | tee "$LOG_DIR/vio_roundtrip.log"

xsdb vivado/p02_4_xsdb_dump.tcl     "$DUMP_DIR" "$XSDB_SERVER_URL"     | tee "$LOG_DIR/xsdb_dump.log"

python scripts/p02_4_fixture.py verify     --fixture-dir "$FIXTURE_DIR"     --source-dump "$DUMP_DIR/source_after.bin"     --full-dump "$DUMP_DIR/full_after.bin"     --mutable-dump "$DUMP_DIR/mutable_after.bin"     | tee "$LOG_DIR/fixture_verify.log"

for marker in     "PASS: P02.4 deterministic DDR fixture generated"     "PASS: P02.4 DDR fixtures provisioned and byte-verified by physical readback with A53 cores halted"     "PASS: P02.4 VIO physical paging sequence completed successfully"     "PASS: P02.4 DDR source/full/mutable records dumped for comparison"     "PASS: P02.4 physical DDR round-trip dumps match expected records"; do
    grep -R -F -q "$marker" "$LOG_DIR" || {
        echo "ERROR: missing P02.4 acceptance marker: $marker" >&2
        exit 3
    }
done

echo
echo "PASS: P02.4a physical DDR round-trip acceptance completed successfully."
echo "Evidence directory: $BUILD_DIR"
echo "IMPORTANT: reboot the KV260 before resuming normal Linux use."
