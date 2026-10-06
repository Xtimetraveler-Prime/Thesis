#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/p03_2_mmio_impl"
PROJECT_XPR="$BUILD_DIR/project/loihi_twin_v3_p03_mmio_impl.xpr"
REPORT_DIR="$BUILD_DIR/reports"
RECOVERY_TCL="$SCRIPT_DIR/recover_p03_mmio_xsa.tcl"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado/Vitis 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi

[[ -f "$PROJECT_XPR" ]] || {
    echo "ERROR: existing P03.2 routed project is missing: $PROJECT_XPR" >&2
    echo "ERROR: run vivado/run_p03_mmio_impl.sh instead." >&2
    exit 3
}

mkdir -p "$REPORT_DIR"

vivado -mode batch     -source "$RECOVERY_TCL"     -tclargs "$PROJECT_XPR" "$REPORT_DIR"     2>&1 | tee "$BUILD_DIR/xsa_recovery.log"

for required in     "$REPORT_DIR/p03_2_ps_mmio.bit"     "$REPORT_DIR/p03_2_ps_mmio.ltx"     "$REPORT_DIR/p03_2_ps_mmio.xsa"; do
    [[ -f "$required" ]] || {
        echo "ERROR: P03.2 recovered artifact missing: $required" >&2
        exit 4
    }
done

BIT_SHA="$(sha256sum "$REPORT_DIR/p03_2_ps_mmio.bit" | awk '{print $1}')"
LTX_SHA="$(sha256sum "$REPORT_DIR/p03_2_ps_mmio.ltx" | awk '{print $1}')"
XSA_SHA="$(sha256sum "$REPORT_DIR/p03_2_ps_mmio.xsa" | awk '{print $1}')"

printf 'PASS: P03.2 recovered artifacts bitstream_sha256=%s probes_sha256=%s xsa_sha256=%s\n'     "$BIT_SHA" "$LTX_SHA" "$XSA_SHA"
echo "PASS: P03.2 routed-project XSA recovery gate completed successfully."
