> **NEWEST 2026-11-10: SOURCE-READY G3.2 FIXED-SCRATCH ORIGINAL AMD XSim REGRESSION NEEDED.** The uploaded genuine owner handshake archive `M06_G3_2_DEBUG_REVIEW_20261110T052354Z.zip` proves the original first read was rejected in our 128-bit simulation-only RAM (`rd_bad_request=1` after genuine original AMD SI32→MI256→SC M00 ARSIZE2 propagation). A new scratch-only aligned narrow AXI INCR fix and real independent Icarus regression tests are staged; vendor IP, user driver, historical evidence and M05 HLS untouched. **NO new actual AMD XSim after the fix.** Perform ONE new run from the updated M06 branch exactly as this runbook describes; expect 10 read/3 write PASS marker if no additional issues, otherwise preserve FIRST new failure and return ONE ZIP with `07_xsim.log`, `08_axi_handshake_trace.log`, `09_axi_probe_summary.json`, generated TB, before/after SHA/source logs. G3.2 stays open until owner genuine PASS; G3.3/G4 blocked pending review, no board/JTAG/DDR/merge/M07.

> **LATEST SOURCE-ONLY G3.2 DECERR DIAGNOSTIC INCREMENT — OWNER XSim PENDING (2026-11-09):** The first actual original AMD connected Vivado 2025.2 run still FAILED (first address 0, RRESP=11, no established origin). The original `ARSIZE=2` first 32-bit read, restrictive simulation-only 128-bit RAM, BOTH original AMD width converters, original D3 SmartConnect and all accepted G1/G2 evidence are UNCHANGED. Newly generated **passive** bounded AR/R/AW/W/B probes observe 32-bit SI, 256-bit converter MI/original S00/S03, and original 128-bit M00/RAM (M00/RAM is ONE shared physical interface); first R/B VALID is observed even if READY=0, before the existing $fatal. Monitors report ARADDR/ARSIZE/ARLEN/ARBURST/cache/ID where present, response/last/data, accepted handshake counters, and RAM `rd_bad_request`, with one first-DECERR-sighting marker. `scripts/m06_g3_axi_trace_audit.py` extracts `08_axi_handshake_trace.log` and `09_axi_probe_summary.json` from genuine `07_xsim.log` on success OR failure; `root_cause_proven=false` until manual original-model evidence review. Positive/negative synthetic source regressions added. This does **not** fix G3.2, and no original vendor/owner XSim has been run against this increment yet. **NEXT:** ONE fresh owner XSim diagnostic, ONE ZIP with raw logs/trace/summary and preserved SHA attestations; **do not alter RAM/functionality until that result is examined.** G3.3/G4 remain OPEN. PR #80 DRAFT/UNMERGED; no physical board/DDR/JTAG or M07.

## Current G3.2 follow-up: passive DECERR tracing (owner-only)

**Diagnostic ONLY**: on unchanged first `read32('h0000)`, the source emits `M06_G3_AXI_TRACE` per accepted AR/R/AW/W/B handshake, plus `R_OBS/B_OBS` on first VALID even when READY=0. `M06_G3_AXI_FIRST_DECERR` means *first observed error*, not guaranteed generating component. The owner runner stores all trace lines in `08_axi_handshake_trace.log` and a conservative, non-acceptance parser summary in `09_axi_probe_summary.json`; in FAIL cases, no positive acceptance marker is expected. Original failed owner run under `~/Thesis_Evidence/m06_g3_real_dwc_original_sc_xsim_20261110T044432Z_1FrIEZ` stays immutable. New runs use a fresh directory.

Copy-paste after current branch pull, from `~/Git/Thesis/Neuromorphic_Accelerator/v1`:

