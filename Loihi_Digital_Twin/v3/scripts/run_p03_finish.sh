#!/usr/bin/env bash
# Unified P03.3c/P03.4/P03.5 physical launch:
# one ELF, 7 or 100 timesteps, five logical cores, three resident slots.
# PC provisions/launches once then ONLY polls a terminal mailbox and dumps
# final DDR bytes AFTER completion. No host algorithmic timesteps or routing.
set -euo pipefail
[[ $# -eq 2 ]] || {
    echo "Usage: bash scripts/run_p03_finish.sh {7|100} <new-evidence-dir>" >&2
    exit 2
}
STEPS="$1"
[[ "$STEPS" == "7" || "$STEPS" == "100" ]] || {
    echo "ERROR: frozen P03 acceptance supports exactly 7 or 100 timesteps" >&2
    exit 2
}
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPORTS="${P03_DIAG_REPORTS:?Set P03_DIAG_REPORTS to previously accepted FPD128 route reports}"
BUILD_DIR="${P03_FINISH_BUILD_DIR:?Set P03_FINISH_BUILD_DIR to new unified A53 build}"
EXPECTED_SHA="${P03_2C_EXPECTED_XSA_SHA:?Set fixed candidate XSA hash}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
ELF="$BUILD_DIR/vitis_workspace/p03_finish_run.elf"
OUT="$2"
XSDB_URL="${P03_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P03_HW_SERVER_URL:-localhost:3121}"
MAX_SECONDS="${P03_RUN_MAX_SECONDS:-600}"
STAMP='P03_AUTONOMOUS_P02_GOLDEN_7_OR_100_V2'
for tool in python xsdb vivado grep cmp sha256sum awk; do
    command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2; exit 2; }
done
for file in "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF"; do
    [[ -s "$file" ]] || { echo "ERROR: missing accepted artifact: $file" >&2; exit 2; }
done
[[ "${P03_XSA:-$XSA}" == "$XSA" ]] || {
    echo "ERROR: unexpected XSA route; refusing incompatible PL" >&2; exit 2;
}
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$EXPECTED_SHA" ]] || {
    echo "ERROR: candidate XSA hash mismatch" >&2; exit 2;
}
for expect in \
    'p03_hpm0_data_width_bits=128' \
    'p03_hpm0_transport=smartconnect_width_protocol' \
    'p03_mmio_slave_data_width_bits=32' \
    'p03_ps_mmio_master=FPD' \
    'p03_mmio_base=0xA4000000'; do
    grep -Fxq "$expect" "$METRICS" || {
        echo "ERROR: routed candidate topology mismatch: $expect" >&2;exit 2;
    }
done
# Catch stale ELF and wrong exported build directories BEFORE touching board.
for source in p03_finish_run.c p03_runtime.c p03_hw_adapter.c p03_hw_runtime_bridge.c p03_hw_xilinx_io.c; do
    [[ -s "$BUILD_DIR/source/$source" ]] || {
        echo "ERROR: staged source missing $source" >&2; exit 2;
    }
    cmp -s "$BUILD_DIR/source/$source" "$V3_DIR/software/p03/$source" || {
        echo "ERROR: stale source in selected Vitis build: $source" >&2; exit 2;
    }
done
grep -aFq "$STAMP" "$ELF" || {
    echo "ERROR: selected ELF does not contain retained autonomy stamp $STAMP" >&2
    exit 2
}
[[ ! -e "$OUT" ]] || {
    echo "ERROR: evidence directory already exists: $OUT" >&2; exit 2;
}
mkdir -p "$OUT"
FIXTURE="$OUT/fixture"
DUMPS="$OUT/final_ddr"
mkdir -p "$FIXTURE" "$DUMPS"
cd "$V3_DIR"
PYTHONPATH="$V3_DIR/src" python scripts/p03_finish_fixture.py \
    --timesteps "$STEPS" --output-dir "$FIXTURE" \
    2>&1 | tee "$OUT/fixture.log"

{
    echo "phase=P03 autonomy/five-over-three/frozen P02 golden"
    echo "branch=agent/v3-p03-autonomous-runtime"
    echo "timesteps=$STEPS"
    echo "cores=5"
    echo "resident_slots=3"
    echo "physical_engines=1"
    echo "single_start_action=true"
    echo "pc_algorithmic_control=false"
    echo "selected_elf=$ELF"
    echo "selected_build_dir=$BUILD_DIR"
    for file in "$XSA" "$BIT" "$LTX" "$ELF" \
        "$FIXTURE/p03_run_config.bin" "$FIXTURE/p03_run_manifest.json"; do
        sha256sum "$file"
    done
} | tee "$OUT/identity.txt"

cat <<'EOF'
P03 AUTONOMOUS PHYSICAL GOLDEN GATE
  KV260 boot firmware must already have initialized DDR.
  This halts Linux and executes a standalone A53 application.
  Project DDR region 0x40000000..0x43FFFFFF WILL be overwritten.
  The PC will not issue MMIO page/route/dispatch/barrier commands.
  Physical FPGA bitstream is the accepted P03.2c FPD128 candidate.
  Restart/reboot KV260 after running, even if this test fails.
EOF
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$OUT/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$OUT/ps_width.log" || {
    echo "ERROR: booted PS FPD width is not 128 bits" >&2; exit 3;
}
xsdb vivado/p03_finish_xsdb_prepare.tcl "$FIXTURE" "$XSDB_URL" \
    2>&1 | tee "$OUT/provision.log"
grep -Fq 'PASS: P03 five DDR records, 256B launch manifest and 256B mailbox provisioned/read back' \
    "$OUT/provision.log" || {
    echo "ERROR: physical DDR provision verification failed" >&2;exit 3;
}

vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" \
    2>&1 | tee "$OUT/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
    "$OUT/program.log" || { echo "ERROR: FPGA program did not pass" >&2;exit 3; }

MAILBOX="$OUT/p03_a53_result.bin"
xsdb vivado/p03_finish_xsdb_run.tcl "$ELF" "$MAILBOX" "$XSDB_URL" "$MAX_SECONDS" \
    2>&1 | tee "$OUT/a53_run.log"
[[ -s "$MAILBOX" ]] || { echo "ERROR: no terminal A53 result mailbox" >&2;exit 4; }

# No host access to per-core final DDR until board-local loop has ended.
xsdb vivado/p03_finish_xsdb_dump.tcl "$DUMPS" "$XSDB_URL" \
    2>&1 | tee "$OUT/final_ddr_dump.log"
grep -Fq 'PASS: P03 five authoritative DDR records captured from KV260' \
    "$OUT/final_ddr_dump.log" || {
    echo "ERROR: final five-core DDR capture failed" >&2; exit 4;
}

set +e
PYTHONPATH="$V3_DIR/src" python scripts/p03_finish_verify.py \
    --mailbox "$MAILBOX" --fixture-dir "$FIXTURE" --dump-dir "$DUMPS" \
    2>&1 | tee "$OUT/verify.log"
VERIFY_EXIT=${PIPESTATUS[0]}
set -e
echo "P03_FINISH_VERIFY_EXIT=$VERIFY_EXIT"
echo "P03_FINISH_EVIDENCE_DIR=$OUT"
echo "IMPORTANT: reboot KV260 now. Do NOT resume halted Linux."
if [[ "$VERIFY_EXIT" != 0 ]]; then
    echo "FAIL: P03 frozen five-core board-autonomous P02 golden; evidence retained"
    exit 5
fi
echo "PASS: P03 $STEPS-step independent board-autonomous physical golden gate"
