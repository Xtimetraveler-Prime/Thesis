#!/usr/bin/env bash
# P05.2g event-bank boundary: two separate physical run modes on SAME accepted A53/PL.
# Prepare once. MUST independently reboot board between "physical-full" and "physical-overflow".
set -euo pipefail
[[ $# -eq 2 ]] || { echo "Usage: $0 {prepare|physical-full|physical-overflow} /absolute/evidence-root" >&2;exit 2; }
MODE="$1"; ROOT="$2"
[[ "$ROOT" == /* ]] || { echo "ERROR: absolute evidence directory required" >&2;exit 2; }
V3_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$V3_DIR"
# Fail before any JTAG/DDR work if a new P05.2g Python module is malformed.
python -m py_compile \
  scripts/p05_2g_capacity_fixture.py \
  scripts/p05_2g_capacity_verify.py \
  tests/test_p05_2g_capacity.py
if [[ "$MODE" == prepare ]]; then
  [[ ! -e "$ROOT" ]] || { echo "ERROR: refuse overwrite of existing capacity evidence" >&2;exit 2; }
  PYTHONPATH="$V3_DIR/src" python scripts/p05_2g_capacity_fixture.py --output-dir "$ROOT"
  python - "$ROOT" <<'PY'
from pathlib import Path
import json,hashlib,struct,sys,zlib
p=Path(sys.argv[1])
g=json.loads((p/"full/p05_2g_full_gate.json").read_text())
n=json.loads((p/"overflow/p05_2g_overflow_gate.json").read_text())
assert g["event_count"]==4096 and n["event_count"]==4097
for folder,expect in ((p/"full",4096),(p/"overflow",4097)):
    h=(folder/"p05_artifacts/p05_header.bin").read_bytes()
    a=(folder/"p05_artifacts/p05_payload.bin").read_bytes()
    words=struct.unpack("<64I",h)
    assert words[13]==expect and words[12]==len(a)
    assert words[22]==zlib.crc32(a)
    assert words[23]==zlib.crc32(h[:92]+bytes(4)+h[96:])
    assert (folder/"p05_mailbox_zero.bin").read_bytes()==bytes(256)
    assert (folder/"p05_artifacts/core0_initial.bin").read_bytes()==(
       folder/"capacity_golden/core0_initial.bin").read_bytes()
    with (folder/"preflight_identity.txt").open("w") as out:
        out.write("MODEL_ONLY; no physical KV260 coverage\n")
        for rel in ("p05_artifacts/p05_header.bin",
                    "p05_artifacts/p05_payload.bin",
                    "p05_artifacts/core0_initial.bin",
                    "capacity_golden/core0_initial.bin"):
            f=folder/rel
            out.write(hashlib.sha256(f.read_bytes()).hexdigest()+"  "+str(f)+"\n")
        for rel in ("p05_2g_full_gate.json","capacity_golden/manifest.json",
                    "capacity_golden/core0_expected.bin") if expect==4096 else (
                    "p05_2g_overflow_gate.json",):
            f=folder/rel
            out.write(hashlib.sha256(f.read_bytes()).hexdigest()+"  "+str(f)+"\n")
print("PASS: P05.2g full 4096 and overflow 4097 P05G CRC/sha preflight; NO KV260 touched")
PY
  echo "P05_2G_ROOT=$ROOT"
  exit 0
fi
case "$MODE" in
 physical-full) PROFILE="full";;
 physical-overflow) PROFILE="overflow";;
 *) echo "ERROR: expected prepare, physical-full or physical-overflow" >&2;exit 2;;
esac
OUT="$ROOT/$PROFILE"
[[ "${P05_2G_CONFIRM_KV260_DDR_OVERWRITE:-}" == YES ]] || {
  echo "ERROR: REBOOT board, then set P05_2G_CONFIRM_KV260_DDR_OVERWRITE=YES" >&2;exit 2;
}
[[ -s "$OUT/preflight_identity.txt" ]] || {
  echo "ERROR: prepare this exact capacity evidence root offline first" >&2;exit 2;
}
[[ ! -e "$OUT/p05_a53_result.bin" && ! -e "$OUT/verify.log" ]] || {
  echo "ERROR: already executed; preserve prior physical evidence, prepare fresh directory" >&2;exit 2;
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
# Independently recheck EVERY staged evidence-file hash before programming.
python - "$OUT" <<'PY'
import hashlib,sys
from pathlib import Path
root=Path(sys.argv[1])
for line in (root/"preflight_identity.txt").read_text().splitlines():
    x=line.split()
    if len(x)==2 and len(x[0])==64:
        if hashlib.sha256(Path(x[1]).read_bytes()).hexdigest()!=x[0]:
            raise SystemExit("FAIL: P05.2g staged SHA changed: "+x[1])
print("PASS: P05.2g exact staged P05G/DDR/golden SHA provenance preserved")
PY
XSDB_URL="${P05_2G_XSDB_SERVER_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P05_2G_HW_SERVER_URL:-localhost:3121}"
MAX_SECONDS="${P05_2G_RUN_MAX_SECONDS:-600}"
{
    echo "phase=P05.2g event-bank ${PROFILE} 4096-success/4097-fail-closed"
    echo "git_commit=$(git rev-parse HEAD)"
    for file in "$XSA" "$BIT" "$LTX" "$ELF"; do
        sha256sum "$file"
    done
} | tee "$OUT/physical_identity.txt"
cat <<'EOF'
P05.2g PHYSICAL GATE — event-bank 4096 success OR CRC-valid 4097 rejection (one separate boot each)
  Requires rebooted KV260 with DDR initialized and accessible JTAG/hw_server.
  This HALTS Linux and OVERWRITES project DDR 0x40000000..0x43FFFFFF.
  Uses new P05 A53 ELF, same accepted P03.2c FPD128 bitstream.
  PC only provisions, starts ELF once, observes terminal and dumps DDR.
  Reboot KV260 afterward, even if it fails. Do NOT resume halted Linux.
EOF
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
    2>&1 | tee "$OUT/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$OUT/ps_width.log"
xsdb vivado/p05_2g_capacity_prepare.tcl "$OUT" "$XSDB_URL" \
    2>&1 | tee "$OUT/provision.log"
grep -Fq 'PASS: P05.2g one initial record, P05G payload/header and zero result mailbox provisioned/read back' \
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
xsdb vivado/p03_finish_xsdb_dump.tcl "$OUT/final_ddr" "$XSDB_URL" \
    2>&1 | tee "$OUT/ddr_dump.log"
grep -Fq 'PASS: P03 five authoritative DDR records captured from KV260' \
    "$OUT/ddr_dump.log"
set +e
PYTHONPATH="$V3_DIR/src" python scripts/p05_2g_capacity_verify.py \
    --mode "$PROFILE" --directory "$OUT" \
    2>&1 | tee "$OUT/verify.log"
CHECK=${PIPESTATUS[0]}
set -e
echo "P05_2G_${PROFILE^^}_VERIFY_EXIT=$CHECK"
echo "P05_2G_${PROFILE^^}_EVIDENCE_DIR=$OUT"
echo "IMPORTANT: reboot KV260 now; do not resume Linux."
if [[ "$CHECK" != 0 ]]; then
    echo "FAIL: P05.2g $PROFILE strict capacity/rejection gate; original evidence retained"
    exit 5
fi
echo "PASS: P05.2g physical $PROFILE mode strict verification passed"
