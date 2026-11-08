#!/usr/bin/env bash
# Offline Vitis HLS Csim; --synth for synthesis; --cosim for C/RTL.
# NEVER calls hardware manager, JTAG, PS, DDR writes, or old v3 scripts.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG="hls/m05_stream_eval/m05_hls_config.cfg"
PART="xck26-sfvc784-2LV-c"
DO_SYNTH=0
DO_COSIM=0
for arg in "$@"; do
    case "$arg" in
        --synth) DO_SYNTH=1;;
        --cosim) DO_SYNTH=1; DO_COSIM=1;;
        *) echo "Unknown option: $arg" >&2; exit 2;;
    esac
done
for tool in git sha256sum vitis-run; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: $tool unavailable (source Vitis settings64.sh)" >&2
        exit 2
    }
done
if [[ "$DO_SYNTH" == 1 ]]; then
    command -v v++ >/dev/null 2>&1 || { echo "ERROR: v++ unavailable" >&2; exit 2; }
fi
VITIS_VERSION="$(vitis-run --version 2>&1 || true)"
if [[ "$VITIS_VERSION" != *2025.2* ]]; then
    echo "ERROR: expected Vitis HLS 2025.2; got: $VITIS_VERSION" >&2
    exit 2
fi
if [[ "${HLS_PART:-$PART}" != "$PART" ]]; then
    echo "ERROR: HLS_PART must match $PART" >&2
    exit 2
fi
cd "$ROOT"
mkdir -p "$HOME/Thesis_Evidence"
UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HOME/Thesis_Evidence/neuromorphic_accel_v1_m05_hls_${UTC}_$$"
mkdir "$OUT"  # new-only; never delete/overwrite original evidence
printf '%s\n' "$PART" > "$OUT/part.txt"
printf '%s\n' "$VITIS_VERSION" > "$OUT/vitis_version.txt"
git rev-parse HEAD > "$OUT/source_head.txt"
sha256sum \
    hls/m05_stream_eval/m05_stream.hpp \
    hls/m05_stream_eval/m05_stream.cpp \
    hls/m05_stream_eval/m05_hls_csim_tb.cpp \
    hls/m05_stream_eval/m05_hls_config.cfg \
    hls/m04_lif_eval/m04_eval.hpp \
    hls/m04_lif_eval/m04_eval.cpp > "$OUT/source_sha256.txt"
echo "M05 OFFLINE HLS evidence: $OUT"
vitis-run --mode hls --csim --config "$CONFIG" \
    --work_dir "$OUT/work" --part "$PART" 2>&1 | tee "$OUT/vitis_csim_original.log"
if [[ "$DO_SYNTH" == 1 ]]; then
    v++ -c --mode hls --config "$CONFIG" \
        --work_dir "$OUT/work" --part "$PART" 2>&1 | tee "$OUT/vpp_synth_original.log"
fi
if [[ "$DO_COSIM" == 1 ]]; then
    vitis-run --mode hls --cosim --config "$CONFIG" \
        --work_dir "$OUT/work" --part "$PART" 2>&1 | tee "$OUT/vitis_cosim_original.log"
fi
find "$OUT" -type f \( -name '*_csynth.rpt' -o -name '*cosim*.rpt' \) -print \
    > "$OUT/report_paths.txt"
find "$OUT" -type f \( -name '*_csynth.rpt' -o -name '*cosim*.rpt' \) \
    -exec sha256sum {} + > "$OUT/report_sha256.txt"
sha256sum "$OUT"/*.log "$OUT/source_sha256.txt" > "$OUT/evidence_sha256.txt"
echo "M05 offline HLS completed; synth=$DO_SYNTH cosim=$DO_COSIM"
echo "All original files under $OUT"
