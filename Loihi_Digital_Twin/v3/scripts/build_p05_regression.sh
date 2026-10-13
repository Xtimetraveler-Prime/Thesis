#!/usr/bin/env bash
# Build P05.1 standalone A53 runtime/adapter gate from proven FPD128 XSA.
# Fresh isolated build; never modifies accepted P03.2c artifacts.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="${P05_1_BUILD_DIR:?Set P05_1_BUILD_DIR to a fresh, unique directory}"
REPORTS="${P03_DIAG_REPORTS:?Set P03_DIAG_REPORTS to the accepted routed FPD128 reports}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
EXPECTED_SHA="${P03_2C_EXPECTED_XSA_SHA:?Set P03_2C_EXPECTED_XSA_SHA to the exact FPD128 XSA fingerprint}"
if [[ -e "$BUILD_DIR" ]]; then
    echo "ERROR: P05.1 build directory already exists; refusing to overwrite $BUILD_DIR" >&2
    exit 2
fi
if [[ "${P03_XSA:-$XSA}" != "$XSA" ]]; then
    echo "ERROR: P03_XSA does not match selected candidate" >&2
    exit 2
fi

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

for tool in python vitis aarch64-none-elf-gcc sha256sum readelf strings grep; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required P05.1 build tool is unavailable: $tool" >&2
        if [[ "$tool" == "aarch64-none-elf-gcc" ]]; then
            echo "ERROR: searched the full Vitis installation tree under: ${XILINX_VITIS:-UNSET}" >&2
            echo "ERROR: the Vitis embedded Arm GNU toolchain component may not be installed." >&2
        fi
        exit 2
    }
done

echo "P05_1_XILINX_VITIS=${XILINX_VITIS:-UNSET}"
echo "P05_1_A53_GCC=$(command -v aarch64-none-elf-gcc)"
[[ -s "$XSA" ]] || { echo "ERROR: candidate XSA missing" >&2; exit 2; }
XSA_SHA="$(sha256sum "$XSA" | awk '{print $1}')"
[[ "$XSA_SHA" == "$EXPECTED_SHA" ]] || {
    echo "ERROR: XSA checksum mismatch" >&2
    exit 2
}
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
for expected in \
    'p03_hpm0_data_width_bits=128' \
    'p03_hpm0_transport=smartconnect_width_protocol' \
    'p03_mmio_slave_data_width_bits=32' \
    'p03_ps_mmio_master=FPD' \
    'p03_mmio_base=0xA4000000'; do
    grep -Fxq "$expected" "$METRICS" || {
        echo "ERROR: FPD128 route mismatch: $expected" >&2
        exit 2
    }
done

SOURCE="$BUILD_DIR/source"
WORKSPACE="$BUILD_DIR/vitis_workspace"
mkdir -p "$SOURCE"
cd "$V3_DIR"

# Separate P05 A53 application: P03 accepted binary/source and
# Python golden fixtures are NEVER overwritten by this build.
cp software/p05/p05_regression_run.c "$SOURCE/"
cp software/p05/p05_deployment.c "$SOURCE/"
cp software/p05/include/p05_deployment.h "$SOURCE/"
for file in \
    p03_runtime.c p03_hw_adapter.c \
    p03_hw_runtime_bridge.c p03_hw_xilinx_io.c; do
    cp "software/p03/$file" "$SOURCE/"
done
for file in \
    p03_mmio.h p03_runtime.h p03_hw_adapter.h \
    p03_hw_runtime_bridge.h p03_hw_xilinx_io.h; do
    cp "software/p03/include/$file" "$SOURCE/"
done


vitis -s software/p05/build_p05_regression.py \
    --xsa "$XSA" --workspace "$WORKSPACE" --source-dir "$SOURCE" \
    --app-name p05_regression_run --source-file p05_regression_run.c \
    2>&1 | tee "$BUILD_DIR/vitis_build.log"

ELF="$WORKSPACE/p05_regression_run.elf"
[[ -s "$ELF" ]] || { echo "ERROR: P05.1 ELF not produced" >&2; exit 3; }
# Verify the complete Vitis process really emitted the current diagnostics.
# This is an ELF content check, not merely a source-string grep.
if ! grep -aFq 'P05_CONFIGURABLE_A53_REGRESSION_V1' "$ELF"; then
    echo "ERROR: built ELF does NOT contain the P05.1 firmware diagnostic identity" >&2
    echo "ERROR: ensure the current p05_regression_run.c was imported and rebuilt" >&2
    exit 3
fi
echo "PASS: P05.1 A53 ELF contains retained P05.1 diagnostic firmware identity"
readelf -lW "$ELF" > "$BUILD_DIR/elf_program_headers.txt"
python - "$BUILD_DIR/elf_program_headers.txt" <<'PY'
from pathlib import Path
import sys
lines = Path(sys.argv[1]).read_text().splitlines()
loads = []
for line in lines:
    fields = line.split()
    if not fields or fields[0] != "LOAD":
        continue
    if len(fields) < 7:
        raise SystemExit("FAIL: malformed ELF LOAD header")
    start = int(fields[2], 16)
    size = int(fields[5], 16)
    loads.append((start, start + size))
if not loads:
    raise SystemExit("FAIL: P05.1 ELF has no load segments")
for lo, hi in loads:
    if lo < 0x44000000 and hi > 0x40000000:
        raise SystemExit(f"FAIL: ELF overlaps reserved DDR: 0x{lo:X}..0x{hi:X}")
print("PASS: P05.1 ELF avoids 64 MiB reserved DDR fixture/mailbox window")
PY

grep -Fq 'PASS: P05.1 standalone A53 runtime-adapter probe built' \
    "$BUILD_DIR/vitis_build.log"
echo "P05_1_XSA_SHA256=$XSA_SHA"
echo "P05_1_ELF_SHA256=$(sha256sum "$ELF" | awk '{print $1}')"
echo "P05_1_ELF=$ELF"
echo "PASS: P05.1 standalone A53 runtime-adapter probe build ready for board verification"
