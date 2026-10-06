#!/usr/bin/env bash
set -euo pipefail

EXPECTED_XSA_SHA="703fa7a44abc56e88e67e1d09424ac59ea96e53aac1708c2c7e6028dcb616f40"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$V3_DIR/vivado/build/p03_2c_smoke"
FIXTURE_DIR="$BUILD_DIR/fixture"
SOURCE_DIR="$BUILD_DIR/source"
WORKSPACE="$BUILD_DIR/vitis_workspace"

XSA="${P03_XSA:-$V3_DIR/vivado/build/p03_2_mmio_impl/reports/p03_2_ps_mmio.xsa}"

for tool in python vitis sha256sum readelf; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required P03.2c build tool is not on PATH: $tool" >&2
        exit 2
    }
done

[[ -f "$XSA" ]] || {
    echo "ERROR: accepted P03.2 XSA missing: $XSA" >&2
    exit 2
}
XSA_SHA="$(sha256sum "$XSA" | awk '{print $1}')"
[[ "$XSA_SHA" == "$EXPECTED_XSA_SHA" ]] || {
    echo "ERROR: P03.2c XSA identity drifted: $XSA_SHA" >&2
    exit 2
}

rm -rf "$BUILD_DIR"
mkdir -p "$FIXTURE_DIR" "$SOURCE_DIR"

cd "$V3_DIR"
PYTHONPATH="$V3_DIR/src" python scripts/p03_2c_smoke_fixture.py     --output-dir "$FIXTURE_DIR"     | tee "$BUILD_DIR/fixture.log"

cp software/p03/p03_2c_smoke.c "$SOURCE_DIR/"
cp software/p03/include/p03_mmio.h "$SOURCE_DIR/"
cp "$FIXTURE_DIR/p03_2c_fixture.h" "$SOURCE_DIR/"

vitis -s software/p03/build_p03_2c_smoke.py     --xsa "$XSA"     --workspace "$WORKSPACE"     --source-dir "$SOURCE_DIR"     2>&1 | tee "$BUILD_DIR/vitis_build.log"

ELF="$WORKSPACE/p03_2c_smoke.elf"
[[ -f "$ELF" ]] || {
    echo "ERROR: P03.2c Vitis build did not produce $ELF" >&2
    exit 3
}

readelf -lW "$ELF" > "$BUILD_DIR/elf_program_headers.txt"

python - "$BUILD_DIR/elf_program_headers.txt" <<'PY'
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
reserved_lo = 0x40000000
reserved_hi = 0x44000000

loads = []
for line in text.splitlines():
    if not line.lstrip().startswith("LOAD"):
        continue
    fields = line.split()
    if len(fields) < 7:
        continue
    vaddr = int(fields[2], 16)
    memsz = int(fields[5], 16)
    loads.append((vaddr, vaddr + memsz))

if not loads:
    raise SystemExit("FAIL: P03.2c could not identify ELF LOAD segments")

for start, end in loads:
    if start < reserved_hi and end > reserved_lo:
        raise SystemExit(
            "FAIL: P03.2c ELF LOAD segment overlaps reserved backing window: "
            f"0x{start:X}..0x{end:X}"
        )

print("PASS: P03.2c ELF LOAD segments avoid reserved 64 MiB backing window")
PY

ELF_SHA="$(sha256sum "$ELF" | awk '{print $1}')"

grep -q '^PASS: P03.2c smoke fixture generated' "$BUILD_DIR/fixture.log"
grep -q '^PASS: P03.2c standalone Cortex-A53 smoke application built' "$BUILD_DIR/vitis_build.log"

printf 'P03_2C_XSA_SHA256=%s\n' "$XSA_SHA"
printf 'P03_2C_ELF_SHA256=%s\n' "$ELF_SHA"
echo "P03_2C_ELF=$ELF"
echo "PASS: P03.2c standalone smoke build gate completed successfully."
