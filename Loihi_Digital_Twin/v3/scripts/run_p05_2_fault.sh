#!/usr/bin/env bash
# P05.2a first directed PHYSICAL diagnostic negative test.
# Intentionally wrong EXPECTED state0 CRC at t=2 core=1.
# Test PASS is ONLY verified A53 0xDEAD000A with exact first mismatch.
# Same accepted P05 ELF, same P03 FPD128 shell, unchanged neuron stimuli.
# Usage: bash scripts/run_p05_2_fault.sh prepare <fresh-absolute-dir>
#        P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES bash scripts/run_p05_2_fault.sh physical <prepared-dir>
set -euo pipefail
[[ $# -eq 2 ]] || { echo "usage: $0 {prepare|physical} <absolute-evidence-dir>" >&2;exit 2; }
MODE="$1";OUT="$2"
[[ "$MODE" == prepare || "$MODE" == physical ]] || { echo "ERROR: mode must be prepare/physical" >&2;exit 2; }
[[ "$OUT" == /* ]] || { echo "ERROR: require absolute evidence path" >&2;exit 2; }
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$V3"
if [[ "$MODE" == prepare ]]; then
    [[ ! -e "$OUT" ]] || { echo "ERROR: evidence already exists" >&2;exit 2; }
    python scripts/p05_2_fault_fixture.py --output-dir "$OUT"
    python - "$OUT" <<'PY'
from pathlib import Path
import hashlib,json,struct,sys,zlib
r=Path(sys.argv[1]);a=r/"p05_artifacts"
g=json.loads((r/"p05_2_fault_gate.json").read_text())
h=(a/"p05_header.bin").read_bytes()
p=(a/"p05_payload.bin").read_bytes()
m=json.loads((a/"p05_manifest.json").read_text())
w=struct.unpack("<64I",h)
assert len(h)==256 and w[12]==len(p) and w[12]<=0xE0000
assert (w[0],w[1],w[3],w[4],w[5],w[6],w[13],w[14])==(0x47353050,1,1,5,3,3,15,15)
assert w[22]==zlib.crc32(p)
assert w[23]==zlib.crc32(h[:92]+bytes(4)+h[96:])
assert g["p05_header_sha256"]==m["header_sha256"]==hashlib.sha256(h).hexdigest()
assert g["p05_payload_sha256"]==m["payload_sha256"]==hashlib.sha256(p).hexdigest()
assert g["expected_terminal"]=="0xDEAD000A"
assert g["target_checkpoint_index"]==7
for core in range(3):
    assert (a/f"core{core}_initial.bin").read_bytes()==(r/"triangle_golden"/f"core{core}_initial.bin").read_bytes()
print("PASS: P05.2 3-core unchanged input and exactly one deliberate bad state CRC staged offline")
PY
    {
        echo "mode=P05.2 diagnostic EXPECTED negative; NO physical test has run"
        echo "must_stop_at=timestep2_core1_class_state0; no final DDR oracle after failure"
        for file in \
            p05_2_fault_gate.json p05_2_fault_spec.json \
            p05_artifacts/p05_header.bin p05_artifacts/p05_payload.bin \
            p05_artifacts/p05_manifest.json triangle_golden/manifest.json; do
            sha256sum "$OUT/$file"
        done
    } | tee "$OUT/preflight_identity.txt"
    echo "P05_2_FAULT_DIR=$OUT"
    echo "PASS: P05.2 negative test PREPARED ON HOST ONLY; KV260 untouched"
    exit 0
fi
[[ "${P05_2_CONFIRM_KV260_DDR_OVERWRITE:-}" == YES ]] || {
    echo "ERROR: explicitly reboot board and set P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES" >&2;exit 2;
}
[[ -s "$OUT/preflight_identity.txt" && -s "$OUT/p05_2_fault_gate.json" ]] || {
    echo "ERROR: prepare a new P05.2 fault evidence directory first" >&2;exit 2;
}
[[ ! -e "$OUT/p05_a53_result.bin" && ! -e "$OUT/verify.log" ]] || {
    echo "ERROR: physical attempt already exists; never overwrite evidence" >&2;exit 2;
}
REPORTS="${P03_DIAG_REPORTS:?Select accepted FPD128 reports}"
BUILD="${P05_1_BUILD_DIR:?Select previously verified P05 A53 ELF}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
ELF="$BUILD/vitis_workspace/p05_regression_run.elf"
EXPECTED="${P03_2C_EXPECTED_XSA_SHA:?Provide accepted XSA fingerprint}"
for tool in python xsdb vivado grep cmp sha256sum git; do
    command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2;exit 2; }
done
for file in "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF"; do
    [[ -s "$file" ]] || { echo "ERROR: missing $file" >&2;exit 2; }
done
[[ "${P03_XSA:-$XSA}" == "$XSA" ]] || { echo "ERROR: XSA selection changed" >&2;exit 2; }
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$EXPECTED" ]] || {
    echo "ERROR: accepted XSA fingerprint mismatch" >&2;exit 2;
}
for metric in \
    'p03_hpm0_data_width_bits=128' \
    'p03_hpm0_transport=smartconnect_width_protocol' \
    'p03_mmio_slave_data_width_bits=32' \
    'p03_ps_mmio_master=FPD' \
    'p03_mmio_base=0xA4000000'; do
    grep -Fxq "$metric" "$METRICS" || { echo "ERROR: topology drift $metric" >&2;exit 2; }
done
for file in p05_regression_run.c p05_deployment.c; do
    cmp -s "$BUILD/source/$file" "software/p05/$file" || {
        echo "ERROR: stale Vitis source $file; do not run" >&2;exit 2;
    }
done
cmp -s "$BUILD/source/p05_deployment.h" software/p05/include/p05_deployment.h || {
    echo "ERROR: stale P05 deployment ABI" >&2;exit 2;
}
for file in p03_runtime.c p03_hw_adapter.c p03_hw_runtime_bridge.c p03_hw_xilinx_io.c; do
    cmp -s "$BUILD/source/$file" "software/p03/$file" || {
        echo "ERROR: stale accepted PS runtime component $file" >&2;exit 2;
    }
done
grep -aFq P05_CONFIGURABLE_A53_REGRESSION_V1 "$ELF" || {
    echo "ERROR: wrong embedded ELF build signature" >&2;exit 2;
}
# The sha ledger is the PREPARED evidence, not a belief that P05R
# terminal ERROR is a successful test. The strict verifier handles that.
python - "$OUT" <<'PY'
import hashlib,sys
from pathlib import Path
r=Path(sys.argv[1])
for line in (r/"preflight_identity.txt").read_text().splitlines():
    w=line.split()
    if len(w)==2 and len(w[0])==64:
        assert hashlib.sha256(Path(w[1]).read_bytes()).hexdigest()==w[0],w[1]
print("PASS: P05.2 offline fault fixture SHA identities unchanged")
PY
{
  echo "status=physical diagnostic fault test launched; must FAIL correctly at first mismatch"
  echo "git_commit=$(git rev-parse HEAD)"
  for file in "$XSA" "$BIT" "$LTX" "$ELF"; do sha256sum "$file";done
} | tee "$OUT/physical_identity.txt"
XSDB_URL="${P05_2_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P05_2_HW_SERVER_URL:-localhost:3121}"
MAX_SECONDS="${P05_2_RUN_MAX_SECONDS:-600}"
cat <<'EOF'
P05.2 EXPECTED-FAILURE PHYSICAL TEST
  Reboot KV260 first; boot firmware must initialize DDR and JTAG/hw_server.
  Halts Linux. Overwrites project DDR region 0x40000000..0x43FFFFFF.
  The neuron model, inputs and weights are unchanged, but checkpoint
  7's EXPECTED CRC is wrong by one bit.
  EXPECT A53 terminal 0xDEAD000A, first fault at barrier t=2 core=1.
  Any other A53 result is a FAILED TEST, even if it says PASS.
  Do not resume Linux; reboot afterward, PASS or FAIL.
EOF
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$OUT/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$OUT/ps_width.log"
# Provision via accepted physical PSU/APU triangle transport:
# it confirms ALL three initial 512KiB records equal independent
# triangle reference, but uses the newly tampered P05G checkpoint table.
xsdb vivado/p05_1_triangle_prepare.tcl "$OUT" "$XSDB_URL" \
    2>&1 | tee "$OUT/provision.log"
grep -Fq 'PASS: P05.1 three triangle records, P05G payload/header and zero result mailbox provisioned/read back' "$OUT/provision.log"
vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" \
    2>&1 | tee "$OUT/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' "$OUT/program.log"
xsdb vivado/p03_finish_xsdb_run.tcl "$ELF" "$OUT/p05_a53_result.bin" \
    "$XSDB_URL" "$MAX_SECONDS" 2>&1 | tee "$OUT/a53_run.log"
grep -Fq 'PASS: P03 A53 terminal mailbox captured after board-local execution' "$OUT/a53_run.log"
# NO final-DDR golden after early failure: resident slots are dirty
# and final write_result/page-out was never called.
set +e
PYTHONPATH="$V3/src" python scripts/p05_2_fault_verify.py \
    --mailbox "$OUT/p05_a53_result.bin" --directory "$OUT" \
    2>&1 | tee "$OUT/verify.log"
CHECK=${PIPESTATUS[0]}
set -e
echo "P05_2_FAULT_VERIFY_EXIT=$CHECK"
echo "P05_2_FAULT_EVIDENCE_DIR=$OUT"
echo "IMPORTANT: reboot KV260 now; do not resume Linux."
if [[ "$CHECK" != 0 ]]; then
    echo "FAIL: P05.2 directed negative checkpoint did not produce exactly planned first-mismatch evidence"
    exit 5
fi
echo "PASS: P05.2 first hardware negative-checkpoint gate (correct early A53 ERROR)"
