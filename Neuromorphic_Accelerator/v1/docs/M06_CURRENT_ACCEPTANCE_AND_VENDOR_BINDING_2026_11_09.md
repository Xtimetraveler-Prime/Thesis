> **CURRENT INTEGRATION UPDATE 2026-11-09:** Genuine original XSim attempt reached xvlog and failed because original AXI `axi_infrastructure_v1_1_0.vh` was omitted by our runner's compile-source filter. A new 186-source manifest-based original include plan fixes it. The synthesis-oriented RTL page DMA bridge now interconnects the residency FSM and single-beat 256b SI0-read/SI3-write bus, verifying byte-exact dirty eviction/reload and poison against an independent memory BFM in real Icarus RTL. The current vendor runner tests both direct original SmartConnect and the same original vendor core coupled to that paged RTL. `116` new M06 Python tests PASS, all integrated/mock RTL checks PASS, **genuine vendor XSim STILL NOT VERIFIED**. [LATEST bounded hardware-integration gate and operator commands](M06_AXI_HEADER_AND_PAGED_VENDOR_HANDOFF_2026_11_09.md). Prior earlier-page content is historical, not final status.

# M06 current acceptance position — original Vivado source accepted, real IP transaction test still open

**2026-11-09; branch `agent/neuromorphic-accelerator-v1-m06-ddr-residency`; draft PR #80 open/unmerged.** This report supersedes prior "original port capture unavailable" statements in older runbooks. No new M06 submilestones and no repetitive SmartConnect warning inventory.

## Actual original Vivado evidence now provided

Owner supplied four authentic reports from accepted original D3 XPR/BD at `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ`, including `02_original_mem_sc_ports.txt`, `03_vivado_readonly.log`, `05_sim_bfm_contract_summary_reaudited.json`, and `06_original_mem_sc_wrapper_headers.json`. The independent offline re-audit returned **exit code 0** with **186 original simulation files** and two module declarations for `m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0`. The old original runner's `result.txt` stays **exit_status=2** (do not rewrite); original Vivado itself reached the standalone completion marker. The old `05_audit.log` was empty, so its original fatal reason was not independently logged. The corrected audit was successful; this DOES NOT mean vendor AXI simulation ran.

From genuine original BD: S00, S01, S02 are 256-bit READ_ONLY; S03 256-bit WRITE_ONLY; M00 128-bit READ_WRITE. SI ID/USER width=0, SI `CONFIG.MAX_BURST_LENGTH=16` and `HAS_BURST=0`; MI `MAX_BURST_LENGTH=32` with burst capability. The PS downstream HP0 exposes additional ID/USER config. No actual generated AXI pin header or APB/DDR behavior is proven until original RTL is bound and XSim elaborates.

Previous `06_original_mem_sc_wrapper_headers.json` identified four plausible module files but zero parsed AXI ports. Source analysis identified parser coverage for ANSI port declarations only. Added **Verilog-1995/non-ANSI module-body port discovery** in `scripts/m06_verilog_port_decls.py`, integrated into `scripts/m06_vendor_wrapper_ports.py`; the new result should be generated with a **new filename**. Do not overwrite the original unsuccessful JSON.

## Implemented vs remaining M06 milestone acceptance

| Required capability | Status | Evidence boundary |
|---|---|---|
| Reproducible logical-neuron → canonical block mapping and bounded LRU cache | **SOFTWARE PASS** | M06 Python cache + poison/owner consistency tests. |
| Correct LIF execution across evictions and 64-tick window boundaries | **SOFTWARE PASS** | Dense/event M02 + sparse M03 parity up to 256 *software* ticks; per-record last-update timestamp and recurrent events persist across windows. |
| Dirty writeback, reloading, faults, and stalls | **SOFTWARE PASS; COMPONENT RTL PASS** | New 1-slot **synthesizable** RTL `m06_residency_control_fsm.sv` orders dirty writeback ACK before fill ACK, exposes counters and sticky quarantine. Its Icarus testbench verifies hits/misses/stalls and failed writeback/fill. The standalone 128-bit AXI scratch target RTL independently passed masked writes, backpressure, deliberate errors; **neither is wired to AMD IP or neural kernel**. |
| Original AMD 4-SI memory SmartConnect functional byte-exact XSim | **OPEN** | Need exact genuine generated wrapper port declarations, vendor compile/elaboration, S03 write to scratch, S00-S02 read, strobe/response and READY stalls. `HAS_BURST=0` on SI means do not assert a generic 128-beat burst; start with one-256b-beat requests. |
| Real transfer adapter connecting the RTL FSM to DMA/AXI and resident-state BRAM | **OPEN** | Abstract `dma_*` signals in FSM represent a future transfer adapter; no memory/address translation/data path attached. |
| Integrated PL neural-paging numerical parity under forced capacity pressure | **OPEN** | Hardware HLS/RTL neural kernel must work with the transfer/residency engine; a standalone software golden-model match is insufficient. |
| Replayable *simulated* DDR/eviction/latency/stall evidence | **OPEN END-TO-END** | Standalone counter evidence is not valid integrated timing/DDR traffic evidence. |
| Physical KV260 DDR measurement | **DEFERRED TO M08**, with distinct approval | Not a prerequisite for M06 *offline simulation* acceptance if authenticated actual vendor AXI + PL neural data correctness is demonstrated; physical memory ownership/programming requires separate operator authorization. |

