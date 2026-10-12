#!/usr/bin/env bash
# P03.3b2 independent physical Cortex-A53 policy + adapter verification.
# Program the accepted FPD128 SmartConnect shell, execute actual adapter code,
# and preserve a new 64-byte mailbox + identity/log evidence bundle.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPORTS="${P03_DIAG_REPORTS:?Set P03_DIAG_REPORTS to the accepted FPD128 routed reports}"
BUILD_DIR="${P03_3B2_BUILD_DIR:?Set P03_3B2_BUILD_DIR to the new probe ELF build}"
EXPECTED_SHA="${P03_2C_EXPECTED_XSA_SHA:?Set P03_2C_EXPECTED_XSA_SHA to its matching routed XSA}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
ELF="$BUILD_DIR/vitis_workspace/p03_3b2_probe.elf"
FIXTURE="$BUILD_DIR/fixture"
MANIFEST="$FIXTURE/manifest.json"
OUT_DIR="${1:?Usage: run_p03_3b2_probe.sh <new-output-evidence-directory>}"
XSDB_URL="${P03_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P03_HW_SERVER_URL:-localhost:3121}"

for tool in xsdb vivado python sha256sum grep; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required hardware probe tool missing: $tool" >&2
        exit 2
    }
done
for input in "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF" \
    "$MANIFEST" "$FIXTURE/core0_initial.bin" "$FIXTURE/mailbox_zero.bin"; do
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
    echo "probe=p03_3b2_two_timestep_one_core_zero_packet"
    echo "ps_master=M_AXI_HPM0_FPD"
    echo "ps_master_width_bits=128"
    echo "mmio_slave_width_bits=32"
    echo "mmio_base=0xA4000000"
    for artifact in "$XSA" "$BIT" "$LTX" "$ELF" "$MANIFEST" \
        "$FIXTURE/core0_initial.bin"; do
        sha256sum "$artifact"
    done
} | tee "$OUT_DIR/artifact_identity.txt"

cat <<'EOF'
P03.3b2 PHYSICAL A53 RUNTIME ADAPTER PROBE
  This uses the P03.2c-accepted 128-bit FPD/SmartConnect shell.
  Reboot KV260 and allow normal boot firmware to initialize PS and DDR.
  This HALTS the A53/Linux execution context and runs an isolated ELF.
  It writes the P03.2c project-reserved DDR backing at 0x40000000
  (512 KiB) and mailbox at 0x43FF0000 (64 bytes).
  It executes two real page/dispatch/barrier timesteps (zero spike packets).
  It does not test physical cross-core packet delivery or dirty page-out.
  Reboot KV260 after execution, including on failure; do not resume Linux.
EOF

cd "$V3_DIR"
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$OUT_DIR/ps_width.log" || {
    echo "ERROR: physical PS FPD HPM0 width is not 128 bits" >&2; exit 3;
}

xsdb vivado/p03_2c_xsdb_prepare.tcl "$FIXTURE" "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/provision.log"
grep -Fq 'PASS: P03.2c backing record provisioned and mailbox cleared by physical readback' \
    "$OUT_DIR/provision.log" || {
    echo "ERROR: P03.3b2 fixture provision did not pass" >&2; exit 3;
}

vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" \
    2>&1 | tee "$OUT_DIR/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
    "$OUT_DIR/program.log" || {
    echo "ERROR: bitstream programming did not pass" >&2; exit 3;
}

MAILBOX="$OUT_DIR/p03_3b2_a53_mailbox.bin"
xsdb vivado/p03_2c_xsdb_run.tcl "$ELF" "$MAILBOX" "$XSDB_URL" \
    2>&1 | tee "$OUT_DIR/a53_run.log"
[[ -s "$MAILBOX" ]] || {
    echo "ERROR: physical mailbox not dumped" >&2; exit 4;
}

# A failure is as valuable as a pass while debugging. Keep all evidence.
set +e
python scripts/p03_3b2_verify_probe.py \
    --mailbox "$MAILBOX" --manifest "$MANIFEST" \
    2>&1 | tee "$OUT_DIR/verify.log"
VERIFY_EXIT=${PIPESTATUS[0]}
set -e
echo "P03_3B2_VERIFY_EXIT=$VERIFY_EXIT"
echo "P03_3B2_EVIDENCE_DIR=$OUT_DIR"
echo 'IMPORTANT: reboot KV260 now; running Linux was replaced by standalone A53'
if [[ "$VERIFY_EXIT" != 0 ]]; then
    echo "FAIL: P03.3b2 physical Cortex-A53 runtime-adapter probe; evidence preserved"
    exit 5
fi
echo "PASS: P03.3b2 physical Cortex-A53 two-timestep runtime-adapter probe"
