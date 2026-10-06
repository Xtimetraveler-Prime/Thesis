#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$V3_DIR/vivado/build/p02_4b_five_over_three"
FIXTURE_DIR="$BUILD_DIR/fixture"
DUMP_DIR="$BUILD_DIR/forensic_dumps"
LOG_DIR="$BUILD_DIR/logs"

XSDB_SERVER_URL="${P02_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"

[[ -d "$FIXTURE_DIR" ]] || {
    echo "ERROR: P02.4b fixture directory missing: $FIXTURE_DIR" >&2
    exit 2
}

rm -rf "$DUMP_DIR"
mkdir -p "$DUMP_DIR" "$LOG_DIR"

cd "$V3_DIR"

# Do not reboot first. This intentionally inspects the DDR image left behind by
# a failed physical P02.4b attempt.
xsdb vivado/p02_4b_xsdb_dump.tcl     "$DUMP_DIR" "$XSDB_SERVER_URL"     | tee "$LOG_DIR/forensic_xsdb_dump.log"

set +e
PYTHONPATH="$V3_DIR/src" python scripts/p02_4b_forensic_ddr.py     --fixture-dir "$FIXTURE_DIR"     --dump-dir "$DUMP_DIR"     | tee "$LOG_DIR/forensic_analysis.log"
status=${PIPESTATUS[0]}
set -e

echo "P02_4B_FORENSIC_ANALYZER_STATUS=$status"
echo "Evidence directory: $DUMP_DIR"

# A static-bank mismatch is diagnostically useful, so preserve the analyzer
# status but do not hide its output behind an opaque shell failure.
exit "$status"
