#!/usr/bin/env bash
# M06 G3 FIRST genuine CONNECTED AMD WIDTH CONVERTER + ORIGINAL SmartConnect
# XSim trial. Independent 32-bit AXI BFM, NOT generated neural HLS yet.
# All original AMD D3, DWC IP and compile-order owner sources READ ONLY.
# NO board, bitstream, JTAG, DDR reservation, device programming or M07.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if (( $# != 5 )); then
  echo "Usage: bash scripts/run_m06_g3_real_dwc_original_sc_xsim.sh <D3> <02_original_mem_sc_ports.txt> <08_header.json> <successful DWC owner> <successful DWC compile-order evidence>" >&2
  exit 2
fi
D3="$(realpath -e -- "$1")"
PORTS="$(realpath -e -- "$2")"
HEADERS="$(realpath -e -- "$3")"
DW="$(realpath -e -- "$4")"
EX="$(realpath -e -- "$5")"
if [[ "$(basename "$D3")" != "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ" ||
      "$(basename "$PORTS")" != "02_original_mem_sc_ports.txt" ||
      "$(basename "$HEADERS")" != "08_mem_sc_wrapper_headers_nonansi_fixed.json" ||
      "$(basename "$DW")" != m06_g3_real_amd_dwc_* ||
      "$(basename "$EX")" != m06_g3_amd_sim_export_* ]]; then
  echo "ERROR: only exact original owner D3, real dual AMD DWC and measured SIM source evidence allowed" >&2
  exit 2
fi
for app in git python3 xvlog xvhdl xelab xsim timeout sha256sum cmp grep tee realpath; do
  command -v "$app" >/dev/null || {
    echo "ERROR: missing $app; source original Vivado 2025.2/Vivado/settings64.sh" >&2
    exit 2
  }
done
xvlog -version 2>&1 | grep -q "2025.2" || {
  echo "ERROR: must use ORIGINAL AMD Vivado 2025.2" >&2
  exit 2
}
[[ -n "${XILINX_VIVADO:-}" ]] || {
  echo "ERROR: source Vivado 2025.2 settings64.sh (XILINX_VIVADO missing)" >&2
  exit 2
}
GLBL="$(realpath -e -- "$XILINX_VIVADO/data/verilog/src/glbl.v")"
grep -Eq '^[[:space:]]*module[[:space:]]+glbl([[:space:](;]|$)' "$GLBL" || {
  echo "ERROR: original Vivado glbl module missing" >&2
  exit 2
}
[[ "$(cat "$EX/result.txt")" == "exit_status=0" ]] || {
  echo "ERROR: saved original AMD compile-order evidence was NOT PASS" >&2
  exit 2
}
mkdir -p "$HOME/Thesis_Evidence"
OUT="$(mktemp -d "$HOME/Thesis_Evidence/m06_g3_real_dwc_original_sc_xsim_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
finish() {
  rc="$?"
  trap - EXIT
  cd "$ROOT" || rc=3
  sha256sum scripts/m06_g3_generate_real_dwc_original_sc_bfm.py \
    scripts/m06_g3_merge_vendor_sources.py \
    scripts/m06_g3_axi_trace_audit.py \
    scripts/run_m06_g3_real_dwc_original_sc_xsim.sh \
    rtl/m06/m06_axi128_scratch_mem.sv > "$OUT/source_after_sha256.txt" || rc=3
  cmp -s "$OUT/source_before_sha256.txt" "$OUT/source_after_sha256.txt" || {
    echo "FATAL: M06 connected original vendor test source SHA changed" >&2
    rc=3
  }
  if [[ -s "$OUT/03_connected_vendor_compile_plan.json" ]]; then
    python3 - "$OUT/03_connected_vendor_compile_plan.json" "$OUT/vendor_sha_after.txt" <<'PY'
import hashlib,json,sys
from pathlib import Path
plan=json.loads(Path(sys.argv[1]).read_text())
paths=plan["verilog_files"]+plan["vhdl_files"]
with open(sys.argv[2],"w") as out:
    for text in paths:
        p=Path(text)
        if not p.is_file():
            raise SystemExit("missing protected original vendor RTL: "+text)
        out.write(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+text+"\n")
PY
    cmp -s "$OUT/vendor_sha_before.txt" "$OUT/vendor_sha_after.txt" || {
      echo "FATAL: original vendor D3/DWC HDL SHA changed" >&2
      rc=3
    }
  fi
  sha256sum -c "$DW/04_real_amd_dwc_xci_sha256.txt" \
    > "$OUT/original_xci_after_sha_check.txt" 2>&1 || rc=3
  printf 'exit_status=%s\n' "$rc" > "$OUT/result.txt"
  echo "M06 REAL combined original AMD XSim owner evidence: $OUT"
  echo "M06 REAL combined DWC->original SmartConnect XSim exit: $rc"
  exit "$rc"
}
trap finish EXIT
cd "$ROOT"
git rev-parse HEAD > "$OUT/commit.txt"
git status --porcelain=v1 > "$OUT/worktree_status.txt"
printf '%s\n' "$D3" > "$OUT/original_d3_folder.txt"
printf '%s\n' "$DW" > "$OUT/original_dwc_folder.txt"
printf '%s\n' "$EX" > "$OUT/original_dwc_compile_order_folder.txt"
sha256sum scripts/m06_g3_generate_real_dwc_original_sc_bfm.py \
  scripts/m06_g3_merge_vendor_sources.py \
  scripts/m06_g3_axi_trace_audit.py \
  scripts/run_m06_g3_real_dwc_original_sc_xsim.sh \
  rtl/m06/m06_axi128_scratch_mem.sv > "$OUT/source_before_sha256.txt"

