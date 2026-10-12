#!/usr/bin/env bash
set -euo pipefail

EXPECTED_BIT_SHA="8b4d1d3996147e73bbe71ec2a5036f0a4d23efc5cc3fe3d25237f855acf72119"
EXPECTED_LTX_SHA="a745b96c24f4e01480d1d89d706e90c52c822b4a7fda7ea43d2ad794a0b86def"
EXPECTED_XSA_SHA="703fa7a44abc56e88e67e1d09424ac59ea96e53aac1708c2c7e6028dcb616f40"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$V3_DIR/vivado/build/p03_2c_smoke"
FIXTURE_DIR="$BUILD_DIR/fixture"
WORKSPACE="$BUILD_DIR/vitis_workspace"
ELF="$WORKSPACE/p03_2c_smoke.elf"
MAILBOX_DUMP="$BUILD_DIR/p03_2c_mailbox.bin"

P03_IMPL_REPORT_DIR="${P03_IMPL_REPORT_DIR:-$V3_DIR/vivado/build/p03_2_mmio_impl/reports}"
BIT_FILE="${P03_BIT_FILE:-$P03_IMPL_REPORT_DIR/p03_2_ps_mmio.bit}"
LTX_FILE="${P03_LTX_FILE:-$P03_IMPL_REPORT_DIR/p03_2_ps_mmio.ltx}"
XSA_FILE="${P03_XSA:-$P03_IMPL_REPORT_DIR/p03_2_ps_mmio.xsa}"

XSDB_SERVER_URL="${P03_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
VIVADO_SERVER_URL="${P03_VIVADO_SERVER_URL:-localhost:3121}"

for tool in python xsdb vivado sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required P03.2c tool is not on PATH: $tool" >&2
        exit 2
    }
done

for artifact in "$BIT_FILE" "$LTX_FILE" "$XSA_FILE" "$ELF"; do
    [[ -f "$artifact" ]] || {
        echo "ERROR: P03.2c required artifact missing: $artifact" >&2
        echo "ERROR: run scripts/build_p03_2c_smoke.sh first if the ELF is missing." >&2
        exit 2
    }
done

BIT_SHA="$(sha256sum "$BIT_FILE" | awk '{print $1}')"
LTX_SHA="$(sha256sum "$LTX_FILE" | awk '{print $1}')"
XSA_SHA="$(sha256sum "$XSA_FILE" | awk '{print $1}')"

[[ "$BIT_SHA" == "$EXPECTED_BIT_SHA" ]] || {
    echo "ERROR: P03.2c bitstream identity drifted: $BIT_SHA" >&2
    exit 2
}
[[ "$LTX_SHA" == "$EXPECTED_LTX_SHA" ]] || {
    echo "ERROR: P03.2c probes identity drifted: $LTX_SHA" >&2
    exit 2
}
[[ "$XSA_SHA" == "$EXPECTED_XSA_SHA" ]] || {
    echo "ERROR: P03.2c XSA identity drifted: $XSA_SHA" >&2
    exit 2
}

for fixture in     "$FIXTURE_DIR/core0_initial.bin"     "$FIXTURE_DIR/mailbox_zero.bin"     "$FIXTURE_DIR/manifest.json"; do
    [[ -f "$fixture" ]] || {
        echo "ERROR: P03.2c fixture missing: $fixture" >&2
        exit 2
    }
done

cat <<'EOF'
P03.2c HARDWARE NOTE:
  Let Linux boot far enough to initialize DDR before starting this test.
  The test then halts all visible Cortex-A53 cores before touching the
  reserved 0x40000000..0x43FFFFFF project DDR window.
  Do not resume that halted Linux instance after the test; reboot the KV260.
EOF

cd "$V3_DIR"

xsdb vivado/p03_2c_xsdb_prepare.tcl     "$FIXTURE_DIR" "$XSDB_SERVER_URL"     | tee "$BUILD_DIR/xsdb_prepare.log"

vivado -mode batch     -source vivado/p03_2c_program_bitstream.tcl     -tclargs "$BIT_FILE" "$LTX_FILE" "$VIVADO_SERVER_URL"     2>&1 | tee "$BUILD_DIR/program.log"

xsdb vivado/p03_2c_xsdb_run.tcl     "$ELF" "$MAILBOX_DUMP" "$XSDB_SERVER_URL"     | tee "$BUILD_DIR/xsdb_run.log"

python scripts/p03_2c_verify_mailbox.py     --mailbox "$MAILBOX_DUMP"     --manifest "$FIXTURE_DIR/manifest.json"     | tee "$BUILD_DIR/verify.log"

for marker in     "PASS: P03.2c backing record provisioned and mailbox cleared by physical readback"     "PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released"     "PASS: P03.2c standalone ELF downloaded to Cortex-A53 #0"     "PASS: P03.2c A53 smoke executed and 64-byte mailbox dumped"     "PASS: P03.2c mailbox verified"; do
    grep -R -F -q "$marker" "$BUILD_DIR" || {
        echo "ERROR: missing P03.2c physical acceptance marker: $marker" >&2
        exit 4
    }
done

ELF_SHA="$(sha256sum "$ELF" | awk '{print $1}')"
printf 'P03_2C_BITSTREAM_SHA256=%s\n' "$BIT_SHA"
printf 'P03_2C_PROBES_SHA256=%s\n' "$LTX_SHA"
printf 'P03_2C_XSA_SHA256=%s\n' "$XSA_SHA"
printf 'P03_2C_ELF_SHA256=%s\n' "$ELF_SHA"
echo "PASS: P03.2c physical Cortex-A53 MMIO smoke gate completed successfully."
echo "Evidence directory: $BUILD_DIR"
echo "IMPORTANT: reboot the KV260 before resuming normal Linux use."
