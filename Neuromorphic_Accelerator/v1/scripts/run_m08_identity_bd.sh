#!/usr/bin/env bash
# M08.2 genuine Vivado 2025.2 *BD VALIDATION ONLY* for isolated read-only ID.
# No package/bitstream, no FPGA programming, no PS DDR, no old evidence edits.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$HERE/.." && pwd)"
TCL="$ROOT/scripts/m08_identity_ps_bd_candidate.tcl"
BASE="${M08_EVIDENCE_BASE:-$HOME/Thesis_Evidence/M08}"

command -v vivado >/dev/null 2>&1 || {
  echo 'ERROR: vivado not on PATH. Source actual Vivado 2025.2 settings64.sh first.' >&2
  exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *2025.2* ]]; then
  echo 'ERROR: Vivado 2025.2 required for this K26 candidate' >&2
  exit 2
fi
test -f "$TCL"
test -d "$BASE" || {
  echo "ERROR: create operator evidence parent manually first: $BASE" >&2
  exit 2
}
DIR="$(mktemp -d "$BASE/m08_2_identity_bd_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
printf 'M08_IDENTITY_BD_EVIDENCE_DIR=%s\n' "$DIR"
export M08_ROOT="$ROOT"
python3 - "$DIR/source_sha256_before.txt" <<'PY'
from pathlib import Path
from hashlib import sha256
import os,sys
root=Path(os.environ["M08_ROOT"])
names=(
    "rtl/m08/m08_axil_readonly_identity.v",
    "scripts/m08_identity_ps_bd_candidate.tcl",
    "scripts/m08_identity_bd_audit.py",
    "scripts/run_m08_identity_bd.sh",
)
with Path(sys.argv[1]).open("x",encoding="utf-8") as output:
    for name in names:
        output.write(f"{sha256((root/name).read_bytes()).hexdigest()}  {name}\n")
PY
set +e
(
  cd "$DIR"
  vivado -mode batch -nojournal -nolog -source "$TCL" \
    -tclargs "$ROOT" "$DIR"
) >"$DIR/01_vivado_identity_bd.log" 2>&1
status=$?
set -e
printf 'exit_status=%d\n' "$status" >"$DIR/result.txt"
cp -- "$DIR/source_sha256_before.txt" "$DIR/source_sha256_after.txt"
# Recompute independent source SHA AFTER the actual tool returned, never
# simply claim the original manifest is still current.
python3 - "$DIR/source_sha256_after.txt" <<'PY'
from pathlib import Path
from hashlib import sha256
import os,sys
root=Path(os.environ["M08_ROOT"])
names=(
    "rtl/m08/m08_axil_readonly_identity.v",
    "scripts/m08_identity_ps_bd_candidate.tcl",
    "scripts/m08_identity_bd_audit.py",
    "scripts/run_m08_identity_bd.sh",
)
with Path(sys.argv[1]).open("w",encoding="utf-8") as output:
    for name in names:
        output.write(f"{sha256((root/name).read_bytes()).hexdigest()}  {name}\n")
PY
if (( status != 0 )); then
  echo "M08_VIVADO_BD_ORIGINAL_FAILED exit_status=$status evidence=$DIR" >&2
  exit "$status"
fi
python3 "$ROOT/scripts/m08_identity_bd_audit.py" \
  --evidence-dir "$DIR" --source-root "$ROOT" \
  --output "$DIR/04_m08_identity_independent_audit.json"
sha256sum "$DIR/01_vivado_identity_bd.log" \
  "$DIR/02_vivado_identity_bd_readback.txt" \
  "$DIR/03_identity_bd_export.tcl" \
  "$DIR/04_m08_identity_independent_audit.json" \
  >"$DIR/05_evidence_sha256.txt"
echo "M08_IDENTITY_BD_GENUINE_LOCAL_VIVADO_VALIDATED_NOT_A_BITSTREAM_OR_FPGA_TEST"
echo "M08_EVIDENCE_DIR=$DIR"
