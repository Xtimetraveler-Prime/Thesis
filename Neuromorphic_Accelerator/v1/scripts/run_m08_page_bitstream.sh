#!/usr/bin/env bash
# M08.2b consolidated implementation gate: offline BITSTREAM ONLY.
# Uses an ORIGINAL SHA-verified K26 post-route DCP, not an old BD or
# Loihi bitstream. Does NOT program FPGA, access Linux MMIO, DDR or DMA.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$HERE/.." && pwd)"
BASE="${M08_EVIDENCE_BASE:-$HOME/Thesis_Evidence/M08}"
ROUTE="${M08_ROUTE_EVIDENCE_DIR:-}"
if [[ "${M08_ACCEPT_RTSTAT10:-NO}" != "YES" ]]; then
  echo "ERROR: set M08_ACCEPT_RTSTAT10=YES only after inspecting the original SmartConnect RTSTAT-10 DRC report" >&2
  exit 2
fi
if [[ -z "$ROUTE" || ! -d "$ROUTE" || -L "$ROUTE" ]]; then
  echo "ERROR: set M08_ROUTE_EVIDENCE_DIR to the owner ORIGINAL complete routed-evidence folder" >&2
  exit 2
fi
if [[ ! -d "$BASE" ]]; then
  echo "ERROR: operator must create evidence parent: $BASE" >&2
  exit 2
fi
command -v vivado >/dev/null || {
  echo "ERROR: source genuine Vivado 2025.2 settings64.sh" >&2
  exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *2025.2* ]]; then
  echo "ERROR: wrong Vivado version" >&2
  exit 2
fi
DIR="$(mktemp -d "$BASE/m08_2b_bitstream_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
printf 'M08_BITSTREAM_EVIDENCE_DIR=%s\n' "$DIR"
export M08_ROOT="$ROOT"
manifest() {
  python3 - "$1" <<'PY'
import os, sys
from pathlib import Path
from hashlib import sha256
root=Path(os.environ["M08_ROOT"])
names=(
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
    "scripts/m08_page_release_preflight.py",
    "scripts/m08_page_bitstream_candidate.tcl",
    "scripts/m08_page_bitstream_audit.py",
    "scripts/run_m08_page_bitstream.sh",
)
with Path(sys.argv[1]).open("x", encoding="utf-8") as out:
    for name in names:
        out.write(f"{sha256((root/name).read_bytes()).hexdigest()}  {name}\n")
PY
}
manifest "$DIR/source_sha256_before.txt"
# The ORIGINAL route folder is read-only; never append, copy back or
# mutate its native log, reports, checkpoint or SHA receipt.
python3 "$ROOT/scripts/m08_page_release_preflight.py" \
  --route-dir "$ROUTE" --source-root "$ROOT" \
  --output "$DIR/01_release_preflight.json"
ROUTE_DCP="$ROUTE/10_m08_page_post_route.dcp"
set +e
(
 cd "$DIR"
 vivado -mode batch -nojournal -nolog \
   -source "$ROOT/scripts/m08_page_bitstream_candidate.tcl" \
   -tclargs "$ROUTE_DCP" "$DIR"
) >"$DIR/02_vivado_bitstream.log" 2>&1
STATUS=$?
set -e
printf 'exit_status=%d\n' "$STATUS" > "$DIR/result.txt"
manifest "$DIR/source_sha256_after.txt"
if ! cmp -s "$DIR/source_sha256_before.txt" "$DIR/source_sha256_after.txt"; then
  echo "M08_BITSTREAM_FAILED original checkout source mutated; preserve $DIR" >&2
  exit 2
fi
if (( STATUS != 0 )); then
  echo "M08_BITSTREAM_VIVADO_FAILED exit_status=$STATUS evidence=$DIR" >&2
  exit "$STATUS"
fi
python3 "$ROOT/scripts/m08_page_bitstream_audit.py" \
  --release-dir "$DIR" --route-dir "$ROUTE" --source-root "$ROOT" \
  --output "$DIR/07_m08_bitstream_independent_audit.json"
sha256sum \
  "$DIR/01_release_preflight.json" "$DIR/02_vivado_bitstream.log" \
  "$DIR/03_rechecked_drc.rpt" "$DIR/04_rechecked_timing.rpt" \
  "$DIR/05_m08_safe_page.bit" "$DIR/06_bitstream_native_metrics.txt" \
  "$DIR/07_m08_bitstream_independent_audit.json" \
  > "$DIR/08_evidence_sha256.txt"
echo "M08_OFFLINE_KV260_SAFE_PAGE_BITSTREAM_AND_SOURCE_RECEIPT_AUDITED"
echo "M08_BITSTREAM_CREATED_NO_KV260_PROGRAMMING_NO_NEURAL_INFERENCE"
echo "M08_BITSTREAM_EVIDENCE_DIR=$DIR"
