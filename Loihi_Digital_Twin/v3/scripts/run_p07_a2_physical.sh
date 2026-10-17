#!/usr/bin/env bash
# P07-A2 guarded *physical* KV260 gate. Requires a rebooted, JTAG-owned
# bare-metal KV260. OVERWRITES reserved 64MiB DDR; NOT safe under Linux.
# No algorithmic PC step orchestration after the ONE A53 ELF launch.
set -euo pipefail

V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="${P07_A2_RUN_DIR:?Set NEW absolute evidence directory P07_A2_RUN_DIR}"
BUILD="${P07_A2_BUILD_DIR:?Set NEW TRACE_CONTEXT_FIX Vitis build directory}"
REPORTS="${P03_DIAG_REPORTS:?Set accepted P03.2c routed reports directory}"
EXPECTED="${P03_2C_EXPECTED_XSA_SHA:?Set accepted routed XSA SHA256}"
BATCH="${P07_A2_BATCH_DIR:?Set absolute batch output directory}"
MASTER="${P07_A2_MASTER_DDR:-$V3/artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin}"
ELF="$BUILD/vitis_workspace/p07_a2_board.elf"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
XSDB_URL="${P07_A2_XSDB_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P07_A2_HW_URL:-localhost:3121}"
TIMEOUT="${P07_A2_TIMEOUT:-900}"
MARKER="P07_A2_KV260_A53_FROZEN_TRACK_A_V1_TRACE_CONTEXT_FIX"
cd "$V3"

