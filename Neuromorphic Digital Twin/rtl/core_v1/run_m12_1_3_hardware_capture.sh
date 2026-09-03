#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m12_1_3"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
CAPTURE_DIR="$BUILD_DIR/captures"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_1_3.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m12_1_3.ltx"
CAPTURE_TCL="$SCRIPT_DIR/vivado/capture_m12_1_3_trace.tcl"
TRACE_JSON="$CAPTURE_DIR/m11_5_4_recurrent_chain_physical_trace_v1.json"
LOG_FILE="$BUILD_DIR/m12_1_3_hardware_capture.log"
VALIDATOR="$PROJECT_DIR/examples/validate_m12_1_3_physical_trace.py"

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
for path in "$BIT_FILE" "$LTX_FILE" "$CAPTURE_TCL" "$VALIDATOR"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M12.1.3 hardware-capture input is missing: $path" >&2
        echo "Run bash run_m12_1_3_bitstream.sh successfully first." >&2
        exit 3
    fi
done

mkdir -p "$BUILD_DIR" "$CAPTURE_DIR"
rm -f "$TRACE_JSON"

echo '=== M12.1.3 physical K26 machine-readable trace capture ==='
echo 'The board must be powered and visible to Vivado Hardware Manager, with PS pl_clk0 running.'
echo 'On stock Kria Linux, unload any active starter-kit PL application first if it owns the PL.'
vivado -mode batch \
    -source "$CAPTURE_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$TRACE_JSON" \
    2>&1 | tee "$LOG_FILE"

for marker in \
    "M12.1.3 bitstream programmed successfully." \
    "M12.1.3 PL clock heartbeat advanced:" \
    "M12.1.3 local capture reset released through VIO." \
    "M12.1.3 preload/reset complete; host-stepped physical execution is ready." \
    "M12.1.3 captured physical tick 4:" \
    "M12.1.3 physical trace capture completed successfully:"; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: physical run returned without expected M12.1.3 marker: $marker" >&2
        exit 4
    fi
done
if [[ ! -s "$TRACE_JSON" ]]; then
    echo "ERROR: physical trace artifact was not created: $TRACE_JSON" >&2
    exit 4
fi

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$VALIDATOR" "$TRACE_JSON"

echo
echo 'M12.1.3 physical-board trace capture completed successfully.'
printf 'Trace JSON: %s\n' "$TRACE_JSON"
printf 'Hardware log: %s\n' "$LOG_FILE"
