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
# Original owner XSim 2026-11-09 progressed through all vendor RTL
# xvlog sources but XPM xpm_cdc.sv references a GLOBAL Verilog module
# 'glbl'. -L unisims_ver/xpm does NOT itself instantiate work.glbl.
# Compile the installed Vivado glbl.v and specify work.glbl as the
# second elaboration root for BOTH independent XSim snapshots.
if [[ -z "${XILINX_VIVADO:-}" ]]; then
  echo "ERROR: XILINX_VIVADO unset; source original Vivado 2025.2 settings64.sh" >&2
  exit 2
fi
# Canonicalize the installation root BEFORE resolving its glbl.v.
# The user may source Vivado through a symlink (or a trailing slash); the
# previous comparison mixed resolved GLBL with unresolved XILINX_VIVADO
# and falsely rejected a genuine installed file after test -f succeeded.
VIVADO_ROOT="$(realpath -e -- "$XILINX_VIVADO")" || {
  echo "ERROR: Vivado installation root does not exist: $XILINX_VIVADO" >&2
  exit 2
}
GLBL_SOURCE="$VIVADO_ROOT/data/verilog/src/glbl.v"
if [[ ! -f "$GLBL_SOURCE" ]]; then
  echo "ERROR: standard Vivado global primitive glbl.v missing: $GLBL_SOURCE" >&2
  exit 2