[[ "$RUN" == /* && ! -e "$RUN" ]] || {
  echo "ERROR: P07_A2_RUN_DIR must be new absolute path (no overwrite)" >&2; exit 2;
}
[[ "$BATCH" == /* && -d "$BATCH" ]] || {
  echo "ERROR: P07_A2_BATCH_DIR must be an existing absolute path" >&2; exit 2;
}
[[ "${P07_A2_CONFIRM_KV260_DDR_OVERWRITE:-}" == YES ]] || {
  echo "ERROR: reboot KV260 into dedicated JTAG/bare-metal use first" >&2
  echo "Then explicitly export P07_A2_CONFIRM_KV260_DDR_OVERWRITE=YES" >&2
  exit 2
}
for tool in xsdb vivado python sha256sum grep cmp strings readelf git; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: missing $tool (source Vitis/Vivado environment)" >&2; exit 2;
  }
done
for file in "$MASTER" "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF"; do
  [[ -s "$file" ]] || { echo "ERROR: missing input $file" >&2; exit 2; }
done
[[ "$EXPECTED" == 52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f ]] || {
  echo "ERROR: unexpected XSA SHA-256 differs from user native accepted build" >&2; exit 2;
}
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$EXPECTED" ]] || {
  echo "ERROR: XSA digest differs from accepted routed artifact" >&2; exit 2;
}
[[ "$(sha256sum "$MASTER" | awk '{print $1}')" ==     9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955 ]] || {
  echo "ERROR: frozen DDR master digest mismatch" >&2; exit 2;
}
grep -aFq "$MARKER" "$ELF" || {
  echo "ERROR: old ELF predates live-timestep trace fix; rebuild P07-A2" >&2; exit 2;
}
for expected in \
    'p03_hpm0_data_width_bits=128' \
    'p03_hpm0_transport=smartconnect_width_protocol' \
    'p03_mmio_slave_data_width_bits=32' \
    'p03_ps_mmio_master=FPD' \
    'p03_mmio_base=0xA4000000'; do
  grep -Fxq "$expected" "$METRICS" || {
    echo "ERROR: changed routed PS/PL physical metric $expected" >&2; exit 2;
  }
done
# Important: no old staged source may be used with a green "Vitis build".
for c in p07_a2_board.c p07_a2_runtime.c p07_a1_ingress.c \
         p07_a2_batch.c p07_a2_sha256.c; do
  cmp -s "$BUILD/source/$c" "software/p07/$c" || {
    echo "ERROR: ELF staging source differs from branch: $c" >&2; exit 2;
  }
done
for h in p07_a1_ingress.h p07_a2_runtime.h p07_a2_batch.h p07_a2_sha256.h; do
  cmp -s "$BUILD/source/$h" "software/p07/include/$h" || {
    echo "ERROR: stale P07 A53 header: $h" >&2; exit 2;
  }
done
for c in p03_runtime.c p03_hw_adapter.c p03_hw_runtime_bridge.c p03_hw_xilinx_io.c; do
  cmp -s "$BUILD/source/$c" "software/p03/$c" || {
    echo "ERROR: accepted P03 source unexpectedly changed/stale: $c" >&2; exit 2;
  }
done
for h in p03_mmio.h p03_runtime.h p03_hw_adapter.h \
         p03_hw_runtime_bridge.h p03_hw_xilinx_io.h; do
  cmp -s "$BUILD/source/$h" "software/p03/include/$h" || {
    echo "ERROR: accepted P03 ABI header unexpectedly changed/stale: $h" >&2; exit 2;
  }
done

# Offline validate both independently versioned envelopes and exact payload.
PYTHONPATH="$V3/src" python - "$MASTER" "$BATCH" <<'PY'
from pathlib import Path
import hashlib
import json
import sys
from loihi_twin_v2.p07_a2_batch import parse_batch, DDR_SHA256, COMPILED_FINGERPRINT
master=Path(sys.argv[1]); batch=Path(sys.argv[2])
manifest=json.loads((batch/"p07_a2_manifest.json").read_text())
header=(batch/"p07_a2_header_64.bin").read_bytes()
body=(batch/"p07_a2_ingress_payload.bin").read_bytes()
records=parse_batch(header,body)
assert hashlib.sha256(master.read_bytes()).hexdigest()==DDR_SHA256
assert manifest["ddr_sha256"]==DDR_SHA256
assert manifest["compiled_fingerprint"]==COMPILED_FINGERPRINT
assert manifest["frame_count"]==len(records)
assert manifest["sha256"]["header"]==hashlib.sha256(header).hexdigest()
assert manifest["sha256"]["payload"]==hashlib.sha256(body).hexdigest()
assert manifest["sha256"]["records"]==[hashlib.sha256(r).hexdigest() for r in records]
assert (batch/"p07_a2_mailbox_zero_64k.bin").read_bytes()==bytes(65536)
print("P07_A2_PHYSICAL_PREFLIGHT_HOST_PASS=1")
print("P07_A2_FRAME_COUNT="+str(len(records)))
PY

# ELF must avoid all reserved P03/P05/P07 DDR addresses.
readelf -lW "$ELF" | python -c '
import sys
data=sys.stdin.read().splitlines()
loads=[r.split() for r in data if r.split() and r.split()[0]=="LOAD"]
assert loads,"No ELF LOAD segments"
for entry in loads:
    low=int(entry[2],16)
    high=low+int(entry[5],16)
    assert not(low<0x44000000 and high>0x40000000),(low,high)
print("P07_A2_ELF_DDR_ISOLATION_PASS=1")
'
mkdir -p "$RUN/readback"
{
  echo "phase=P07-A2 autonomous trained 784x32x10 26-tick physical gate"
  echo "status=BOARD_NOT_YET_RUN"
  echo "git_commit=$(git rev-parse HEAD)"
  sha256sum "$XSA" "$BIT" "$LTX" "$ELF" "$MASTER" \
      "$BATCH/p07_a2_header_64.bin" "$BATCH/p07_a2_ingress_payload.bin" \
      "$BATCH/p07_a2_manifest.json"
} | tee "$RUN/physical_identity.txt"
cat <<'EOF'
P07-A2 PHYSICAL BOARD GATE: THIS HALTS A53 CORES AND OVERWRITES
DEDICATED DDR FROM 0x40000000 TO 0x43FFFFFF. Do NOT run under Linux.
The user must reboot the KV260 after this test, success or failure.
One XSDB 'con' starts the A53 autonomous application once; the PC
does not control per-tick dispatch, event injection, or packet routing.
EOF
# P03 width diagnostic is read-only for PS/PL, but stops A53s.
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL" \
   2>&1 | tee "$RUN/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$RUN/ps_width.log" || {
    echo "ERROR: runtime FPD width not accepted 128 bits" >&2; exit 3;
}
# Stage the immutable original image and unmodified accepted A1 records.
xsdb vivado/p07_a2_xsdb_prepare.tcl \
   "$MASTER" "$BATCH" "$RUN/readback" "$XSDB_URL" \
   2>&1 | tee "$RUN/provision.log"
grep -Fq 'P07_A2_XSDB_PROVISION_PASS=1' "$RUN/provision.log"
# Load exactly the previously accepted routed bitstream (no RTL/HLS change).
vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl \
   -tclargs "$BIT" "$LTX" "$HW_URL" \
   2>&1 | tee "$RUN/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released' \
   "$RUN/program.log"
xsdb vivado/p07_a2_xsdb_run.tcl \
   "$ELF" "$RUN/p07_a2_mailbox.bin" "$XSDB_URL" "$TIMEOUT" \
   2>&1 | tee "$RUN/a53_run.log"
grep -Fq 'P07_A2_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS' "$RUN/a53_run.log" || {
   echo "ERROR: A53 terminal status not success; preserve mailbox/logs" >&2; exit 4;
}
PYTHONPATH="$V3/src" python scripts/p07_a2_verify.py \
   --mailbox "$RUN/p07_a2_mailbox.bin" --batch-dir "$BATCH" \
   2>&1 | tee "$RUN/verify.log"
grep -Fxq 'P07_A2_PHYSICAL_TRACES_EXACT=1' "$RUN/verify.log"
echo "P07_A2_PHYSICAL_EVIDENCE_DIR=$RUN"
echo "P07_A2_GATE_FULL_PHYSICAL_PASS=1"
echo "REBOOT THE KV260; do not resume the halted operating system."
