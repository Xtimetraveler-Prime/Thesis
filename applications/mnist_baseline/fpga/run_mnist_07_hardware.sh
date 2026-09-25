#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd -- "$APP_DIR/../.." && pwd)"
PROJECT_DIR="$REPO_ROOT/Neuromorphic Digital Twin"
CORE_RTL="$PROJECT_DIR/rtl/core_v1"
BUILD_DIR="$APP_DIR/build/mnist-07"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
GOLDEN_DIR="$BUILD_DIR/golden"
CAPTURE_DIR="$BUILD_DIR/captures"
REPORT_DIR="$BUILD_DIR/differential_reports"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_mnist_07.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_mnist_07.ltx"
METADATA="$GOLDEN_DIR/hardware_cases.tsv"
MANIFEST="$GOLDEN_DIR/manifest.json"
CAPTURE_TCL="$CORE_RTL/vivado/capture_m12_3_multitick.tcl"
SUITE_VALIDATOR="$APP_DIR/scripts/validate_fpga_conformance_suite.py"
LOG_FILE="$BUILD_DIR/mnist_07_hardware.log"

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
for path in "$BIT_FILE" "$LTX_FILE" "$METADATA" "$MANIFEST" "$CAPTURE_TCL" "$SUITE_VALIDATOR"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required MNIST-07 hardware input is missing: $path" >&2
        echo "Run applications/mnist_baseline/fpga/run_mnist_07_bitstream.sh successfully first." >&2
        exit 3
    fi
done

rm -rf "$CAPTURE_DIR" "$REPORT_DIR"
mkdir -p "$CAPTURE_DIR" "$REPORT_DIR"

echo '=== MNIST-07 exact physical single-image conformance ==='
echo 'The board must be powered and visible to Vivado Hardware Manager, with PS pl_clk0 running.'
echo 'On stock Kria Linux, unload any active starter-kit PL application first if it owns the PL.'

vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_DIR" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M12.3 bitstream programmed successfully." \
    "M12.3 PL clock heartbeat advanced:" \
    "M12.3 local capture reset released through VIO." \
    "M12.3 physical directed multi-tick suite capture completed successfully: cases=2 ticks=32"; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: physical run returned without expected capture-shell marker: $marker" >&2
        exit 4
    fi
done

mapfile -t physical_files < <(find "$CAPTURE_DIR" -maxdepth 1 -type f -name '*.physical.json' -print | sort)
if [[ "${#physical_files[@]}" -ne 2 ]]; then
    echo "ERROR: MNIST-07 expected 2 physical JSON artifacts; found ${#physical_files[@]}." >&2
    exit 4
fi

PYTHONPATH="$APP_DIR:$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$SUITE_VALIDATOR" \
    --manifest "$MANIFEST" \
    --physical-dir "$CAPTURE_DIR" \
    --report-dir "$REPORT_DIR"

if [[ ! -s "$REPORT_DIR/suite_report.json" ]]; then
    echo "ERROR: MNIST-07 suite differential report was not created." >&2
    exit 5
fi

echo
echo 'MNIST-07 physical single-image conformance completed successfully.'
printf 'Physical traces: %s\n' "$CAPTURE_DIR"
printf 'Differential reports: %s\n' "$REPORT_DIR"
printf 'Hardware log: %s\n' "$LOG_FILE"
