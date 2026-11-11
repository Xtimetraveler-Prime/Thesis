# M08.2b.1 — First M08-specific physicalizable signed16 state-page staging

**Status:** Source and standalone first-party RTL development. No original new M08 vendor BD, synth, route, bitstream, PL programming, real AXI/PS or DDR proof. Distinct from accepted M08.2a identity-only offline Vivado BD.

## Engineering choice based on accepted research

Loihi Digital Twin v2 P08.4.3a/b proved host-owned K26 resident-page replacement, exclusive host/compute memory access, and a representative physical neural dispatch. It implemented a **different** signed24 full-context 10-bank model using VIO/JTAG. We reuse its *ownership and quiescence invariants*, not its memory shape, neuron arithmetic, RTL, or bitstream. See [cross-project source and physical evidence](M08_3_LOIHI_KV260_MEMORY_OWNERSHIP_REUSE_2026_11_11.md).

Our M06 accepted signed16 state representation has **16 neurons × 16 bytes = 256 bytes** in one canonical block, two signed16 voltage bytes per neuron and 32-bit tick metadata in record bytes 2–5. This first M08 hardware slice deliberately uses one 64×32-bit page of those records, rather than Loihi's three resident full-context slots.

## New RTL: one 256-byte single-clock page

`rtl/m08/m08_host_staged_page_bank.sv` provides host load/readback and a distinct compute access port, with one request per clock and explicit byte strobes. Control states are EMPTY, LOADING, READY, RUNNING, DIRTY, FAILED. Reset invalidates the page regardless of uninitialized RAM contents. Host must write **all 256 bytes** (partial writes accumulate unique byte coverage) **and actually read all 64 words after their final writes** before asserting verified-load completion; hardware tracks a separate readback bit per word and a write clears its readback bit. Only a READY page with the exact logical ID can dispatch. Compute may access memory only while RUNNING. Once completed, the page is DIRTY; the hardware requires host to read **all 64 words** in DIRTY mode (tracked readback bitmap) and externally save them before it accepts the host save acknowledgment and allows replacement. A host request while compute owns the page, wrong page tag, incomplete fill, illegal overlap or external compute fault creates sticky FAILED quarantine.

The RTL **does not itself authenticate** host assertions `host_readback_verified` or `host_save_done`. A future host controller must actually read and compare all page words, verify the destination backing image, enforce timeouts and failed-response rejection before asserting either one. The RTL has no DMA, AXI-Lite, memory master, Linux mapping, full HLS neural engine or evidence of a real clock frequency.

## Standalone first-party HDL test

`rtl/m08/tb_m08_host_staged_page_bank.sv` instantiates the new hardware alongside M06's original signed16 `m06_lif16_neuron_step.sv`. It loads all 64 page words for logical context 7, independently reads all words back, dispatches, applies signed16 LIF step (previous voltage 4, decay 3/4, bias 1 and input current 2 yield new voltage 6), modifies only the two voltage bytes of the first record, finishes, reads changed state back into the *testbench's* software backing, explicitly saves, and replaces with logical page 9. Negative cases verify incomplete fills, dishonest load-complete assertion without real full-page readback, dishonest dirty-save assertion without full-page host readback, dirty eviction without save, host/compute overlap, wrong logical tag and sticky external fault.

`tests/test_m08_host_staged_page_rtl.py` runs actual Icarus Verilog in CI and rejects compiler warnings. If Icarus is unavailable on the operator PC, that specific runtime test is SKIPPED and must not be treated as a passed HDL proof. Source-only assertions are not genuine vendor evidence.

## Next ordered deployment gates

