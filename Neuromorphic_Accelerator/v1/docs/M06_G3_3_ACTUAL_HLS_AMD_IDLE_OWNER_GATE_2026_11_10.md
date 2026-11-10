# M06 G3.3.1 — Actual HLS + original AMD connected IDLE XSim owner gate (2026-11-10)

**Status:** Original genuine AMD G3.2 connected 10-read/3-write BFM PASS remains ACCEPTED; G3.3 prior read-only actual HLS inventory from user ZIP M06_G3_3_REAL_HLS_INVENTORY_REVIEW_20261110T061549Z.zip **PASS**, `result.txt=exit_status=0`, at original commit 98980a4545b836d90db7bfba3c6574dae9c13489. This is not an error: worktree `??` logs/evidence are untracked, not failed tests, and `g3_3_complete=false` is the correct strict acceptance boundary. Do not delete prior evidence or rerun G1/G2/G3.2/inventory.

## What the genuine inventory measured

Actual generated HLS `m06_paged_rolling_replay` has exactly 125 top-level ports and **40 Verilog source files**, including 7-bit AXI-Lite control address; neural input streams `neurons_TDATA[127:0]`, `synapses_TDATA[191:0]`, `external_events_TDATA[127:0]`; `trace_TDATA[191:0]` and `metrics_TDATA[255:0]` output streams. HLS read and write bundles each expose 32-bit AXI data and 64-bit AXI addresses and full HLS sidebands; original DWC input SI has 32-bit data and 32-bit address, original D3 SmartConnect S00 (READ_ONLY) and S03 (WRITE_ONLY) are 256-bit with 32-bit addresses. The generated HLS ARLOCK/AWLOCK is **2 bits**, original DWC SI lock **1 bit**; ID and USER/REGION sidebands require explicit handling.

## Source-only development, not yet owner genuine XSim

New `scripts/m06_g3_3_generate_actual_hls_idle_tb.py` requires the accepted inventory to EXACTLY match the 40 real HLS file hashes, all 125 generated HLS pin directions/widths, real original D3 96-port SHA-audited wrapper, two actual SHA-audited AMD converter SIM wrapper ABIs. It produces a testbench instantiating the **actual generated HLS RTL**, `m06_axi64_to32_read_guard` and `m06_axi64_to32_write_guard`, the **two genuine AMD 32→256 width converters**, **original** D3 SmartConnect, and one 64KiB simulated 128b RAM. All 125 HLS top pins connect by exact name. The non-target generated HLS AXI channels are tied to explicitly inactive responses, AXI-Lite and input streams have `VALID=0` and `ap_start=0`. The original vendor role-only bindings are preserved. Active HLS requests with unsupported two-bit LOCK, REGION, USER, WID, wrong-master-direction fail closed rather than silently truncating. The test holds HLS in RESET then IDLE 100 cycles; success checks real RTL elaboration + idle integration ONLY; **no actual HLS processing is started**. It is **G3.3.1**, not G3.3 functional completion/G4.

New `scripts/run_m06_g3_3_actual_hls_idle_xsim.py` reads original prior G3.3 owner inventory folder directly (no second inventory/G1/G2), validates source owner identity + accepted genuine G3.2 ZIP, snapshots local source and the 40 actual HLS and 67 vendor HDL hashes, uses previously verified original DWC compile-order and D3 plan, generates one fresh TB, compiles and elaborates via genuine Vivado 2025.2 tools, runs genuine XSim IDLE smoke, fail-closes on nonzero XSim or Fatal/FAIL marker, preserves logs/ZIP input provenance on pass and failure, hashes all original sources afterward, and rechecks original `.xci` files. No original HLS RTL or AMD HDL copied/modified. **THIS HAS NOT BEEN RUN WITH ACTUAL ORIGINAL VIVADO ON OWNER YET**.

`tests/test_m06_g3_3_actual_hls_idle_link.py` checks all original HLS/AMD/guard module binding names and negative source ABI drift and actual HLS SHA change, with an actual Icarus `-tnull` syntax test against labelled synthetic HLS/vendor declarations and the REAL candidate guard+RAM RTL; no fake-IP `vvp` functional sim, no false vendor claim. M06 CI requires this syntax test after installing Icarus.

## Exact local VS Code commands

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_g3_3_actual_hls_idle_link.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v

source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
xvlog -version

