#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m12_2"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
GOLDEN_DIR="$BUILD_DIR/golden"
CAPTURE_DIR="$BUILD_DIR/captures"
DIFF_DIR="$BUILD_DIR/differential_reports"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_2.ltx"
METADATA="$GOLDEN_DIR/hardware_cases.tsv"
CAPTURE_TCL="$SCRIPT_DIR/vivado/capture_m12_2_single_tick.tcl"
VALIDATOR="$PROJECT_DIR/examples/validate_m12_2_physical_suite.py"
LOG_FILE="$BUILD_DIR/m12_2_hardware_suite.log"

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
for path in "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_TCL" "$VALIDATOR"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.2 hardware-suite input is missing: $path" >&2
        echo "Run bash run_m12_2_bitstream.sh successfully first." >&2
        exit 3
    fi
done

rm -rf "$CAPTURE_DIR" "$DIFF_DIR"
mkdir -p "$CAPTURE_DIR" "$DIFF_DIR"

echo '=== M12.2 exact physical single-tick directed suite ==='
echo 'The board must be powered and visible to Vivado Hardware Manager, with PS pl_clk0 running.'
echo 'On stock Kria Linux, unload any active starter-kit PL application first if it owns the PL.'

vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_DIR" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M12.2 bitstream programmed successfully." \
    "M12.2 PL clock heartbeat advanced:" \
    "M12.2 local capture reset released through VIO." \
    "M12.2 captured physical case 15:" \
    "M12.2 physical directed suite capture completed successfully: cases=16"; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: physical run returned without expected M12.2 marker: $marker" >&2
        exit 4
    fi
done

mapfile -t physical_files < <(find "$CAPTURE_DIR" -maxdepth 1 -type f -name '*.physical.json' -print | sort)
if [[ "${#physical_files[@]}" -ne 16 ]]; then
    echo "ERROR: M12.2 expected 16 physical JSON artifacts; found ${#physical_files[@]}." >&2
    exit 4
fi

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$VALIDATOR" \
    --physical-dir "$CAPTURE_DIR" \
    --report-dir "$DIFF_DIR"

if [[ ! -s "$DIFF_DIR/suite_report.json" ]]; then
    echo "ERROR: M12.2 suite differential report was not created." >&2
    exit 5
fi

echo
echo 'M12.2 physical directed single-tick suite completed successfully.'
printf 'Physical traces: %s\n' "$CAPTURE_DIR"
printf 'Differential reports: %s\n' "$DIFF_DIR"
printf 'Hardware log: %s\n' "$LOG_FILE"
