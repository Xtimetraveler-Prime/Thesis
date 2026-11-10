> **SUPERSEDING RESULT AFTER PRIOR HEADER FIX (2026-11-09):** The owner-run `xvlog` now passed authentic AMD SmartConnect compilation: 56 real vendor RTL sources + 5 authentic headers, both M06 TBs. It then failed at `xelab` with VRFC 10-2989: XPM `glbl` undeclared. The revised runner now includes installed Vivado `glbl.v` and `work.glbl` as a SECOND elaboration root in both snapshots, plus source SHA evidence. NEW real Icarus RTL paging+independent M02 signed16 neural arithmetic PASS on 32 neurons ×4 ticks /1 resident block. This historical handoff remains useful for original port contracts; use [LATEST glbl/neural gate](M06_GLBL_AND_PAGED_NEURAL_PARITY_2026_11_09.md) for commands. Original vendor XSim behavioral transaction result remains NOT YET RUN after glbl fix.

# M06 — original AMD SmartConnect compiler include fix + paged RTL XSim handoff

**2026-11-09 · M06 IN PROGRESS · draft PR #80 UNMERGED · NO BOARD.**

## Latest authentic owner tool result (do not overstate)

Owner ran the genuine 2025.2 `xvlog` original-IP simulator attempt on commit `d58afefca515c0ff6c68f85d225363b92197a22c` and supplied `03_xvlog.log` plus `result.txt` from owner-created evidence directory:
`~/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261109T201640Z_Jf2kCY/`

