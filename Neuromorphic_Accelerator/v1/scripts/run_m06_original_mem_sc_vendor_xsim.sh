#!/usr/bin/env bash
# Genuine ORIGINAL AMD SmartConnect functional XSim, original D3 READ ONLY.
# No Vivado project edit, no DDR reservation, no bitstream, no JTAG.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ "$#" != 3 ]]; then
  echo "Usage: bash scripts/run_m06_original_mem_sc_vendor_xsim.sh <original D3> <02_original_mem_sc_ports.txt> <08_mem_sc_wrapper_headers_nonansi_fixed.json>" >&2
  exit 2
fi
D3="$(realpath -e -- "$1")"
PORTS="$(realpath -e -- "$2")"
HEADER="$(realpath -e -- "$3")"
if [[ "$(basename "$D3")" != "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ" ||
      "$(basename "$PORTS")" != "02_original_mem_sc_ports.txt" ||
      "$(basename "$HEADER")" != "08_mem_sc_wrapper_headers_nonansi_fixed.json" ]]; then
  echo "ERROR: must use original owner D3 + completed 2026-11-09 metadata" >&2
  exit 2
fi
for app in python3 git xvlog xvhdl xelab xsim sha256sum cmp timeout; do
  command -v "$app" >/dev/null || { echo "ERROR: missing $app; source Vivado 2025.2 settings64.sh" >&2; exit 2; }
done
xvlog -version 2>&1 | grep -q '2025.2' || {
  echo "ERROR: must use Vivado 2025.2 original simulation libraries" >&2
  exit 2
}
SIM_TOP="$D3/13_file_backed_project/m05_d3_output_products.gen/sources_1/bd/m05_12d3_real_signed32_hls_six_control_address_candidate/ip/m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0/sim/m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0.sv"
BD_SUB="$D3/13_file_backed_project/m05_d3_output_products.gen/sources_1/bd/m05_12d3_real_signed32_hls_six_control_address_candidate/ip/m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0/bd_0/sim/bd_13bd.v"
mkdir -p "$HOME/Thesis_Evidence"
OUT="$(mktemp -d "$HOME/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finalize() {
  code="$?"
  trap - EXIT
  if [[ -f "$OUT/sha_before.txt" ]]; then
    sha256sum "$SIM_TOP" "$BD_SUB" > "$OUT/sha_after.txt" || code=3
    cmp -s "$OUT/sha_before.txt" "$OUT/sha_after.txt" || {
      echo "FATAL: ORIGINAL vendor source hashes changed" >&2
      code=3
    }
  fi
  printf 'exit_status=%s\n' "$code" > "$OUT/result.txt"
  echo "M06 genuine original vendor XSim evidence: $OUT"
  exit "$code"
}
trap finalize EXIT
cd "$ROOT"
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/worktree_status.txt"
sha256sum "$SIM_TOP" "$BD_SUB" > "$OUT/sha_before.txt"
printf '%s\n' "$D3" > "$OUT/original_directory.txt"
python3 scripts/m06_generate_original_mem_sc_bfm.py \
  --original "$D3" --headers "$HEADER" \
  --output "$OUT/tb_m06_original_mem_sc_vendor.sv" \
  2>&1 | tee "$OUT/01_authentic_bfm.log"
python3 scripts/m06_generate_original_paged_vendor_bfm.py \
  --original "$D3" --headers "$HEADER" \
  --output "$OUT/tb_m06_original_vendor_paged.sv" \
  2>&1 | tee "$OUT/01b_authentic_paged_bfm.log"
python3 scripts/m06_vendor_compile_plan.py \
  --original "$D3" --report "$PORTS" \
  --output "$OUT/02_original_vendor_compile_plan.json" \
  2>&1 | tee "$OUT/02_compile_plan.log"
python3 - "$OUT/02_original_vendor_compile_plan.json" "$OUT" <<'PY'
import json
from pathlib import Path
import sys
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = Path(sys.argv[2])
for name, key in (
    ("verilog_sources.txt", "verilog_files"),
    ("vhdl_sources.txt", "vhdl_files"),
    ("include_dirs.txt", "include_directories"),
):
    (out / name).write_text("\n".join(manifest[key])+"\n", encoding="utf-8")
