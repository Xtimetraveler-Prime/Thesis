#!/usr/bin/env bash
# P03.3b3 independent physical Cortex-A53 policy + adapter verification.
# Program the accepted FPD128 SmartConnect shell, execute actual adapter code,
# and preserve a new 128-byte mailbox + identity/log evidence bundle.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPORTS="${P03_DIAG_REPORTS:?Set P03_DIAG_REPORTS to the accepted FPD128 routed reports}"
BUILD_DIR="${P03_3B3_BUILD_DIR:?Set P03_3B3_BUILD_DIR to the new probe ELF build}"
EXPECTED_SHA="${P03_2C_EXPECTED_XSA_SHA:?Set P03_2C_EXPECTED_XSA_SHA to its matching routed XSA}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
ELF="$BUILD_DIR/vitis_workspace/p03_3b3_probe.elf"
FIXTURE="$BUILD_DIR/fixture"
MANIFEST="$FIXTURE/manifest.json"
OUT_DIR="${1:?Usage: run_p03_3b3_probe.sh <new-output-evidence-directory>}"
XSDB_URL="${P03_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P03_HW_SERVER_URL:-localhost:3121}"

for tool in xsdb vivado python sha256sum grep; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required hardware probe tool missing: $tool" >&2
        exit 2
    }
done
for input in "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF" \
    "$MANIFEST" "$FIXTURE/core0_initial.bin" "$FIXTURE/core1_initial.bin" "$FIXTURE/mailbox_zero.bin"; do
    [[ -s "$input" ]] || { echo "ERROR: probe input missing: $input" >&2; exit 2; }
done
[[ "${P03_XSA:-$XSA}" == "$XSA" ]] || {
    echo "ERROR: P03_XSA does not match the routed FPD128 candidate" >&2
    exit 2
}
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$EXPECTED_SHA" ]] || {
    echo "ERROR: routed probe XSA hash mismatch" >&2; exit 2;
}
for expected in \
    'p03_hpm0_data_width_bits=128' \
    'p03_hpm0_transport=smartconnect_width_protocol' \
    'p03_mmio_slave_data_width_bits=32' \
    'p03_ps_mmio_master=FPD' \
    'p03_mmio_base=0xA4000000'; do
    grep -Fxq "$expected" "$METRICS" || {
        echo "ERROR: candidate route metric missing $expected" >&2
        exit 2
    }
done
[[ ! -e "$OUT_DIR" ]] || {
    echo "ERROR: evidence directory already exists: $OUT_DIR" >&2; exit 2;
}
mkdir -p "$OUT_DIR"
{
    echo "branch=agent/v3-p03-autonomous-runtime"
    echo "probe=p03_3b3_two_timestep_two_core_one_slot_real_hls_packets"
    echo "ps_master=M_AXI_HPM0_FPD"
    echo "ps_master_width_bits=128"
    echo "mmio_slave_width_bits=32"
    echo "mmio_base=0xA4000000"
    for artifact in "$XSA" "$BIT" "$LTX" "$ELF" "$MANIFEST" \
        "$FIXTURE/core0_initial.bin" "$FIXTURE/core1_initial.bin"; do
        sha256sum "$artifact"
    done
} | tee "$OUT_DIR/artifact_identity.txt"

cat <<'EOF'
P03.3b3 — REAL FPGA PACKETS / NONRESIDENT DDR ROUTING / DIRTY PAGE ROUNDTRIP
    Requires accepted FPD128 SmartConnect shell; NO Vivado RTL rebuild.
    Power-cycle/reboot KV260 and allow normal boot firmware to init DDR.
    Halts Cortex-A53/Linux. Replaces A53 #0 with a standalone app.
    Provisions TWO 512KiB records at 0x40000000 and 0x40080000,
    clears a 128-byte mailbox at 0x43FF0000.
    Physical page-in/out and packet writes modify the project DDR region.
    Reboot KV260 after running (including any failure). Do NOT resume Linux.
    This is a directed two-core test, not P03.4 five-over-three acceptance.
EOF

cd "$V3_DIR"
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$OUT_DIR/ps_width.log" || {
    echo "ERROR: physical PS FPD HPM0 width is not 128 bits" >&2; exit 3;
}

xsdb vivado/p03_3b3_xsdb_prepare.tcl "$FIXTURE" "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/provision.log"
grep -Fq 'PASS: P03.3b3 two 512KiB backing records and 128-byte mailbox physically verified' \
    "$OUT_DIR/provision.log" || {
    echo "ERROR: P03.3b3 fixture provision did not pass" >&2; exit 3;
}

vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" \
    2>&1 | tee "$OUT_DIR/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
    "$OUT_DIR/program.log" || {
    echo "ERROR: bitstream programming did not pass" >&2; exit 3;
}

MAILBOX="$OUT_DIR/p03_3b3_a53_mailbox.bin"
xsdb vivado/p03_3b3_xsdb_run.tcl "$ELF" "$MAILBOX" "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/a53_run.log"
[[ -s "$MAILBOX" ]] || {
    echo "ERROR: physical mailbox not dumped" >&2; exit 4;
}

# A failure is as valuable as a pass while debugging. Keep all evidence.
set +e
python scripts/p03_3b3_verify_probe.py \
    --mailbox "$MAILBOX" --manifest "$MANIFEST" \
    2>&1 | tee "$OUT_DIR/verify.log"
VERIFY_EXIT=${PIPESTATUS[0]}
set -e
echo "P03_3B3_VERIFY_EXIT=$VERIFY_EXIT"
echo "P03_3B3_EVIDENCE_DIR=$OUT_DIR"
echo 'IMPORTANT: reboot KV260 now; running Linux was replaced by standalone A53'
if [[ "$VERIFY_EXIT" != 0 ]]; then
    echo "FAIL: P03.3b3 physical HLS packet/DDR/dirty-page roundtrip; evidence preserved"
    exit 5
fi
echo "PASS: P03.3b3 physical Cortex-A53 two-core HLS packet/DDR/dirty-page roundtrip"
