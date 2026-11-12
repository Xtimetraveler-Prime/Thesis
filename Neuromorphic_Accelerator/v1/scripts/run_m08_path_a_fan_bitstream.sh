#!/usr/bin/env bash
# M08.2b Path A new OFFLINE fan-safe page .bit release on Linux PC ONLY.
# NO xmutil, FPGA programming, firmware install, PS AXI, fan or boot writes.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(cd -- "$HERE/.." && pwd)"
BASE="${M08_EVIDENCE_BASE:-$HOME/Thesis_Evidence/M08}"
ROUTE="${M08_FAN_ROUTE_EVIDENCE_DIR:-}"
if [[ "${M08_ACCEPT_FAN_RTSTAT10:-NO}" != YES ]]; then
    echo "ERROR: owner must explicitly review genuine RTSTAT-10 then set M08_ACCEPT_FAN_RTSTAT10=YES" >&2
    exit 2
fi
if [[ -z "$ROUTE" || ! -d "$ROUTE" || -L "$ROUTE" ]]; then
    echo "ERROR: M08_FAN_ROUTE_EVIDENCE_DIR must be the ORIGINAL completed routed evidence folder" >&2
    exit 2
fi
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
    echo "ERROR: trusted existing M08 owner evidence parent required" >&2
    exit 2
fi
command -v vivado >/dev/null || {
    echo "ERROR: source genuine PC Vivado 2025.2 settings64.sh" >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *2025.2* ]]; then
    echo "ERROR: native Vivado 2025.2 required" >&2
    exit 2
fi
DIR="$(mktemp -d "$BASE/m08_2b_path_a_fan_bitstream_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
echo "M08_PATH_A_FAN_BITSTREAM_EVIDENCE_DIR=$DIR"
files=(
  scripts/m08_path_a_fan_release_preflight.py
  scripts/m08_path_a_fan_bitstream.tcl
  scripts/m08_path_a_fan_bitstream_audit.py
  scripts/run_m08_path_a_fan_bitstream.sh
)
manifest() {
  (
    cd "$ROOT"
    sha256sum -- "${files[@]}"
  ) > "$1"
}
manifest "$DIR/00_source_sha256_before.txt"
printf 'source_head=%s\noriginal_route_dir=%s\n' \
  "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unavailable)" "$ROUTE" \
  > "$DIR/00_owner_input.txt"
PREFLIGHT_RC=99
VIVADO_RC=99
AUDIT_RC=99
DCP_SHA=""
set +e
python3 "$HERE/m08_path_a_fan_release_preflight.py" \
    --route-dir "$ROUTE" --source-root "$ROOT" \
    --output "$DIR/01_original_route_preflight.json" \
    > "$DIR/01_preflight_console.log" 2>&1
PREFLIGHT_RC=$?
set -e
printf 'preflight_exit_status=%d\n' "$PREFLIGHT_RC" > "$DIR/01_preflight_status.txt"
if (( PREFLIGHT_RC == 0 )); then
  # Original route folder remains read-only. Hash original first, copy,
  # independently hash/cmp new snapshot BEFORE opening native checkpoint.
  DCP_SHA="$(python3 - "$DIR/01_original_route_preflight.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    print(json.load(f)["original_route_dcp_sha256"])
