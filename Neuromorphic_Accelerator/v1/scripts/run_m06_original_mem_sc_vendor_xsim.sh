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
python3 - "$D3" "$PORTS" "$OUT" <<'PY'
from pathlib import Path
import sys
orig,report,out=(Path(x).resolve() for x in sys.argv[1:])
design="m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0"
raw=[line.split("|",1)[1] for line in report.read_text().splitlines()
     if line.startswith("SIM_SOURCE|")]
if len(raw)!=186:
    raise SystemExit("ERROR: not the original 186-file Vivado compile order")
chosen=[]
for name in raw:
    p=Path(name)
    if not p.is_absolute() or not p.is_relative_to(orig):
        continue
    mem=f"/{design}/" in str(p)
    shared=("/ipshared/" in str(p) and p.name.startswith(
        ("sc_","axi_register_slice_v2_1","proc_sys_reset_v5_0")))
    if not (mem or shared) or p.suffix.lower() not in (".v",".sv",".vhd",".vh",".svh"):
        continue
    if not p.is_file():
        raise SystemExit("ERROR: missing original compile source: "+str(p))
    chosen.append(p)
if len(chosen)<50 or len(chosen)!=len(set(chosen)):
    raise SystemExit(f"ERROR: original mem_sc subgraph incomplete or repeated ({len(chosen)})")
if not any(p.name==design+".sv" for p in chosen) or not any(p.name=="bd_13bd.v" for p in chosen):
    raise SystemExit("ERROR: original vendor top and nested BD missing")
(out/"original_selected_sources.txt").write_text(
    "\n".join(map(str,chosen))+"\n")
(out/"verilog_sources.txt").write_text(
    "\n".join(map(str,(p for p in chosen if p.suffix in (".sv",".v"))))+"\n")
(out/"vhdl_sources.txt").write_text(
    "\n".join(map(str,(p for p in chosen if p.suffix==".vhd")))+"\n")
(out/"include_dirs.txt").write_text(
    "\n".join(map(str,dict.fromkeys(p.parent for p in chosen)))+"\n")
print(f"M06 vendor source selection: {len(chosen)} original AMD files; "
      "not regenerated, not copied into Git, no board.")
PY
mapfile -t VLOG < "$OUT/verilog_sources.txt"
mapfile -t VHDL < "$OUT/vhdl_sources.txt"
mapfile -t INC < "$OUT/include_dirs.txt"
FLAGS=()
for dir in "${INC[@]}"; do FLAGS+=(-i "$dir"); done
cd "$OUT"
if (( ${#VHDL[@]} > 0 )); then
  xvhdl -2008 "${VHDL[@]}" 2>&1 | tee "$OUT/02_xvhdl.log"
fi
xvlog --relax -sv "${FLAGS[@]}" "${VLOG[@]}" \
  "$ROOT/rtl/m06/m06_axi128_scratch_mem.sv" \
  "$OUT/tb_m06_original_mem_sc_vendor.sv" \
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
echo "PASS: exact AMD original SmartConnect S03 write → M00/128b → S00-S02 reads. NO DDR/BOARD."