fi
GLBL="$(realpath -e -- "$GLBL_SOURCE")" || {
  echo "ERROR: standard Vivado glbl.v is not readable" >&2
  exit 2
}
# glbl.v may itself be a valid symlink into Vivado's installed files.
# Source provenance is protected by its SHA256 and module declaration;
# no fragile comparison against the unnormalized environment variable.
grep -Eq '^[[:space:]]*module[[:space:]]+glbl([[:space:](;]|$)' "$GLBL" || {
  echo "ERROR: installed Vivado glbl.v does not declare module glbl" >&2
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
sha256sum "$GLBL" > "$OUT/installed_vivado_glbl_sha256.txt"
printf '%s\n' "$GLBL" > "$OUT/installed_vivado_glbl_path.txt"
printf '%s\n' "$D3" > "$OUT/original_directory.txt"
python3 scripts/m06_generate_original_mem_sc_bfm.py \
  --original "$D3" --headers "$HEADER" \
  --output "$OUT/tb_m06_original_mem_sc_vendor.sv" \
  2>&1 | tee "$OUT/01_authentic_bfm.log"
python3 scripts/m06_generate_original_paged_vendor_bfm.py \
  --original "$D3" --headers "$HEADER" \
  --output "$OUT/tb_m06_original_vendor_paged.sv" \
  2>&1 | tee "$OUT/01b_authentic_paged_bfm.log"
# M02 independent dense reference generates the neural values/expected
# spike and voltage trace. This only supplies a test oracle/current stream,
# not the unchanged M05 HLS streaming engine itself.
python3 scripts/m06_generate_paged_lif16_vectors.py \
  --output "$OUT/m06_lif16_vectors.vh" \
  2>&1 | tee "$OUT/01c_neural_reference.log"
python3 scripts/m06_generate_original_vendor_neural_paged_bfm.py \
  --original "$D3" --headers "$HEADER" \
  --output "$OUT/tb_m06_original_vendor_neural_paged.sv" \
  2>&1 | tee "$OUT/01d_neural_paged_bfm.log"
python3 scripts/m06_generate_original_vendor_lru8_bfm.py \
  --original "$D3" --headers "$HEADER" \
  --output "$OUT/tb_m06_original_vendor_lru8.sv" \
  2>&1 | tee "$OUT/01e_lru8_bfm.log"
python3 scripts/m06_generate_original_vendor_4096_bfm.py \
  --original "$D3" --headers "$HEADER" \
  --output "$OUT/tb_m06_original_vendor_4096.sv" \
  2>&1 | tee "$OUT/01f_4096_bfm.log"
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
xvlog --relax -sv "${FLAGS[@]}" -i "$OUT" "${VLOG[@]}" \
  "$ROOT/rtl/m06/m06_axi128_scratch_mem.sv" \
  "$ROOT/rtl/m06/m06_residency_control_fsm.sv" \
  "$ROOT/rtl/m06/m06_axi256_block_transfer.sv" \
  "$OUT/tb_m06_original_mem_sc_vendor.sv" \
  "$OUT/tb_m06_original_vendor_paged.sv" \
  "$ROOT/rtl/m06/m06_lif16_neuron_step.sv" \
  "$ROOT/rtl/m06/m06_residency_lru8.sv" \
  "$ROOT/rtl/m06/m06_axi256_multislot_transfer.sv" \
  "$OUT/tb_m06_original_vendor_neural_paged.sv" \
  "$OUT/tb_m06_original_vendor_lru8.sv" \
  "$OUT/tb_m06_original_vendor_4096.sv" \
  "$GLBL" \
  2>&1 | tee "$OUT/03_xvlog.log"
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
  work.tb_m06_original_mem_sc_vendor work.glbl \
  -s m06_original_vendor_snapshot \
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
  work.tb_m06_original_vendor_paged work.glbl \
  -s m06_original_paged_vendor_snapshot \
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
# Stage 3: ACTUAL AMD SmartConnect + same RTL page-control data path
# + M02 LIF arithmetic in RTL. This checks numerical state preservation
# across vendor AXI writeback/reload, NOT acceptance of original M05 HLS IP.
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
  work.tb_m06_original_vendor_neural_paged work.glbl \
  -s m06_original_vendor_neural_paged_snapshot \
  2>&1 | tee "$OUT/08_neural_paged_xelab.log"
timeout --signal=TERM 360s xsim m06_original_vendor_neural_paged_snapshot -R \
  --onfinish quit 2>&1 | tee "$OUT/09_neural_paged_xsim.log"
if grep -Eq 'M06_VENDOR_NEURAL_FAIL|FATAL_ERROR|Fatal: ' "$OUT/09_neural_paged_xsim.log"; then
  echo "ERROR: original vendor neural-paged RTL simulation reported failure" >&2
  exit 1
fi
for pattern in "M06_ORIGINAL_VENDOR_NEURAL_PAGED_M02_PARITY_PASS" \
               "M06_ORIGINAL_VENDOR_NEURAL_PAGED_FAULT_PASS"; do
  grep -Fq "$pattern" "$OUT/09_neural_paged_xsim.log" || {
    echo "ERROR: genuine original vendor neural-paged XSim marker missing: $pattern" >&2
    exit 1
  }
done
# Stage 4: Same real original AMD SmartConnect, now through the full
# eight-slot/2048B RTL LRU physical state-cache candidate with page9+
# eviction and observed dirty writeback/reload. NOT a neural HLS run.
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
  work.tb_m06_original_vendor_lru8 work.glbl \
  -s m06_original_vendor_lru8_snapshot \
  2>&1 | tee "$OUT/10_lru8_xelab.log"
timeout --signal=TERM 360s xsim m06_original_vendor_lru8_snapshot -R \
  --onfinish quit 2>&1 | tee "$OUT/11_lru8_xsim.log"
if grep -Eq 'M06_VENDOR_LRU8_FAIL|FATAL_ERROR|Fatal: ' "$OUT/11_lru8_xsim.log"; then
  echo "ERROR: original vendor LRU8 RTL simulation reported a fatal failure" >&2
  exit 1
fi
for pattern in "M06_ORIGINAL_VENDOR_LRU8_RTL_PASS" \
               "M06_ORIGINAL_VENDOR_LRU8_FAULT_PASS"; do
  grep -Fq "$pattern" "$OUT/11_lru8_xsim.log" || {
    echo "ERROR: genuine original vendor eight-slot XSim marker missing: $pattern" >&2
    exit 1
  }
done
# Stage 5: address the FULL 4096-neuron 64KiB canonical image in
# original AMD SmartConnect from scratch, with both bounded AXI roles:
# block255 is the highest legal page and block256 is invalid. Scratch
# BFM parameter ONLY; original 2025.2 IP and prior evidence immutable.
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
  work.tb_m06_original_vendor_4096 work.glbl \
  -s m06_original_vendor_4096_snapshot \
  2>&1 | tee "$OUT/12_4096_xelab.log"
timeout --signal=TERM 360s xsim m06_original_vendor_4096_snapshot -R \
  --onfinish quit 2>&1 | tee "$OUT/13_4096_xsim.log"
if grep -Eq 'M06_VENDOR_4096_FAIL|FATAL_ERROR|Fatal: ' "$OUT/13_4096_xsim.log"; then
  echo "ERROR: original vendor 4096-neuron canonical address simulation failed" >&2
  exit 1
fi
for pattern in "M06_ORIGINAL_VENDOR_4096_RANGE_PASS" \
               "M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS"; do
  grep -Fq "$pattern" "$OUT/13_4096_xsim.log" || {
    echo "ERROR: full 4096-neuron canonical original-vendor marker missing: $pattern" >&2
    exit 1
  }
done
echo "PASS: all FIVE original AMD SmartConnect XSim stages incl 4096-neuron 64KiB canonical high-page bound. NO original M05 HLS RTL instantiated; NO actual DDR/board."
