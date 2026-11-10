> **IMPORTANT SUPERSEDING UPDATE 2026-11-09:** The original owner XSim run failed at `xvlog` because our simulator runner excluded the genuine vendor `axi_infrastructure_v1_1_0.vh` include directory, NOT because of a broken memory transaction. A new compile plan includes all headers from original 186 Vivado source paths and the required infrastructure RTL, and the runner now checks TWO genuine vendor XSim snapshots: direct original SmartConnect byte integrity, then real RTL residency controller + 8x256b AXI block mover + original SmartConnect. **Use NEW owner commands in [M06 AMD include + paged vendor integration handoff](M06_AXI_HEADER_AND_PAGED_VENDOR_HANDOFF_2026_11_09.md)** rather than the original invocation below. No genuine vendor functional PASS yet; old sections below are historical.

# M06 — authentic original AMD SmartConnect functional XSim gate

**Developed 2026-11-09, M06 draft PR #80, ORIGINAL IP NOT YET EXECUTED.**

## Why the owner's latest files matter

The owner uploaded genuine original generated D3 simulation wrapper
`m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0.sv` and its nested `bd_13bd.v` from
`~/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ/`, plus an offline-original 96-signal ABI report `08_mem_sc_wrapper_headers_nonansi_fixed.json`. Hashes in the uploaded JSON and both actual uploaded files match:
- original vendor simulation wrapper SHA256: `0ec8a01dfc7c23825a8d5c8934c7f26dc5b92b924be88d51addd9e76555b8e12`
- original nested BD Verilog SHA256: `c3d7c5021f532aae29c860a63fb92da9529dac489f87a74267b9af82472444f3`
- original Vivado endpoint report SHA256: `3c85a47ad2230efd730d30a07739c18ca00690b1a1e6ed7ad998fc6e39fd76d0`

The SIM top's exact pin contract has 96 external AXI signals, plus original `aclk/aresetn`. S00/S01/S02 are each **READ ONLY** 256b, S03 **WRITE ONLY** 256b, M00 **READ/WRITE** 128b; M00 addresses are 49b and original source SI addresses are 32b. Crucially the actual vendor RTL exposes **8-bit AWLEN/ARLEN pins** despite its Vivado BD endpoint property `HAS_BURST=0` and max length16. The testbench drives ONLY one 256-bit SI beat per request (`LEN=0,SIZE=5,INCR`), leaving multi-beat legality unresolved pending real XSim. No AXI ID/USER pins are fabricated or driven.

**Do NOT commit or modify the original AMD-generated HDL or treat its confidentiality header as a license.** The M06 repository contains only our generated HDL TB, Python generator, shell runner and independent 128-bit scratch RTL; the runner reads the original files in-place. The original old port probe exit2 and empty audit log remain immutable; its corrected re-audit exit0 remains accepted **port-only** evidence.

## New functional integration test

The runner first validates the JSON port list against an EXACT expected 96-pin name/width/direction contract, both actual original wrapper source SHA256s and original report SHA. It generates an independently authored SystemVerilog BFM testbench (NOT AMD code), selects 57 original mem_sc + required AMD `ipshared` simulation files from original 186-source compile order, compiles using actual Vivado 2025.2 `xvhdl`/`xvlog`/`xelab`, and simulates the true vendor instance in XSim, connected to our **standalone simulation-only 128-bit AXI scratch-memory** (no PS DDR).

The initial directed transaction sequence is bounded and meaningful:
1. FOUR original S03 single-beat 256b writes at 0x0fe0, 0x1000, 0x1020, 0x1040, using full plus sparse 32-lane WSTRB masks. The bench requires BVALID held under stalled BREADY and BRESP=OKAY.
2. THREE original read-only S00, S01 and S02 masters each read back all FOUR updated words with byte-exact scoreboard against the independent canonical formula `(13*address+17)&255` plus mask writes; RVALID/RDATA/RRESP/RLAST must hold under stalls.
3. TWO more independent S00 reads around the 4KiB boundary; **no 4KiB-crossing AXI burst**. The bench also requires actual M00 128-bit downstream AW/W/R handshake activity (at least 8 write and 28 read beats). A global watchdog fails a deadlocked DUT.
4. The sole vendor integration PASS marker is **\`M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS\`** appearing in an authentic original XSim run log AFTER all scoreboard assertions. The generator and source tests explicitly do not emit a simulated-pass claim.

Potential original generated IP compile/elaboration issues MUST be reported as real failures with xelab/xvlog logs. The generic CI syntax check uses a FAKE stub **without simulating it** and cannot prove anything about proprietary AMD IP; standalone Icarus memory/residency component passes also cannot. This run intentionally does not include a neural kernel, DMA paging, or real PS DDR. After this vendor gate, these remain M06 acceptance requirements; physical board remains M08 and separately unauthorized.

## ONE owner verification run — offline Vivado/XSim only, no board

From the working M06 branch and VS Code terminal:

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

    export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"

    # The operator should confirm this is the same Vivado 2025.2 used for D3:
    source "$HOME/Vivado/2025.2/settings64.sh"
    command -v xvlog
    xvlog -version

    # This launches xelab/XSim ONLY on ORIGINAL read-only vendor source files
    # + independent scratch model. No Vivado project/BIT/DDR/board operations.
    bash scripts/run_m06_original_mem_sc_vendor_xsim.sh \
      "$D3" \
      "$PORTS/02_original_mem_sc_ports.txt" \
      "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json"

    echo "Original vendor XSim command exit code: $?"

The runner creates a fresh, exclusive directory:

    ~/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_YYYYMMDDTHHMMSSZ_XXXXXX/

It always writes `result.txt` (exit0 only when the real compiled vendor simulation prints the full byte-checked PASS). It saves `01_authentic_bfm.log`, `02_xvhdl.log` (if relevant), `03_xvlog.log`, `04_xelab.log`, `05_xsim.log`, `commit.txt`, both `sha_before.txt` and `sha_after.txt`, the selected original source file list, and generated bench.

Retrieve the most recent result and relevant terminal excerpts:

    export RUN="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
      -name 'm06_original_vendor_mem_sc_xsim_*' | sort | tail -n 1)"
    echo "$RUN"
    cat "$RUN/result.txt" "$RUN/commit.txt"
    cmp "$RUN/sha_before.txt" "$RUN/sha_after.txt"
    grep -E 'M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS|M06_VENDOR_FAIL|ERROR:|FATAL' \
      "$RUN/05_xsim.log" | tail -n 40 || true
    tail -n 60 "$RUN/04_xelab.log" 2>/dev/null || true
    tail -n 60 "$RUN/03_xvlog.log" 2>/dev/null || true

**If any stage fails, do not replace original AMD output or run warnings-only IP inventories.** Upload just the stage logs that actually exist: `01_authentic_bfm.log`, `03_xvlog.log`, `04_xelab.log`, `05_xsim.log`, plus `result.txt` and `commit.txt`; originals themselves are unnecessary now. If the compiled XSim PASS succeeds, upload `05_xsim.log` and `result.txt` as real evidence, not just a terminal summary.

**M06 remains IN PROGRESS regardless of this isolated vendor test's result** until original signed neural fixture parity with bounded working-set < logical network and an actual PL transfer bridge to the residency controller are independently demonstrated.
