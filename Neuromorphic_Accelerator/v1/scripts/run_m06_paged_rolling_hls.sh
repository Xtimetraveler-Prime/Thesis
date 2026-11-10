#!/usr/bin/env bash
# M06 offline ONLY: genuine Vitis 2025.2 HLS CSim/C-synthesis/co-sim of
# NEW autonomous M05-derived rolling event engine with M_AXI canonical pages.
# DOES NOT program devices, open JTAG, allocate PS/Linux DDR or modify D3.
# Preserves all evidence in a new unique ~/Thesis_Evidence folder.
#
# bash scripts/run_m06_paged_rolling_hls.sh --csim
# bash scripts/run_m06_paged_rolling_hls.sh --synth
# bash scripts/run_m06_paged_rolling_hls.sh --cosim
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PART=xck26-sfvc784-2LV-c
TOP=m06_paged_rolling_replay
CONFIG="$ROOT/hls/m06_paged_rolling/m06_paged_rolling_hls_config.cfg"
if (( $# != 1 )) || [[ "$1" != "--csim" && "$1" != "--synth" && "$1" != "--cosim" ]]; then
  echo "Usage: bash $0 --csim|--synth|--cosim (offline ONLY)" >&2
  exit 2
fi
MODE="${1#--}"
for cmd in git python3 sha256sum realpath vitis-run grep tee find; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: missing $cmd; source Vitis 2025.2 settings64.sh" >&2
    exit 2
  }
done
if [[ "$MODE" != "csim" ]]; then
  command -v v++ >/dev/null 2>&1 || {
    echo "ERROR: v++ required for genuine HLS C synthesis" >&2
    exit 2
  }
fi
VERSION="$(vitis-run --version 2>&1)" || {
  echo "ERROR: vitis-run --version did not succeed" >&2; exit 2;
}
[[ "$VERSION" == *2025.2* ]] || {
  echo "ERROR: expected Vitis 2025.2: $VERSION" >&2; exit 2;
}
[[ -f "$CONFIG" ]] || { echo "ERROR: missing M06 HLS config" >&2; exit 2; }
grep -qx "part=$PART" "$CONFIG" || {
  echo "ERROR: incorrect target K26 part" >&2; exit 2;
}
grep -qx "syn.top=$TOP" "$CONFIG" || {
  echo "ERROR: unexpected HLS top" >&2; exit 2;
}
cd "$ROOT"
mkdir -p "$HOME/Thesis_Evidence"
OUT="$(mktemp -d "$HOME/Thesis_Evidence/m06_paged_rolling_hls_${MODE}_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
HASHES=(
  hls/m04_lif_eval/m04_eval.cpp
  hls/m04_lif_eval/m04_eval.hpp
  hls/m05_stream_eval/m05_stream.hpp
  hls/m05_integrated/m05_integrated.hpp
  hls/m05_rolling/m05_rolling.hpp
  hls/m05_rolling/m05_rolling.cpp
  hls/m06_paged_rolling/m06_paged_rolling.hpp
  hls/m06_paged_rolling/m06_paged_rolling.cpp
  hls/m06_paged_rolling/m06_paged_rolling_csim_tb.cpp
  hls/m06_paged_rolling/m06_paged_rolling_hls_config.cfg
  hls/m06_paged_rolling/prepare_hls_config.py
  scripts/run_m06_paged_rolling_hls.sh
)
finish() {
  rc="$?"
  trap - EXIT
  cd "$ROOT" || rc=3
  sha256sum "${HASHES[@]}" > "$OUT/source_after_sha256.txt" || rc=3
  cmp -s "$OUT/source_before_sha256.txt" "$OUT/source_after_sha256.txt" || {
    echo "FATAL: original M05 or M06 HLS source changed during offline run" >&2
    rc=3
  }
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  find "$OUT" -type f \( -name '*_csynth.rpt' -o -name '*cosim*.rpt' \
      -o -name '*_impl*.rpt' -o -name 'syn_report*.xml' \) -print \
      > "$OUT/report_paths.txt" || true
  find "$OUT" -type f \( -name '*_csynth.rpt' -o -name '*cosim*.rpt' \
      -o -name 'syn_report*.xml' \) -print0 | sort -z |
      xargs -0 -r sha256sum > "$OUT/report_sha256.txt" || true
  echo "M06 genuine offline Vitis HLS evidence: $OUT"
  echo "M06 HLS $MODE exit=$rc"
  exit "$rc"
}
trap finish EXIT
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/worktree_status.txt"
printf '%s\n' "$VERSION" > "$OUT/vitis_version.txt"
printf '%s\n' "$PART" > "$OUT/part.txt"
printf '%s\n' "$TOP" > "$OUT/top.txt"
printf '%s\n' "$MODE" > "$OUT/mode.txt"
sha256sum "${HASHES[@]}" > "$OUT/source_before_sha256.txt"
python3 hls/m06_paged_rolling/prepare_hls_config.py \
  --root "$ROOT" --template "$CONFIG" \
  --output "$OUT/m06_effective_config.cfg" --top "$TOP" \
  2>&1 | tee "$OUT/00_config.log"
sha256sum "$OUT/m06_effective_config.cfg" > "$OUT/config_sha256.txt"
echo "== Offline REAL Vitis HLS C simulation of m_axi paged rolling neural core =="
vitis-run --mode hls --csim --config "$OUT/m06_effective_config.cfg" \
  --work_dir "$OUT/work" --part "$PART" \
  2>&1 | tee "$OUT/01_csim.log"
# Vitis may put CSim stdout into local csim.log rather than launcher log.
if ! grep -R -F -q --include='*.log' \
  "M06_PAGED_ROLLING_HLS_CSIM_PASS" "$OUT/work" "$OUT/01_csim.log"; then
  echo "ERROR: HLS CSim PASS marker missing from genuine tool output" >&2
  exit 1
fi
if [[ "$MODE" != "csim" ]]; then
  echo "== Genuine Vitis C synthesis (BRAM and m_axi resource report) =="
  v++ -c --mode hls --config "$OUT/m06_effective_config.cfg" \
    --work_dir "$OUT/work" --part "$PART" \
    2>&1 | tee "$OUT/02_csynth.log"
  if ! find "$OUT/work" -type f -name '*_csynth.rpt' | grep -q .; then
    echo "ERROR: Vitis successful status had no generated C synthesis report" >&2
    exit 1
  fi
fi
if [[ "$MODE" == "cosim" ]]; then
  echo "== Real generated HLS RTL C/RTL co-simulation with AXI memory model =="
  vitis-run --mode hls --cosim --config "$OUT/m06_effective_config.cfg" \
    --work_dir "$OUT/work" --part "$PART" \
    2>&1 | tee "$OUT/03_cosim.log"
fi
echo "PASS: M06_PAGED_ROLLING_VITIS_${MODE^^}_REAL_TOOL_NO_BOARD"
