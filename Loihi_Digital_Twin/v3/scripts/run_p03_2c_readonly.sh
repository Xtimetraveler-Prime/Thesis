#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="${P03_2C_BUILD_DIR:?Set P03_2C_BUILD_DIR to the existing, fresh read-only Vitis build directory}"
DIAG_REPORTS="${P03_DIAG_REPORTS:?Set P03_DIAG_REPORTS to the routed diagnostic bitstream/probes report directory}"
XSDB_SERVER_URL="${P03_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
VIVADO_SERVER_URL="${P03_HW_SERVER_URL:-localhost:3121}"
READONLY_MMIO_BASE="${P03_2C_READONLY_MMIO_BASE:-0xA4000000}"

FIXTURE_DIR="$BUILD_DIR/fixture"
ELF="$BUILD_DIR/vitis_workspace/p03_2c_readonly.elf"
BIT="$DIAG_REPORTS/p03_2_ps_mmio.bit"
LTX="$DIAG_REPORTS/p03_2_ps_mmio.ltx"
XSA="$DIAG_REPORTS/p03_2_ps_mmio.xsa"
MAILBOX="$BUILD_DIR/p03_2c_readonly_mailbox.bin"
EVIDENCE="$BUILD_DIR/read_only_physical_evidence"
case "$READONLY_MMIO_BASE" in
    0xA4000000|0x80000000) ;;
    *) echo "ERROR: unsupported diagnostic MMIO base $READONLY_MMIO_BASE" >&2; exit 2 ;;
esac
if [[ "${P03_XSA:-$XSA}" != "$XSA" ]]; then
    echo "ERROR: P03_XSA must match the XSA in P03_DIAG_REPORTS" >&2
    exit 2
fi
if [[ -z "${P03_2C_EXPECTED_XSA_SHA:-}" ||
      "$(sha256sum "$XSA" | awk '{print $1}')" != "$P03_2C_EXPECTED_XSA_SHA" ]]; then
    echo "ERROR: candidate XSA SHA-256 must match P03_2C_EXPECTED_XSA_SHA" >&2
    exit 2
fi

for tool in xsdb vivado python sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: missing P03.2c diagnostic tool $tool" >&2
        exit 2
    }
done
for input in "$ELF" "$BIT" "$LTX" "$XSA" \
    "$FIXTURE_DIR/core0_initial.bin" "$FIXTURE_DIR/mailbox_zero.bin"; do
    [[ -f "$input" ]] || {
        echo "ERROR: read-only diagnostic input missing: $input" >&2
        exit 2
    }
done
[[ ! -e "$EVIDENCE" && ! -e "$MAILBOX" ]] || {
    echo "ERROR: read-only physical evidence already exists; use a fresh P03_2C_BUILD_DIR." >&2
    exit 2
}
mkdir -p "$EVIDENCE"
echo "P03_2C_READONLY_XSA_SHA256=$(sha256sum "$XSA" | awk '{print $1}')"
echo "P03_2C_READONLY_BIT_SHA256=$(sha256sum "$BIT" | awk '{print $1}')"
echo "P03_2C_READONLY_ELF_SHA256=$(sha256sum "$ELF" | awk '{print $1}')"
echo "P03_2C_READONLY_PROGRAM_SKIP=${P03_2C_SKIP_PROGRAM:-0}"

cat <<'EOF'
P03.2c A53 READ-ONLY DIAGNOSTIC:
  - Allow the KV260 to complete a normal boot so PS DDR is initialized.
  - This workflow halts the A53 CPUs, overwrites the reserved 512 KiB
    core0 fixture and 64-byte result mailbox in project DDR, and replaces
    the A53 #0 Linux execution context with a standalone read-only program.
  - It writes no P03 MMIO registers.
  - Do not resume the halted Linux instance; reboot afterward.
EOF

cd "$V3_DIR"
xsdb vivado/p03_2c_xsdb_prepare.tcl "$FIXTURE_DIR" "$XSDB_SERVER_URL" \
    2>&1 | tee "$EVIDENCE/provision.log"

if [[ "${P03_2C_SKIP_PROGRAM:-0}" == 1 ]]; then
    echo "INFO: skipping PL reprogramming; caller is responsible for the exact matching bitstream/probes."
else
    vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
        -tclargs "$BIT" "$LTX" "$VIVADO_SERVER_URL" \
        2>&1 | tee "$EVIDENCE/program.log"
fi

xsdb vivado/p03_2c_xsdb_run.tcl "$ELF" "$MAILBOX" "$XSDB_SERVER_URL" \
    2>&1 | tee "$EVIDENCE/a53_run.log"

python scripts/p03_2c_verify_readonly.py --mailbox "$MAILBOX" --base "$READONLY_MMIO_BASE" \
    2>&1 | tee "$EVIDENCE/verify.log"

echo "PASS: P03.2c standalone A53 read-only MMIO diagnostic collected"
echo "Evidence: $EVIDENCE"
echo "IMPORTANT: reboot the KV260 before resuming regular Linux use."
