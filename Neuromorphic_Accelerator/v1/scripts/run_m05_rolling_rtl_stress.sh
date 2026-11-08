#!/usr/bin/env bash
# M05: direct Verilog XSim AXIS handshake stress against an ALREADY VERIFIED
# generated RTL snapshot. No Vitis HLS re-synthesis, Vivado implementation,
# JTAG, PS/DDR access, or physical board operations.
#
# usage: bash scripts/run_m05_rolling_rtl_stress.sh \
#          "$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_..."
#
# All newly generated files are under a fresh ~/Thesis_Evidence directory.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$#" -ne 1 ]]; then
    echo "Usage: bash $0 <existing completed rolling --impl evidence dir>" >&2
    exit 2
fi
IMPL="$(realpath -e -- "$1")"
if [[ ! -d "$IMPL" ]] || [[ "$(basename "$IMPL")" != neuromorphic_v1_m05_rolling_impl_* ]]; then
    echo "ERROR: input must be a genuine rolling M05 implementation evidence directory" >&2
    exit 2
fi
if [[ "$(cat "$IMPL/result.txt" 2>/dev/null)" != "exit_status=0" ]] || \
   [[ "$(cat "$IMPL/top.txt" 2>/dev/null)" != "m05_rolling_replay" ]] || \
   [[ "$(cat "$IMPL/part.txt" 2>/dev/null)" != "xck26-sfvc784-2LV-c" ]]; then
    echo "ERROR: implementation evidence did not PASS or has the wrong top/device" >&2
    exit 2
fi
for tool in xvlog xelab xsim python3 git sha256sum realpath timeout; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: missing $tool. Source Vivado 2025.2 settings64.sh" >&2
        exit 2
    }
done
for field in 2025.2; do
    xvlog -version 2>&1 | grep -q "$field" || {
        echo "ERROR: expected Vivado $field simulation tools" >&2; exit 2;
    }
done
cd "$ROOT"
# Source identity is checked against the EXACT previous proven HLS build.
# When a new kernel is intentionally introduced, it requires its own impl.
manifest="$IMPL/source_sha256.txt"
[[ -f "$manifest" ]] || { echo "ERROR: missing source hashes" >&2; exit 2; }
hls_src_hash="$(awk '$2 == "hls/m05_rolling/m05_rolling.cpp" {print $1}' "$manifest")"
current_src_hash="$(sha256sum hls/m05_rolling/m05_rolling.cpp | awk '{print $1}')"
if [[ -z "$hls_src_hash" ]] || [[ "$hls_src_hash" != "$current_src_hash" ]]; then
    echo "ERROR: current HLS kernel != routed implementation evidence source. No stale RTL testing." >&2
    exit 2
fi
SYN_RTL="$IMPL/work/hls/syn/verilog"
[[ -d "$SYN_RTL" ]] || {
    echo "ERROR: no HLS syn/verilog RTL: $SYN_RTL" >&2; exit 2;
}
[[ -f "$SYN_RTL/m05_rolling_replay.v" ]] || {
    echo "ERROR: generated top RTL missing: $SYN_RTL/m05_rolling_replay.v" >&2; exit 2;
}
mkdir -p "$HOME/Thesis_Evidence"
OUT="$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_$(date -u +%Y%m%dT%H%M%SZ)_$$"
mkdir "$OUT"
echo "$IMPL" > "$OUT/source_impl_evidence.txt"
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/working_tree_status.txt"
printf '%s\n' "xck26-sfvc784-2LV-c" > "$OUT/part.txt"
sha256sum "$ROOT/hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_stress.sv" \
    "$ROOT/scripts/m05_axis_regmap.py" \
    "$ROOT/scripts/m05_rtl_meminit.py" \
    "$ROOT/scripts/run_m05_rolling_rtl_stress.sh" \
    "$ROOT/hls/m05_rolling/m05_rolling.cpp" > "$OUT/stress_source_sha256.txt"
finish() {
    status="$?"
    trap - EXIT
    printf 'exit_status=%s\n' "$status" > "$OUT/result.txt"
    echo "RTL STRESS evidence: $OUT"
    echo "RTL STRESS exit code: $status"
    exit "$status"
}
trap finish EXIT

python3 scripts/m05_axis_regmap.py --impl-evidence "$IMPL" \
    --output "$OUT/m05_rolling_regmap.svh" | tee "$OUT/01_regmap.log"

# The original direct XSim proof passed, but emitted warnings about
# generated $readmemh(... .dat) files absent from the simulator cwd.
# This new gate requires the exact original Vitis-generated files. If none
# were retained, STOP; never inject fake memory contents or suppress warning.
python3 scripts/m05_rtl_meminit.py --impl-evidence "$IMPL" \
    --output-directory "$OUT" | tee "$OUT/01_ram_init.log"

mapfile -t VERILOG_FILES < <(find "$SYN_RTL" -maxdepth 1 -type f \
    \( -name '*.v' -o -name '*.sv' \) -print | sort)
if (( ${#VERILOG_FILES[@]} == 0 )); then
    echo "ERROR: no generated HDL sources" >&2
    exit 2
fi
printf '%s\n' "${VERILOG_FILES[@]}" > "$OUT/rtl_source_paths.txt"
TOP_SV="$ROOT/hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_stress.sv"
# Compile in a unique evidence-local cwd so no xsim.dir or .jou is deposited
# in the user's Git worktree or an earlier Vitis proof directory.
cd "$OUT"
echo "== Compiling generated Vivado RTL with direct AXI stressbench =="
xvlog --relax -sv -i "$OUT" -i "$SYN_RTL" \
    "${VERILOG_FILES[@]}" "$TOP_SV" \
    2>&1 | tee "$OUT/02_xvlog.log"
# The design can reference Xilinx XPM/UNISIM primitives. Use the installed
# Vivado simulator library, but do not compile the unrelated impl wrapper.
echo "== Elaborating direct RTL stressbench =="
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
    work.tb_m05_rolling_axis_stress \
    -s m05_rolling_axis_stress_snapshot \
    2>&1 | tee "$OUT/03_xelab.log"
echo "== Running with actual TREADY/TVALID stall injection =="
timeout --signal=TERM 180s xsim m05_rolling_axis_stress_snapshot -R \
    --onfinish quit 2>&1 | tee "$OUT/04_xsim.log"
grep -Fq "PASS: M05 REAL RTL AXIS stall stress" "$OUT/04_xsim.log" || {
    echo "ERROR: XSim ended without RTL handshake PASS marker" >&2
    exit 1
}
# Any warning about missing RAM init assets invalidates the strengthened
# initialized-memory gate, even if XSim emits its old PASS marker.
if grep -Eiq 'cannot be opened for reading|failed to open.*\\.dat|no such file.*\\.dat' "$OUT/04_xsim.log"; then
    echo "ERROR: XSim reported missing RTL memory .dat initialization files" >&2
    exit 1
fi
echo "PASS: Direct generated RTL AXI stall stress; no board operations."
