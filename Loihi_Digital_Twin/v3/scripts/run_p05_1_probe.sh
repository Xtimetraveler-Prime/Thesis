#!/usr/bin/env bash
# P05.1 first physical probe: accepted 7-step P02 neural workload,
# but NEW P05G deployment, NEW A53 runner and 35 intermediate checkpoints.
# Usage: bash scripts/run_p05_1_probe.sh prepare <new-dir>
#        P05_1_CONFIRM_KV260_DDR_OVERWRITE=YES bash scripts/run_p05_1_probe.sh physical <prepared-dir>
# NO PC algorithmic loop, page selection, spike routing or barriers.
set -euo pipefail
[[ $# -eq 2 ]] || { echo "Usage: $0 {prepare|physical} <evidence-dir>" >&2; exit 2; }
MODE="$1"; OUT="$2"
[[ "$MODE" == "prepare" || "$MODE" == "physical" ]] || {
    echo "ERROR: mode must be prepare or physical" >&2; exit 2;
}
[[ "$OUT" == /* ]] || { echo "ERROR: evidence path must be absolute" >&2; exit 2; }
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$V3_DIR"
STAMP=P05_CONFIGURABLE_A53_REGRESSION_V1
if [[ "$MODE" == prepare ]]; then
    [[ ! -e "$OUT" ]] || { echo "ERROR: evidence folder already exists" >&2; exit 2; }
    mkdir -p "$OUT"
    python scripts/p03_finish_fixture.py --timesteps 7 \
        --output-dir "$OUT/p03_golden" 2>&1 | tee "$OUT/fixture.log"
    python scripts/p05_deployment.py from-p03 \
        --fixture-dir "$OUT/p03_golden" \
        --output-spec "$OUT/p05_spec.json" \
        --state-checkpoints 2>&1 | tee "$OUT/from_p03.log"
    python scripts/p05_deployment.py build \
        --spec "$OUT/p05_spec.json" \
        --output-dir "$OUT/p05_artifacts" 2>&1 | tee "$OUT/deployment.log"
    python - "$OUT" <<'PY'
from pathlib import Path
import hashlib, json, struct, sys, zlib
out=Path(sys.argv[1])
a=out/"p05_artifacts";g=out/"p03_golden"
h=(a/"p05_header.bin").read_bytes()
p=(a/"p05_payload.bin").read_bytes()
m=json.loads((a/"p05_manifest.json").read_text())
f=json.loads((g/"p03_run_manifest.json").read_text())
w=struct.unpack("<64I",h)
assert (w[0],w[1],w[3],w[4],w[5],w[6],w[13],w[14],w[20]) == (
    0x47353050,1,1,7,5,3,35,35,35)
assert w[12]==len(p) and 0<len(p)<=0xE0000
assert w[22]==zlib.crc32(p)
assert w[23]==zlib.crc32(h[:92]+bytes(4)+h[96:])
assert m["header_sha256"]==hashlib.sha256(h).hexdigest()
assert m["payload_sha256"]==hashlib.sha256(p).hexdigest()
assert m["input_spec_sha256"]==hashlib.sha256((out/"p05_spec.json").read_bytes()).hexdigest()
assert m["logical_core_ids_in_service_order"]==[0,1,2,3,4]
assert f["dispatch_count"]==35 and f["expected_packet_count_total"]==30
assert f["trace_fingerprint"]=="9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac"
for k in range(5):
    actual=(a/f"core{k}_initial.bin").read_bytes()
    assert len(actual)==0x80000
    assert actual==(g/f"core{k}_initial.bin").read_bytes()
    assert hashlib.sha256(actual).hexdigest()==m["record_sha256"][str(k)]
(out/"p05_mailbox_zero.bin").write_bytes(bytes(256))
print("PASS: P05.1 preflight manifest CRC/SHA, frozen five DDR records, 35 external events, 35 model checkpoints")
PY
    {
        echo "phase=P05.1 autonomous PS regression / first frozen ring/checkpoint probe"
        echo "status=prepared only; no physical verification yet"
        echo "branch=agent/v3-p05-board-regression"
        echo "neural_oracle=frozen P02.4b accepted 7-step five-core ring"
        for name in p05_artifacts/p05_header.bin p05_artifacts/p05_payload.bin \
            p05_artifacts/p05_manifest.json p03_golden/p03_run_manifest.json; do
            sha256sum "$OUT/$name"
        done
    } | tee "$OUT/preflight_identity.txt"
    echo "P05_1_PROBE_DIR=$OUT"
    echo "PASS: P05.1 offline probe generated; board has NOT been touched"
    exit 0
fi

[[ "${P05_1_CONFIRM_KV260_DDR_OVERWRITE:-}" == YES ]] || {
    echo "ERROR: set P05_1_CONFIRM_KV260_DDR_OVERWRITE=YES after rebooting KV260" >&2
    exit 2
}
[[ -d "$OUT/p05_artifacts" && -s "$OUT/preflight_identity.txt" ]] || {
    echo "ERROR: run prepare first" >&2; exit 2;
}
[[ ! -e "$OUT/p05_a53_result.bin" && ! -e "$OUT/verify.log" ]] || {
    echo "ERROR: probe has already run; prepare a NEW evidence folder" >&2
    exit 2
}
REPORTS="${P03_DIAG_REPORTS:?Set P03_DIAG_REPORTS to accepted FPD128 report directory}"
BUILD="${P05_1_BUILD_DIR:?Set P05_1_BUILD_DIR to separately accepted P05.1 Vitis build}"
EXPECTED="${P03_2C_EXPECTED_XSA_SHA:?Set exact accepted FPD128 XSA fingerprint}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
ELF="$BUILD/vitis_workspace/p05_regression_run.elf"
for tool in python xsdb vivado sha256sum cmp grep; do
    command -v "$tool" >/dev/null || { echo "ERROR: $tool missing" >&2; exit 2; }
done
for file in "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF"; do
    [[ -s "$file" ]] || { echo "ERROR: missing artifact $file" >&2; exit 2; }
done
[[ "${P03_XSA:-$XSA}" == "$XSA" ]] || { echo "ERROR: wrong XSA selection" >&2;exit 2; }
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$EXPECTED" ]] || {
    echo "ERROR: XSA identity drift" >&2;exit 2;
}
for expect in \
    'p03_hpm0_data_width_bits=128' \
    'p03_hpm0_transport=smartconnect_width_protocol' \
    'p03_mmio_slave_data_width_bits=32' \
    'p03_ps_mmio_master=FPD' \
    'p03_mmio_base=0xA4000000'; do
    grep -Fxq "$expect" "$METRICS" || { echo "ERROR: routed topology mismatch" >&2; exit 2; }
done
for file in p05_regression_run.c p05_deployment.c; do
    cmp -s "$BUILD/source/$file" "$V3_DIR/software/p05/$file" || {
        echo "ERROR: stale P05 source in Vitis build: $file" >&2; exit 2;
    }
done
cmp -s "$BUILD/source/p05_deployment.h" "$V3_DIR/software/p05/include/p05_deployment.h" || {
    echo "ERROR: stale P05 ABI header" >&2; exit 2;
}
for file in p03_runtime.c p03_hw_adapter.c p03_hw_runtime_bridge.c p03_hw_xilinx_io.c; do
    cmp -s "$BUILD/source/$file" "$V3_DIR/software/p03/$file" || {
        echo "ERROR: stale accepted P03 adapter/runtime source $file" >&2;exit 2;
    }
done
grep -aFq "$STAMP" "$ELF" || {
    echo "ERROR: ELF missing P05 source identity (not the accepted new binary)" >&2; exit 2;
}
# Detect mutation of prepared fixture/spec/manifest after the offline gate.
python - "$OUT" <<'PY'
from pathlib import Path
import hashlib,json,sys,struct,zlib
p=Path(sys.argv[1]);a=p/"p05_artifacts";g=p/"p03_golden"
m=json.loads((a/"p05_manifest.json").read_text())
h=(a/"p05_header.bin").read_bytes();b=(a/"p05_payload.bin").read_bytes()
w=struct.unpack("<64I",h)
assert m["header_sha256"]==hashlib.sha256(h).hexdigest()
assert m["payload_sha256"]==hashlib.sha256(b).hexdigest()
assert m["input_spec_sha256"]==hashlib.sha256((p/"p05_spec.json").read_bytes()).hexdigest()
assert (w[4],w[5],w[6],w[13],w[14],w[3])==(7,5,3,35,35,1)
assert w[23]==zlib.crc32(h[:92]+bytes(4)+h[96:])
assert w[22]==zlib.crc32(b)
for k in range(5):
    raw=(a/f"core{k}_initial.bin").read_bytes()
    assert raw==(g/f"core{k}_initial.bin").read_bytes()
    assert hashlib.sha256(raw).hexdigest()==m["record_sha256"][str(k)]
print("PASS: P05.1 immutable launch content independently revalidated")
PY
XSDB_URL="${P05_1_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P05_1_HW_SERVER_URL:-localhost:3121}"
MAX_SECONDS="${P05_1_RUN_MAX_SECONDS:-600}"
{
    echo "source_git_commit=$(git rev-parse HEAD)"
    echo "status=physical probe invoked; PASS only if strict post-run verifier passes"
    for file in "$XSA" "$BIT" "$LTX" "$ELF"; do sha256sum "$file"; done
} | tee "$OUT/physical_identity.txt"
cat <<'EOF'
P05.1 FIRST PHYSICAL PROBE
  KV260 boot firmware MUST initialize DDR first. This STOPS Linux.
  DDR 0x40000000..0x43FFFFFF will be overwritten.
  Accepted P03.2c FPD128 FPGA bitstream, new P05-only A53 ELF.
  PC performs no algorithmic paging, dispatch, routing or barriers.
  Reboot board afterward, even if physical verification fails.
EOF
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$OUT/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$OUT/ps_width.log"
xsdb vivado/p05_1_xsdb_prepare.tcl "$OUT" "$XSDB_URL" \
    2>&1 | tee "$OUT/provision.log"
grep -Fq 'PASS: P05.1 five initial records, P05G payload/header and zero result mailbox provisioned/read back' \
    "$OUT/provision.log"
vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" \
    2>&1 | tee "$OUT/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
    "$OUT/program.log"
# Reuse ACCEPTED P03 terminal-only XSDB poller: same result word at
# 0x43FF0000 and same 0x600D600D / 0xDEADxxxx terminal protocol.
# P05R magic/structure are interpreted only by P05 verifier afterward.
xsdb vivado/p03_finish_xsdb_run.tcl "$ELF" "$OUT/p05_a53_result.bin" \
    "$XSDB_URL" "$MAX_SECONDS" 2>&1 | tee "$OUT/a53_run.log"
grep -Fq 'PASS: P03 A53 terminal mailbox captured after board-local execution' \
    "$OUT/a53_run.log"
mkdir -p "$OUT/final_ddr"
# Accepted P03 physical DDR dump operates AFTER terminal status, no
# timestep control, and captures the same frozen five 512KiB addresses.
xsdb vivado/p03_finish_xsdb_dump.tcl "$OUT/final_ddr" "$XSDB_URL" \
    2>&1 | tee "$OUT/ddr_dump.log"
grep -Fq 'PASS: P03 five authoritative DDR records captured from KV260' \
    "$OUT/ddr_dump.log"
set +e
PYTHONPATH="$V3_DIR/src" python scripts/p05_1_verify.py \
    --mailbox "$OUT/p05_a53_result.bin" \
    --fixture-dir "$OUT/p03_golden" \
    --artifact-dir "$OUT/p05_artifacts" \
    --dump-dir "$OUT/final_ddr" 2>&1 | tee "$OUT/verify.log"
VERIFY_EXIT=${PIPESTATUS[0]}
set -e
echo "P05_1_VERIFY_EXIT=$VERIFY_EXIT"
echo "P05_1_EVIDENCE_DIR=$OUT"
echo "IMPORTANT: reboot KV260 now; do not resume halted Linux."
if [[ "$VERIFY_EXIT" != 0 ]]; then
    echo "FAIL: P05.1 35-checkpoint physical A53 replay (evidence retained)"
    exit 5
fi
echo "PASS: P05.1 first 7-step 35-checkpoint A53 physical golden probe"