```bash
python3 -m compileall -q src scripts tests
bash -n scripts/run_m06_g3_real_dwc_original_sc_xsim.sh
python3 -m unittest discover -s tests -p 'test_m06_g3_axi_probe.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g3_generate_real_dwc_original_sc_bfm.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g3_merge_vendor_sources.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
xvlog -version
export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
export DW="$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3"
export EX="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_amd_sim_export_*' | sort | tail -n 1)"
test "$(cat "$EX/result.txt")" = 'exit_status=0' || { echo 'Original genuine AMD DWC source evidence not accepted'; exit 2; }
bash scripts/run_m06_g3_real_dwc_original_sc_xsim.sh "$D3" \
  "$PORTS/02_original_mem_sc_ports.txt" \
  "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" "$DW" "$EX"
echo "G3.2 diagnosis exit: $?"
export LINK="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_real_dwc_original_sc_xsim_*' | sort | tail -n 1)"
echo "G3.2 diagnosis files: $LINK"
cat "$LINK/result.txt" "$LINK/commit.txt"
test -f "$LINK/08_axi_handshake_trace.log" && tail -n 80 "$LINK/08_axi_handshake_trace.log"
test -f "$LINK/09_axi_probe_summary.json" && cat "$LINK/09_axi_probe_summary.json"
```

Use the SINGLE ZIP packager specified in `M06_G3_2_DECERR_DIAGNOSIS_NEXT_CHAT_HANDOFF_2026_11_09.md` §5. It explicitly includes generated BFM, compilation logs, 08/09 probes, before/after vendor and source SHA, original provenance directories, result and commit. It accepts missing files if any stage fails before producing them; send only the one resulting `~/Thesis_Evidence/M06_G3_2_DEBUG_REVIEW_*.zip`. Do not upload AMD proprietary HDL/XCI and do not rerun unchanged accepted G1/G2.

> **CURRENT AFTER OWNER RUN 2026-11-09 21:45 MST — THE G3.2 TEST BELOW ACTUALLY FAILED.** The user ran the exact owner genuine Vivado/XSim command at 286e2257044d63a29ce745eab9fea2f1eaa27aca, submitted the full M06_G3_REAL_DWC_SC_XSIM_REVIEW_20261110T044546Z.zip. Original vivado xvhdl/xvlog/xelab complete successfully but FIRST read 0x0 returns AXI DECERR=11 (RDATA0 versus expected 0x382b1e11) 755ns; result.txt=exit_status=1. Original vendor and local source SHA manifests MATCH. This does not disprove G1/G2 or genuine converter-generation component passes; it blocks G3.2 acceptance. **Do NOT follow the old unconditional rerun commands below on unchanged source**. FIRST next action: instrument valid/ready AR/R across converter SI, MI/SC S00, SC M00, RAM, determine narrow ARSIZE versus strict M00 scratch size4 source and trace DECERR origin. See [NEW AUTHORITATIVE diagnostic fix plan, latest owner paths, exact tests and one-ZIP packaging](M06_G3_2_DECERR_DIAGNOSIS_NEXT_CHAT_HANDOFF_2026_11_09.md). No implementation change has yet been made. No original AMD IP edits or board.

# M06 G3.2 owner trial: REAL AMD width converters + ORIGINAL SmartConnect shared 64KiB XSim

Date 2026-11-09 America/Denver; continuing PR #80 on agent/neuromorphic-accelerator-v1-m06-ddr-residency. **Not M06 closeout yet.** No board/JTAG/bitstream/PS DDR, no HLS generated neural core wired into this first G3.2 test, no original AMD D3 IP files modified, no merge/M07.

## Latest genuine owner archive: correct, PASS at its measured scope

