#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
P02_IMPL_REPORT_DIR="${P02_IMPL_REPORT_DIR:-$V3_DIR/vivado/build/p02_ddr_impl/reports}"
LTX_FILE="${P02_LTX_FILE:-$P02_IMPL_REPORT_DIR/p02_ddr_paged.ltx}"
VIVADO_SERVER_URL="${P02_VIVADO_SERVER_URL:-localhost:3121}"
EXPECTED_LTX_SHA="f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe"

[[ -f "$LTX_FILE" ]] || { echo "ERROR: accepted probes missing: $LTX_FILE" >&2; exit 2; }
[[ "$(sha256sum "$LTX_FILE" | awk '{print $1}')" == "$EXPECTED_LTX_SHA" ]] || {
    echo "ERROR: P02.4b postfailure probes identity drifted" >&2
    exit 2
}

cd "$V3_DIR"
vivado -mode batch     -source vivado/p02_4b_postfailure_resident_probe.tcl     -tclargs "$LTX_FILE" "$VIVADO_SERVER_URL"