print("M06 compiler source/include plan: ",
      len(manifest["verilog_files"]), "Verilog modules,",
      len(manifest["vhdl_files"]), "VHDL modules,",
      len(manifest["original_include_files"]), "original included headers,",
      len(manifest["include_directories"]), "original include paths")
PY
mapfile -t VLOG < "$OUT/verilog_sources.txt"
mapfile -t VHDL < "$OUT/vhdl_sources.txt"
mapfile -t INC < "$OUT/include_dirs.txt"
FLAGS=()
for dir in "${INC[@]}"; do
  [[ -d "$dir" ]] || { echo "ERROR: Original include directory missing: $dir" >&2; exit 2; }
  FLAGS+=(-i "$dir")
done
# Direct regression guard against the owner's xvlog VRFC 10-3195 error.
python3 - "$OUT/02_original_vendor_compile_plan.json" <<'PY'
import json
from pathlib import Path
import sys
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
header = Path(data["axi_infrastructure_header"])
if header.name != "axi_infrastructure_v1_1_0.vh":
    raise SystemExit("ERROR: authentic infrastructure header name changed")
if not header.is_file() or str(header.parent) not in data["include_directories"]:
    raise SystemExit("ERROR: authentic infrastructure header not on xvlog -i path")
print("M06 AUTHENTIC AMD AXI INFRASTRUCTURE .vh INCLUDED (not fabricated)")
PY
cd "$OUT"
if (( ${#VHDL[@]} > 0 )); then
  xvhdl -2008 "${VHDL[@]}" 2>&1 | tee "$OUT/02_xvhdl.log"
fi
xvlog --relax -sv "${FLAGS[@]}" "${VLOG[@]}" \
  "$ROOT/rtl/m06/m06_axi128_scratch_mem.sv" \
  "$ROOT/rtl/m06/m06_residency_control_fsm.sv" \
  "$ROOT/rtl/m06/m06_axi256_block_transfer.sv" \
  "$OUT/tb_m06_original_mem_sc_vendor.sv" \
  "$OUT/tb_m06_original_vendor_paged.sv" \
  2>&1 | tee "$OUT/03_xvlog.log"
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
  work.tb_m06_original_mem_sc_vendor -s m06_original_vendor_snapshot \
  2>&1 | tee "$OUT/04_xelab.log"
timeout --signal=TERM 360s xsim m06_original_vendor_snapshot -R \
  --onfinish quit 2>&1 | tee "$OUT/05_xsim.log"
if grep -Eq 'M06_VENDOR_FAIL|FATAL_ERROR|Fatal: ' "$OUT/05_xsim.log"; then
  echo "ERROR: original SmartConnect functional simulation reported a fatal failure" >&2
  exit 1
fi
grep -Fq 'M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS' "$OUT/05_xsim.log" || {
  echo "ERROR: genuine vendor scoreboard PASS marker missing" >&2
  exit 1
}
# Stage 2: SAME authenticated original AMD IP, now driven by the
# synthesis-oriented one-slot 256B RTL page manager + AXI block mover.
# The earlier byte-exact port test must already PASS before this stage.
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
  work.tb_m06_original_vendor_paged -s m06_original_paged_vendor_snapshot \
  2>&1 | tee "$OUT/06_paged_xelab.log"
timeout --signal=TERM 360s xsim m06_original_paged_vendor_snapshot -R \
  --onfinish quit 2>&1 | tee "$OUT/07_paged_xsim.log"
if grep -Eq 'M06_ORIGINAL_PAGED_FAIL|FATAL_ERROR|Fatal: ' "$OUT/07_paged_xsim.log"; then
  echo "ERROR: real vendor paged memory simulation reported a fatal failure" >&2
  exit 1
fi
for pattern in "M06_ORIGINAL_VENDOR_PAGED_RTL_PASS" \
               "M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS"; do
  grep -Fq "$pattern" "$OUT/07_paged_xsim.log" || {
    echo "ERROR: required actual original vendor paged XSim marker missing: $pattern" >&2
    exit 1
  }
done
echo "PASS: ORIGINAL AMD SmartConnect basic byte integrity AND 256B RTL page evict/reload/quarantine XSim in synthetic scratch; NO real DDR/BOARD."
