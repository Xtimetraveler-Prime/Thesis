#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd -- "$APP_DIR/../.." && pwd)"
PROJECT_DIR="$REPO_ROOT/Neuromorphic Digital Twin"
CORE_RTL="$PROJECT_DIR/rtl/core_v1"
BUILD_DIR="$APP_DIR/build/mnist-08"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
GOLDEN_DIR="$BUILD_DIR/golden"
CAPTURE_DIR="$BUILD_DIR/captures"
REPORT_DIR="$BUILD_DIR/differential_reports"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_mnist_08.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_mnist_08.ltx"
METADATA="$GOLDEN_DIR/hardware_cases.tsv"
MANIFEST="$GOLDEN_DIR/manifest.json"
CAPTURE_TCL="$BUILD_DIR/capture_mnist_08_corpus.tcl"
SUITE_VALIDATOR="$APP_DIR/scripts/validate_fpga_corpus_suite.py"
LOG_FILE="$BUILD_DIR/mnist_08_hardware.log"

if ! command -v vivado >/dev/null 2>&1; then
    echo "ERROR: vivado is not on PATH. Source the Vivado 2025.2 settings64.sh first." >&2
    exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is not on PATH." >&2
    exit 2
fi
VIVADO_VERSION="$(vivado -version 2>&1 || true)"
if [[ "$VIVADO_VERSION" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: vivado is not reporting version $EXPECTED_VERSION." >&2
    echo "$VIVADO_VERSION" >&2
    exit 2
fi
for path in \
    "$BIT_FILE" "$LTX_FILE" "$METADATA" "$MANIFEST" \
    "$CORE_RTL/vivado/capture_m12_3_multitick.tcl" "$SUITE_VALIDATOR"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required MNIST-08 hardware input is missing: $path" >&2
        echo "Run applications/mnist/fpga/run_mnist_08_bitstream.sh successfully first." >&2
        exit 3
    fi
done

PYTHONPATH="$APP_DIR:$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 - "$CORE_RTL/vivado/capture_m12_3_multitick.tcl" "$CAPTURE_TCL" <<'PY'
from pathlib import Path
import sys
from mnist_app.fpga_corpus_shell import write_patched_capture_tcl
write_patched_capture_tcl(Path(sys.argv[1]), Path(sys.argv[2]))
PY

if ! grep -Fq 'expected_case_nibble' "$CAPTURE_TCL"; then
    echo "ERROR: MNIST-08 capture Tcl did not receive the >15 case-witness patch." >&2
    exit 3
fi

rm -rf "$CAPTURE_DIR" "$REPORT_DIR"
mkdir -p "$CAPTURE_DIR" "$REPORT_DIR"

echo '=== MNIST-08 exact physical frozen-corpus conformance ==='
echo 'The board must be powered and visible to Vivado Hardware Manager, with PS pl_clk0 running.'
echo 'On stock Kria Linux, unload any active starter-kit PL application first if it owns the PL.'
echo 'This run executes 60 cases (30 frozen source images x 2 profiles), 16 ticks per case.'

vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$METADATA" "$CAPTURE_DIR" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M12.3 bitstream programmed successfully." \
    "M12.3 PL clock heartbeat advanced:" \
    "M12.3 local capture reset released through VIO." \
    "M12.3 physical directed multi-tick suite capture completed successfully: cases=60 ticks=960"; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: physical run returned without expected capture-shell marker: $marker" >&2
        exit 4
    fi
done

mapfile -t physical_files < <(find "$CAPTURE_DIR" -maxdepth 1 -type f -name '*.physical.json' -print | sort)
if [[ "${#physical_files[@]}" -ne 60 ]]; then
    echo "ERROR: MNIST-08 expected 60 physical JSON artifacts; found ${#physical_files[@]}." >&2
    exit 4
fi

PYTHONPATH="$APP_DIR:$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$SUITE_VALIDATOR" \
    --manifest "$MANIFEST" \
    --physical-dir "$CAPTURE_DIR" \
    --report-dir "$REPORT_DIR"

if [[ ! -s "$REPORT_DIR/suite_report.json" ]]; then
    echo "ERROR: MNIST-08 suite differential report was not created." >&2
    exit 5
fi

echo
echo 'MNIST-08 physical frozen-corpus conformance completed successfully.'
printf 'Physical traces: %s\n' "$CAPTURE_DIR"
printf 'Differential reports: %s\n' "$REPORT_DIR"
printf 'Hardware log: %s\n' "$LOG_FILE"