The original attempt **FAILED at Verilog compile, exit_status=1**. The first error is AMD vendor `axi_register_slice_v2_1_vl_rfs.v` line 3894 unable to find `axi_infrastructure_v1_1_0.vh` (VRFC 10-3195), followed by undeclared macro-generated AXI payload widths. The original Vivado source report ALREADY LISTS the genuine header in `ipshared/ec67/hdl/axi_infrastructure_v1_1_0.vh`, which our earlier shell selector omitted because it filtered by `sc_` or `axi_register_slice` prefix. This is a runner dependency selection error, **not** a hardware AXI response, vendor bug, or proof of DDR failure. Original immutable D3 2025.2 generated sources were not changed (owner's before/after digest compare succeeded). The actual AMD simulator did not elaborate or perform ANY transfers.

**Fix implemented:** `scripts/m06_vendor_compile_plan.py` parses all **186 exact original Vivado SIM_SOURCE entries**, strictly admits only files under the original accepted D3 directory, preserves the genuine Vivado source order, selects the original 56 relevant executable vendor RTL modules (53 Verilog/SystemVerilog + 3 VHDL, based on original report), adds genuine original RTL dependencies `axi_infrastructure_v1_1_vl_rfs.v`, `util_vector_logic`, `xlconstant`, and passes **all five** original `.vh/.svh` header directories (not just the 56 selected source directories) to `xvlog -i`. A dedicated preflight fails before compiler invocation unless the genuine original `axi_infrastructure_v1_1_0.vh` path exists uniquely, is inside D3, and is in the XVLOG include path. It records the original header's SHA256 and full source/include manifest in a new run-specific JSON. Test cases include missing header, altered header name, duplicate source manifest, excluded external paths and expected original RTL dependency. No AMD code is fabricated, edited or copied into Git.

**Important:** The compile-plan/source test passing in CI demonstrates *selection and argument logic*, not that a proprietary AMD vendor RTL library elaborates. Follow genuine XSim compile logs. Future compile errors, if any, must be investigated as missing original generated dependencies, not reclassified as old PS SmartConnect warnings.

## Additional real RTL progress toward M06 acceptance

The earlier one-slot `m06_residency_control_fsm.sv` has been wired to a new **synthesis-oriented RTL 256-byte block mover** `rtl/m06/m06_axi256_block_transfer.sv`. This circuit reads via original SI0-style 256b AXI4-READ and writes via SI3-style 256b AXI4-WRITE, using **eight individual single-beat 256b transactions per block**, avoiding unproven original SI multi-beat capability. It stores eight 256b words in a resident slot with a byte-write-enable client port. On a dirty eviction, the FSM requires eight accepted AXI write replies before the next block's eight reads. Response errors and timeouts return failed completion to the FSM, which quarantines the state. The mover bounds canonical scratch block IDs to 0..31 so its byte addresses never exceed the model 8KiB capacity.

**Real standalone RTL simulation in GitHub Actions passed:** independent M06 FSM + AXI block mover + separate 256-bit mock canonical memory BFM, one resident slot, fill/dirty edit/evict/writeback/reload/byte-compare, and injected SLVERR triggering sticky poison:
- `M06_PAGED_BLOCK_AXIBRIDGE_RTL_PASS fills=3 dirty_wb=1 reads=24 writes=8 source=MODEL_ONLY`
- `M06_PAGED_BLOCK_FAULT_QUARANTINE_RTL_PASS`, 25 accepted AR/R beats and 111 modeled stall cycles in this particular simulation.

This is real synthesizable RTL and real Icarus simulation, but the mock endpoint is NOT original vendor SmartConnect/PS DDR and the client edits are deterministic testbench data, NOT the original M05 neural RTL accelerator.

## Two genuine ORIGINAL AMD vendor XSim tests in ONE owner invocation

Updated `scripts/run_m06_original_mem_sc_vendor_xsim.sh` performs strict original wrapper SHA and exact 96-pin interface authentication and creates a fresh exclusive evidence folder. It then:

1. Loads the new source/include plan, records all authentic original paths and original file SHA before/after. **Stage A:** compiles the ORIGINAL AMD SmartConnect/BD with an independent 128-bit AXI scratch target, and elaborates/runs `tb_m06_original_mem_sc_vendor`. This bench uses FOUR S03 single-beat 256b masked writes and 14 independent S00/S01/S02 byte-exact readbacks, including legal 4KiB boundary neighborhoods; holds responses under B/R backpressure, requires actual downstream M00/128b beats and timeouts.
2. **Stage B, only if A passes:** elaborates/runs `tb_m06_original_vendor_paged`, generated by `scripts/m06_generate_original_paged_vendor_bfm.py`, with the same authenticated AMD 96-pin DUT connected to our actual synthesis-oriented RTL residency FSM + 256B AXI block mover and the 128b scratch RAM. It forces page1 fill/edit, dirty page1 eviction→page2 fill, page1 reload with all eight words byte-checked, no-AXI hit, and injected downstream read-error quarantine. Requires real M00/128b traffic, actual command/byte counters and independently checked state.

The only valid end-to-end PASS requires **authentic** `05_xsim.log` containing `M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS` plus authenticated `07_paged_xsim.log` containing both `M06_ORIGINAL_VENDOR_PAGED_RTL_PASS` and `M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS`, with `result.txt exit_status=0` and matching original before/after SHA. Merely generating either testbench or compiling the fake CI stub is NOT vendor functional evidence.

The whole runner is OFFLINE against an isolated simulated scratch region: no original Vivado project mutation, no generating HLS products, no Linux/PS DDR physical ownership, no bitstream, no JTAG, no board programming.

## Exact VS Code terminal commands for owner

Run one time with Vivado 2025.2 available (if you have already sourced the environment, omit the source command).

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1

    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m06*.py' -q
    bash -n scripts/run_m06_original_mem_sc_vendor_xsim.sh
    # source <YOUR EXISTING Vivado 2025.2>/settings64.sh
    xvlog -version

    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"

    bash scripts/run_m06_original_mem_sc_vendor_xsim.sh \
      "$D3" "$PORTS/02_original_mem_sc_ports.txt" \
      "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json"
    echo "M06 original AMD vendor XSim both-stage exit: $?"

    export RUN="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
      -name 'm06_original_vendor_mem_sc_xsim_*' | sort | tail -n 1)"
    echo "$RUN"
    cat "$RUN/result.txt" "$RUN/commit.txt"
    cmp "$RUN/sha_before.txt" "$RUN/sha_after.txt"
    python3 -m json.tool "$RUN/02_original_vendor_compile_plan.json" \
      | head -n 80
    grep -E \
      'M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS|M06_VENDOR_FAIL|FATAL|ERROR' \
      "$RUN/05_xsim.log" 2>/dev/null | tail -n 40 || true
    grep -E \
      'M06_ORIGINAL_VENDOR_PAGED_|M06_ORIGINAL_PAGED_FAIL|FATAL|ERROR' \
      "$RUN/07_paged_xsim.log" 2>/dev/null | tail -n 40 || true
    tail -n 60 "$RUN/03_xvlog.log" 2>/dev/null || true
    tail -n 60 "$RUN/04_xelab.log" 2>/dev/null || true
    tail -n 60 "$RUN/06_paged_xelab.log" 2>/dev/null || true

If stage A or B fails, **do not automatically rerun**: upload `result.txt`, `commit.txt`, `02_compile_plan.log`, and the **last** nonempty stage log: `03_xvlog.log` or `04_xelab.log` / `05_xsim.log` / `06_paged_xelab.log` / `07_paged_xsim.log`. If all PASS, send both authentic XSim logs plus summary. Do not upload all 186 original generated sources.

## Remaining M06 acceptance even after two vendor snapshots

The two original-memory-model gates demonstrate behavioral synthetic canonical bytes and a bounded **one-slot** resident page path. They do NOT by themselves establish exact M05 HLS neural kernel execution from paged DDR, an eight-slot LRU option-B FPGA cache matching M01 geometry, original 4096 neuron signed16 state partition with all metadata, scalable PL queue/synapse paging or actual PS DDR allocation/physical ownership. Those require further distinct design and acceptance proofs. Keep M06 **OPEN until required neural parity through the physical-architecture PL paging integration is demonstrated**, and do not confuse physical board measurements (deferred hardware campaign) with simulation.

No original 63 warnings were waived or reinvestigated. PR #80 remains DRAFT/UNMERGED.
