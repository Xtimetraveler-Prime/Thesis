# M08 D3.D — first genuine KV260 neural-inference parity over proven JTAG readback

**Status:** D3.D.1 signed16 LIF RTL, exact-M02 fixture generator, RTL tests, new Vivado builder, native receipt gate, guarded physical runner and independent physical receipt auditor are implemented **in source**. A genuine owner Vivado D3.D bitstream and physical neural execution have NOT yet been demonstrated. The r2 D3.C communication experiment completed physically and is preserved; D3.C is not itself a neural accelerator.

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

**D3.C communication PASS is necessary but insufficient for a full-scale physical neuromorphic-accelerator claim.** The current r2 bitstream has no neural executor. First implement D3.D.1 with a new honest compute-bearing PL image and compare hardware results to M02; extend to 32×4 and beyond before considering performance/capacity/DDR claims. The physical runner exists only for a later separately authorized one-shot. Do not run it until the owner native D3.D build has passed all gates, original image SHA/DRC/timing have been inspected, and cooling, UART and stock recovery conditions are safe.

## 2026-11-19 D3.D.1 implementation — real clocked neuron RTL, PC/native verification (PHYSICAL PENDING)

**Scope:** Implemented a **new** compute-bearing, standalone diagnostic JTAG design, not the full 32-neuron M06 HLS and not DDR-backed inference. It executes ONE signed16 M02 LIF neuron over FOUR finite hardware clocked ticks and stores all four resulting membrane voltages and spike bits. Supported decay ratios are **0/1, 1/2, 1/1 only**. This is deliberately a computational subset of M02 v1, not a replacement for M05/M06 integrated event/synapse engine. No synapses, delays, event router, cache, DRAM, classifier, chip benchmark, or physical neural result is claimed.

**Implemented sources:**
- `rtl/m08/m08_d3d_lif_axil.sv` — AXI4-Lite 32-bit slave, independent AW/W capture and stable R/B under backpressure, 1 initial signed16 neuron, signed bias/threshold/reset, four externally supplied signed32 per-tick currents, hardware-only 4-tick sequential LIF datapath using M02 saturate-after-full-add, inclusive firing threshold, signed negative truncation-toward-zero for the half decay and reset. Rejects incomplete WSTRB, invalid thresholds or decoder values and writes to read-only outputs. Hardware output is gated to `DONE`, and each new START records the caller's nonce, invalidates stale outputs, and increments a hardware run count only after four clocked updates.
- `rtl/m08/tb_m08_d3d_lif_axil.sv` — directed Icarus AXI4-Lite/arith tests for four independent M02 fixtures including negative truncation, saturation, spike/reset, autonomous bias/threshold equality, invalid writes, unaligned addresses and stalled stable responses.
- `scripts/m08_d3d_neuron_vectors.py` — PC generates golden results via the **actual** existing `m02_dense_reference.evaluate_dense` AND `m02_event_reference.evaluate_events`, requires exact matching references; outputs four distinct nonce/input/expected-output fixtures, never writes HW outputs.
- `scripts/m08_d3d_neuron_build.tcl` — **fresh new** Vivado 2025.2 native candidate, preserves D3.C r2 JTAG→SmartConnect→AXI BRAM at `0xA0000000`, adds AXI-Lite neuron at `0xA0001000`; two SmartConnect targets; same PS PL0 nominal 100 MHz, separate 256-cycle fabric-POR reset, TTC0 waveout2 to A12, no PS HPM masters. Native builder checks both address segments, clock/reset, memory dimensions, DRC, timing; hashes exact original builder + POR RTL + neuron RTL into result receipt, no board contact.
- `scripts/run_m08_d3d_neuron_pc.sh` & `scripts/m08_d3d_neuron_gate.py` — new evidence folder, **12 SHA entries**, checks native Vivado identity, source hashes, exact RTL provenance, scoped DRC findings and nonnegative routed timing. The seven D3.C vendor/debug warnings may remain, but are only accepted if the **exact reviewed D3.C pattern** matches; new/changed warnings block physical authorization.
- `scripts/m08_d3d_neuron_readback_once.tcl` & `scripts/run_m08_d3d_neuron_physical_once.sh` — **not yet authorized or executed**. Separate one-shot hardware runner first revalidates fresh native D3.D acceptance, checks explicitly named new bitstream SHA and JTAG K26 identity, program once, confirms retained BRAM echo, sends four M02-only inputs, invokes genuine hardware neuron start, reads four voltages/spike mask/nonce/monotonic completion count per fixture, and records trace equality in new immutable PC-only SHA evidence. Separate owner physical authorization, independent cooling, UART monitor and stock power-cycle recovery are mandatory.

