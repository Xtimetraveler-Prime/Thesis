#!/usr/bin/env bash
# M08.2b Path A offline Vivado 2025.2 TTC0 channel-2 to A12 BD CANDIDATE.
# Does NOT build .bit, run synth/route, program KV260, alter Linux or fan.
# Keeps all original M08/Loihi evidence and accepted bitstream unchanged.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(cd -- "$HERE/.." && pwd)"
BASE="${M08_EVIDENCE_BASE:-$HOME/Thesis_Evidence/M08}"
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
  echo "ERROR: existing trusted owner M08 evidence parent required: $BASE" >&2
  exit 2
fi
command -v vivado >/dev/null 2>&1 || {
  echo "ERROR: source the genuine Vivado 2025.2 settings64.sh on your PC" >&2
  exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *2025.2* ]]; then
  echo "ERROR: M08 Path A requires native Vivado 2025.2" >&2
  exit 2
fi
DIR="$(mktemp -d "$BASE/m08_2b_path_a_fan_bd_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
printf 'M08_PATH_A_FAN_BD_EVIDENCE_DIR=%s\n' "$DIR"
files=(
  rtl/m08/m08_axil_readonly_identity.v
  rtl/m08/m08_host_staged_page_bank.sv
  rtl/m08/m08_axil_page_control.sv
  rtl/m08/m08_ps_page_safe_shell.v
  scripts/m08_page_ps_bd_candidate.tcl
  scripts/m08_path_a_fan_bd_candidate.tcl
  scripts/m08_path_a_fan_bd_audit.py
  scripts/run_m08_path_a_fan_bd.sh
)
manifest() {
  local target="$1"
  (
    cd "$ROOT"
    sha256sum -- "${files[@]}" >"$target"
  )
}
manifest "$DIR/00_source_sha256_before.txt"
printf 'source_head=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unavailable)" > "$DIR/00_source_head.txt"
set +e
(
  cd "$DIR"
  vivado -mode batch -nojournal -nolog \
    -source "$ROOT/scripts/m08_path_a_fan_bd_candidate.tcl" \
    -tclargs "$ROOT" "$DIR"
) > "$DIR/01_vivado_fan_bd.log" 2>&1
RC=$?
set -e
printf 'vivado_exit_status=%d\n' "$RC" > "$DIR/03_run_result.txt"
manifest "$DIR/04_source_sha256_after.txt"
if ! cmp -s "$DIR/00_source_sha256_before.txt" "$DIR/04_source_sha256_after.txt"; then
  echo "ERROR: M08 Path A checkout source drift; preserve original $DIR" >&2
  exit 3
fi
if (( RC != 0 )); then
  (cd "$DIR" && sha256sum -- 00_source_sha256_before.txt 00_source_head.txt \
    01_vivado_fan_bd.log 03_run_result.txt 04_source_sha256_after.txt \
    > 30_evidence_sha256.txt)
  echo "M08_PATH_A_FAN_BD_NOT_ACCEPTED_NATIVE_FAILURE rc=$RC preserve=$DIR" >&2
  exit "$RC"
fi
python3 "$HERE/m08_path_a_fan_bd_audit.py" \
  --evidence "$DIR" --source-root "$ROOT" \
  --output "$DIR/23_independent_fan_bd_audit.json"
(
  cd "$DIR"
  sha256sum -- 00_source_sha256_before.txt 00_source_head.txt \
    01_vivado_fan_bd.log 02_vivado_page_bd_readback.txt \
    03_page_bd_export.tcl 03_run_result.txt 04_source_sha256_after.txt \
    20_m08_fan_bd_readback.txt 21_m08_fan_pwm_a12.xdc \
    22_m08_fan_bd_export.tcl 23_independent_fan_bd_audit.json \
    > 30_evidence_sha256.txt
)
echo "M08_PATH_A_FAN_BD_OFFLINE_CANDIDATE_AUDITED_NOT_ROUTED_NOT_PROGRAMMED"
echo "M08_PATH_A_FAN_BD_EVIDENCE_DIR=$DIR"
