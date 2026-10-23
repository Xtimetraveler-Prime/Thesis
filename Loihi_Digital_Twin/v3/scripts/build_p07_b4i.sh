#!/usr/bin/env bash
# P07-B.4i: genuinely link a new isolated read-only mailbox A53 ELF.
# No XSDB, Vivado hardware-manager, PS/PL writes, resets, or inference.
set -euo pipefail
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="${P07_B4I_BUILD_DIR:?set NEW absolute out-of-repository build dir}"
REPORTS="${P07_B4I_REPORTS:?set accepted P03.2c reports directory}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
fail(){ echo "P07_B4I_BUILD_NO_GO: $*" >&2; exit 2; }
[[ "$BUILD" == /* && ! -e "$BUILD" && ! -L "$BUILD" ]] || fail "fresh absolute build path required"
[[ "$(realpath -m "$BUILD")" == "$BUILD" ]] || fail "normalized build path required"
case "$BUILD/" in "$(cd "$V3/../.." && pwd)/"*) fail "build path inside Thesis";; esac
[[ -s "$XSA" && -f "$METRICS" ]] || fail "accepted XSA/metrics unavailable"
[[ "$(sha256sum "$XSA" | cut -d' ' -f1)" == 52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f ]] || fail "XSA SHA mismatch"
for field in \
  p03_hpm0_data_width_bits=128 p03_hpm0_transport=smartconnect_width_protocol \
  p03_mmio_slave_data_width_bits=32 p03_ps_mmio_master=FPD \
  p03_mmio_base=0xA4000000; do
  grep -Fxq "$field" "$METRICS" || fail "missing routed metric: $field"
done
for tool in vitis aarch64-none-elf-readelf aarch64-none-elf-nm; do
  command -v "$tool" >/dev/null || fail "missing $tool; source Vitis 2025.2 settings"
done
mkdir -p "$BUILD/source"
for name in p07_b4i_readonly_mailbox_board.c p07_b4b_board_admission.c p07_b4b_xilinx_platform.c; do
  cp -- "$V3/software/p07/$name" "$BUILD/source/"
done
for name in p03_hw_adapter.c p03_hw_xilinx_io.c; do
  cp -- "$V3/software/p03/$name" "$BUILD/source/"
done
for name in p07_b4b_board_admission.h p07_b4b_xilinx_platform.h \
            p07_b4a_current_ingress.h p07_b2_ingress.h p07_b3_pager.h; do
  cp -- "$V3/software/p07/include/$name" "$BUILD/source/"
done
for name in p03_hw_adapter.h p03_hw_xilinx_io.h p03_runtime.h p03_mmio.h; do
  cp -- "$V3/software/p03/include/$name" "$BUILD/source/"
done
(
  cd "$V3"
  vitis -s software/p07/build_p07_b4i.py --xsa "$XSA" \
    --workspace "$BUILD/vitis_workspace" --source-dir "$BUILD/source"
) 2>&1 | tee "$BUILD/vitis_build.log"
ELF="$BUILD/vitis_workspace/p07_b4i_mailbox_probe.elf"
MAP="$BUILD/vitis_workspace/p07_b4i_mailbox_probe.map"
[[ -s "$ELF" && -s "$MAP" ]] || fail "actual Vitis ELF/map missing"
grep -aFq P07_B4I_A53_MAILBOX_FPD128_PROBE_V1 "$ELF" || fail "ELF marker mismatch"
aarch64-none-elf-readelf -W -h -l -S "$ELF" > "$BUILD/readelf_layout.txt"
aarch64-none-elf-nm "$ELF" > "$BUILD/elf_symbols.txt"
sha256sum "$XSA" "$ELF" "$MAP" > "$BUILD/artifact_sha256.txt"
echo "P07_B4I_REAL_VITIS_ELF_AND_MAP_BUILT=1"
echo "P07_B4I_PHYSICAL_BOARD_RUN_AUTHORIZED=0"
