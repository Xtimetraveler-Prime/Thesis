#!/usr/bin/env bash
# P07-B.4c FIRST real A53 READ-ONLY candidate ELF build, NOT board execution.
# Reuses accepted P03/P07-A Vitis 2025.2 empty-application interface.
# Outputs created only in a fresh user-owned directory outside repository.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V3="$(cd -- "$HERE/.." && pwd)"
BUILD="${P07_B4C_BUILD_DIR:?Set unique absolute out-of-repo build directory}"
XSA="${P07_B4C_XSA:?Set accepted P03 128-bit FPD routed XSA}"
EXPECTED="${P07_B4C_XSA_SHA256:?Set independently pinned XSA SHA256}"
METRICS="${P07_B4C_ROUTE_METRICS:?Set accepted P03 routed metrics text path}"
# The build can complete before stack/heap have been measured from the real
# BSP/map. Their absence MUST prevent ELF admission, not artifact creation.
STACK="${P07_B4C_STACK:-}"
HEAP="${P07_B4C_HEAP:-}"
if [[ -n "$STACK" || -n "$HEAP" ]]; then
  [[ -n "$STACK" && -n "$HEAP" ]] ||
    { echo "P07_B4C_BUILD_NO_GO: supply BOTH actual stack and heap extents" >&2; exit 2; }
fi

