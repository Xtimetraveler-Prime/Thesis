#!/usr/bin/env bash
# P07-A4.2b *candidate* A53 ELF, isolated from accepted P05 binaries.
# Must run on user's Linux/Vitis installation, not on GitHub CI.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD="${P07_A4_BUILD_DIR:?Set a NEW P07_A4_BUILD_DIR outside the repository}"
XSA="${P07_A4_XSA:?Set P07_A4_XSA to a known routed FPD128 XSA}"
EXPECTED="${P07_A4_XSA_SHA256:?Set P07_A4_XSA_SHA256 from accepted routed XSA evidence}"
[[ ! -e "$BUILD" ]] || { echo "P07-A4.2b refuses to overwrite $BUILD" >&2; exit 2; }
[[ -s "$XSA" ]] || { echo "P07-A4.2b XSA not found" >&2; exit 2; }
for tool in python vitis sha256sum readelf strings; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "P07-A4.2b missing tool $tool; source the Vitis environment" >&2; exit 2;
    }
done
ACTUAL="$(sha256sum "$XSA" | awk '{print $1}')"
[[ "$ACTUAL" == "$EXPECTED" ]] || {
    echo "P07-A4.2b refuses unverified XSA digest $ACTUAL" >&2; exit 2;
}
mkdir -p "$BUILD/source/include"
cd "$V3"
for name in \
    p07_a4_board.c p07_a4_stream.c p07_a4_supervisor.c \
    p07_a2_runtime.c p07_a1_ingress.c p07_a2_sha256.c; do
    cp "software/p07/$name" "$BUILD/source/"
done
for name in \
    p07_a1_ingress.h p07_a2_runtime.h \
    p07_a2_batch.h p07_a2_sha256.h p07_a4_stream.h \
    p07_a4_supervisor.h; do
    cp "software/p07/include/$name" "$BUILD/source/$name"
    cp "software/p07/include/$name" "$BUILD/source/include/$name"
done
for name in p03_runtime.c p03_hw_adapter.c \
            p03_hw_runtime_bridge.c p03_hw_xilinx_io.c; do
    cp "software/p03/$name" "$BUILD/source/"
done
for name in p03_mmio.h p03_runtime.h p03_hw_adapter.h \
            p03_hw_runtime_bridge.h p03_hw_xilinx_io.h; do
    cp "software/p03/include/$name" "$BUILD/source/"
done
vitis -s "$V3/software/p07/build_p07_a4.py" \
    --xsa "$XSA" --workspace "$BUILD/vitis_workspace" \
    --source-dir "$BUILD/source" 2>&1 | tee "$BUILD/vitis_build.log"
ELF="$BUILD/vitis_workspace/p07_a4_board.elf"
[[ -s "$ELF" ]] || { echo "P07-A4.2b no ELF generated" >&2; exit 3; }
grep -aFq "P07_A4_KV260_A53_FROZEN_TRACK_A_V1_TRACE_CONTEXT_FIX" "$ELF" || {
    echo "P07-A4.2b wrong compiled firmware identity" >&2; exit 3;
}
readelf -lW "$ELF" > "$BUILD/elf_program_headers.txt"
python - "$BUILD/elf_program_headers.txt" <<'PY'
from pathlib import Path
import sys
lines=Path(sys.argv[1]).read_text().splitlines()
count=0
for line in lines:
    f=line.split()
    if not f or f[0]!="LOAD":
        continue
    count+=1
    start=int(f[2],16);size=int(f[5],16)
    if start < 0x44000000 and start+size > 0x40000000:
        raise SystemExit("FAIL: ELF overlaps reserved DDR data/trace region")
if count==0:
    raise SystemExit("FAIL: ELF has no program LOAD segments")
print("PASS: P07-A4.2b standalone ELF stays outside reserved 64MiB PS/PL DDR region")
PY
grep -Fq "P07_A4_A53_VITIS_BUILD_PASS=1" "$BUILD/vitis_build.log"
echo "P07_A4_XSA_SHA256=$ACTUAL"
echo "P07_A4_ELF=$ELF"
echo "P07_A4_ELF_SHA256=$(sha256sum "$ELF" | awk '{print $1}')"
echo "P07_A4_VITIS_NATIVE_GATE_PASS=1"
echo "P07_A4_KV260_STATUS=NOT_RUN"
