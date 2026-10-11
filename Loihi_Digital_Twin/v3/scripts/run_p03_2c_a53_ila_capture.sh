#!/usr/bin/env bash
# Correlate A53-generated MMIO reads with BOTH PL-side ILA captures.
# This is diagnostic evidence, NOT P03.2c acceptance.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
DIAG_REPORTS="${P03_DIAG_REPORTS:?Set P03_DIAG_REPORTS to the routed diagnostic reports}"
A53_BUILD_DIR="${P03_2C_BUILD_DIR:?Set P03_2C_BUILD_DIR to the matching existing read-only ELF build}"
MMIO_BASE="${P03_2C_READONLY_MMIO_BASE:?Set P03_2C_READONLY_MMIO_BASE explicitly (0x80000000 for LPD, 0xA4000000 for FPD)}"
XSA_SHA="${P03_2C_EXPECTED_XSA_SHA:?Set P03_2C_EXPECTED_XSA_SHA to the matching candidate XSA sha256}"
OUT_DIR="${1:?Usage: run_p03_2c_a53_ila_capture.sh <NEW_evidence_directory>}"
HW_URL="${P03_HW_SERVER_URL:-localhost:3121}"
XSDB_URL="${P03_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"

BIT="$DIAG_REPORTS/p03_2_ps_mmio.bit"
LTX="$DIAG_REPORTS/p03_2_ps_mmio.ltx"
XSA="$DIAG_REPORTS/p03_2_ps_mmio.xsa"
ELF="$A53_BUILD_DIR/vitis_workspace/p03_2c_readonly.elf"
FIXTURE_DIR="$A53_BUILD_DIR/fixture"
ARMED_MARKER="$OUT_DIR/armed.marker"
VIVADO_LOG="$OUT_DIR/vivado_ila_capture.log"
MAILBOX="$OUT_DIR/p03_2c_a53_readonly_mailbox.bin"

case "$MMIO_BASE" in
    0x80000000|0xA4000000) ;;
    *) echo "ERROR: unsupported P03_2C_READONLY_MMIO_BASE=$MMIO_BASE" >&2; exit 2 ;;
esac
if [[ -n "${P03_XSA:-}" && "$P03_XSA" != "$XSA" ]]; then
    echo "ERROR: P03_XSA differs from reports XSA; refusing mixed evidence." >&2
    exit 2
fi
for tool in xsdb vivado python sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: missing $tool" >&2; exit 2; }
done
for file in "$BIT" "$LTX" "$XSA" "$ELF" "$FIXTURE_DIR/core0_initial.bin" "$FIXTURE_DIR/mailbox_zero.bin"; do
    [[ -s "$file" ]] || { echo "ERROR: missing/empty diagnostic input: $file" >&2; exit 2; }
done
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$XSA_SHA" ]] || {
    echo "ERROR: diagnostic XSA hash mismatch" >&2; exit 2;
}
if [[ -e "$OUT_DIR" ]]; then
    echo "ERROR: evidence output directory already exists: $OUT_DIR" >&2
    exit 2
fi
mkdir -p "$OUT_DIR"
cd "$V3_DIR"

{
    printf 'candidate_xsa_sha256=%s\n' "$(sha256sum "$XSA" | awk '{print $1}')"
    printf 'candidate_bit_sha256=%s\n' "$(sha256sum "$BIT" | awk '{print $1}')"
    printf 'candidate_ltx_sha256=%s\n' "$(sha256sum "$LTX" | awk '{print $1}')"
    printf 'a53_elf_sha256=%s\n' "$(sha256sum "$ELF" | awk '{print $1}')"
    printf 'a53_mmio_base=%s\n' "$MMIO_BASE"
} | tee "$OUT_DIR/identity.txt"

cat <<'EOF'
P03.2c A53-originated ILA capture:
  - Reboot board and allow normal PS/DDR initialization first.
  - This test HALTS Cortex-A53 processors and replaces A53 #0 Linux context.
  - Provisions reserved 512 KiB core-0 fixture and 64-byte result mailbox.
  - Captures AXI while executing an A53-only read diagnostic; no MMIO writes.
  - Reboot KV260 after the test; do not resume the stopped Linux instance.
