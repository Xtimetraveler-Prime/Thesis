#!/usr/bin/env bash
# M05 isolated, offline Vitis HLS 2025.2 on AMD K26.
# No Vivado Hardware Manager, JTAG, PS access, physical DDR, old v3 scripts.
# From Neuromorphic_Accelerator/v1:
#   bash hls/m05_stream_eval/run_m05_offline_hls.sh [--csim|--synth|--cosim|--impl]
# Each run creates original, unique evidence; failure preserves originals.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG="$ROOT/hls/m05_stream_eval/m05_hls_config.cfg"
PART="xck26-sfvc784-2LV-c"
LEVEL=0
case "${1:---csim}" in
    --csim)  LEVEL=0 ;;
    --synth) LEVEL=1 ;;
    --cosim) LEVEL=2 ;;
    --impl)  LEVEL=3 ;;
    *) echo "Usage: $0 [--csim|--synth|--cosim|--impl]" >&2; exit 2 ;;
esac
if [[ "$#" -gt 1 ]]; then
    echo "Only one mode flag may be supplied." >&2; exit 2
fi
for tool in git sha256sum vitis-run; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool missing. Source the Vitis 2025.2 settings64.sh first." >&2
        exit 2
    fi
done
if (( LEVEL >= 1 )) && ! command -v v++ >/dev/null 2>&1; then
    echo "ERROR: Vitis v++ missing; HLS synthesis cannot run." >&2
    exit 2
fi
VERSION="$(vitis-run --version 2>&1)"
if [[ "$VERSION" != *2025.2* ]]; then
    echo "ERROR: use Vitis 2025.2; reported: $VERSION" >&2
    exit 2
fi
if [[ "${HLS_PART:-$PART}" != "$PART" ]]; then
    echo "ERROR: HLS_PART must be exactly $PART" >&2
    exit 2
fi
if ! grep -qx "part=$PART" "$CONFIG" || \
   ! grep -qx "syn.output.format=rtl" "$CONFIG"; then
    echo "ERROR: K26 part or HLS RTL output configuration not as expected" >&2
    exit 2
fi

cd "$ROOT"
mkdir -p "$HOME/Thesis_Evidence"
UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HOME/Thesis_Evidence/neuromorphic_accel_v1_m05_hls_${UTC}_$$"
mkdir "$OUT"  # exclusive, never wipe previous evidence
printf '%s\n' "$OUT" > "$OUT/evidence_location.txt"
printf '%s\n' "$VERSION" > "$OUT/tool_version.txt"
printf '%s\n' "$PART" > "$OUT/part.txt"
printf '%s\n' "${1:---csim}" > "$OUT/mode.txt"
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/working_tree_status.txt"
sha256sum \
    hls/m04_lif_eval/m04_eval.cpp \
    hls/m04_lif_eval/m04_eval.hpp \
    hls/m05_stream_eval/m05_stream.hpp \
    hls/m05_stream_eval/m05_stream.cpp \
    hls/m05_stream_eval/m05_hls_csim_tb.cpp \
    hls/m05_stream_eval/m05_hls_config.cfg \
    hls/m05_stream_eval/run_m05_offline_hls.sh \
    > "$OUT/source_sha256.txt"

# Always preserve logs and hashes, including after an unsuccessful tool step.
finish() {
    local status="$?"
    trap - EXIT
    printf 'exit_status=%s\n' "$status" > "$OUT/result.txt"
    find "$OUT" -type f \( -name '*_csynth.rpt' \
          -o -name '*cosim*.rpt' -o -name '*_impl*.rpt' \
          -o -name 'syn_report*.xml' \) -print \
          > "$OUT/report_paths.txt" || true
    find "$OUT" -type f \( -name '*_csynth.rpt' \
          -o -name '*cosim*.rpt' -o -name '*_impl*.rpt' \
          -o -name 'syn_report*.xml' \) -print0 \
          | sort -z | xargs -0 -r sha256sum > "$OUT/report_sha256.txt" || true
    find "$OUT" -maxdepth 1 -type f -name '*.log' -print0 \
          | sort -z | xargs -0 -r sha256sum > "$OUT/log_sha256.txt" || true
    echo "M05 evidence directory: $OUT"
    echo "M05 final exit code: $status"
    echo "Share result.txt, original logs and *_csynth.rpt if synthesis was attempted."
    exit "$status"
}
trap finish EXIT

echo "M05 offline HLS, mode ${1:---csim}, source $(cat "$OUT/commit.txt")"
echo "Original output folder: $OUT"
echo "== 1/4 Vitis C simulation =="
vitis-run --mode hls --csim --config "$CONFIG" \
    --work_dir "$OUT/work" --part "$PART" \
    2>&1 | tee "$OUT/01_csim.log"

if (( LEVEL >= 1 )); then
    echo "== 2/4 Vitis HLS C synthesis; 10ns requested, II must be read from report =="
    v++ -c --mode hls --config "$CONFIG" \
        --work_dir "$OUT/work" --part "$PART" \
        2>&1 | tee "$OUT/02_csynth.log"
fi
if (( LEVEL >= 2 )); then
    echo "== 3/4 RTL co-simulation of synthesized HLS design =="
    vitis-run --mode hls --cosim --config "$CONFIG" \
        --work_dir "$OUT/work" --part "$PART" \
        2>&1 | tee "$OUT/03_cosim.log"
fi
if (( LEVEL >= 3 )); then
    echo "== 4/4 Vivado OOC implementation (not board timing) =="
    vitis-run --mode hls --impl --config "$CONFIG" \
        --work_dir "$OUT/work" --part "$PART" \
        2>&1 | tee "$OUT/04_ooc_impl.log"
fi
echo "M05 offline HLS stages completed."
