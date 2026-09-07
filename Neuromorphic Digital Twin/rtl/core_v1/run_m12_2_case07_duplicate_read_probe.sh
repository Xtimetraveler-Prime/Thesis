#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m12_2"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
PROBE_DIR="$BUILD_DIR/case07_duplicate_read_probe"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2.ltx"
BASE_TCL="$SCRIPT_DIR/vivado/capture_m12_2_single_tick.tcl"
PATCHED_TCL="$PROBE_DIR/capture_m12_2_case07_duplicate_read.tcl"
METADATA="$PROBE_DIR/case07_only.tsv"
LOG_FILE="$PROBE_DIR/case07_duplicate_read_hardware.log"

if ! command -v vivado >/dev/null 2>&1; then
    echo "ERROR: vivado is not on PATH. Source the Vivado 2025.2 settings64.sh first." >&2
    exit 2
fi
VIVADO_VERSION="$(vivado -version 2>&1 || true)"
if [[ "$VIVADO_VERSION" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: vivado is not reporting version $EXPECTED_VERSION." >&2
    echo "$VIVADO_VERSION" >&2
    exit 2
fi
for path in "$BIT_FILE" "$LTX_FILE" "$BASE_TCL"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.2 duplicate-read probe input is missing: $path" >&2
        exit 3
    fi
done

rm -rf "$PROBE_DIR"
mkdir -p "$PROBE_DIR"
printf 'case_id\tcase_name\tneuron_count\n7\tthreshold-over-refractory-entry\t1\n' > "$METADATA"

python3 - "$BASE_TCL" "$PATCHED_TCL" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1]).read_text(encoding="utf-8")
old = '''    set routed_outputs {}\n    for {set idx 0} {$idx < $routed_count} {incr idx} {\n        lappend routed_outputs [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr $routed_space $idx]\n    }\n'''
new = '''    set routed_outputs {}\n    for {set idx 0} {$idx < $routed_count} {incr idx} {\n        set first_routed_read [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr $routed_space $idx]\n        lappend routed_outputs $first_routed_read\n        if {$case_id == 7 && $idx == 0} {\n            set second_routed_read [trace_read_word $vio $p_trace_ready $p_rsp_seq $p_rsp_space $p_rsp_addr $p_rsp_data $p_rsp_error $p_trace_req $p_trace_space $p_trace_addr $routed_space $idx]\n            puts "M12.2 case07 recurrent-bank duplicate read: bank=$current_bank space=$routed_space addr=$idx first=$first_routed_read second=$second_routed_read"\n        }\n    }\n'''
if old not in src:
    raise SystemExit("ERROR: could not locate routed-output read loop in capture Tcl")
Path(sys.argv[2]).write_text(src.replace(old, new, 1), encoding="utf-8")
PY

echo '=== M12.2 targeted physical probe: case 07 recurrent-bank duplicate read ==='
echo 'No bitstream rebuild is required. The same routed bank word will be read twice.'

vivado -mode batch \
    -source "$PATCHED_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$METADATA" "$PROBE_DIR" \
    2>&1 | tee "$LOG_FILE"

if ! grep -q 'M12.2 case07 recurrent-bank duplicate read:' "$LOG_FILE"; then
    echo "ERROR: duplicate-read diagnostic marker was not produced." >&2
    exit 4
fi

echo
echo 'M12.2 case-07 recurrent-bank duplicate-read probe completed.'
printf 'Hardware log: %s\n' "$LOG_FILE"
