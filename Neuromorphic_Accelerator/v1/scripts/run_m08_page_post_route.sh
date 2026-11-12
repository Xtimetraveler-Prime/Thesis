#!/usr/bin/env bash
# M08.2b.4a: genuine local K26 synthesis & route + original reports.
# DOES NOT create bitstream, program FPGA or touch DDR/Linux MMIO.
# NEVER reuse or modify any accepted M08.2a/M08.2b.3 evidence folder.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$HERE/.." && pwd)"
TCL="$ROOT/scripts/m08_page_post_route_candidate.tcl"
BASE="${M08_EVIDENCE_BASE:-$HOME/Thesis_Evidence/M08}"
JOBS="${M08_ROUTE_JOBS:-4}"
if ! [[ "$JOBS" =~ ^[1-8]$ ]]; then
  echo "ERROR: M08_ROUTE_JOBS must be an integer 1..8" >&2
  exit 2
fi
command -v vivado >/dev/null 2>&1 || {
  echo "ERROR: source genuine Vivado 2025.2 settings64.sh first" >&2
  exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *2025.2* ]]; then
  echo "ERROR: requires original Vivado 2025.2" >&2
  exit 2
fi
test -f "$TCL"
test -d "$BASE" || {
  echo "ERROR: operator must create evidence parent first: $BASE" >&2
  exit 2
}
DIR="$(mktemp -d "$BASE/m08_2b_4_route_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
printf 'M08_ROUTE_EVIDENCE_DIR=%s\n' "$DIR"
export M08_ROOT="$ROOT"
# Pin ten original sources to the exact checkout. Include all seven
# already-accepted page-BD files plus three NEW route-specific tools.
manifest() {
  python3 - "$1" <<'PY'
import os, sys
from hashlib import sha256
from pathlib import Path
root = Path(os.environ["M08_ROOT"])
names = (
    "rtl/m08/m08_axil_readonly_identity.v",
    "rtl/m08/m08_host_staged_page_bank.sv",
    "rtl/m08/m08_axil_page_control.sv",
    "rtl/m08/m08_ps_page_safe_shell.v",
    "scripts/m08_page_ps_bd_candidate.tcl",
    "scripts/m08_page_bd_audit.py",
    "scripts/run_m08_page_bd.sh",
    "scripts/m08_page_post_route_candidate.tcl",
    "scripts/m08_page_post_route_audit.py",
    "scripts/run_m08_page_post_route.sh",
)
with Path(sys.argv[1]).open("x", encoding="utf-8") as output:
    for name in names:
        output.write(f"{sha256((root/name).read_bytes()).hexdigest()}  {name}\n")
PY
}
manifest "$DIR/source_sha256_before.txt"
set +e
(
  cd "$DIR"
  vivado -mode batch -nojournal -nolog -source "$TCL" \
    -tclargs "$ROOT" "$DIR" "$JOBS"
) >"$DIR/01_vivado_impl.log" 2>&1
status=$?
set -e
printf 'exit_status=%d\n' "$status" >"$DIR/result.txt"
manifest "$DIR/source_sha256_after.txt"
if ! cmp -s "$DIR/source_sha256_before.txt" "$DIR/source_sha256_after.txt"; then
  echo "M08_ROUTE_ORIGINAL_FAILED source changed during tool execution; preserve DIR=$DIR" >&2
  exit 2
fi
if (( status != 0 )); then
  echo "M08_ROUTE_VIVADO_ORIGINAL_FAILED exit_status=$status evidence=$DIR" >&2
  exit "$status"
fi
python3 "$ROOT/scripts/m08_page_post_route_audit.py" \
    --evidence-dir "$DIR" --source-root "$ROOT" \
    --output "$DIR/11_m08_route_independent_audit.json"
sha256sum \
    "$DIR/01_vivado_impl.log" \
    "$DIR/02_vivado_page_bd_readback.txt" \
    "$DIR/03_page_bd_export.tcl" \
    "$DIR/04_implementation_metrics.txt" \
    "$DIR/05_timing_summary_post_route.rpt" \
    "$DIR/06_utilization_post_route.rpt" \
    "$DIR/07_drc_post_route.rpt" \
    "$DIR/08_methodology_post_route.rpt" \
    "$DIR/09_clock_utilization_post_route.rpt" \
    "$DIR/10_m08_page_post_route.dcp" \
    "$DIR/11_m08_route_independent_audit.json" \
    >"$DIR/12_evidence_sha256.txt"
echo "M08_NATIVE_POST_ROUTE_SOURCE_AND_REPORT_RECEIPT_AUDITED_NOT_PHYSICAL"
echo "M08_NATIVE_ROUTE_NO_BITSTREAM_NO_FPGA_PROGRAMMING"
echo "M08_ROUTE_EVIDENCE_DIR=$DIR"
