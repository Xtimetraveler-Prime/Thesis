#!/usr/bin/env bash
# P08-B4.5 unprotected PERFORMANCE-only full1024 new A53: PC/Vitis build ONLY.
# NO XSDB, JTAG, PL programming, DDR writes, physical deployment or TEST.
set -euo pipefail
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
THESIS="$(cd -- "$V3/../.." && pwd)"
MODE="${P08_B45_MODE:?set once or unchecked}"
BUILD="${P08_B45_BUILD_DIR:?set new absolute out-of-repo build directory}"
ORIGINAL_ELF="${P08_B45_ORIGINAL_ELF:?set original accepted B2.3 full1024 ELF}"
REPORTS="${P07_B4L_REPORTS:?set original P03 routed reports}"
PINS="${P08_B2_RESET_PINS:?set original B2.2 pins directory}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
die(){ echo "P08_B45_BUILD_NO_GO=$*" >&2; exit 2; }
case "$MODE" in
    once) MAIN="p08_b45_perf_once_full1024_a53.c"
          APP="p08_b45_perf_once_full1024"
          ID="P08_B45_PERF_AUTH_ONCE_ORIGINAL_27CORE_1024_A53_V2";;
    unchecked) MAIN="p08_b45_perf_unchecked_full1024_a53.c"
          APP="p08_b45_perf_unchecked_full1024"
          ID="P08_B45_PERF_UNCHECKED_ORIGINAL_27CORE_1024_A53_V2";;
    *) die "mode must be exactly once or unchecked";;
esac
[[ "$BUILD" == /* && ! -e "$BUILD" && ! -L "$BUILD" ]] || die "NEW absolute build path required"
[[ "$(realpath -m "$BUILD")" == "$BUILD" ]] || die "canonical build path required"
case "$BUILD/" in "$THESIS/"*) die "out-of-repository build required";; esac
[[ -s "$XSA" && -f "$METRICS" ]] || die "accepted P03 XSA/metrics absent"
[[ "$ORIGINAL_ELF" == /* && -s "$ORIGINAL_ELF" && ! -L "$ORIGINAL_ELF" ]] || die "original B2.3 ELF missing or symlink"
[[ "$(sha256sum "$ORIGINAL_ELF" | cut -d' ' -f1)" == "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1" ]] || die "accepted original B2.3 ELF SHA drift"
[[ "$(sha256sum "$XSA" | cut -d' ' -f1)" == "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f" ]] || die "accepted routed P03 XSA SHA drift"
for field in p03_hpm0_data_width_bits=128 p03_hpm0_transport=smartconnect_width_protocol \
             p03_mmio_slave_data_width_bits=32 p03_ps_mmio_master=FPD p03_mmio_base=0xA4000000; do
    grep -Fxq "$field" "$METRICS" || die "routed P03 width/MMIO drift: $field"
done
PIN_HEADER="$PINS/p08_b2_2_original_context_sha256.h"
PIN_MANIFEST="$PINS/p08_b2_2_original_context_reset_pins.json"
[[ -f "$PIN_HEADER" && ! -L "$PIN_HEADER" && -f "$PIN_MANIFEST" && ! -L "$PIN_MANIFEST" ]] || die "B2.2 pins missing"
[[ "$(sha256sum "$PIN_HEADER" | cut -d' ' -f1)" == "5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171" ]] || die "original context SHA header drift"
[[ "$(sha256sum "$PIN_MANIFEST" | cut -d' ' -f1)" == "1d915c36eaf42740bac9e62afae58ffe80c94ae51cbf6c6c809d3fd6e626ce34" ]] || die "original SHA manifest drift"
for tool in vitis aarch64-none-elf-readelf aarch64-none-elf-nm python3; do
    command -v "$tool" >/dev/null || die "missing $tool; source Vitis 2025.2 tools"
done
mkdir -p "$BUILD/source"
for n in "$MAIN" p08_b45_perf_reset.c p08_b45_perf_startup.c \
         p08_b2_ingress.c p08_b2_service_meter.c; do
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
for n in p08_b2_ingress.h p08_b2_context_reset.h p08_b45_reset_variants.h \
         p08_b45_perf_reset.h p08_b45_perf_startup.h p08_b2_service_meter.h; do
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
# Frozen originals copied to external stage; only the accepted B4m
# local route-capacity copy adjustment is permitted.
sed -i 's@#include "include/p07_a2_sha256.h"@#include "p07_a2_sha256.h"@' \
    "$BUILD/source/p07_a2_sha256.c"
grep -Fq '#include "p07_a2_sha256.h"' "$BUILD/source/p07_a2_sha256.c" || die "P07 SHA header flattening failed"
[[ "$(grep -Fc '#define P07_B2_MAX_ROUTE_BINDINGS 8192u' "$BUILD/source/p07_b2_packet.h")" == 1 ]] || die "original P07 route ceiling changed"
sed -i 's@#define P07_B2_MAX_ROUTE_BINDINGS 8192u@#define P07_B2_MAX_ROUTE_BINDINGS 10000u@' \
    "$BUILD/source/p07_b2_packet.h"
grep -Fq '#define P07_B2_MAX_ROUTE_BINDINGS 10000u' "$BUILD/source/p07_b2_packet.h" || die "B4m route-capacity stage failed"
# Check the actual copied source before Vitis import.
python3 "$V3/software/p08/build_p08_b45_perf_full1024.py" \
    --mode "$MODE" --check-stage-only "$BUILD/source" \
    || die "mode-specific source stage rejected before Vitis"
(
    cd "$V3"
    vitis -s software/p08/build_p08_b45_perf_full1024.py \
      --mode "$MODE" --xsa "$XSA" \
      --workspace "$BUILD/vitis_workspace" \
      --source-dir "$BUILD/source"
) 2>&1 | tee "$BUILD/vitis_build.log"
ELF="$BUILD/vitis_workspace/$APP.elf"
MAP="$BUILD/vitis_workspace/$APP.map"
[[ -s "$ELF" && -s "$MAP" ]] || die "genuine new B4.5 mode ELF/map missing"
grep -aFq "$ID" "$ELF" || die "mode-specific ELF identity missing"
aarch64-none-elf-readelf -W -h -l -S "$ELF" > "$BUILD/readelf_layout.txt"
aarch64-none-elf-nm "$ELF" > "$BUILD/elf_symbols.txt"
sha256sum "$XSA" "$ELF" "$MAP" "$PIN_HEADER" > "$BUILD/artifact_sha256.txt"
REPORT="$BUILD/p08_b45_perf_${MODE}_full1024_elf_admission.json"
PYTHONPATH="$V3/scripts:$V3/src" python3 "$V3/scripts/p08_b45_perf_full1024_elf_admission.py" \
    --mode "$MODE" --elf "$ELF" --map "$MAP" \
    --original-elf "$ORIGINAL_ELF" --xsa "$XSA" \
    --pins-header "$PIN_HEADER" --out "$REPORT"
echo "P08_B45_PERF_${MODE}_FULL1024_A53_ELF_AND_MAP_BUILT=1"
echo "P08_B45_PERF_HARDWARE_BACKUP_PROTECTED=0"
echo "P08_B45_PERF_FULL1024_KV260_PHYSICAL_RUN=NOT_RUN"
echo "P08_B45_PERF_DESTRUCTIVE_JTAG_PERMISSION=NOT_GRANTED_BY_BUILD"
echo "P08_B45_PERF_DDR_OWNER_EXCLUSIVITY=NOT_PROVEN"
