#!/usr/bin/env bash
# P08-B4.4.2 original B2.4 / 1024 image-only NEW A53 ELF candidate: PC ONLY.
# NO XSDB, NO PL programming, NO JTAG, NO DDR writes, NO physical deployment.
set -euo pipefail
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
THESIS="$(cd -- "$V3/../.." && pwd)"
BUILD="${P08_B44_BUILD_DIR:?set NEW absolute out-of-Thesis build directory}"
ORIGINAL_ELF="${P08_B44_ORIGINAL_ELF:?set original accepted full1024 B2.3 ELF absolute path}"
REPORTS="${P07_B4L_REPORTS:?set original accepted P03 routed reports directory}"
PINS="${P08_B2_RESET_PINS:?set genuine P08-B2.2 SHA pin stage directory}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
die(){ echo "P08_B44_NEW_A53_BUILD_NO_GO=$*" >&2; exit 2; }
[[ "$BUILD" == /* && ! -e "$BUILD" && ! -L "$BUILD" ]] || die "NEW absolute build path required"
[[ "$(realpath -m "$BUILD")" == "$BUILD" ]] || die "canonical build path required"
case "$BUILD/" in "$THESIS/"*) die "out-of-Thesis build required";; esac
[[ -s "$XSA" && -f "$METRICS" ]] || die "original accepted P03 XSA/metrics absent"
[[ "$ORIGINAL_ELF" == /* && -s "$ORIGINAL_ELF" && ! -L "$ORIGINAL_ELF" ]] || die "original immutable B2.3 genuine ELF missing"
[[ "$(sha256sum "$ORIGINAL_ELF" | cut -d' ' -f1)" == "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1" ]] || die "original accepted A53 full1024 ELF SHA changed"
[[ "$(sha256sum "$XSA" | cut -d' ' -f1)" == "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f" ]] || die "original accepted P03 XSA drift"
for field in p03_hpm0_data_width_bits=128 p03_hpm0_transport=smartconnect_width_protocol \
             p03_mmio_slave_data_width_bits=32 p03_ps_mmio_master=FPD p03_mmio_base=0xA4000000; do
    grep -Fxq "$field" "$METRICS" || die "original accepted routed P03 width/MMIO drift: $field"
done
for tool in vitis aarch64-none-elf-readelf aarch64-none-elf-nm python3; do
    command -v "$tool" >/dev/null || die "missing $tool; source 2025.2 Vitis environment"
done
PIN_HEADER="$PINS/p08_b2_2_original_context_sha256.h"
PIN_MANIFEST="$PINS/p08_b2_2_original_context_reset_pins.json"
[[ -f "$PIN_HEADER" && ! -L "$PIN_HEADER" && -f "$PIN_MANIFEST" && ! -L "$PIN_MANIFEST" ]] || die "original frozen SHA pin stage missing"
[[ "$(sha256sum "$PIN_HEADER" | cut -d' ' -f1)" == "5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171" ]] || die "B2.2 original 27xSHA header drift"
[[ "$(sha256sum "$PIN_MANIFEST" | cut -d' ' -f1)" == "1d915c36eaf42740bac9e62afae58ffe80c94ae51cbf6c6c809d3fd6e626ce34" ]] || die "operator-pinned B2.2 SHA manifest drift"
mkdir -p "$BUILD/source"
for n in p08_b2_3_image_only_a53.c p08_b2_ingress.c p08_b2_context_reset.c p08_b2_service_meter.c; do
    cp -- "$V3/software/p08/$n" "$BUILD/source/"
done
for n in p07_b4m_dispatch_metadata.c p07_b4l_b3_bindings.c p07_b4m_frozen_routes.c \
         p07_b4m_spike_trace.c p07_b4m_epoch_bridge.c p07_b4m_full_inference.c \
         p07_b4a_current_ingress.c p07_b2_ingress.c p07_b3c2_hw_scheduler.c \
         p07_b3_pager.c p07_b2_packet.c p07_b3c_packet_bridge.c \
         p07_b3c3_next_commit.c p07_a2_sha256.c; do
    cp -- "$V3/software/p07/$n" "$BUILD/source/"
done
for n in p03_hw_adapter.c p03_hw_xilinx_io.c; do
    cp -- "$V3/software/p03/$n" "$BUILD/source/"
done
for n in p08_b2_ingress.h p08_b2_context_reset.h p08_b2_service_meter.h; do
    cp -- "$V3/software/p08/$n" "$BUILD/source/"
done
cp -- "$PIN_HEADER" "$BUILD/source/p08_b2_2_original_context_sha256.h"
for n in p07_b4l_b3_bindings.h p07_b4m_dispatch_metadata.h \
         p07_b4m_frozen_routes.h p07_b4m_spike_trace.h p07_b4m_epoch_bridge.h \
         p07_b4m_full_inference.h p07_b4a_current_ingress.h \
         p07_b2_ingress.h p07_b3c2_hw_scheduler.h p07_b3_pager.h \
         p07_b2_packet.h p07_b3c_packet_bridge.h p07_b3c3_next_commit.h \
         p07_a2_sha256.h; do
    cp -- "$V3/software/p07/include/$n" "$BUILD/source/"
done
for n in p03_hw_adapter.h p03_hw_xilinx_io.h p03_runtime.h p03_mmio.h; do
    cp -- "$V3/software/p03/include/$n" "$BUILD/source/"
done
cp -- "$V3/software/p05/include/p05_deployment.h" "$BUILD/source/"
# Isolated Vitis import only: original accepted P07 source is never changed.
sed -i 's@#include "include/p07_a2_sha256.h"@#include "p07_a2_sha256.h"@' \
    "$BUILD/source/p07_a2_sha256.c"
grep -Fq '#include "p07_a2_sha256.h"' "$BUILD/source/p07_a2_sha256.c" || die "accepted P07 SHA include flattening failed"
[[ "$(grep -Fc '#define P07_B2_MAX_ROUTE_BINDINGS 8192u' "$BUILD/source/p07_b2_packet.h")" == 1 ]] || die "original P07 packet-route ceiling drift"
sed -i 's@#define P07_B2_MAX_ROUTE_BINDINGS 8192u@#define P07_B2_MAX_ROUTE_BINDINGS 10000u@' \
    "$BUILD/source/p07_b2_packet.h"
grep -Fq '#define P07_B2_MAX_ROUTE_BINDINGS 10000u' "$BUILD/source/p07_b2_packet.h" || die "separate B4m original 10K route ceiling absent"
(
    cd "$V3"
    vitis -s software/p08/build_p08_b44_profile_full1024.py \
      --xsa "$XSA" \
      --workspace "$BUILD/vitis_workspace" \
      --source-dir "$BUILD/source"
) 2>&1 | tee "$BUILD/vitis_build.log"
ELF="$BUILD/vitis_workspace/p08_b44_reset_profile_1024.elf"
MAP="$BUILD/vitis_workspace/p08_b44_reset_profile_1024.map"
[[ -s "$ELF" && -s "$MAP" ]] || die "genuine new image-only A53 ELF/map missing"
grep -aFq P08_B44_ORIGINAL_27CORE_1024_IMAGE_ONLY_A53_V1 "$ELF" || die "new ELF identity not linked"
aarch64-none-elf-readelf -W -h -l -S "$ELF" > "$BUILD/readelf_layout.txt"
aarch64-none-elf-nm "$ELF" > "$BUILD/elf_symbols.txt"
sha256sum "$XSA" "$ELF" "$MAP" "$PIN_HEADER" > "$BUILD/artifact_sha256.txt"
REPORT="$BUILD/p08_b44_profile_elf_ptload_preflight.json"
PYTHONPATH="$V3/src" python3 "$V3/scripts/p08_b44_profile_elf_admission.py" \
  --profile-elf "$ELF" --profile-map "$MAP" \
  --original-elf "$ORIGINAL_ELF" --xsa "$XSA" \
  --pins-header "$PIN_HEADER" --out "$REPORT"
echo "P08_B44_SEPARATE_RESET_PROFILE_1024_A53_ELF_AND_MAP_BUILT=1"
echo "P08_B44_NEW_PROFILE_KV260_PHYSICAL_RUN=NOT_RUN"
echo "P08_B44_EXPERIMENTAL_DESTRUCTIVE_JTAG_PERMISSION=NOT_GRANTED"
echo "P08_B44_INDEPENDENT_PSU_MEMORY_OWNER=NOT_PROVEN"
