#!/usr/bin/env bash
# B4l: isolated REAL standalone A53 B3 scheduler/P03 first-epoch candidate.
# OFFLINE BUILD ONLY. NO DDR/JTAG/PL writes, no inference claim.
set -euo pipefail
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="${P07_B4L_B3_BUILD_DIR:?set new absolute out-of-repository build directory}"
REPORTS="${P07_B4L_REPORTS:?set accepted P03.2c reports dir}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
die(){ echo "P07_B4L_B3_BUILD_NO_GO=$*" >&2; exit 2; }
[[ "$BUILD" == /* && ! -e "$BUILD" && ! -L "$BUILD" ]] || die "fresh absolute build path required"
[[ "$(realpath -m "$BUILD")" == "$BUILD" ]] || die "normalized build path required"
case "$BUILD/" in "$(cd "$V3/../.." && pwd)/"*) die "out of repository path required";; esac
[[ -s "$XSA" && -f "$METRICS" ]] || die "accepted P03 XSA/metrics missing"
[[ "$(sha256sum "$XSA" | cut -d' ' -f1)" == 52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f ]] || die "original P03 XSA SHA mismatch"
for field in p03_hpm0_data_width_bits=128 p03_hpm0_transport=smartconnect_width_protocol \
             p03_mmio_slave_data_width_bits=32 p03_ps_mmio_master=FPD p03_mmio_base=0xA4000000; do
  grep -Fxq "$field" "$METRICS" || die "accepted P03 routed metric missing: $field"
done
for tool in vitis aarch64-none-elf-readelf aarch64-none-elf-nm; do
  command -v "$tool" >/dev/null || die "missing Vitis build tool $tool"
done
mkdir -p "$BUILD/source"
for n in p07_b4l_b3_epoch_board.c p07_b4l_b3_epoch.c p07_b4l_b3_bindings.c \
         p07_b3c2_hw_scheduler.c p07_b3_pager.c p07_b2_packet.c \
         p07_b3c_packet_bridge.c p07_b3c3_next_commit.c; do
  cp -- "$V3/software/p07/$n" "$BUILD/source/"
done
for n in p03_hw_adapter.c p03_hw_xilinx_io.c; do
  cp -- "$V3/software/p03/$n" "$BUILD/source/"
done
# Original accepted P07 SHA256 source has "include/p07_a2_sha256.h".
# Vitis flattens app imports into one src/; modify ONLY fresh STAGED COPY
# of this include directive, not the accepted original crypto source.
cp -- "$V3/software/p07/p07_a2_sha256.c" "$BUILD/source/"
sed -i 's@#include "include/p07_a2_sha256.h"@#include "p07_a2_sha256.h"@' "$BUILD/source/p07_a2_sha256.c"
grep -Fq '#include "p07_a2_sha256.h"' "$BUILD/source/p07_a2_sha256.c" || die "SHA staged include rewrite failed"
for n in p07_b4l_b3_epoch.h p07_b4l_b3_bindings.h p07_b3c2_hw_scheduler.h \
         p07_b3_pager.h p07_b3c_packet_bridge.h p07_b3c3_next_commit.h \
         p07_b2_packet.h p07_b2_ingress.h p07_a2_sha256.h; do
  cp -- "$V3/software/p07/include/$n" "$BUILD/source/"
done
for n in p03_hw_adapter.h p03_hw_xilinx_io.h p03_runtime.h p03_mmio.h; do
  cp -- "$V3/software/p03/include/$n" "$BUILD/source/"
done
cp -- "$V3/software/p05/include/p05_deployment.h" "$BUILD/source/"
(
  cd "$V3"
  vitis -s software/p07/build_p07_b4l_b3_epoch.py --xsa "$XSA" \
    --workspace "$BUILD/vitis_workspace" --source-dir "$BUILD/source"
) 2>&1 | tee "$BUILD/vitis_build.log"
ELF="$BUILD/vitis_workspace/p07_b4l_b3_first_epoch.elf"
MAP="$BUILD/vitis_workspace/p07_b4l_b3_first_epoch.map"
[[ -s "$ELF" && -s "$MAP" ]] || die "real first-epoch ELF/link map missing"
grep -aFq P07_B4L_A53_B3_ONE_EPOCH_V1 "$ELF" || die "ELF candidate identity mismatch"
aarch64-none-elf-readelf -W -h -l -S "$ELF" > "$BUILD/readelf_layout.txt"
aarch64-none-elf-nm "$ELF" > "$BUILD/elf_symbols.txt"
sha256sum "$XSA" "$ELF" "$MAP" > "$BUILD/artifact_sha256.txt"
echo "P07_B4L_REAL_B3_ONE_EPOCH_VITIS_ELF_AND_MAP_BUILT=1"
echo "P07_B4L_B3_ONE_EPOCH_PHYSICAL_BOARD_RUN_AUTHORIZED=0"
