#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/m11_6"
ARTIFACT_DIR="$BUILD_DIR/artifacts"
BIT_FILE="$ARTIFACT_DIR/neuromorphic_twin_m11_6.bit"
LTX_FILE="$ARTIFACT_DIR/neuromorphic_twin_m11_6.ltx"
PROGRAM_TCL="$SCRIPT_DIR/vivado/program_m11_6_smoke.tcl"
LOG_FILE="$BUILD_DIR/m11_6_hardware_smoke.log"

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
for path in "$BIT_FILE" "$LTX_FILE" "$PROGRAM_TCL"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required M11.6 hardware-smoke input is missing: $path" >&2
        echo "Run bash run_m11_6_bitstream.sh successfully first." >&2
        exit 3
    fi
done

mkdir -p "$BUILD_DIR"

echo '=== M11.6 physical K26 VIO smoke ==='
echo 'The board must be powered, visible to the Vivado hardware server, and have its PS running so pl_clk0 is active.'
echo 'On stock Kria Linux, unload the active starter-kit PL application first with: sudo xmutil unloadapp'
vivado -mode batch \
    -source "$PROGRAM_TCL" \
    -tclargs "$BIT_FILE" "$LTX_FILE" \
    2>&1 | tee "$LOG_FILE"

# Match stable message prefixes. Reset/start diagnostics append readback details,
# so requiring the historical trailing period would reject a successful run.
for marker in \
    "M11.6 bitstream programmed successfully." \
    "M11.6 PL clock heartbeat advanced:" \
    "M11.6 local smoke reset released through VIO" \
    "M11.6 smoke_start pulse committed through VIO" \
    "M11.6 physical VIO smoke passed:"; do
    if ! grep -Fq "$marker" "$LOG_FILE"; then
        echo "ERROR: physical run returned without expected M11.6 marker: $marker" >&2
        exit 4
    fi
done

echo
echo 'M11.6 physical-board smoke completed successfully.'
printf 'Log: %s\n' "$LOG_FILE"
