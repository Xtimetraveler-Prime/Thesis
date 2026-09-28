#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m12_4"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
GOLDEN_DIR="$BUILD_DIR/golden"
CAPTURE_DIR="$BUILD_DIR/captures"
DIFF_DIR="$BUILD_DIR/differential_reports"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_4.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_4.ltx"
METADATA="$GOLDEN_DIR/hardware_cases.tsv"
CAPTURE_TCL="$SCRIPT_DIR/vivado/capture_m12_4_broad.tcl"
SUITE_VALIDATOR="$PROJECT_DIR/examples/validate_m12_4_physical_suite.py"
LOG_FILE="$BUILD_DIR/m12_4_hardware_suite.log"
DIFF_LOG="$BUILD_DIR/m12_4_differential.log"

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
for path in "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_TCL" "$SUITE_VALIDATOR"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.4 hardware-suite input is missing: $path" >&2
        echo "Run bash run_m12_4_bitstream.sh successfully first." >&2
        exit 3
    fi
done

rm -rf "$CAPTURE_DIR" "$DIFF_DIR"
rm -f "$DIFF_LOG"
mkdir -p "$CAPTURE_DIR" "$DIFF_DIR"

echo '=== M12.4 broad deterministic physical regression ==='
echo 'The board must be powered and visible to Vivado Hardware Manager, with PS pl_clk0 running.'
echo 'On stock Kria Linux, unload any active starter-kit PL application first if it owns the PL.'
echo 'Corpus: 16 seeded generated networks + 6 selected finite-capacity stress cases.'

vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_DIR" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M12.4 bitstream programmed successfully." \
    "M12.4 PL clock heartbeat advanced:" \
    "M12.4 local capture reset released through VIO." \
    "M12.4 captured physical case 21 complete:" \
    "M12.4 physical broad deterministic suite capture completed successfully: cases=22 ticks=166"; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: physical run returned without expected M12.4 marker: $marker" >&2
        exit 4
    fi
done

mapfile -t physical_files < <(find "$CAPTURE_DIR" -maxdepth 1 -type f -name '*.physical.json' -print | sort)
if [[ "${#physical_files[@]}" -ne 22 ]]; then
    echo "ERROR: M12.4 expected 22 physical JSON artifacts; found ${#physical_files[@]}." >&2
    exit 4
fi

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$SUITE_VALIDATOR" \
    --physical-dir "$CAPTURE_DIR" \
    --report-dir "$DIFF_DIR" \
    2>&1 | tee "$DIFF_LOG"

if [[ ! -s "$DIFF_DIR/suite_report.json" ]]; then
    echo "ERROR: M12.4 suite differential report was not created." >&2
    exit 5
fi
if ! grep -Fq 'M12.4 exact broad physical differential passed: cases=22 ticks=166 mismatches=0' "$DIFF_LOG"; then
    echo "ERROR: M12.4 exact differential did not produce the expected pass marker." >&2
    exit 5
fi

echo
echo 'M12.4 physical broad deterministic regression completed successfully.'
printf 'Physical traces: %s\n' "$CAPTURE_DIR"
printf 'Differential reports: %s\n' "$DIFF_DIR"
printf 'Corpus manifest: %s\n' "$GOLDEN_DIR/manifest.json"
printf 'Hardware log: %s\n' "$LOG_FILE"
printf 'Differential log: %s\n' "$DIFF_LOG"
