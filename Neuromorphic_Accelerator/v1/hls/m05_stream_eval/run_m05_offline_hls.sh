#!/usr/bin/env bash
# M05: isolated K26 Vitis 2025.2 WITHOUT board/JTAG/PS/DDR operations.
# Use from Neuromorphic_Accelerator/v1 (or any cwd):
#   bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --csim
#   bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --synth
#   bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --cosim
#   bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --impl
# Modes are cumulative; no reusing/deleting any old evidence.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
PART="xck26-sfvc784-2LV-c"
KERNEL="stream"
LEVEL=0
MODE="csim"
SEEN_MODE=0
SEEN_KERNEL=0
usage() {
    echo "Usage: bash $0 [--stream|--stateful] [--csim|--synth|--cosim|--impl]"
    echo "Default: --stream --csim. All steps are offline and create new evidence."
}
for arg in "$@"; do
    case "$arg" in
        --stream|--stateful)
            if (( SEEN_KERNEL != 0 )); then
                echo "ERROR: specify only one kernel" >&2; exit 2
            fi
            KERNEL="${arg#--}"
            SEEN_KERNEL=1
            ;;
        --csim|--synth|--cosim|--impl)
            if (( SEEN_MODE != 0 )); then
                echo "ERROR: specify one stage/mode" >&2; exit 2
            fi
            MODE="${arg#--}"
            SEEN_MODE=1
            case "$MODE" in
                csim) LEVEL=0;; synth) LEVEL=1;;
                cosim) LEVEL=2;; impl) LEVEL=3;;
            esac
            ;;
        --help|-h) usage; exit 0 ;;
        *) echo "ERROR: unknown option: $arg" >&2; usage >&2; exit 2 ;;
    esac
done
if [[ "$KERNEL" == "stateful" ]]; then
    CONFIG="$ROOT/hls/m05_stateful/m05_stateful_hls_config.cfg"
    TOP="m05_stateful_service"
else
    CONFIG="$ROOT/hls/m05_stream_eval/m05_hls_config.cfg"
    TOP="m05_stream_eval"
fi
for tool in git sha256sum vitis-run; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool missing; source Vitis 2025.2 settings64.sh" >&2
        exit 2
    fi
done
if (( LEVEL >= 1 )) && ! command -v v++ >/dev/null 2>&1; then
    echo "ERROR: v++ missing; cannot synthesize" >&2; exit 2
fi
VERSION="$(vitis-run --version 2>&1)"
if [[ "$VERSION" != *2025.2* ]]; then
    echo "ERROR: expected Vitis 2025.2, found: $VERSION" >&2; exit 2
fi
if [[ "${HLS_PART:-$PART}" != "$PART" ]]; then
    echo "ERROR: HLS_PART must match $PART" >&2; exit 2
fi
if [[ ! -f "$CONFIG" ]] || \
   ! grep -qx "part=$PART" "$CONFIG" || \
   ! grep -qx "syn.top=$TOP" "$CONFIG" || \
   ! grep -qx "syn.output.format=rtl" "$CONFIG" || \
   ! grep -qx "clock=10ns" "$CONFIG"; then
    echo "ERROR: config/part/top/clock mismatch: $CONFIG" >&2; exit 2
fi

cd "$ROOT"
mkdir -p "$HOME/Thesis_Evidence"
UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HOME/Thesis_Evidence/neuromorphic_v1_m05_${KERNEL}_${MODE}_${UTC}_$$"
mkdir "$OUT"  # exclusive; preserve all old measurements
printf '%s\n' "$OUT" > "$OUT/evidence_location.txt"
printf '%s\n' "$VERSION" > "$OUT/tool_version.txt"
printf '%s\n' "$PART" > "$OUT/part.txt"
printf '%s\n' "$MODE" > "$OUT/mode.txt"
printf '%s\n' "$TOP" > "$OUT/top.txt"
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/working_tree_status.txt"
sha256sum \
    hls/m04_lif_eval/m04_eval.cpp \
    hls/m04_lif_eval/m04_eval.hpp \
    hls/m05_stream_eval/m05_stream.hpp \
    hls/m05_stream_eval/m05_stream.cpp \
    hls/m05_stream_eval/m05_hls_csim_tb.cpp \
    hls/m05_stream_eval/m05_hls_config.cfg \
    hls/m05_stateful/m05_stateful.hpp \
    hls/m05_stateful/m05_stateful.cpp \
    hls/m05_stateful/m05_stateful_csim_tb.cpp \
    hls/m05_stateful/m05_stateful_hls_config.cfg \
    hls/m05_stream_eval/run_m05_offline_hls.sh \
    > "$OUT/source_sha256.txt"
# A nonzero tool status still preserves original logs and an explicit failure.
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
    echo "M05 evidence: $OUT"
    echo "M05 $KERNEL $MODE exit code: $status"
    echo "Share result.txt, report_paths.txt, stage logs and *_csynth.rpt."
    exit "$status"
}
trap finish EXIT

echo "M05 OFFLINE HLS kernel=$KERNEL mode=$MODE source=$(cat "$OUT/commit.txt")"
echo "Preserving outputs under $OUT"
echo "== Step 1: Vitis C simulation =="
vitis-run --mode hls --csim --config "$CONFIG" \
    --work_dir "$OUT/work" --part "$PART" \
    2>&1 | tee "$OUT/01_csim.log"
if (( LEVEL >= 1 )); then
    echo "== Step 2: HLS C synthesis, report *achieved* II/latency/resources =="
    v++ -c --mode hls --config "$CONFIG" \
        --work_dir "$OUT/work" --part "$PART" \
        2>&1 | tee "$OUT/02_csynth.log"
fi
if (( LEVEL >= 2 )); then
    echo "== Step 3: synthesized C/RTL co-simulation =="
    vitis-run --mode hls --cosim --config "$CONFIG" \
        --work_dir "$OUT/work" --part "$PART" \
        2>&1 | tee "$OUT/03_cosim.log"
fi
if (( LEVEL >= 3 )); then
    echo "== Step 4: Vivado out-of-context implementation (NOT full shell) =="
    vitis-run --mode hls --impl --config "$CONFIG" \
        --work_dir "$OUT/work" --part "$PART" \
        2>&1 | tee "$OUT/04_ooc_impl.log"
fi
echo "M05 offline HLS stages completed successfully (inspect reports)."
