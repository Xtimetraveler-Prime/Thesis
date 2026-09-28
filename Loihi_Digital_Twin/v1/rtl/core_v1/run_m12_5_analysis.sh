#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m12_5"
REPORT_DIR="$BUILD_DIR/reports"
CHAR_DIR="$BUILD_DIR/characterization"
CYCLE_TSV="$BUILD_DIR/m12_5_tick_cycles.tsv"
VIVADO_LOG="$BUILD_DIR/m12_5_vivado.log"
ANALYZER="$PROJECT_DIR/examples/analyze_m12_5_characterization.py"

for path in \
    "$CYCLE_TSV" \
    "$REPORT_DIR/utilization_impl.rpt" \
    "$REPORT_DIR/ram_utilization_impl.rpt" \
    "$VIVADO_LOG" \
    "$ANALYZER"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.5 analysis input is missing: $path" >&2
        exit 2
    fi
done

rm -rf "$CHAR_DIR"
mkdir -p "$CHAR_DIR"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$ANALYZER" \
    --cycles "$CYCLE_TSV" \
    --utilization "$REPORT_DIR/utilization_impl.rpt" \
    --ram-utilization "$REPORT_DIR/ram_utilization_impl.rpt" \
    --vivado-log "$VIVADO_LOG" \
    --output-dir "$CHAR_DIR"

echo 'M12.5 host-side characterization analysis completed successfully.'
printf 'Characterization evidence: %s\n' "$CHAR_DIR"
