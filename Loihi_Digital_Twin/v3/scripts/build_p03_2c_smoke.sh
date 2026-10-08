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

# Vivado's top-level settings can make the `vitis` launcher visible without
# necessarily placing the embedded A53 cross-toolchain on PATH.  Recover the
# Vitis installation root from XILINX_VITIS or from the launcher itself, then
# source the embedded Vitis environment inside this build process.
if [[ -n "${XILINX_VITIS:-}" && -f "$XILINX_VITIS/settings64.sh" ]]; then
    # AMD settings scripts may inspect variables that are unset in the caller.
    set +u
    # shellcheck disable=SC1090
    source "$XILINX_VITIS/settings64.sh"
    set -u
elif command -v vitis >/dev/null 2>&1; then
    VITIS_BIN="$(readlink -f "$(command -v vitis)")"
    VITIS_ROOT="$(cd -- "$(dirname -- "$VITIS_BIN")/.." && pwd)"
    if [[ -f "$VITIS_ROOT/settings64.sh" ]]; then
        set +u
        # shellcheck disable=SC1090
        source "$VITIS_ROOT/settings64.sh"
        set -u
    fi
fi

# Vitis settings64.sh does not consistently export the processor-specific
# bare-metal compiler directories. Discover the bundled Cortex-A53/A72
# toolchain directly from the Vitis installation before declaring it absent.
if ! command -v aarch64-none-elf-gcc >/dev/null 2>&1; then
    A53_GCC_CANDIDATES=(
        "${XILINX_VITIS:-}/gnu/aarch64/lin/aarch64-none/bin/aarch64-none-elf-gcc"
        "${XILINX_VITIS:-}/gnu/aarch64/lin64/aarch64-none/bin/aarch64-none-elf-gcc"
    )
    A53_GCC=""
    for candidate in "${A53_GCC_CANDIDATES[@]}"; do
        if [[ -n "$candidate" && -x "$candidate" ]]; then
            A53_GCC="$candidate"
            break
        fi
    done
    if [[ -z "$A53_GCC" && -n "${XILINX_VITIS:-}" &&
          -d "$XILINX_VITIS" ]]; then
        A53_GCC="$(find "$XILINX_VITIS" -type f             -name aarch64-none-elf-gcc -perm -u+x -print -quit 2>/dev/null || true)"
    fi
    if [[ -z "$A53_GCC" && -n "${XILINX_VITIS:-}" ]]; then
        VITIS_VERSION_ROOT="$(cd -- "$XILINX_VITIS/.." && pwd)"
        A53_GCC="$(find "$VITIS_VERSION_ROOT" -type f             -name aarch64-none-elf-gcc -perm -u+x -print -quit 2>/dev/null || true)"
    fi
    if [[ -n "$A53_GCC" ]]; then
        export PATH="$(dirname "$A53_GCC"):$PATH"
    fi
fi

for tool in python vitis aarch64-none-elf-gcc sha256sum readelf; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required P03.2c build tool is unavailable: $tool" >&2
        if [[ "$tool" == "aarch64-none-elf-gcc" ]]; then
            echo "ERROR: searched the full Vitis installation tree under: ${XILINX_VITIS:-UNSET}" >&2
            echo "ERROR: the Vitis embedded Arm GNU toolchain component may not be installed." >&2
        fi
        exit 2
    }
done

echo "P03_2C_XILINX_VITIS=${XILINX_VITIS:-UNSET}"
echo "P03_2C_A53_GCC=$(command -v aarch64-none-elf-gcc)"
aarch64-none-elf-gcc --version | head -n 1

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
