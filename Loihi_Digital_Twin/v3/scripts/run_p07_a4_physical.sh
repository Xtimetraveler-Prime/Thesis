#!/usr/bin/env bash
# P07-A4.2c candidate persistent A53 hardware gate. DO NOT run under Linux.
# This OVERWRITES 0x40000000..0x43FFFFFF JTAG-owned DDR (64MiB).
# Must reboot to dedicated bare-metal state BEFORE and AFTER each run.
# Physical result is unverified until independent packed replay matches.
set -euo pipefail

V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="${P07_A4_RUN_DIR:?Set a NEW absolute P07_A4_RUN_DIR}"
BUILD="${P07_A4_BUILD_DIR:?Set P07_A4_BUILD_DIR from new accepted Vitis native build}"
REPORTS="${P03_DIAG_REPORTS:?Set accepted P03.2c physical reports directory}"
EXPECTED="${P03_2C_EXPECTED_XSA_SHA:?Set accepted routed XSA SHA}"
STAGE="${P07_A4_STAGE_DIR:?Set absolute A4.2a synthetic/validation stage}"
MASTER="${P07_A4_MASTER_DDR:-$V3/artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin}"
ELF="$BUILD/vitis_workspace/p07_a4_board.elf"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
BIT="$REPORTS/p03_2_ps_mmio.bit"
LTX="$REPORTS/p03_2_ps_mmio.ltx"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
XSDB_URL="${P07_A4_XSDB_URL:-tcp:127.0.0.1:3121}"
HW_URL="${P07_A4_HW_URL:-localhost:3121}"
TIMEOUT="${P07_A4_TIMEOUT:-3600}"
MARKER="P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1"
cd "$V3"
[[ "$RUN" == /* && ! -e "$RUN" ]] || {
  echo "ERROR: evidence directory must be NEW and ABSOLUTE, refusing overwrite" >&2
  exit 2
}
[[ "$STAGE" == /* && -d "$STAGE" ]] || {
  echo "ERROR: stage directory must exist and be absolute" >&2; exit 2;
}
[[ "${P07_A4_CONFIRM_KV260_DDR_OVERWRITE:-}" == YES ]] || {
  echo "ERROR: reboot KV260 into dedicated bare-metal JTAG-only state" >&2
  echo "Explicitly set P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES AFTER reboot" >&2
  exit 2
}
for tool in python xsdb vivado sha256sum grep cmp strings readelf git; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: missing $tool (load Vitis/Vivado environment)" >&2; exit 2;
  }
done
for file in "$MASTER" "$XSA" "$BIT" "$LTX" "$METRICS" "$ELF"; do
  [[ -s "$file" ]] || { echo "ERROR: missing required physical artifact $file" >&2; exit 2; }
done
[[ "$EXPECTED" == 52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f ]] || {
  echo "ERROR: wrong routed XSA acceptance identity" >&2; exit 2;
}
[[ "$(sha256sum "$XSA" | awk '{print $1}')" == "$EXPECTED" ]] || {
  echo "ERROR: routed XSA SHA mismatch" >&2; exit 2;
}
[[ "$(sha256sum "$MASTER" | awk '{print $1}')" == 9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955 ]] || {
  echo "ERROR: frozen immutable trained master SHA differs" >&2; exit 2;
}
grep -aFq "$MARKER" "$ELF" || {
  echo "ERROR: ELF must be NEW A4.2b persistent Vitis ELF (not A2)" >&2; exit 2;
}
for expected in   p03_hpm0_data_width_bits=128   p03_hpm0_transport=smartconnect_width_protocol   p03_mmio_slave_data_width_bits=32   p03_ps_mmio_master=FPD   p03_mmio_base=0xA4000000; do
  grep -Fxq "$expected" "$METRICS" || {
    echo "ERROR: mismatch in accepted routed FPD128 fabric: $expected" >&2; exit 2;
  }
done
# Reject stale compiled firmware sources, including accepted P03 untouched ABI.
for file in p07_a4_board.c p07_a4_stream.c p07_a4_supervisor.c             p07_a2_runtime.c p07_a1_ingress.c p07_a2_sha256.c; do
  cmp -s "$BUILD/source/$file" "software/p07/$file" || {
    echo "ERROR: A53 staged source does not match this branch: $file" >&2; exit 2;
  }
done
for file in p07_a1_ingress.h p07_a2_runtime.h p07_a2_batch.h             p07_a2_sha256.h p07_a4_stream.h p07_a4_supervisor.h; do
  cmp -s "$BUILD/source/include/$file" "software/p07/include/$file" || {
    echo "ERROR: A53 staged P07 header drift: $file" >&2; exit 2;
  }
done
for file in p03_runtime.c p03_hw_adapter.c p03_hw_runtime_bridge.c p03_hw_xilinx_io.c; do
  cmp -s "$BUILD/source/$file" "software/p03/$file" || {
    echo "ERROR: staged accepted P03 C drift: $file" >&2; exit 2;
  }
done
for file in p03_mmio.h p03_runtime.h p03_hw_adapter.h             p03_hw_runtime_bridge.h p03_hw_xilinx_io.h; do
  cmp -s "$BUILD/source/$file" "software/p03/include/$file" || {
    echo "ERROR: staged accepted P03 header drift: $file" >&2; exit 2;
  }
done
PYTHONPATH="$V3/src" python scripts/p07_a4_2_check.py --stage-dir "$STAGE"
readelf -lW "$ELF" | python -c '
import sys
loads=[x.split() for x in sys.stdin if x.split() and x.split()[0]=="LOAD"]
assert loads,"no ELF LOAD segments"
for line in loads:
    lo=int(line[2],16)
    hi=lo+int(line[5],16)
    assert not(lo<0x44000000 and hi>0x40000000),(
        "P07-A4.2c ELF overlaps reserved 64MiB DDR",hex(lo),hex(hi))
print("P07_A4_2C_ELF_DDR_ISOLATION_PASS=1")
'
# Board physical validation is explicitly sealed to synthetic and
# TRAIN-derived validation only: independent stage checker rejects TEST.
mkdir -p "$RUN/readback"
python - "$RUN/trace_zero_64k.bin" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
with path.open("xb") as f: f.write(bytes(65536))
PY
{
  echo "phase=P07-A4.2c persistent A53 TRAIN-derived validation physical gate"
  echo "status=BOARD_NOT_YET_RUN"
  echo "git_commit=$(git rev-parse HEAD)"
  sha256sum "$XSA" "$BIT" "$LTX" "$ELF" "$MASTER"     "$STAGE/p07_a4_descriptor_256.bin"     "$STAGE/p07_a4_mapping_1568.bin"     "$STAGE/p07_a4_pixels_raw.bin"     "$STAGE/p07_a4_journal_initial_1m.bin"     "$STAGE/p07_a4_2a_stage_manifest.json"
} | tee "$RUN/physical_identity.txt"
cat <<'EOF'
P07-A4.2c PHYSICAL: THIS HALTS A53 CORES AND OVERWRITES THE RESERVED
64MiB DDR AT 0x40000000..0x43FFFFFF. NEVER RUN WITH LINUX DDR OWNERSHIP.
ONE XSDB 'con' STARTS THE A53 PERSISTENT NEURAL LOOP; PC DOES NOT
SCHEDULE INDIVIDUAL FRAMES OR TIMESTEPS. REBOOT KV260 AFTERWARD.
EOF
xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl "$XSDB_URL"     2>&1 | tee "$RUN/ps_width.log"
grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128' "$RUN/ps_width.log" || {
    echo "ERROR: physical FPD HPM0 did not verify 128-bit" >&2; exit 3;
}
xsdb vivado/p07_a4_xsdb_prepare.tcl     "$MASTER" "$STAGE" "$RUN/trace_zero_64k.bin"     "$RUN/readback" "$XSDB_URL"     2>&1 | tee "$RUN/provision.log"
grep -Fq 'P07_A4_2C_XSDB_PROVISION_PASS=1' "$RUN/provision.log"
vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl     -tclargs "$BIT" "$LTX" "$HW_URL"     2>&1 | tee "$RUN/program.log"
grep -Fq 'PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released'     "$RUN/program.log"
xsdb vivado/p07_a4_xsdb_run.tcl     "$ELF" "$RUN/p07_a4_journal_1m.bin" "$RUN/p07_a4_trace_64k.bin"     "$XSDB_URL" "$TIMEOUT"     2>&1 | tee "$RUN/a53_run.log"
grep -Fq 'P07_A4_2C_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS'     "$RUN/a53_run.log" || {
      echo "ERROR: A53 terminal was not successful; preserve all evidence" >&2; exit 4;
    }
PYTHONPATH="$V3/src" python scripts/p07_a4_2_verify.py     --stage-dir "$STAGE"     --journal "$RUN/p07_a4_journal_1m.bin"     --trace "$RUN/p07_a4_trace_64k.bin"     2>&1 | tee "$RUN/verify.log"
grep -Fxq 'P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1' "$RUN/verify.log"
echo "P07_A4_2C_PHYSICAL_EVIDENCE_DIR=$RUN"
echo "P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1"
echo "REBOOT THE KV260; do not resume the halted operating system."
