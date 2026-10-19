#!/usr/bin/env bash
# P08-A2.1 latency-only, new experimental A53 ELF. BUILD ONLY, NO BOARD ACCESS.
set -euo pipefail
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="${P08_A2_BUILD_DIR:?Set NEW absolute P08_A2_BUILD_DIR outside Git}"
REPORTS="${P03_DIAG_REPORTS:?Point to existing user-accepted P03.2c routed reports}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
EXPECTED=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
[[ "$BUILD" == /* && ! -e "$BUILD" ]] || {
  echo "ERROR: P08_A2_BUILD_DIR must be new, absolute and untracked" >&2; exit 2;
}
[[ -s "$XSA" ]] || { echo "ERROR: accepted routed XSA not found" >&2; exit 2; }
for tool in python vitis sha256sum readelf grep; do
  command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2; exit 2; }
done
ACTUAL="$(sha256sum "$XSA" | awk '{print $1}')"
[[ "$ACTUAL" == "$EXPECTED" ]] || { echo "ERROR: XSA SHA mismatch" >&2; exit 2; }
mkdir -p "$BUILD/source/include"
cd "$V3"
for file in p08_a2_board.c p08_a2_timing.c; do
  cp "software/p08/$file" "$BUILD/source/$file"
done
cp software/p08/p08_a2_timing.h "$BUILD/source/p08_a2_timing.h"
for file in p07_a4_stream.c p07_a4_supervisor.c p07_a2_runtime.c p07_a1_ingress.c p07_a2_sha256.c; do
  cp "software/p07/$file" "$BUILD/source/$file"
done
for file in p07_a1_ingress.h p07_a2_runtime.h p07_a2_batch.h p07_a2_sha256.h p07_a4_stream.h p07_a4_supervisor.h; do
  cp "software/p07/include/$file" "$BUILD/source/$file"
  cp "software/p07/include/$file" "$BUILD/source/include/$file"
done
for file in p03_runtime.c p03_hw_adapter.c p03_hw_runtime_bridge.c p03_hw_xilinx_io.c; do
  cp "software/p03/$file" "$BUILD/source/$file"
done
for file in p03_mmio.h p03_runtime.h p03_hw_adapter.h p03_hw_runtime_bridge.h p03_hw_xilinx_io.h; do
  cp "software/p03/include/$file" "$BUILD/source/$file"
done
# Vitis 2025.2 builder creates a new isolated workspace and ELF.
vitis -s "$V3/software/p08/build_p08_a2.py" \
  --xsa "$XSA" --workspace "$BUILD/vitis_workspace" \
  --source-dir "$BUILD/source" 2>&1 | tee "$BUILD/vitis_build.log"
ELF="$BUILD/vitis_workspace/p08_a2_board.elf"
[[ -s "$ELF" ]] || { echo "ERROR: instrumented ELF missing" >&2; exit 3; }
grep -aFq "P08_A2_1_LATENCY_ONLY_KV260_A53_CANDIDATE_V1" "$ELF" || {
  echo "ERROR: incorrect experimental ELF identity" >&2; exit 3;
}
if grep -aFq "P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1" "$ELF"; then
  echo "ERROR: old P07 firmware identity present in experimental ELF" >&2; exit 3
fi
readelf -lW "$ELF" > "$BUILD/elf_program_headers.txt"
python - "$BUILD/elf_program_headers.txt" <<'PY'
from pathlib import Path
import sys
loads = [l.split() for l in Path(sys.argv[1]).read_text().splitlines()
         if l.split() and l.split()[0] == "LOAD"]
if not loads:
    raise SystemExit("ERROR: ELF has no LOAD segments")
for fields in loads:
    start = int(fields[2], 16)
    stop = start + int(fields[5], 16)
    if start < 0x44000000 and stop > 0x40000000:
        raise SystemExit("ERROR: candidate ELF overlaps frozen JTAG DDR window")
print("P08_A2_1_ELF_DDR_ISOLATION_PASS=1")
PY
grep -Fq "P08_A2_A53_VITIS_BUILD_PASS=1" "$BUILD/vitis_build.log"
{
  echo "P08_A2_1_XSA_SHA256=$ACTUAL"
  echo "P08_A2_1_ELF=$ELF"
  echo "P08_A2_1_ELF_SHA256=$(sha256sum "$ELF" | awk '{print $1}')"
  echo "P08_A2_1_VITIS_BUILD_PASS=1"
  echo "P08_A2_1_KV260_LATENCY=NOT_RUN"
} | tee "$BUILD/build_identity.txt"