**AXI4-Lite register map** (all offsets relative to `0xA0001000`; 4-byte aligned; 32-bit full `WSTRB=0xF` mandatory for writes):

| Offset | Access | Meaning |
|---|---|---|
| `0x000` | R | Magic `0x4D384C46` (M8LF) |
| `0x004` | R | Version `0x00010000` |
| `0x008` | R | Status: bit0 DONE, bit1 BUSY |
| `0x00C` | R/W | Host-set nonzero nonce (input tag) |
| `0x010` | R/W | Signed16 initial membrane as signed-extended 32 |
| `0x014` | R/W | Signed16 bias as signed-extended 32 |
| `0x018` | R/W | Signed16 threshold >0 as signed-extended 32 |
| `0x01C` | R/W | Signed16 reset voltage < threshold |
| `0x020` | R/W | Decay mode 0: 0/1, 1: 1/2, 2: 1/1 |
| `0x024..0x030` | R/W | Four successive signed32 total external currents, one per tick |
| `0x034` | W | START value exactly `1`: validates parameters; clears prior DONE; starts four sequential clocked updates |
| `0x038` | R after DONE | Completed nonce (not a computed answer) |
| `0x03C` | R after DONE | Four spike bits (tick0 bit0 through tick3 bit3) |
| `0x040..0x04C` | R after DONE | Four signed16 resulting voltages, signed-extended 32 |
| `0x050` | R | Hardware-completed run counter (increments after four real updates) |

This exposes the true output state; the PC supplies initial parameters and per-tick input currents, **not** expected spike/voltage values. All trace registers are inaccessible with SLVERR before DONE, and an accepted START clears stale trace data; invalid control writes generate SLVERR/DECERR. A single applied current is an already aggregated per-neuron current (no synaptic pipeline exists).

**Verification (owner PC, NO FPGA PROGRAMMING):**

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d-neural-jtag-parity
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d-neural-jtag-parity
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3d_neuron_gate.py' -v
python3 scripts/m08_d3d_neuron_gate.py --source-only
bash -n scripts/run_m08_d3d_neuron_pc.sh
bash -n scripts/run_m08_d3d_neuron_physical_once.sh
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
bash scripts/run_m08_d3d_neuron_pc.sh
```

The last command is a fresh **offline synth/place/route/bitgen** requiring real owner Vivado; it may fail with a genuine IP interface or DRC finding not visible to CI. Preserve any first native failure in its new original directory; do not patch receipts, skip checks, or retry on the same folder. **Do not run the physical-programming script until the new offline evidence, source SHA, actual route reports, cooling/UART/recovery and a separate operator decision have been reviewed.** The previously successful r2 D3.C bit SHA `87e04662...` is *not* a neural candidate and will be rejected by D3.D audit.

### Independent physical evidence verifier (only AFTER a separately approved D3.D load)

A new `scripts/m08_d3d_neuron_physical_audit.py` independently verifies the six-file physical SHA ledger, exact executed Tcl, real Vivado exit=0, original JTAG transaction log, source-consistent native image SHA, original M02 dense+event fixture file and all four hardware-produced signed16 voltage/spike traces. It rejects a false or edited result even if an attacker rehashes the result receipt. Its only successful status is `M08_D3D_PHYSICAL_SINGLE_NEURON_FOUR_TICK_M02_PARITY_ACCEPTED`, with explicit claims `full_m06_neuromorphic_accelerator_verified=false`, `physical_ddr_verified=false` and `ps_clock_independence_verified=false`.

For a **future reviewed** hardware run, the separately armed one-shot command is:

```bash
# NEVER run this with the old D3.C r2 BRAM-only bitstream.
# RUN must be a new, genuinely accepted m08_d3d_neuron_* native directory.
# Requires owner-approved board preflight, live independent backup cooling,
# UART/recovery readiness, and explicit consent for ONE JTAG reprogramming.
M08_D3D_ALLOW_PROGRAM=YES bash scripts/run_m08_d3d_neuron_physical_once.sh "$RUN"
```

The physical runner will automatically run the independent auditor before printing a hardware success marker. Afterward, an owner can separately verify the 6/6 SHA receipt and run:

```bash
HW="<FRESH_m08_d3d_neuron_HW_...>"
(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_d3d_neuron_physical_audit.py --run-dir "$RUN" --hw-dir "$HW"
```

Any native Vivado error, unknown DRC warning, actual negative route slack, mismatched golden trace, failed board JTAG transaction, lost cooling, or ambiguous stock recovery stops the checkpoint; do not repeat immediately or relabel a BRAM echo as neural computation.
