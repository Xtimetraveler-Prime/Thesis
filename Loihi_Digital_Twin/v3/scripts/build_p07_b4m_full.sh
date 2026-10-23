#!/usr/bin/env bash
# New B4m full-26tick standalone A53 Vitis build. PC ONLY; no XSDB.
# The result's ELF low-DDR footprint is NEW and NOT board-authorized.
set -euo pipefail
V3="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="${P07_B4M_BUILD_DIR:?set a NEW absolute out-of-repository build directory}"
REPORTS="${P07_B4L_REPORTS:?set accepted P03 routed reports path}"
XSA="$REPORTS/p03_2_ps_mmio.xsa"
METRICS="$REPORTS/p03_2_post_route_metrics.txt"
die(){ echo "P07_B4M_BUILD_NO_GO=$*" >&2; exit 2; }
[[ "$BUILD" == /* && ! -e "$BUILD" && ! -L "$BUILD" ]] || die "NEW absolute build path required"
[[ "$(realpath -m "$BUILD")" == "$BUILD" ]] || die "canonical build path required"
case "$BUILD/" in "$(cd "$V3/../.." && pwd)/"*) die "out-of-repo only";; esac
[[ -s "$XSA" && -f "$METRICS" ]] || die "missing exact accepted P03 XSA/metrics"
[[ "$(sha256sum "$XSA" | cut -d' ' -f1)" == 52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f ]] || die "XSA SHA differs from original accepted Track A/B4l"
for field in p03_hpm0_data_width_bits=128 p03_hpm0_transport=smartconnect_width_protocol \
             p03_mmio_slave_data_width_bits=32 p03_ps_mmio_master=FPD p03_mmio_base=0xA4000000; do
    grep -Fxq "$field" "$METRICS" || die "changed accepted routed PS/PL setting: $field"
done
for cmd in vitis aarch64-none-elf-readelf aarch64-none-elf-nm; do
    command -v "$cmd" >/dev/null || die "missing $cmd; source Vitis environment"
done
mkdir -p "$BUILD/source"
for n in p07_b4m_full_board.c p07_b4l_b3_bindings.c \
         p07_b4m_frozen_routes.c p07_b4m_spike_trace.c \
         p07_b4m_epoch_bridge.c p07_b4m_full_inference.c \
         p07_b4a_current_ingress.c p07_b2_ingress.c \
         p07_b3c2_hw_scheduler.c p07_b3_pager.c \
         p07_b2_packet.c p07_b3c_packet_bridge.c \
         p07_b3c3_next_commit.c; do
    cp -- "$V3/software/p07/$n" "$BUILD/source/"
done
for n in p03_hw_adapter.c p03_hw_xilinx_io.c; do
    cp -- "$V3/software/p03/$n" "$BUILD/source/"
done
cp -- "$V3/software/p07/p07_a2_sha256.c" "$BUILD/source/"
# Accepted native source stays IMMUTABLE. Only the fresh Vitis copy
# receives the import-flattened accepted SHA header include path.
sed -i 's@#include "include/p07_a2_sha256.h"@#include "p07_a2_sha256.h"@' "$BUILD/source/p07_a2_sha256.c"
grep -Fq '#include "p07_a2_sha256.h"' "$BUILD/source/p07_a2_sha256.c" || die "SHA header flattening failed"
for n in p07_b4l_b3_bindings.h p07_b4m_frozen_routes.h \
         p07_b4m_spike_trace.h p07_b4m_epoch_bridge.h \
         p07_b4m_full_inference.h p07_b4a_current_ingress.h \
         p07_b2_ingress.h p07_b3c2_hw_scheduler.h \
         p07_b3_pager.h p07_b2_packet.h \
         p07_b3c_packet_bridge.h p07_b3c3_next_commit.h \
         p07_a2_sha256.h; do
    cp -- "$V3/software/p07/include/$n" "$BUILD/source/"
done
for n in p03_hw_adapter.h p03_hw_xilinx_io.h p03_runtime.h p03_mmio.h; do
    cp -- "$V3/software/p03/include/$n" "$BUILD/source/"
done
cp -- "$V3/software/p05/include/p05_deployment.h" "$BUILD/source/"
# Explicit B4m-only 10,000-edge route capacity. The accepted B4l
# and original P07-B.2 native header remain default 8192 bytes unchanged.
# Only the FRESH standalone Vitis source copy receives this opt-in macro.
[[ "$(grep -Fc '#define P07_B2_MAX_ROUTE_BINDINGS 8192u' "$BUILD/source/p07_b2_packet.h")" == 1 ]] || die "original route cap declaration changed"
sed -i 's@#define P07_B2_MAX_ROUTE_BINDINGS 8192u@#define P07_B2_MAX_ROUTE_BINDINGS 10000u@' "$BUILD/source/p07_b2_packet.h"
grep -Fq '#define P07_B2_MAX_ROUTE_BINDINGS 10000u' "$BUILD/source/p07_b2_packet.h" || die "B4m route ceiling opt-in failed"

(
    cd "$V3"
    vitis -s software/p07/build_p07_b4m_full.py --xsa "$XSA" \
        --workspace "$BUILD/vitis_workspace" --source-dir "$BUILD/source"
) 2>&1 | tee "$BUILD/vitis_build.log"
ELF="$BUILD/vitis_workspace/p07_b4m_full_26tick.elf"
MAP="$BUILD/vitis_workspace/p07_b4m_full_26tick.map"
[[ -s "$ELF" && -s "$MAP" ]] || die "new real full 26-tick ELF/map missing"
grep -aFq P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1 "$ELF" || die "new physical firmware identity missing"
aarch64-none-elf-readelf -W -h -l -S "$ELF" > "$BUILD/readelf_layout.txt"
aarch64-none-elf-nm "$ELF" > "$BUILD/elf_symbols.txt"
sha256sum "$XSA" "$ELF" "$MAP" > "$BUILD/artifact_sha256.txt"
echo "P07_B4M_REAL_A53_26TICK_ELF_AND_MAP_BUILT=1"
echo "P07_B4M_REAL_BOARD_RUN_AUTHORIZED=0"
echo "P07_B4M_EXPANDED_LOW_DDR_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0"