**Assessment:** M06 is **past the software architectural prototype**, but is **not near its final gate**. The unproven portion involves the highest-risk integration: actual AMD IP transactions + RTL DMA adapter + forced-eviction neural correctness. Do not infer a percent complete from test counts. M06 must stay OPEN pending the original simulated memory-path and neural integration acceptance. M07 should not begin on a fictitious source-only DDR PASS.

## Next owner action (NO Vivado re-run needed to determine module ports)

First pull latest M06 branch, then in `Neuromorphic_Accelerator/v1`:

    git rev-parse HEAD
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m06*.py' -q

    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"

    python3 scripts/m06_vendor_wrapper_ports.py \
      --original "$D3" \
      --report "$PORTS/02_original_mem_sc_ports.txt" \
      --output "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json"
    echo "Original HDL header extraction: $?"

    python3 -m json.tool "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" | head -n 180

Check `wrappers_with_ansi_axi_ports` (legacy field means **parsed AXI ports**, including non-ANSI). Exit0 means original declared ports were found, **NOT functional XSim**; exit3 means no parseable original HDL declaration and the JSON explains why. Share the **single new** `08_mem_sc_wrapper_headers_nonansi_fixed.json` file.

**If exit3 persists**, please share only these two original generated files (do not edit, rename, regenerate or upload all 382 products). Their original paths are listed in the uploaded `02_original_mem_sc_ports.txt`. To locate and upload their literal source, run:

    grep '^SIM_SOURCE|' "$PORTS/02_original_mem_sc_ports.txt" \
      | sed 's/^SIM_SOURCE|//' \
      | grep -E '/sim/(bd_13bd\.v|m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0\.sv)$'

The two files are under `$D3/13_file_backed_project/m05_d3_output_products.gen/sources_1/bd/m05_12d3_real_signed32_hls_six_control_address_candidate/ip/m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0/`:
- `sim/m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0.sv`
- `bd_0/sim/bd_13bd.v`

These files contain actual module/port declarations, not just paths/hashes. They will enable the vendor-BFM to use only real ports. They are original generated code, so preserve immutable owner evidence and share only if comfortable. If needed, instead capture only the module declaration and port-direction sections in a fresh *separate* text file.

## Local independent standalone RTL verification (NO XSim required)

After installing Icarus (`iverilog`/`vvp`) or using the latest GitHub M06 workflow:

    mkdir -p "$HOME/Thesis_Evidence"
    iverilog -g2012 -s tb_m06_residency_control_fsm \
      -o "/tmp/m06_residency_fsm_$$" \
      rtl/m06/m06_residency_control_fsm.sv \
      rtl/m06/tb_m06_residency_control_fsm.sv
    vvp "/tmp/m06_residency_fsm_$$"

    iverilog -g2012 -s tb_m06_axi128_scratch_mem \
      -o "/tmp/m06_scratch_$$" \
      rtl/m06/m06_axi128_scratch_mem.sv \
      rtl/m06/tb_m06_axi128_scratch_mem.sv
    vvp "/tmp/m06_scratch_$$"

Neither test invokes vendor IP or touches hardware. Do not call either test a DDR-integrated acceptance result. CI also retains nine original-role-safe *host stimulus only* cases whose address offsets were corrected to remain within the 8KiB scratch space.

**Upcoming development after authentic header readback:** wire real vendor wrapper to the 128-bit scratch endpoint, drive 256-bit S03 writes, then observe independent 256-bit S00-S02 reads with actual full/sparse byte strobe equivalence, B/R responses and stalls. Next, connect the RTL residency FSM to a real data-transfer adapter and the neural engine, verify a logical network larger than the resident working set, and retain raw XSim waveforms/transcripts. Physical JTAG/PS DDR remains separately unauthorized.