die(){ echo "P07_B4C_BUILD_NO_GO: $*" >&2; exit 2; }
[[ "$BUILD" == /* ]] || die "build directory must be absolute"
[[ "$XSA" == /* && "$METRICS" == /* ]] || die "XSA/metrics require absolute paths"
[[ ! -e "$BUILD" && ! -L "$BUILD" ]] || die "refusing existing or symlinked build"
BUILD_CANON="$(realpath -m -- "$BUILD")"
PROJECT_ROOT="$(cd "$V3/../.." && pwd)"
case "$BUILD_CANON/" in "$PROJECT_ROOT/"* )
  die "build must be outside entire Thesis repository" ;;
esac
[[ "$BUILD_CANON" == "$BUILD" ]] ||
  die "use a normalized, absolute build path without dot components"
[[ -f "$XSA" && -s "$XSA" && -f "$METRICS" ]] || die "pinned XSA or route metrics missing"
[[ "$EXPECTED" =~ ^[a-fA-F0-9]{64}$ ]] || die "expected sha must be 64 hex bytes"
for tool in sha256sum python3 grep realpath cut tee; do
  command -v "$tool" >/dev/null 2>&1 || die "required executable not on PATH: $tool"
done
ACTUAL="$(sha256sum "$XSA" | cut -d' ' -f1)"
[[ "${EXPECTED,,}" == "$ACTUAL" ]] || die "XSA SHA mismatch expected=${EXPECTED,,}, actual=$ACTUAL"
for field in \
    "p03_hpm0_data_width_bits=128" \
    "p03_hpm0_transport=smartconnect_width_protocol" \
    "p03_mmio_slave_data_width_bits=32" \
    "p03_ps_mmio_master=FPD" \
    "p03_mmio_base=0xA4000000"; do
  grep -Fxq -- "$field" "$METRICS" || die "missing independently accepted route evidence: $field"
done
# The original Vitis launcher may be visible while A53 tools are not.
if [[ -n "${XILINX_VITIS:-}" && -f "$XILINX_VITIS/settings64.sh" ]]; then
  set +u
  # shellcheck disable=SC1090
  source "$XILINX_VITIS/settings64.sh"
  set -u
fi
command -v vitis >/dev/null 2>&1 || die "Vitis launcher unavailable (source 2025.2 environment)"
command -v aarch64-none-elf-gcc >/dev/null 2>&1 || {
  # Matches the accepted P05 recovery when settings64 omits embedded tools.
  for candidate in \
    "${XILINX_VITIS:-/nonexistent}/gnu/aarch64/lin/aarch64-none/bin" \
    "${XILINX_VITIS:-/nonexistent}/gnu/aarch64/lin64/aarch64-none/bin"; do
    if [[ -x "$candidate/aarch64-none-elf-gcc" ]]; then
      export PATH="$candidate:$PATH"
      break
    fi
  done
}
command -v aarch64-none-elf-gcc >/dev/null 2>&1 || die "A53 embedded GNU compiler missing"
command -v aarch64-none-elf-nm >/dev/null 2>&1 || die "A53 binutils nm missing"
command -v aarch64-none-elf-readelf >/dev/null 2>&1 || die "A53 binutils readelf missing"

# Never stage or mutate the original accepted P03/P05/Track A/B files.
mkdir -p "$BUILD/source"
for name in \
    p07_b4c_readonly_board.c p07_b4b_board_admission.c \
    p07_b4b_xilinx_platform.c; do
  cp -- "$V3/software/p07/$name" "$BUILD/source/"
done
for name in p03_hw_adapter.c p03_hw_xilinx_io.c; do
  cp -- "$V3/software/p03/$name" "$BUILD/source/"
done
for name in \
    p07_b4b_board_admission.h p07_b4b_xilinx_platform.h \
    p07_b4a_current_ingress.h p07_b2_ingress.h p07_b3_pager.h; do
  cp -- "$V3/software/p07/include/$name" "$BUILD/source/"
done
for name in \
    p03_hw_adapter.h p03_hw_xilinx_io.h p03_runtime.h p03_mmio.h; do
  cp -- "$V3/software/p03/include/$name" "$BUILD/source/"
done

# Vitis 2025.2 creates a NEW standalone psu_cortexa53_0 platform, and
# expects an actual map from the toolchain. If the template does not emit
# a map, the gate fails rather than synthesizing a false linker document.
(
  cd "$V3"
  vitis -s software/p07/build_p07_b4c.py \
    --xsa "$XSA" --workspace "$BUILD/vitis_workspace" \
    --source-dir "$BUILD/source"
) 2>&1 | tee "$BUILD/vitis_build.log"

ELF="$BUILD/vitis_workspace/p07_b4c_readonly_probe.elf"
MAP="$BUILD/vitis_workspace/p07_b4c_readonly_probe.map"
[[ -s "$ELF" && -s "$MAP" ]] || die "actual ELF and matching linker map not both produced"
grep -aFq "P07_B4C_A53_READONLY_FPD128_SHELL_PROBE_V1" "$ELF" ||
  die "ELF lacks expected new B.4c board probe build identity"
sha256sum "$XSA" "$ELF" "$MAP" > "$BUILD/artifact_sha256.txt"
printf 'P07_B4C_XSA_SHA256=%s\n' "$ACTUAL"
printf 'P07_B4C_PROBE_ELF=%s\nP07_B4C_LINKER_MAP=%s\n' "$ELF" "$MAP"
echo "P07_B4C_A53_ELF_BUILT=1"
if [[ -n "$STACK" && -n "$HEAP" ]]; then
  # The gate reads real Vitis bytes and cross-binutils; it may FAIL after a
  # successful build if the linker map/stack/heap lacks sufficient evidence.
  (
    cd "$V3"
    python3 scripts/p07_b4c_verify_elf.py \
      --elf "$ELF" --linker-map "$MAP" \
      --stack "$STACK" --heap "$HEAP" \
      --readelf "$(command -v aarch64-none-elf-readelf)" \
      --nm "$(command -v aarch64-none-elf-nm)"
  ) | tee "$BUILD/elf_admission.json"
  echo "P07_B4C_A53_READONLY_ELF_ADMISSION_PASS=1"
else
  # No guessed BSP stack/heap offsets. Derive from genuine ELF .heap/.stack
  # allocated section headers, then validate LOAD/DDR/non-overlap against
  # the actual linker-generated map and original P03 BSS.
  (
    cd "$V3"
    python3 scripts/p07_b4c_verify_elf.py \
      --elf "$ELF" --linker-map "$MAP" \
      --stack auto --heap auto \
      --readelf "$(command -v aarch64-none-elf-readelf)" \
      --nm "$(command -v aarch64-none-elf-nm)"
  ) | tee "$BUILD/elf_admission.json"
  echo "P07_B4C_A53_READONLY_ELF_SECTION_LAYOUT_PASS=1"
  echo "P07_B4C_PHYSICAL_STACK_HEAP_OWNERSHIP=PENDING"
fi
echo "P07_B4C_KV260_BOARD_STATUS=NOT_RUN"
echo "P07_B4C_INFERENCE_AUTHORIZED=0"
