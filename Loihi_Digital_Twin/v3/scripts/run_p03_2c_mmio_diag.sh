#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
XSDB_SERVER_URL="${P03_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"

command -v xsdb >/dev/null 2>&1 || {
    echo "ERROR: xsdb is not on PATH. Source Vitis 2025.2 settings64.sh first." >&2
    exit 2
}

cd "$V3_DIR"
xsdb vivado/p03_2c_xsdb_mmio_diag.tcl "$XSDB_SERVER_URL"