# Prove on owner's machine that earlier original Vivado D3 and DWC
# evidence is genuine and no previously accepted vendor source is changed.
python3 scripts/m06_g3_amd_dwc_evidence_audit.py \
  --evidence "$DW" --output "$OUT/00_reaudit_real_amd_dwc.json"
python3 scripts/m06_g3_real_amd_compile_order_audit.py \
  --compile-order "$EX/02_genuine_dwc_sim_compile_order.tsv" \
  --owner-dwc "$DW" --output "$OUT/01_reaudit_dwc_sim_sources.json" \
  --paths-output "$OUT/01_reaudit_dwc_sim_paths.txt"
cmp "$OUT/01_reaudit_dwc_sim_sources.json" "$EX/06_amd_sim_compile_order_audit.json"

python3 scripts/m06_generate_original_mem_sc_bfm.py \
  --original "$D3" --headers "$HEADERS" \
  --output "$OUT/00_original_vendor_contract_syntax_tb.sv"
python3 scripts/m06_vendor_compile_plan.py \
  --original "$D3" --report "$PORTS" \
  --output "$OUT/02_original_sc_compile_plan.json"
python3 scripts/m06_g3_merge_vendor_sources.py \
  --d3-plan "$OUT/02_original_sc_compile_plan.json" \
  --dwc-audit "$OUT/01_reaudit_dwc_sim_sources.json" \
  --output "$OUT/03_connected_vendor_compile_plan.json"
python3 scripts/m06_g3_generate_real_dwc_original_sc_bfm.py \
  --original-d3 "$D3" --original-headers "$HEADERS" \
  --original-dwc "$DW" --output "$OUT/tb_m06_g3_real_dwc_original_sc.sv"
sha256sum "$OUT/tb_m06_g3_real_dwc_original_sc.sv" \
  > "$OUT/generated_bfm_sha256.txt"

python3 - "$OUT/03_connected_vendor_compile_plan.json" "$OUT" <<'PY'
import hashlib,json,sys
from pathlib import Path
plan=json.loads(Path(sys.argv[1]).read_text())
out=Path(sys.argv[2])
for key,name in (("verilog_files","verilog_sources.txt"),
                 ("vhdl_files","vhdl_sources.txt"),
                 ("include_directories","include_dirs.txt")):
    (out/name).write_text("\n".join(plan[key])+"\n")
with (out/"vendor_sha_before.txt").open("w") as stream:
    for text in plan["verilog_files"]+plan["vhdl_files"]:
        path=Path(text)
        stream.write(hashlib.sha256(path.read_bytes()).hexdigest()+
                     "  "+text+"\n")
print("M06 G3 original IP compile plan:",len(plan["verilog_files"]),
      "Verilog, ",len(plan["vhdl_files"]),"VHDL, ",
      len(plan["deduplicated_same_name_same_sha"]),"verified AMD source duplicates")
PY
mapfile -t VLOG < "$OUT/verilog_sources.txt"
mapfile -t VHDL < "$OUT/vhdl_sources.txt"
mapfile -t INCLUDES < "$OUT/include_dirs.txt"
FLAGS=()
for dir in "${INCLUDES[@]}"; do
  [[ -d "$dir" ]] || { echo "ERROR: original vendor include missing: $dir" >&2; exit 2; }
  FLAGS+=(-i "$dir")
done
cd "$OUT"
if (( ${#VHDL[@]} > 0 )); then
  xvhdl -2008 "${VHDL[@]}" 2>&1 | tee "$OUT/04_xvhdl.log"
fi
xvlog --relax -sv "${FLAGS[@]}" -i "$OUT" "${VLOG[@]}" \
  "$ROOT/rtl/m06/m06_axi128_scratch_mem.sv" \
  "$OUT/tb_m06_g3_real_dwc_original_sc.sv" \
  "$GLBL" 2>&1 | tee "$OUT/05_xvlog.log"
xelab --relax -debug typical -L xpm -L unisims_ver -L secureip \
  work.tb_m06_g3_real_dwc_original_sc work.glbl \
  -s m06_g3_real_dwc_original_sc_snapshot \
  2>&1 | tee "$OUT/06_xelab.log"
# Genuine XSim may exit 0 after $fatal. Preserve logs on either status.
if timeout --signal=TERM 600s xsim m06_g3_real_dwc_original_sc_snapshot \
  -R --onfinish quit 2>&1 | tee "$OUT/07_xsim.log"; then
  sim_rc=0
else
  sim_rc=$?
fi
python3 "$ROOT/scripts/m06_g3_axi_trace_audit.py" \
  --xsim-log "$OUT/07_xsim.log" \
  --trace-output "$OUT/08_axi_handshake_trace.log" \
  --summary-output "$OUT/09_axi_probe_summary.json"
if (( sim_rc != 0 )); then
  echo "ERROR: genuine XSim nonzero exit: $sim_rc" >&2
  exit 1
fi
if grep -Eq "M06_G3_REAL_DWC_SC_FAIL|FATAL_ERROR|Fatal: " "$OUT/07_xsim.log"; then
  echo "ERROR: actual original AMD connected converter/smartconnect RTL failure" >&2
  exit 1
fi
grep -Fq "M06_G3_REAL_DWC_ORIGINAL_SC_32TO256_XSIM_PASS" "$OUT/07_xsim.log" || {
  echo "ERROR: original combined vendor XSim PASS marker absent" >&2
  exit 1
}
echo "M06 G3 REAL 2x AMD DWC->ORIGINAL AMD SmartConnect->64KiB SCRATCH XSim PASS; BFM ONLY NO GENERATED HLS, NO BOARD/REAL DDR"
