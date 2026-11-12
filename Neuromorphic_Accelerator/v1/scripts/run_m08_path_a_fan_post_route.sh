#!/usr/bin/env bash
# M08.2b Path A genuine PC-only fan+M08 dual-AXI Vivado route.
# No bitstream, no Linux changes, no hardware programming or raw MMIO.
# Run in VS Code on PC with Vivado 2025.2 sourced. Fresh evidence only.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(cd -- "$HERE/.." && pwd)"
BASE="${M08_EVIDENCE_BASE:-$HOME/Thesis_Evidence/M08}"
JOBS="${M08_FAN_ROUTE_JOBS:-4}"
if ! [[ "$JOBS" =~ ^[1-8]$ ]]; then
    echo "ERROR: M08_FAN_ROUTE_JOBS must be an integer 1..8" >&2
    exit 2
fi
if [[ ! -d "$BASE" || -L "$BASE" ]]; then
    echo "ERROR: existing trusted M08 owner evidence parent required" >&2
    exit 2
fi
command -v vivado >/dev/null || {
    echo "ERROR: source native Vivado 2025.2 settings64.sh on PC" >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *2025.2* ]]; then
    echo "ERROR: native Vivado 2025.2 required" >&2
    exit 2
fi
DIR="$(mktemp -d "$BASE/m08_2b_path_a_fan_route_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
echo "M08_PATH_A_FAN_ROUTE_EVIDENCE_DIR=$DIR"
files=(
    rtl/m08/m08_axil_readonly_identity.v
    rtl/m08/m08_host_staged_page_bank.sv
    rtl/m08/m08_axil_page_control.sv
    rtl/m08/m08_ps_page_safe_shell.v
    scripts/m08_page_ps_bd_candidate.tcl
    scripts/m08_path_a_baseline_report_gate.tcl
    scripts/m08_path_a_fan_bd_candidate.tcl
    scripts/m08_path_a_fan_bd_audit.py
    scripts/run_m08_path_a_fan_bd.sh
    scripts/m08_path_a_fan_post_route.tcl
    scripts/m08_path_a_fan_post_route_audit.py
    scripts/run_m08_path_a_fan_post_route.sh
)
manifest() {
  local target="$1"
  (
    cd "$ROOT"
    sha256sum -- "${files[@]}" > "$target"
  )
}
manifest "$DIR/00_source_sha256_before.txt"
printf 'source_head=%s\njobs=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unavailable)" "$JOBS" > "$DIR/00_run_input.txt"
set +e
(
    cd "$DIR"
    vivado -mode batch -nojournal -nolog \
        -source "$ROOT/scripts/m08_path_a_fan_post_route.tcl" \
        -tclargs "$ROOT" "$DIR" "$JOBS"
) > "$DIR/01_vivado_fan_route.log" 2>&1
VIVADO_RC=$?
set -e
printf 'vivado_exit_status=%d\n' "$VIVADO_RC" > "$DIR/03_route_status.txt"
manifest "$DIR/04_source_sha256_after.txt"
# Audit only after an actual native run SUCCESS and no source mutation.
AUDIT_RC=99
if [[ "$VIVADO_RC" -eq 0 ]] &&
    cmp -s "$DIR/00_source_sha256_before.txt" "$DIR/04_source_sha256_after.txt"; then
    set +e
    python3 "$HERE/m08_path_a_fan_post_route_audit.py" \
        --evidence "$DIR" --source-root "$ROOT" \
        --output "$DIR/49_independent_fan_route_audit.json" \
        > "$DIR/50_audit_console.log" 2>&1
    AUDIT_RC=$?
    set -e
else
    printf 'AUDIT_NOT_RUN: original Vivado failure or source manifest drift\n' > "$DIR/50_audit_console.log"
fi
printf 'independent_audit_exit_status=%d\n' "$AUDIT_RC" > "$DIR/51_audit_status.txt"
# Retain SHA ledger for all AVAILABLE vendor originals, including partial
# native artifacts if routing or audit stops. Never alter previous folders.
(
    cd "$DIR"
    : > 52_evidence_sha256.txt
    for name in \
        00_source_sha256_before.txt 00_run_input.txt 01_vivado_fan_route.log \
        03_route_status.txt 04_source_sha256_after.txt \
        02_vivado_page_bd_readback.txt 03_page_bd_export.tcl \
        20_m08_fan_bd_readback.txt 21_m08_fan_pwm_a12.xdc \
        22_m08_fan_bd_export.tcl 40_fan_route_metrics.txt \
        41_fan_timing_post_route.rpt 42_fan_utilization_post_route.rpt \
        43_fan_drc_post_route.rpt 44_fan_methodology_post_route.rpt \
        45_fan_clock_utilization_post_route.rpt 46_fan_io_post_route.rpt \
        47_fan_route_status_post_route.rpt 48_fan_post_route.dcp \
        49_independent_fan_route_audit.json 50_audit_console.log \
        51_audit_status.txt; do
        if [[ -f "$name" ]]; then sha256sum -- "$name" >> 52_evidence_sha256.txt; fi
    done
)
if (( VIVADO_RC != 0 )); then
    echo "M08_PATH_A_FAN_ROUTE_VIVADO_FAILED preserve=$DIR rc=$VIVADO_RC" >&2
    exit "$VIVADO_RC"
fi
if ! cmp -s "$DIR/00_source_sha256_before.txt" "$DIR/04_source_sha256_after.txt"; then
    echo "M08_PATH_A_FAN_ROUTE_SOURCE_CHANGED preserve=$DIR" >&2
    exit 3
fi
if (( AUDIT_RC != 0 )); then
    echo "M08_PATH_A_FAN_ROUTE_AUDIT_FAILED preserve=$DIR rc=$AUDIT_RC" >&2
    exit 3
fi
echo "M08_PATH_A_FAN_NATIVE_ROUTED_SHA_AUDITED_DRC_UNCONSTRAINED_PENDING_NO_BOARD"
echo "M08_PATH_A_FAN_ROUTE_EVIDENCE_DIR=$DIR"