1. **M08.2b.1** (this source stage): independent 256-byte signed16 hardware staging, safe host/compute memory exclusion and negative HDL tests. No real board experiment.
2. **M08.2b.2 NEXT**: PS-accessible first-party 32-bit **AXI4-Lite page/control adapter**, preserving AW/W independence, B/R backpressure, 4-byte strobes, no unsafe register aliases, reset and error response. Connect to this page bank. Do NOT assume a hardcoded physical Linux MMIO address. Use accepted M08.2a PS FPD HPM0/SmartConnect board preset and actual clock propagation as native Vivado precedent.
3. **M08.2b.3**: generate and independently audit a new **genuine Vivado 2025.2** native K26 PS→PL staging BD (no bitstream yet), preserving original owner raw logs, source SHA, warnings and Vivado-assigned apertures.
4. **M08.2b.4**: genuine synthesis, full implementation, WNS/WHS, resource reports, new uniquely SHA-identified M08 bitstream and probes. No Loihi bitstream reuse.
5. **M08.4**: after safe KV260 boot and identified M08 bitstream, demonstrate real PS→PL read-only identity, then verified single-page write/readback, one signed16 compute operation and independent final state conformance. This is still NOT physical PS DDR.
6. **M08.3/M08.4 later**: full M06 signed16 paged HLS path, fail-closed G4 output quarantine and actual bound Linux DMA API ownership for experiments that use real PS DDR. Measured event/DDR performance and fair controls follow only after these gates.

The Loihi P08 host staging success means we should NOT reinvent host/compute arbitration; it does NOT authorize an unsupervised M08 PL memory master or real DDR writes.

## Local source verification

From `~/Git/Thesis/Neuromorphic_Accelerator/v1` on the branch `agent/neuromorphic-accelerator-v1-m08-kv260-bringup`:

~~~bash
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_host_staged_page_rtl.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
~~~

Require 8/8 M01–M08 CI success at the exact new final SHA. Original seven M08.2 offline Vivado evidence folders remain untouched. No JTAG, bitstream, MMIO, DDR or kernel DMA is called by this stage.

## Owner first Icarus runtime failure — compute-port handshake boundary (2026-11-11)

Owner independently sourced Vivado/Vitis 2025.2 but used real `/usr/bin/iverilog` and `/usr/bin/vvp` to compile the original M08.2b.1 first-party page bank + accepted M06 signed16 lane + testbench. The command compiled, then **FAILED** at `tb_m08_host_staged_page_bank.sv:158` with `M08_PAGE_COMPUTE_READ_FAILED` at simulation time **2,686,000 ps**, inside the **first** `compute_read(6'd0,32'h55550004)`, after `fill_page` and `start_compute` passed. This is a real first-party simulation failure; **M08.2b.1 HDL acceptance remains OPEN**. The original failure string used `!compute_ack || compute_rdata!==expected` without printing which expression failed. Neither the cause nor a clock/RTL correctness PASS was established by this original report.

**Narrow correction, not an accepted physical result:** `tb_m08_host_staged_page_bank.sv` now drives compute read/write requests until an explicit ACK is observed, bounded by **eight clock edges**; checks received data on the ACK edge, fails fast on poison/idle, and emits separate `M08_PAGE_COMPUTE_READ_REJECTED`, `M08_PAGE_COMPUTE_BAD_DATA`, `M08_PAGE_COMPUTE_READ_TIMEOUT`, `M08_PAGE_COMPUTE_WRITE_REJECTED`, or `M08_PAGE_COMPUTE_WRITE_TIMEOUT` diagnostics (including DUT request/phase/armed/memory values where useful). The Python source regression requires these conditions to be present. This change intentionally does **not** relax expected signed16 voltage/page byte values, ignore a corrupt read, accept an unknown ACK, or change the M08.2b.1 RTL or accepted M06 lane.

**Next acceptance:** Owner must rerun the **exact new HEAD** using original direct `iverilog -g2012 -s tb_m08_host_staged_page_bank` compile and `vvp` (not a mocked source test). A passing run must print all expected positive and negative markers. If it fails, preserve the new precise fatal line; that discriminates an actual compute-port/arbitration failure from testbench timing. The CI infrastructure has independently shown intermittent apt/DNS failures when trying to install Icarus; GitHub queued status is **not** an RTL PASS. Do not proceed to PS AXI4-Lite/Vivado placement/board operation until this particular test passes.
