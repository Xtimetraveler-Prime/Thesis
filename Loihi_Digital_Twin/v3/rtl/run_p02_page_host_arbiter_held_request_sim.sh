#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$V3_DIR/vivado/build/p02_arbiter_held_request_sim"

command -v iverilog >/dev/null 2>&1 || {
    echo "ERROR: iverilog is required for P02 arbiter regression" >&2
    exit 2
}
command -v vvp >/dev/null 2>&1 || {
    echo "ERROR: vvp is required for P02 arbiter regression" >&2
    exit 2
}

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

iverilog -g2012     -o "$BUILD_DIR/test_p02_page_host_arbiter_held_request.vvp"     "$V3_DIR/rtl/p02_page_host_arbiter.v"     "$V3_DIR/rtl/tb/test_p02_page_host_arbiter_held_request.v"

vvp "$BUILD_DIR/test_p02_page_host_arbiter_held_request.vvp"     | tee "$BUILD_DIR/test.log"

grep -q '^PASS: p02_page_host_arbiter_held_request$' "$BUILD_DIR/test.log"
echo "PASS: P02 held-request arbiter regression completed successfully."