export HLS="$HOME/Thesis_Evidence/m06_paged_rolling_hls_cosim_20261110T022111Z_iMNors"
export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
export DW="$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3"
export EX="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_amd_sim_export_*' | sort | tail -n 1)"
export INV="$HOME/Thesis_Evidence/m06_g3_3_hls_source_inventory_20261110T061525Z_qbrHKZ"
export INVOCATION_LOG="$HOME/Thesis_Evidence/m06_g3_3_actual_hls_idle_invocation_$(date -u +%Y%m%dT%H%M%SZ).log"
set -o pipefail
if python3 scripts/run_m06_g3_3_actual_hls_idle_xsim.py \
  --hls-cosim "$HLS" --original-d3 "$D3" \
  --original-report "$PORTS/02_original_mem_sc_ports.txt" \
  --original-headers "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" \
  --original-dwc "$DW" --amd-export "$EX" \
  --accepted-inventory "$INV" 2>&1 | tee "$INVOCATION_LOG"; then
  echo "G3.3.1 TRUE HLS+AMD IDLE verification completed"
else
  echo "G3.3.1 owner run FAILED; retain FIRST evidence"
fi
export LINK="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_3_actual_hls_idle_xsim_*' | sort | tail -n 1)"
echo "New evidence directory: $LINK"
test -d "$LINK" && cat "$LINK/result.txt" "$LINK/commit.txt"
test -f "$LINK/07_xsim.log" && tail -n 50 "$LINK/07_xsim.log"
test -f "$LINK/owner_error.txt" && cat "$LINK/owner_error.txt"
~~~

The genuine XSim IDLE-only marker if successful is `M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS 40_REAL_HLS_RTL 2_REAL_AMD_DWC ORIGINAL_SC 64K_SCRATCH GUARDS_CONNECTED NO_START_NO_NEURAL_NO_DDR_NO_BOARD`, plus `result.txt=exit_status=0` and before/after matched hashes. On actual failure, do not alter original HLS/IP or repeat the identical experiment; package the first-failure evidence.

## Mandatory single owner evidence ZIP

Package new `$LINK` folder with Python `zipfile` allowlisted paths only: `result.txt`, `commit.txt`, `worktree_status.txt`, `owner_error.txt`, `00_accepted_hls_interface_inventory.json`, `01_reaudit_dwc_owner.log`, `01_reaudit_dwc_sim_sources.json`, `01_reaudit_dwc_sim_paths.txt`, `02_vendor_plan.log`, `02_original_sc_compile_plan.json`, `03_merge_plan.log`, `03_connected_vendor_compile_plan.json`, `03_generation.log`, `04_xvhdl.log`, `05_xvlog.log`, `06_xelab.log`, `07_xsim.log`, `tb_m06_g3_3_actual_hls_original_amd_idle.sv`, `generated_hls_link_tb_sha256.txt`, `source_before_sha256.txt`, `source_after_sha256.txt`, `hls_sources_before_sha256.txt`, `hls_sources_after_sha256.txt`, `vendor_sha_before.txt`, `vendor_sha_after.txt`, `original_xci_after_sha_check.txt`, `verilog_sources.txt`, `vhdl_sources.txt`, `hls_sources.txt`, `include_dirs.txt`, `original_hls_folder.txt`, `original_d3_folder.txt`, `original_dwc_folder.txt`, `original_dwc_compile_order_folder.txt`, `original_g3_3_inventory_folder.txt`, `original_g3_2_zip_path.txt`, and `$INVOCATION_LOG` as `08_operator_invocation_console.log`. The exact copy-paste ZIP packager is in chat. **Do NOT include original AMD proprietary source RTL or original HLS-generated Verilog content.** Name `M06_G3_3_ACTUAL_HLS_AMD_IDLE_REVIEW_<timestamp>.zip`. On failure, include only files that exist; keep exact first-error logs.

## Gates still open after G3.3.1 idle PASS

G3.3.2: drive actual AXI-Lite start, actual five AXI streams, real HLS memory transaction, and cross-master B ack→AR; compare independent M02/M03 expected complete canonical state, event/spike trace. G4 negative: stale/evicted pages, read/write faults, timeouts, FIFO stalls, sticky quarantine, uncertain partial write and recovery with genuine original AMD. M06 closeout requires owner review and independent correctness; original G1/G2/G3.2 remain accepted, never conflate. PR #80 stays draft/unmerged, no board/DDR/JTAG/M07 without explicit authorization.