PY
)"
  if [[ "$(sha256sum -- "$ROUTE/48_fan_post_route.dcp" | cut -d ' ' -f1)" != "$DCP_SHA" ]]; then
    echo "M08_PATH_A_FAN_ROUTE_DCP_CHANGED_AFTER_PREFLIGHT preserve=$DIR" >&2
    exit 3
  fi
  cp -- "$ROUTE/48_fan_post_route.dcp" "$DIR/48_fan_post_route.dcp"
  COPY_SHA="$(sha256sum -- "$DIR/48_fan_post_route.dcp" | cut -d ' ' -f1)"
  printf 'copied_dcp_sha256=%s\n' "$COPY_SHA" > "$DIR/04_copied_dcp_sha256.txt"
  if [[ "$COPY_SHA" == "$DCP_SHA" ]]; then
    set +e
    (
      cd "$DIR"
      vivado -mode batch -nojournal -nolog \
        -source "$HERE/m08_path_a_fan_bitstream.tcl" \
        -tclargs "$DIR/48_fan_post_route.dcp" "$DIR" "$DCP_SHA"
    ) > "$DIR/02_vivado_fan_bitstream.log" 2>&1
    VIVADO_RC=$?
    set -e
  else
    printf 'M08 copied routed DCP SHA mismatch; native Vivado NOT attempted\n' > "$DIR/02_vivado_fan_bitstream.log"
  fi
else
  printf 'M08 original route preflight failed; native Vivado NOT attempted\n' > "$DIR/02_vivado_fan_bitstream.log"
fi
printf 'vivado_exit_status=%d\n' "$VIVADO_RC" > "$DIR/02_vivado_fan_bitstream_exit.txt"
manifest "$DIR/03_source_sha256_after.txt"
if (( PREFLIGHT_RC == 0 && VIVADO_RC == 0 )) &&
    cmp -s "$DIR/00_source_sha256_before.txt" "$DIR/03_source_sha256_after.txt"; then
  set +e
  python3 "$HERE/m08_path_a_fan_bitstream_audit.py" \
    --release-dir "$DIR" --route-dir "$ROUTE" --source-root "$ROOT" \
    --output "$DIR/07_fan_bitstream_independent_audit.json" \
    > "$DIR/07_audit_console.log" 2>&1
  AUDIT_RC=$?
  set -e
else
  printf 'M08 bitstream audit not run: preflight/Vivado failure or source drift\n' > "$DIR/07_audit_console.log"
fi
printf 'audit_exit_status=%d\n' "$AUDIT_RC" > "$DIR/07_audit_status.txt"
# Every output, even failed/partial vendor output, is preserved with its SHA.
(
  cd "$DIR"
  : > 08_evidence_sha256.txt
  for name in \
    00_source_sha256_before.txt 00_owner_input.txt \
    01_original_route_preflight.json 01_preflight_console.log 01_preflight_status.txt \
    48_fan_post_route.dcp 04_copied_dcp_sha256.txt \
    02_vivado_fan_bitstream.log 02_vivado_fan_bitstream_exit.txt \
    03_fan_release_drc.rpt 04_fan_release_timing.rpt \
    05_m08_path_a_fan_page.bit 06_fan_bitstream_metrics.txt \
    03_source_sha256_after.txt 07_fan_bitstream_independent_audit.json \
    07_audit_console.log 07_audit_status.txt; do
    if [[ -f "$name" ]]; then sha256sum -- "$name" >> 08_evidence_sha256.txt; fi
  done
)
if (( PREFLIGHT_RC != 0 )); then
    echo "M08_PATH_A_FAN_ORIGINAL_ROUTE_PREFLIGHT_FAILED preserve=$DIR" >&2
    exit 3
fi
if (( VIVADO_RC != 0 )); then
    echo "M08_PATH_A_FAN_NATIVE_BITSTREAM_FAILED preserve=$DIR" >&2
    exit 3
fi
if ! cmp -s "$DIR/00_source_sha256_before.txt" "$DIR/03_source_sha256_after.txt"; then
    echo "M08_PATH_A_FAN_SOURCE_MUTATED preserve=$DIR" >&2
    exit 3
fi
if (( AUDIT_RC != 0 )); then
    echo "M08_PATH_A_FAN_NEW_BITSTREAM_AUDIT_FAILED preserve=$DIR" >&2
    exit 3
fi
echo "M08_PATH_A_NEW_OFFLINE_FAN_BITSTREAM_SHA_AUDITED_NOT_PROGRAMMED"
echo "M08_PATH_A_FAN_BITSTREAM_EVIDENCE_DIR=$DIR"
