#!/usr/bin/env bash
# Full physical P03.2c smoke against the independently verified 128-bit
# PS HPM0 / 32-bit AXI-Lite SmartConnect candidate.
# Requires a fresh, matching candidate standalone A53 ELF and report XSA.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPORTS="${P03_DIAG_REPORTS:?Set P03_DIAG_REPORTS to corrected FPD128 routed reports}"
BUILD_DIR="${P03_2C_BUILD_DIR:?Set P03_2C_BUILD_DIR to the matching full-smoke Vitis build}"
CANDIDATE_SHA="${P03_2C_EXPECTED_XSA_SHA:?Set P03_2C_EXPECTED_XSA_SHA to the candidate XSA fingerprint}"
[[ "${P03_2C_SMOKE_CANDIDATE:-0}" == 1 ]] || {
    echo "ERROR: P03_2C_SMOKE_CANDIDATE=1 is required for this isolated gate" >&2
    exit 2
}
[[ "${P03_2C_READONLY_MMIO_BASE:-0xA4000000}" == 0xA4000000 ]] || {
    echo "ERROR: full smoke supports only FPD MMIO @ 0xA4000000" >&2
    exit 2
}
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
ELF="$BUILD_DIR/vitis_workspace/p03_2c_smoke.elf"
FIXTURE="$BUILD_DIR/fixture"
MANIFEST="$FIXTURE/manifest.json"
XSDB_URL="${P03_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P03_HW_SERVER_URL:-localhost:3121}"

for tool in xsdb vivado python sha256sum grep; do
    command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: missing $tool" >&2; exit 2; }
done
for file in "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF" "$MANIFEST" \
    "$FIXTURE/core0_initial.bin" "$FIXTURE/mailbox_zero.bin"; do
    [[ -s "$file" ]] || { echo "ERROR: full-smoke input missing/empty: $file" >&2; exit 2; }
done
[[ "${P03_XSA:-$XSA}" == "$XSA" ]] || {
    echo "ERROR: P03_XSA differs from candidate reports XSA" >&2
    exit 2
}
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$CANDIDATE_SHA" ]] || {
    echo "ERROR: candidate XSA checksum mismatch" >&2
    exit 2
}
for expected in \
    'p03_hpm0_data_width_bits=128' \
    'p03_hpm0_transport=smartconnect_width_protocol' \
    'p03_mmio_slave_data_width_bits=32' \
    'p03_ps_mmio_master=FPD' \
    'p03_mmio_base=0xA4000000'; do
    grep -Fxq "$expected" "$METRICS" || {
        echo "ERROR: routed hardware metrics missing $expected" >&2
        exit 2
    }
done

OUT_DIR="${1:-$BUILD_DIR/full_physical_evidence_$(date -u +%Y%m%dT%H%M%SZ)}"
[[ ! -e "$OUT_DIR" ]] || {
    echo "ERROR: physical evidence directory already exists: $OUT_DIR" >&2
    exit 2
}
mkdir -p "$OUT_DIR"
{
    echo "branch=agent/v3-p03-autonomous-runtime"
    echo "ps_master=M_AXI_HPM0_FPD"
    echo "ps_master_width_bits=128"
    echo "mmio_slave_width_bits=32"
    echo "mmio_base=0xA4000000"
    for file in "$XSA" "$BIT" "$LTX" "$ELF" "$MANIFEST"; do
        sha256sum "$file"
    done
} | tee "$OUT_DIR/artifact_identity.txt"

cat <<'EOF'
P03.2c FULL PHYSICAL SMOKE — WRITES MMIO PAGE/DEBUG/DISPATCH COMMANDS
  - Reboot KV260 before test so board firmware initializes PS clocks/DDR.
  - This halts A53 CPUs and replaces the running A53 #0 Linux context.
  - This provisions 512 KiB backing DDR at 0x40000000 and a 64-byte mailbox
    at 0x43FF0000; ensure these regions are reserved for this project.
  - The program writes page/debug/dispatch command registers and runs the PL.
  - Reboot KV260 after the test; do not resume the stopped Linux context.
  - This is the physical P03.2c full-smoke acceptance candidate only.
EOF

cd "$V3_DIR"

# Check the *actual running PS* configuration, not only the Vivado BD report.
# AMD warns these static selectors cannot safely be changed after boot.
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$OUT_DIR/ps_width.log" || {
    echo "ERROR: live PS HPM0_FPD does not match routed 128-bit design" >&2
    exit 3
}

xsdb vivado/p03_2c_xsdb_prepare.tcl "$FIXTURE" "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/provision.log"
grep -Fq 'PASS: P03.2c backing record provisioned and mailbox cleared by physical readback' \
    "$OUT_DIR/provision.log" || {
    echo "ERROR: DDR fixture provisioning did not pass" >&2
    exit 3
}

vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" \
    2>&1 | tee "$OUT_DIR/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
    "$OUT_DIR/program.log" || {
    echo "ERROR: corrected FPGA program/reset gate did not pass" >&2
    exit 3
}

MAILBOX="$OUT_DIR/p03_2c_full_smoke_mailbox.bin"
xsdb vivado/p03_2c_xsdb_run.tcl "$ELF" "$MAILBOX" "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/a53_run.log"
[[ -s "$MAILBOX" ]] || {
    echo "ERROR: physical smoke mailbox missing after standalone A53 run" >&2
    exit 4
}

# Deliberately preserve the complete evidence even on a failing verification.
set +e
python scripts/p03_2c_verify_mailbox.py \
    --mailbox "$MAILBOX" --manifest "$MANIFEST" \
    2>&1 | tee "$OUT_DIR/verify.log"
VERIFY_EXIT=${PIPESTATUS[0]}
set -e
echo "P03_2C_FULL_SMOKE_VERIFY_EXIT=$VERIFY_EXIT"
echo "P03_2C_FULL_SMOKE_EVIDENCE_DIR=$OUT_DIR"
echo "IMPORTANT: reboot KV260 after diagnostic (the Linux context was replaced)."
if [[ "$VERIFY_EXIT" -ne 0 ]]; then
    echo "FAIL: P03.2c full A53 physical page/resident/dispatch smoke; evidence preserved"
    exit 5
fi
echo "PASS: P03.2c full A53 physical page/resident/dispatch smoke (independent review pending)"
