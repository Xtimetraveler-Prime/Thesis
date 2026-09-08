#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m12_5"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
GOLDEN_DIR="$BUILD_DIR/golden"
REPORT_DIR="$BUILD_DIR/reports"
CAPTURE_DIR="$BUILD_DIR/captures"
DIFF_DIR="$BUILD_DIR/differential_reports"
CHAR_DIR="$BUILD_DIR/characterization"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_5.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_5.ltx"
METADATA="$GOLDEN_DIR/hardware_cases.tsv"
CYCLE_TSV="$BUILD_DIR/m12_5_tick_cycles.tsv"
CAPTURE_TCL="$SCRIPT_DIR/vivado/capture_m12_5_characterization.tcl"
SUITE_VALIDATOR="$PROJECT_DIR/examples/validate_m12_4_physical_suite.py"
ANALYZER="$PROJECT_DIR/examples/analyze_m12_5_characterization.py"
VIVADO_LOG="$BUILD_DIR/m12_5_vivado.log"
HARDWARE_LOG="$BUILD_DIR/m12_5_hardware_characterization.log"

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

for path in \
    "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_TCL" \
    "$SUITE_VALIDATOR" "$ANALYZER" \
    "$REPORT_DIR/utilization_impl.rpt" "$REPORT_DIR/ram_utilization_impl.rpt" "$VIVADO_LOG"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.5 characterization input is missing: $path" >&2
        echo "Run bash run_m12_5_bitstream.sh successfully first." >&2
        exit 3
    fi
done

rm -rf "$CAPTURE_DIR" "$DIFF_DIR" "$CHAR_DIR"
rm -f "$CYCLE_TSV"
mkdir -p "$CAPTURE_DIR" "$DIFF_DIR" "$CHAR_DIR"

echo '=== M12.5 physical timing/performance characterization ==='
echo 'The computational core is frozen; this image adds only passive tick-cycle observation.'
echo 'The same 22-case / 166-tick M12.4 corpus will be fully trace-validated again.'
echo 'The board must be powered and visible to Vivado Hardware Manager, with PS pl_clk0 running.'
echo 'On stock Kria Linux, unload any active starter-kit PL application first if it owns the PL.'

vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_DIR" "$CYCLE_TSV" \
    2>&1 | tee "$HARDWARE_LOG"

for marker in \
    "M12.5 bitstream programmed successfully." \
    "M12.5 PL clock heartbeat advanced:" \
    "M12.5 local capture reset released through VIO." \
    "M12.5 captured physical case 21 complete:" \
    "M12.5 physical characterization capture completed successfully: cases=22 ticks=166"; do
    if ! grep -Fq "$marker" "$HARDWARE_LOG"; then
        echo "ERROR: physical run returned without expected M12.5 marker: $marker" >&2
        exit 4
    fi
done

mapfile -t physical_files < <(find "$CAPTURE_DIR" -maxdepth 1 -type f -name '*.physical.json' -print | sort)
if [[ "${#physical_files[@]}" -ne 22 ]]; then
    echo "ERROR: M12.5 expected 22 physical JSON artifacts; found ${#physical_files[@]}." >&2
    exit 4
fi
if [[ ! -s "$CYCLE_TSV" ]]; then
    echo "ERROR: M12.5 cycle TSV is missing or empty: $CYCLE_TSV" >&2
    exit 4
fi
cycle_rows="$(($(wc -l < "$CYCLE_TSV") - 1))"
if [[ "$cycle_rows" -ne 166 ]]; then
    echo "ERROR: M12.5 expected 166 measured cycle rows; found $cycle_rows." >&2
    exit 4
fi

# Characterization instrumentation is acceptable only if the complete M12.4
# architectural trace still matches Python exactly on the new image.
PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$SUITE_VALIDATOR" \
    --physical-dir "$CAPTURE_DIR" \
    --report-dir "$DIFF_DIR" \
    | tee "$BUILD_DIR/m12_5_exact_revalidation.log"

if ! grep -Fq 'M12.4 exact broad physical differential passed: cases=22 ticks=166 mismatches=0' \
    "$BUILD_DIR/m12_5_exact_revalidation.log"; then
    echo "ERROR: passive M12.5 image did not preserve the exact M12.4 physical result." >&2
    exit 5
fi
if [[ ! -s "$DIFF_DIR/suite_report.json" ]]; then
    echo "ERROR: M12.5 exact revalidation suite report was not created." >&2
    exit 5
fi

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$ANALYZER" \
    --cycles "$CYCLE_TSV" \
    --utilization "$REPORT_DIR/utilization_impl.rpt" \
    --ram-utilization "$REPORT_DIR/ram_utilization_impl.rpt" \
    --vivado-log "$VIVADO_LOG" \
    --output-dir "$CHAR_DIR" \
    | tee "$BUILD_DIR/m12_5_analysis.log"

for output in \
    "$CHAR_DIR/characterization.json" \
    "$CHAR_DIR/tick_characterization.csv" \
    "$CHAR_DIR/CHARACTERIZATION_SUMMARY.md"; do
    if [[ ! -s "$output" ]]; then
        echo "ERROR: required M12.5 characterization output is missing: $output" >&2
        exit 6
    fi
done

if ! grep -Fq 'M12.5 characterization assembled: ticks=166' "$BUILD_DIR/m12_5_analysis.log"; then
    echo "ERROR: M12.5 analyzer did not consume all 166 physical tick measurements." >&2
    exit 6
fi

echo
echo 'M12.5 physical characterization completed successfully.'
printf 'Physical traces: %s\n' "$CAPTURE_DIR"
printf 'Exact differential reports: %s\n' "$DIFF_DIR"
printf 'Cycle measurements: %s\n' "$CYCLE_TSV"
printf 'Characterization evidence: %s\n' "$CHAR_DIR"
printf 'Vivado implementation log: %s\n' "$VIVADO_LOG"
printf 'Hardware log: %s\n' "$HARDWARE_LOG"
