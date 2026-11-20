# M08 D3.D — first genuine KV260 neural-inference parity over proven JTAG readback

**Status:** architecture/acceptance contract only. No D3.D Vivado bitstream has been generated, no D3.D board programming, no neural inference. The r2 D3.C communication experiment completed physically and is preserved; D3.C is not itself a neural accelerator.

## Physical prerequisite established (owner originals, 2026-11-19)

The owner provided native accepted r2 Vivado JTAG-to-AXI-to-4KiB-BRAM candidate SHA256 `87e04662b038ded01bd020141c541a33d62370df02bdeaacdad695b17c9d00a1`, 11/11 original offline SHA evidence rows OK, +5.242 ns WNS, +0.010 ns WHS, 7 precisely reviewed vendor debug DRC warnings. Owner then demonstrated a separately immutable genuine hardware evidence directory `m08_d3c_jtag_HW_sMEfyq6l` with **5/5 SHA rows OK**, `vivado_physical_exit=0`, `result=FOUR_BRAM_WORDS_WRITTEN_READ_AND_MATCHED`, actual JTAG `hw_axi_1` and four exact matched words at addresses `A0000000,A0000004,A0000008,A000000C`. This proves PL JTAG-AXI-to-BRAM communication for that actual run, not neuromorphic execution or PS independence. r1 physical trial failed first AXI write; that negative evidence remains preserved.

## Important existing implementation boundaries

- `docs/M02_PROVISIONAL_LIF_CONTRACT.md`: reference signed16 LIF semantics: decay truncates toward zero, external and delayed synaptic currents sum before one saturation, inclusive threshold and reset, every neuron updates each tick including quiet neurons, positive recurrent delays. This is the correctness oracle.
- `rtl/m06/m06_lif16_neuron_step.sv`: reusable **combinational neuron arithmetic lane** only. It does NOT include a finite network scheduler, stream ingress/egress, recurrent routing, AXI peripheral or complete accelerator.
- `hls/m06_paged_rolling/m06_paged_rolling.cpp` and `.hpp`: accepted M06 signed16 neural/paged HLS core, with **two m_axi canonical-memory masters**, an AXI-Lite control interface and **five AXI streams** (neuron, synapse, external events; trace, metrics). These require real hardware producers/consumers and verified memory ownership; a standalone JTAG-AXI BRAM echo cannot directly exercise the HLS top.
- `docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md`: original Vitis/AMD XSim parity at 32 neurons × 4 ticks and simulated 64 KiB memory image, including directed injected AXI faults. There is **no** physical DDR allocation, connected KV260 runnable neural engine or physical neural result.
- D3.C r2 source `scripts/m08_d3c_jtag_bram_build.tcl`: actual physical transport and `rtl/m08_d3c_fabric_por.v` reset mechanism; uses **PS pl_clk0 at nominal 100 MHz** and fan TTC0 to A12. Preserve this proven baseline and do not use PS HPM0/DDR for the initial neural-parity experiment.

## D3.D.1 — first neural computation with exact PC oracle

Design a **new** diagnostic PL image, not a change to or override of the existing accepted r2 image:

1. Reuse JTAG AXI master + SmartConnect + physical fabric POR + fan A12 route. Keep HPM0/HPM1/LPD disabled and stock Linux/DDR out of test datapath.
2. Create a **real** AXI-Lite command/result endpoint or explicitly specified BRAM command mailbox with atomic start/done and input/output ownership; define exact address offsets, 32-bit alignment, endianness, staging bounds, completion/error flags and pre/post-start memory visibility. Never treat simply reading PC-written golden words back as neural execution.
3. Connect a genuinely clocked, on-chip, finite inference datapath. Its first workload may be a single signed16 M02 LIF neuron-step with signed current/threshold/decay/reset edge cases, but the final D3.D.1 acceptance should cover a **multi-neuron, multi-tick** fixture, ideally building toward the accepted M06 32-neuron ×4-tick reference. Use `m06_lif16_neuron_step.sv` only with a separate proven scheduler and state update machinery, or integrate the actual M06 HLS design with bounded on-chip canonical-memory and stream adapters.
4. Host writes **inputs/parameters**, not predicted answers; PL computes state and spikes, writes its own observable completed result. JTAG reads that fresh output through the proven path. Capture a nonce/epoch or scratch poison and a sequence of distinct fixtures so stale/prepopulated output cannot fake inference.
5. A separate PC oracle generates exact expected M02 per-tick signed16 voltages and spikes, including negative currents, threshold equality, saturation, zero-input decay and delayed recurrent delivery when enabled. Compare each exposed actual hardware state and spike tick to that oracle, not just a high-level digest.
6. Negative cases: illegal control parameters, busy/start collisions, reset/reprogram clearing stale completion, output unavailable before done, small and maximum supported N/T, and nonexistent or unaligned addresses. A bounded watchdog must never be presented as a measured throughput benchmark.

**Offline gates before any board access:** actual Vivado 2025.2 project elaboration/BD, original implementation timing and DRC, exact port/address/clock/reset mapping, independently authenticated source hashes and generated RTL, host-only unit and RTL tests, plus if using the HLS top original Vitis artifacts and ABI verification. Require a new one-shot program SHA, no auto retries, preserved UART/fan/stock recovery preflight. Physical program remains owner-authorized as a separate action.

**Physical D3.D.1 acceptance:** authenticated distinct candidate SHA + successful JTAG program; hardware `done` asserted for finite input-dependent work; exact M02 neural state/spike equality for all tested ticks and neurons; source/version and hardware result receipts hash-verified. Successful BRAM echo alone must fail this gate.

## D3.D.2 — progressively larger on-chip neural workloads

After D3.D.1 neural parity, expand N/T/fanout/activity and multiple seeds, strictly measuring PL resource, timing closure, on-chip capacity and device-only execution latency. Compare timestep and event-driven modes only when exact numerical/input/clock/resource contracts are matched; label work unsupported when it does not fit on-chip. Keep JTAG outside inference timing measurements (its control overhead is separately measured).

## D3.D.3 — genuine paged/DDR physical experiment (separately gated)

Only after real neural outputs are available, integrate M06 two `m_axi` ports through an explicitly verified on-board memory pathway with owner-approved allocation/ownership, physical address and DMA/driver provenance, read-before-use and writeback/ordering proofs, and fault response quarantine. Avoid `/dev/mem` and arbitrary physical addresses. A software/PS/Linux-compatible workflow may be required; this JTAG/BRAM proof does **not** magically establish a safe DDR path. Benchmark the four logical timestep/event × on-chip/DDR variants only after all actually exist on the device with matched work and valid capacity gates.

## Scope / release decision

**D3.C communication PASS is necessary but insufficient for a full-scale physical neuromorphic-accelerator claim.** The current r2 bitstream has no neural executor. First implement D3.D.1 with a new honest compute-bearing PL image and compare hardware results to M02; extend to 32×4 and beyond before considering performance/capacity/DDR claims. No physical run command belongs in this plan until an actual D3.D native image passes independent gates.