EOF

# Previous diagnostic scripts already proved physical DDR provisioning and
# reset-pulse programming; preserve both command logs from THIS execution.
xsdb vivado/p03_2c_xsdb_prepare.tcl "$FIXTURE_DIR" "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/prepare.log"

vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" \
    >"$OUT_DIR/program.log" 2>&1
grep -F 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
    "$OUT_DIR/program.log" || {
    echo "ERROR: candidate bitstream did not program/reset successfully." >&2
    exit 3
}

# Arms on ARVALID at both boundaries. Trigger is expected at the first
# processor MMIO read (ID), capturing subsequent VERSION/CAP reads if they
# occur within the 1024-sample post-trigger window.
vivado -mode batch -source vivado/p03_2c_ila_capture.tcl \
    -tclargs "$OUT_DIR" "$ARMED_MARKER" "$LTX" "$HW_URL" \
    >"$VIVADO_LOG" 2>&1 &
VIVADO_PID=$!

cleanup() {
    if kill -0 "$VIVADO_PID" 2>/dev/null; then
        kill "$VIVADO_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

for _ in $(seq 1 200); do
    if [[ -f "$ARMED_MARKER" ]]; then
        break
    fi
    if ! kill -0 "$VIVADO_PID" 2>/dev/null; then
        echo "ERROR: Vivado exited before arming; see $VIVADO_LOG" >&2
        tail -80 "$VIVADO_LOG" >&2
        exit 4
    fi
    sleep 0.25
done
[[ -f "$ARMED_MARKER" ]] || {
    echo "ERROR: Vivado did not arm within 50 seconds; see $VIVADO_LOG" >&2
    tail -80 "$VIVADO_LOG" >&2
    exit 4
}

echo 'PASS: both ILAs armed; launching the real Cortex-A53 diagnostic ELF'
xsdb vivado/p03_2c_xsdb_run.tcl "$ELF" "$MAILBOX" "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/a53_run.log"

# Wait for capture/export even if either ILA saw no ARVALID. Keep every partial
# file for forensic inspection rather than deleting an unsuccessful capture.
set +e
wait "$VIVADO_PID"
CAPTURE_EXIT=$?
set -e
trap - EXIT

if [[ "$CAPTURE_EXIT" -ne 0 ]]; then
    echo "WARNING: one or both ILA captures failed (exit=$CAPTURE_EXIT); see $VIVADO_LOG"
fi

# FAIL is an EXPECTED diagnostic result until the original bug is fixed:
# show and preserve all four actual A53 reads without letting verify's
# nonzero status discard otherwise-successful AXI captures.
set +e
python scripts/p03_2c_verify_readonly.py --mailbox "$MAILBOX" --base "$MMIO_BASE" \
    2>&1 | tee "$OUT_DIR/verify.log"
VERIFY_EXIT=${PIPESTATUS[0]}
set -e
echo "P03_2C_A53_MAILBOX_VERIFY_EXIT=$VERIFY_EXIT"

for name in p03_2c_hpm0_capture.csv p03_2c_mmio_slave_capture.csv; do
    if [[ -s "$OUT_DIR/$name" ]]; then
        echo "PASS: captured $OUT_DIR/$name"
    else
        echo "WARNING: capture missing or empty: $OUT_DIR/$name"
    fi
done
echo "P03_2C_A53_ILA_EVIDENCE_DIR=$OUT_DIR"
echo 'IMPORTANT: reboot KV260 after diagnostic; Cortex-A53 Linux context was replaced.'
if [[ "$CAPTURE_EXIT" -ne 0 ]]; then
    exit 5
fi
for name in p03_2c_hpm0_capture.csv p03_2c_mmio_slave_capture.csv; do
    [[ -s "$OUT_DIR/$name" ]] || exit 6
done
echo 'PASS: P03.2c A53-originated dual-ILA capture artifacts collected (not MMIO acceptance)'
