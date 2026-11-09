#!/usr/bin/env bash
# Direct original Vitis 2025.2 HLS generated RTL + new 4-port transport shell.
# No board, actual PS, DMA IP, kernel re-synthesis, routing or bitstream.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$#" -ne 1 ]]; then
  echo "Usage: bash scripts/run_m05_11c_hls_shell_xsim.sh <original K26 --impl evidence directory>" >&2
  exit 2
fi
IMPL="$(realpath -e -- "$1")"
if [[ ! -d "$IMPL" || "$(basename "$IMPL")" != neuromorphic_v1_m05_rolling_impl_* ]]; then
  echo "ERROR: genuine K26 rolling --impl evidence directory required" >&2; exit 2
fi
if [[ "$(cat "$IMPL/result.txt" 2>/dev/null)" != "exit_status=0" ||
      "$(cat "$IMPL/top.txt" 2>/dev/null)" != "m05_rolling_replay" ||
      "$(cat "$IMPL/part.txt" 2>/dev/null)" != "xck26-sfvc784-2LV-c" ]]; then
  echo "ERROR: original implementation proof/top/part incorrect" >&2; exit 2
fi
for tool in git xvlog xelab xsim python3 sha256sum realpath timeout; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: missing $tool (source Vivado 2025.2 settings64.sh)" >&2; exit 2
  }
done
xvlog -version 2>&1 | grep -q 2025.2 || {
  echo "ERROR: Vivado 2025.2 XSim required" >&2; exit 2
}
cd "$ROOT"
OLD_HASH="$(awk '$2 == "hls/m05_rolling/m05_rolling.cpp" {print $1}' "$IMPL/source_sha256.txt")"
NEW_HASH="$(sha256sum hls/m05_rolling/m05_rolling.cpp | awk '{print $1}')"
if [[ -z "$OLD_HASH" || "$OLD_HASH" != "$NEW_HASH" ]]; then
  echo "ERROR: HLS source hash changed since validated implementation" >&2; exit 2
fi
SYN_RTL="$IMPL/work/hls/syn/verilog"
[[ -f "$SYN_RTL/m05_rolling_replay.v" ]] || {
  echo "ERROR: real HLS generated top missing" >&2; exit 2
}
mapfile -t GEN_RTL < <(find "$SYN_RTL" -maxdepth 1 -type f \
  \( -name '*.v' -o -name '*.sv' \) -print | sort)
(( ${#GEN_RTL[@]} > 0 )) || { echo "ERROR: no generated HDL source" >&2; exit 2; }
EVIDENCE_ROOT="${M05_EVIDENCE_ROOT:-$HOME/Thesis_Evidence}"
mkdir -p "$EVIDENCE_ROOT"
OUT="$(mktemp -d "$EVIDENCE_ROOT/neuromorphic_v1_m05_11c_real_hls_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M05.11c REAL HLS+SHELL XSim evidence: $OUT"
  exit "$rc"
}
trap finish EXIT
echo "$IMPL" > "$OUT/source_impl_evidence.txt"
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/working_tree_status.txt"
printf '%s\n' "${GEN_RTL[@]}" > "$OUT/generated_rtl_files.txt"
sha256sum \
  "$ROOT/rtl/m05_11/m05_11_axil_session_controller.v" \
  "$ROOT/rtl/m05_11/m05_11_stream_shell.v" \
  "$ROOT/rtl/m05_11/m05_trace_dma_packetizer.v" \
  "$ROOT/rtl/m05_11/m05_ingress_dma_unpad.v" \
  "$ROOT/rtl/m05_11/tb_m05_11c_real_hls_shell.sv" \
  "$ROOT/scripts/run_m05_11c_hls_shell_xsim.sh" \
  "$ROOT/scripts/m05_11c_replay.py" \
  "$ROOT/scripts/m05_axis_regmap.py" \
  "$ROOT/scripts/m05_rtl_meminit.py" \
  "$ROOT/hls/m05_rolling/m05_rolling.cpp" > "$OUT/source_sha256.txt"
python3 scripts/m05_axis_regmap.py --impl-evidence "$IMPL" \
  --output "$OUT/m05_rolling_regmap.svh" 2>&1 | tee "$OUT/01_regmap.log"
python3 scripts/m05_rtl_meminit.py --impl-evidence "$IMPL" \
  --output-directory "$OUT" 2>&1 | tee "$OUT/01_ram_init.log"
cd "$OUT"
xvlog --relax -sv -i "$OUT" -i "$SYN_RTL" \
  "${GEN_RTL[@]}" \
  "$ROOT/rtl/m05_11/m05_11_axil_session_controller.v" \
  "$ROOT/rtl/m05_11/m05_trace_dma_packetizer.v" \
  "$ROOT/rtl/m05_11/m05_ingress_dma_unpad.v" \
  "$ROOT/rtl/m05_11/m05_11_stream_shell.v" \
  "$ROOT/rtl/m05_11/tb_m05_11c_real_hls_shell.sv" \
  2>&1 | tee "$OUT/02_xvlog.log"
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
  work.tb_m05_11c_real_hls_shell -s m05_11c_hls_shell_snapshot \
  2>&1 | tee "$OUT/03_xelab.log"
timeout --signal=TERM 240s xsim m05_11c_hls_shell_snapshot -R \
  --onfinish quit 2>&1 | tee "$OUT/04_xsim.log"
if grep -Eq 'Fatal: M05_11C_FAIL|ERROR: M05_11C_FAIL' "$OUT/04_xsim.log"; then
  echo "ERROR: RTL bench signaled M05_11C_FAIL" >&2; exit 1
fi
if grep -Eiq 'cannot be opened for reading|failed to open.*\.dat|no such file.*\.dat' "$OUT/04_xsim.log"; then
  echo "ERROR: missing genuine Vitis RAM .dat initialization" >&2; exit 1
fi
grep -Fq "PASS: M05.11c REAL HLS RTL + AXIL shell" "$OUT/04_xsim.log" || {
  echo "ERROR: expected genuine integrated RTL PASS marker missing" >&2; exit 1
}
python3 "$ROOT/scripts/m05_11c_replay.py" \
  --xsim-log "$OUT/04_xsim.log" 2>&1 | tee "$OUT/05_dma_frame_replay.log"
echo "PASS: M05.11c genuine original HLS RTL with new transport shell (not DMA or board)."