Owner upload `M06_G3_REAL_AMD_SIM_SOURCE_REVIEW_20261110T041140Z.zip` (13 files), original commit `4b0929c7b1cc994045fd100ebe2e407d058f3e19`:
- `result.txt=exit_status=0`; original source_before SHA == source_after SHA, and XCI before/after checks byte-identical.
- Two distinct official AMD 2025.2 `axi_dwidth_converter` SIM wrapper modules: `m06_g3_read_dwc` 36 ports, `m06_g3_write_dwc` 42 ports. 32-bit SI/256-bit MI, 32-bit addresses; SI_ID width 1, no original SmartConnect SI ID ports.
- `02_genuine_dwc_sim_compile_order.tsv` lists **13 genuine owner Vivado source dependencies for EACH** converter: Verilog, one VHDL, authentic `axi_infrastructure_v1_1_0.vh`, exact generated `sim/m06_g3_read_dwc.v` and `sim/m06_g3_write_dwc.v`.
- `06_amd_sim_compile_order_audit.json` is PASS as `REAL_AMD_XSIM_SOURCES_RECORDED_NOT_EXPORTED_NOT_COMPILED`; source SHA authentic by previous original owner's local auditor. The first 12 library source SHA are **identical** between READ and WRITE, while the final wrapper module SHA differs. The actual 2025.2 tool successfully read source paths and wrapper pin metadata; no vendor XSim ran in this step. Board part warnings and locked original project are background.
- Original accepted A-E SmartConnect vendor functional XSim and corrected HLS C/RTL cosim independent PASS remain accepted at those component-only scopes. No new physical DDR evidence.

## New engineering increment: first REAL vendor converter + ORIGINAL SmartConnect connected XSim

New `scripts/m06_g3_generate_real_dwc_original_sc_bfm.py` verifies the original D3 wrapper SHA/source and the REAL AMD owner-generated 36/42 port ABI (not synthetic guesses), then generates a single XSim testbench:
`tb_m06_g3_real_dwc_original_sc`:

    independent 32-bit AXI4 read/write BFM
        | 64KiB bounded RAW 32-bit byte address (not 64-bit HLS yet)
       m06_g3_read_dwc + m06_g3_write_dwc (actual Vivado 2025.2 SIM IP)
        | 256-bit AXI4 MI (2 separate channels, no actual SmartConnect ID ports)
       ORIGINAL immutable AMD SmartConnect S00 read + S03 write
        | original M00 128-bit AXI
       m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536)) [simulated bytes, not PS DDR]

S01/S02 are explicitly idle-tied, all original 96 AXI wrapper ports are bound. Actual generated DWC REGION (no original S00/S03 equivalent) output safely unconnected, *only* for this known 4-bit output. Testbench drives `ARCACHE/AWCACHE=4'b0011` and AXI LEN0/SIZE2 INCR for single 4-byte words. Self-check tests 4-byte reads at 0x0, 0x0FFC and 0x1000 separately, plus last legal word 0xFFFC (=bytes 65532–65535 / neuron 4095), three writes across high page and 4KiB neighborhood with sparse `WSTRB=4'b0101`, TEN reads and THREE writes, deliberate R/B backpressure, AXI ID and RLAST/BRESP, independent expected byte-image formula `(13*addr+17)&255`, no unwanted neighbor edits and real M00 AR/R/AW/W/B traffic counters. Each read follows completion of the previous write B response. This does not assert standalone cross-master asynchronous coherency or synthesized HLS B→AR ordering. Tested candidate source with Icarus **FAKE stub SYNTAX ONLY, never run against fake vendor functionality**; genuine AMD IP simulation remains owner-only.

New `scripts/m06_g3_merge_vendor_sources.py`: receives unchanged original D3 `m06_vendor_compile_plan.py` output and genuine owner `m06_g3_real_amd_compile_order_audit.py` output; merges exact real source lists, retains VHDL/Verilog/headers/include dirs, deduplicates identical AMD library names ONLY if SHA matches, rejects unexpected same-name/different-SHA collision, missing/displaced owner source/role/wrapper, and leaves original vendor RTL unchanged. It does not silently overwrite earlier source/IP libraries.

New `scripts/run_m06_g3_real_dwc_original_sc_xsim.sh`: unique independent owner evidence directory `~/Thesis_Evidence/m06_g3_real_dwc_original_sc_xsim_*`, live independent owner DWC XCI and source re-audit, exact original 96-port SmartConnect SHA, fresh testbench, merged original and genuine DWC source SHA digests before/after. Compiles original full vendor graphs with genuine `xvhdl`, `xvlog` and authenticated installed `glbl.v`; elaborates original real vendor + genuine converter testbench and runs `xsim` with 600s timeout, checks `M06_G3_REAL_DWC_ORIGINAL_SC_32TO256_XSIM_PASS` marker. Any error (source collision, compile issue, payload mismatch) is a **genuine FAILED** owner trial, not a PASS. NEVER runs M06 HLS and never opens Vivado IDE/physical device.

