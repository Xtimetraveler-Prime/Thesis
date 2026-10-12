#!/usr/bin/env bash
# P05.1 SECOND genuine physical profile: 3-core/3-slot, threshold-2 triangle.
# Reuses SAME P05 configurable standalone A53 ELF and accepted FPD128 shell.
# Usage: bash scripts/run_p05_1_triangle.sh prepare <absolute-new-evidence-dir>
#        P05_1_CONFIRM_KV260_DDR_OVERWRITE=YES bash scripts/run_p05_1_triangle.sh physical <absolute-prepared-dir>
set -euo pipefail
[[ $# -eq 2 ]] || { echo "Usage: $0 {prepare|physical} <absolute-evidence-dir>" >&2; exit 2; }
MODE="$1"; OUT="$2"
[[ "$MODE" == prepare || "$MODE" == physical ]] || { echo "ERROR: use prepare or physical" >&2; exit 2; }
[[ "$OUT" == /* ]] || { echo "ERROR: evidence path must be absolute" >&2; exit 2; }
V3_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$V3_DIR"

if [[ "$MODE" == prepare ]]; then
    [[ ! -e "$OUT" ]] || { echo "ERROR: use a fresh evidence path" >&2; exit 2; }
    python scripts/p05_1_triangle_fixture.py --output-dir "$OUT"
    python - "$OUT" <<'PY'
from pathlib import Path
import json,hashlib,struct,sys,zlib
root=Path(sys.argv[1]);a=root/"p05_artifacts";g=root/"triangle_golden"
gate=json.loads((root/"triangle_gate.json").read_text())
info=json.loads((a/"p05_manifest.json").read_text())
raw=(a/"p05_header.bin").read_bytes()
payload=(a/"p05_payload.bin").read_bytes()
w=struct.unpack("<64I",raw)
assert (w[0],w[1],w[2],w[3],w[4],w[5],w[6],w[13],w[14],w[20])==(0x47353050,1,256,1,5,3,3,15,15,15)
assert w[12]==len(payload) and len(payload)<=0xE0000
assert w[22]==zlib.crc32(payload)
assert w[23]==zlib.crc32(raw[:92]+bytes(4)+raw[96:])
assert info["header_sha256"]==hashlib.sha256(raw).hexdigest()
assert info["payload_sha256"]==hashlib.sha256(payload).hexdigest()
assert gate["expected_resident_deliveries"]==12
assert gate["expected_packets"]==12
assert gate["expected_replacement_page_ins"]==0
assert gate["expected_final_page_outs"]==3
for cid in range(3):
    image=(a/f"core{cid}_initial.bin").read_bytes()
    assert len(image)==0x80000
    assert image==(g/f"core{cid}_initial.bin").read_bytes()
    assert info["record_sha256"][str(cid)]==hashlib.sha256(image).hexdigest()
assert (root/"p05_mailbox_zero.bin").read_bytes()==bytes(256)
print("PASS: P05.1 distinct triangle offline neural model and P05G binary preflight (12 real resident-delivery predictions)")
PY
    {
      echo "status=host-only; NO physical FPGA acceptance"
      echo "branch=agent/v3-p05-board-regression"
      echo "profile=p05-1-three-core-resident-triangle-threshold4-v1"
      for name in triangle_gate.json triangle_golden/manifest.json \
          p05_artifacts/p05_header.bin p05_artifacts/p05_payload.bin \
          p05_artifacts/p05_manifest.json; do
          sha256sum "$OUT/$name"
      done
    } | tee "$OUT/preflight_identity.txt"
    echo "P05_1_TRIANGLE_DIR=$OUT"
    echo "PASS: P05.1 triangle offline prepare finished; KV260 was NOT touched"
    exit 0
fi

[[ "${P05_1_CONFIRM_KV260_DDR_OVERWRITE:-}" == YES ]] || {
    echo "ERROR: reboot KV260 first; then set P05_1_CONFIRM_KV260_DDR_OVERWRITE=YES" >&2; exit 2;
}
[[ -s "$OUT/preflight_identity.txt" && -s "$OUT/triangle_gate.json" ]] || {
    echo "ERROR: prepare the triangle offline first" >&2; exit 2;
}
[[ ! -e "$OUT/p05_a53_result.bin" && ! -e "$OUT/verify.log" ]] || {
    echo "ERROR: evidence path was already run; never overwrite evidence" >&2; exit 2;
}
REPORTS="${P03_DIAG_REPORTS:?Set P03_DIAG_REPORTS to accepted FPD128 route}"
BUILD="${P05_1_BUILD_DIR:?Set P05_1_BUILD_DIR to successful P05 A53 ELF build}"
EXPECTED="${P03_2C_EXPECTED_XSA_SHA:?Set accepted XSA fingerprint}"
XSA="$REPORTS/p03_2_ps_mmio.xsa";BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
ELF="$BUILD/vitis_workspace/p05_regression_run.elf"
for tool in python xsdb vivado sha256sum cmp grep git; do
    command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2; exit 2; }
done
for file in "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF"; do
    [[ -s "$file" ]] || { echo "ERROR: missing accepted artifact: $file" >&2; exit 2; }
done
[[ "${P03_XSA:-$XSA}" == "$XSA" ]] || { echo "ERROR: unexpected XSA choice" >&2; exit 2; }
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$EXPECTED" ]] || {
    echo "ERROR: selected XSA SHA256 differs" >&2; exit 2;
}
for expected_metric in \
    'p03_hpm0_data_width_bits=128' \
    'p03_hpm0_transport=smartconnect_width_protocol' \
    'p03_mmio_slave_data_width_bits=32' \
    'p03_ps_mmio_master=FPD' \
    'p03_mmio_base=0xA4000000'; do
    grep -Fxq "$expected_metric" "$METRICS" || {
        echo "ERROR: accepted PS–PL route metric drift: $expected_metric" >&2;exit 2;
    }
done
for file in p05_regression_run.c p05_deployment.c; do
    cmp -s "$BUILD/source/$file" "software/p05/$file" || {
        echo "ERROR: stale Vitis P05 C source $file; rebuild before physical testing" >&2; exit 2;
    }
done
cmp -s "$BUILD/source/p05_deployment.h" software/p05/include/p05_deployment.h || {
    echo "ERROR: stale Vitis P05 ABI header" >&2; exit 2;
}
for file in p03_runtime.c p03_hw_adapter.c p03_hw_runtime_bridge.c p03_hw_xilinx_io.c; do
    cmp -s "$BUILD/source/$file" "software/p03/$file" || {
        echo "ERROR: stale imported P03 hardware adapter $file" >&2; exit 2;
    }
done
grep -aFq P05_CONFIGURABLE_A53_REGRESSION_V1 "$ELF" || {
    echo "ERROR: P05 runtime signature absent" >&2; exit 2;
}
# Critical: independently revalidate original profile/data before touching DDR.
python - "$OUT" <<'PY'
import sys,importlib.util
from pathlib import Path
root=Path.cwd()
spec=importlib.util.spec_from_file_location("p05_triangle_check",root/"scripts/p05_1_triangle_verify.py")
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
# Reuse the strict physical admission portion with synthetic mailbox/dump
# is not appropriate here, so verify each immutable preflight SHA instead.
target=Path(sys.argv[1])
for line in (target/"preflight_identity.txt").read_text().splitlines():
    parts=line.split()
    if len(parts)!=2 or len(parts[0])!=64:
        continue
    import hashlib
    original=parts[1]
    actual=hashlib.sha256(Path(original).read_bytes()).hexdigest()
    if parts[0]!=actual:
        raise SystemExit("FAIL: triangle preflight SHA drift: "+original)
print("PASS: P05.1 triangle offline evidence SHA identities unchanged")
PY
XSDB_URL="${P05_1_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P05_1_HW_SERVER_URL:-localhost:3121}"
MAX_SECONDS="${P05_1_RUN_MAX_SECONDS:-600}"
{
    echo "phase=P05.1 second independent neural network"
    echo "git_commit=$(git rev-parse HEAD)"
    for file in "$XSA" "$BIT" "$LTX" "$ELF"; do
        sha256sum "$file"
    done
} | tee "$OUT/physical_identity.txt"
cat <<'EOF'
P05.1 SECOND PHYSICAL GATE — THREE-CORE RESIDENT TRIANGLE
  Requires rebooted KV260 with DDR initialized and accessible JTAG/hw_server.
  This HALTS Linux and OVERWRITES project DDR 0x40000000..0x43FFFFFF.
  Uses new P05 A53 ELF, same accepted P03.2c FPD128 bitstream.
  PC only provisions, starts ELF once, observes terminal and dumps DDR.
  Reboot KV260 afterward, even if it fails. Do NOT resume halted Linux.
EOF
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$OUT/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$OUT/ps_width.log"
xsdb vivado/p05_1_triangle_prepare.tcl "$OUT" "$XSDB_URL" \
    2>&1 | tee "$OUT/provision.log"
grep -Fq 'PASS: P05.1 three triangle records, P05G payload/header and zero result mailbox provisioned/read back' \
    "$OUT/provision.log"
vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
    -tclargs "$BIT" "$LTX" "$HW_URL" \
    2>&1 | tee "$OUT/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
    "$OUT/program.log"
xsdb vivado/p03_finish_xsdb_run.tcl "$ELF" "$OUT/p05_a53_result.bin" \
    "$XSDB_URL" "$MAX_SECONDS" 2>&1 | tee "$OUT/a53_run.log"
grep -Fq 'PASS: P03 A53 terminal mailbox captured after board-local execution' \
    "$OUT/a53_run.log"
mkdir -p "$OUT/final_ddr"
xsdb vivado/p05_1_triangle_dump.tcl "$OUT/final_ddr" "$XSDB_URL" \
    2>&1 | tee "$OUT/ddr_dump.log"
grep -Fq 'PASS: P05.1 three triangle authoritative DDR records captured from KV260' \
    "$OUT/ddr_dump.log"
set +e
PYTHONPATH="$V3_DIR/src" python scripts/p05_1_triangle_verify.py \
    --mailbox "$OUT/p05_a53_result.bin" --directory "$OUT" \
    2>&1 | tee "$OUT/verify.log"
CHECK=${PIPESTATUS[0]}
set -e
echo "P05_1_TRIANGLE_VERIFY_EXIT=$CHECK"
echo "P05_1_TRIANGLE_EVIDENCE_DIR=$OUT"
echo "IMPORTANT: reboot KV260 now; do not resume Linux."
if [[ "$CHECK" != 0 ]]; then
    echo "FAIL: P05.1 second independent 3-core triangle golden; evidence kept"
    exit 5
fi
echo "PASS: P05.1 SECOND independent 3-core resident triangle 15-checkpoint physical gate"