New `tests/test_m06_g3_generate_real_dwc_original_sc_bfm.py`: five positive/negative source-only tests, full measured 36/42 pin orientation, swapped mode, altered/missing SI/MI pins, check generated TB shared 64K/4K/high page/WSTRB and actual Icarus **syntax check** with clearly marked FAKE (never simulated) DWC and original SC stubs. M06 CI installs Icarus then requires this syntax test. `tests/test_m06_g3_merge_vendor_sources.py`: five positive/negative synthetic source-collision, missing/modified/out-of-root, false-status checks. CI DOES NOT simulate original vendor models.

This is G3.2 (two genuine DWC + original SC via 32b BFM). It is a real end-to-end **memory-path** trial but still NOT the full corrected generated-HLS neural core; G3.3 needs guard, actual generated HLS and full neural streams with independent oracle and G4 needs full state/fault containment.

## Exact next owner terminal commands

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
bash -n scripts/run_m06_g3_real_dwc_original_sc_xsim.sh
python3 -m unittest discover -s tests -p 'test_m06_g3_generate_real_dwc_original_sc_bfm.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g3_merge_vendor_sources.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v

source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
xvlog -version
export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
export DW="$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3"
export EX="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_amd_sim_export_*' | sort | tail -n 1)"
echo "Confirmed ORIGINAL AMD SIM source evidence: $EX"
cat "$EX/result.txt"
bash scripts/run_m06_g3_real_dwc_original_sc_xsim.sh \
  "$D3" "$PORTS/02_original_mem_sc_ports.txt" \
  "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" \
  "$DW" "$EX"
echo "M06 G3.2 genuine combined AMD converter+SmartConnect XSim exit: $?"

export LINK="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_real_dwc_original_sc_xsim_*' | sort | tail -n 1)"
echo "New G3.2 original AMD combined evidence: $LINK"
cat "$LINK/result.txt" "$LINK/commit.txt"
test -f "$LINK/07_xsim.log" && tail -n 35 "$LINK/07_xsim.log"
```

If `EX/result.txt` is not exit_status=0, STOP: do not substitute old failed metadata. If genuine XSim fails, archive the new `$LINK` evidence **once**, do not rerun before analyzing first ERROR. Do not modify D3, DWC or HLS originals. New common-module source collision fail-closed is possible and will need analysis of that original vendor filename/hashes, not blindly choose a duplicate.

## Exactly which files to upload next

**ONE ZIP**: `~/Thesis_Evidence/M06_G3_REAL_DWC_SC_XSIM_REVIEW_<timestamp>.zip`. Include these **15** files when present, all inside the new `$LINK` folder:

1. `result.txt`
2. `commit.txt`
3. `03_connected_vendor_compile_plan.json`
4. `generated_bfm_sha256.txt`
5. `tb_m06_g3_real_dwc_original_sc.sv` — our new BFM only; no proprietary vendor IP source
6. `04_xvhdl.log` (if selected)
7. `05_xvlog.log`
8. `06_xelab.log`
9. `07_xsim.log`
10. `00_reaudit_real_amd_dwc.json`
11. `01_reaudit_dwc_sim_sources.json`
12. `vendor_sha_before.txt`
13. `vendor_sha_after.txt`
14. `source_before_sha256.txt`
15. `source_after_sha256.txt`

On a FAILED stage, collect whichever files exist, including `02_original_sc_compile_plan.json` if the preflight failed before merged compilation. No need to upload 64KiB memory array, original .xci, proprietary vendor RTL or rerun earlier accepted simulations. Future G3.3 still MUST be connected to real HLS before M06 can close.
