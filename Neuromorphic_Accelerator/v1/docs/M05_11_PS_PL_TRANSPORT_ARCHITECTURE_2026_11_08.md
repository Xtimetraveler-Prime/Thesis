> **M05.12d.1 ORIGINAL OWNER REAL VIVADO VERIFIED/ACCEPTED (2026-11-08 18:12 local / 2026-11-09 01:12 UTC):** User-owned genuine evidence `~/Thesis_Evidence/neuromorphic_v1_m05_12d1_axis_graph_20261109T011233Z_Qjt8oT`, source checkout `c702d1712e153aa283c55f1e35c079738ea1c50e`, `result.txt exit_status=0`. Vivado 2025.2 prints `M05_12D1_SOURCE_MGMT_MODE=All`, correctly infers four 256-bit AXIS bus interfaces, and reads four true separate point-to-point nets: `dma_neurons/M_AXIS_MM2S→shell/S_AXIS_NEURONS`, `dma_synapses/M_AXIS_MM2S→shell/S_AXIS_SYNAPSES`, `dma_external/M_AXIS_MM2S→shell/S_AXIS_EXTERNAL`, `shell/M_AXIS_TRACE→dma_trace/S_AXIS_S2MM`. Strict independent audit **PASS connections=4**. Prior original failed evidence `neuromorphic_v1_m05_12d1_axis_graph_20261109T005602Z_nTb0oa` remains preserved as genuine `exit_status=1`. **Important remaining Vivado warning:** `IP_Flow 19-11770` inferred `clk` has NO `FREQ_HZ`; `ASSOCIATED_BUSIF` inferred only `S_AXIS_NEURONS`, not all four streams. This does NOT invalidate the limited four-net proof, but is a BLOCKER for claiming a properly clocked/routed full PS/PL BD. No HLS, PS DDR, AXI-MM memory, AXI-Lite address map or clock/reset connectivity was built in this gate.

> **NEW M05.12d.2 IMPLEMENTATION — PS INVENTORY & SIX-CONTROL-BANK ADDRESS ADMISSION (2026-11-08 local):** D2a `scripts/m05_12d2a_ps_inventory.tcl` creates **another isolated in-memory K26 Vivado project**, instantiates an **unconfigured** `zynq_ultra_ps_e` PS IP catalog cell, READS actual default HPM/HP/HPC/LPD/ACP/ACE AXI interface presence/direction, clock/reset/IRQ pins, available PCW enable/frequency properties. `run_m05_12d2a_ps_inventory.sh` saves new immutable original evidence and `m05_12d2a_ps_inventory_audit.py` fails closed on wrong/missing/duplicate schema. Real Vivado PS IP discovery **PENDING owner** (native fake reports are NOT actual PS evidence). D2b `src/neuromorphic_accelerator_v1/m05_12d2_control_map.py` requires six separate explicit 4KiB-aligned, nonoverlapping PROPOSED control MMIO windows: **three MM2S DMA banks, one S2MM bank, custom shell, independent HLS control**. It has NO default physical addresses, MMIO driver, Linux reservations or `assign_bd_address`; HLS native offsets not assumed. 14 new host-only named tests across D2a/D2b; CI verification separate. AMD UG1085/PG201 says Zynq UltraScale+ HP/HPC DDR-facing PS ports are ≤128 bits while four DMA AXI-MM sides are 256 bits; a genuine future BD will need a verified SmartConnect width conversion, HPM control-plane mapping, suitable clock/reset/IRQ and explicit noncoherent/cache ownership. [M05.12d.2 source/runbook](docs/M05_12D2_PS_INVENTORY_AND_CONTROL_APERTURES_2026_11_08.md). M05 OPEN, PR #79 DRAFT/UNMERGED, NO BOARD.

> **M05.12c GENUINE OWNER VIVADO 2025.2 FOUR-IP CONFIG ACCEPTED (2026-11-08 local / 2026-11-09 UTC):** `~/Thesis_Evidence/neuromorphic_v1_m05_12c_dma_candidate_20261109T003049Z_y5AEce`, checkout `0ea2178c71023250150609a2983a67bbd6c84ef2`, `result.txt exit_status=0`. Four K26 AXI DMA 7.1 IP cells truly report three MM2S-only plus one S2MM-only, all 256-bit AXIS/AXI-MM, SG0, length-width24, addr32, no DRE/micro, async=0; all expected direction pins exist and independent Python audit PASS. Original `02_vivado.log` contained **four BD 41-737 CRITICAL WARNINGs** from attempting to WRITE the read-only `CONFIG.c_prmry_is_aclk_async`; the original *readback was 0* so configuration still passed. Later source stopped writing this field, continued REQUIRING readback0, and added a native regression. Preserve original warning-containing evidence folder; this acceptance covers only **unconnected IP configuration**, NOT PS/DDR/DMA transfers or clocks/route.

> **M05.12d.1 OFFLINE PL STREAM-ONLY CONNECTIVITY DEVELOPMENT (2026-11-08 local):** `rtl/m05_12/m05_12d_axis_shell_ref.v` is an attribute-annotated pass-through of **all 54 original M05.11 shell ports**; 20 AXIS signal attributes group four 256-bit `TDATA/TKEEP/TLAST/TVALID/TREADY` interfaces. `scripts/m05_12d1_axis_graph.tcl` creates an *in-memory K26 Vivado BD*, adds genuine source module reference plus the four 256-bit AXI DMA IPs, uses `connect_bd_intf_net` for the 3 MM2S→shell and shell→S2MM nets, requires each net be **actual point-to-point** using Vivado readback, and audits separate typed report with strict Python checker. **M05.12d.1 Vivado gate NOT YET OPERATOR-RUN; this is only a PARTIAL connected PL AXIS graph**, no real PS DDR/AXI MM/AXI-Lite/HLS/clock/reset wiring, no full BD validation, no physical transfer. [Exact M05.12d.1 engineering/commands](docs/M05_12D1_OFFLINE_PL_AXIS_GRAPH_2026_11_08.md). M05 OPEN; PR #79 remains DRAFT/UNMERGED.

> **ACCEPTED 2026-11-08 LOCAL / 2026-11-09 UTC — M05.11c COMPLETE (genuine OFFLINE XSim + independent replay):** Owner ran original generated signed32 HLS + real shell under Vivado 2025.2 on checkout `bf20f33aa07df2b187bfb837ee5ba2a946cb7098` at `~/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy`, recorded `exit_status=0`, RTL PASS and `PASS: M05.11c raw 256-bit RTL DMA transcript replay`. One successful session generated **24 neural rows + TLAST footer/status0/committed24**, followed without reset by an intentionally invalid session generating **8 provisional rows + TLAST footer/status4/committed0**. 148 HLS/output stalled cycles were observed. Original first FAILED overall gate remains separately archived at `neuromorphic_v1_m05_11c_real_hls_20261108T235448Z_NzKhyY`. The new PASS is genuine integrated **simulated generated RTL**, not physical DMA/DDR/PS or complete routed timing. **M05.12 is now IN PROGRESS; M05 overall remains OPEN, PR #79 draft/unmerged.**

> **CONTINUATION:** M05.12 host-only DMA admission and IP-catalog gates are tracked in [M05.12 engineering document](M05_12_DMA_ADMISSION_AND_IP_CATALOG_2026_11_08.md). No real DMA block design or PS memory ownership has been demonstrated; earlier pending M05.11 text below is historical.

> **M05.11c LATEST (2026-11-08):** Owner **genuine Vivado 2025.2 M05.11b AXI4-Lite controller XSim PASS** `exit_status=0` on checkout `90c31f05a40603914fed507b7f9507220df4d932`; original `~/Thesis_Evidence/neuromorphic_v1_m05_11_axil_20261108T230817Z_HFWBlw`, actual AW/W stagger, R/B backpressure, START/FINISH/ACK, FAULT + verified reset. **M05.11c developed (NOT YET operator XSim verified):** real original Vitis-generated signed32 `m05_rolling_replay` Verilog plus current `m05_11_stream_shell` in one full RTL testbench with **two separate AXI-Lite banks**, 3 padded 256-bit input shims, one 256-bit S2MM-facing TLAST footer. Test two consecutive runs: valid 2-neuron/12-tick recurrent inference must stream **24 rows+1 footer**, hardware status0, COMMIT 24; deliberately unsorted external ticks 0,4,3 must stream **8 provisional+1 footer**, actual HLS status4, REJECT all, custom FAULT (no ACK). Output TREADY 1/7 cycles, exact row semantics and footer counts/session IDs. New `scripts/run_m05_11c_hls_shell_xsim.sh` reuses immutable K26 --impl HLS RTL source + RAM init and regenerates actual HLS regmap, no resynthesis/board. `scripts/m05_11c_replay.py` replays **actual simulator-captured 256-bit handshake words** (16 undefined C padding bits explicitly normalized) through native `accept_dma_frame` and `RollingTraceCommitGate`; independent **14 synthetic native tests**. 231 named M05+91 M01–M04 =322 native tests; **no physical DMA/PS/DDR or new routed clock result**. [Full M05.11c engineering/verification runbook](M05_11C_REAL_HLS_STREAM_SHELL_INTEGRATION_2026_11_08.md); [M05.11b verified register protocol](M05_11B_AXIL_SESSION_CONTROL_2026_11_08.md); [canonical evaluation-engine evolution](M05_EVALUATION_ENGINE_EVOLUTION.md). M05 OPEN; PR #79 DRAFT UNMERGED; no physical board actions.
>

> **LATEST 2026-11-08 — M05.11a owner Vivado XSim VERIFIED; M05.11b AXI-Lite MMIO developed:** Owner's existing bridge XSim evidence `~/Thesis_Evidence/neuromorphic_v1_m05_11_bridge_20261108T224957Z_AQzMlG`, checkout `b3385619b81bc43ee69a082a2f5c8af258e03696`, `exit_status=0`: *both* genuine Vivado 2025.2 standalone bridge RTL snapshots passed (trace 3 TLAST terminal cases +12 egress stalls +sticky overflow, ingress 128/192 unpad +7 ingress stalls +bad TLAST quarantine). **M05.11b NEW:** `rtl/m05_11/m05_11_axil_session_controller.v` 32b AXI4-Lite slave, independently buffered AW/W channels, persistent B/R under backpressure, programmable session/count registers, start/finalize/ACK lifecycle, nonzero-status quarantine; `m05_11_stream_shell.v` structurally wires MMIO control to three input bridges and trace packetizer, all under single clock; typed host-only register client `m05_11_mmio.py` + 14 fake-MMIO tests; new independent RTL testbench + safe Vivado XSim runner. Original HLS kernel and real Vivado OOC timing unchanged. **Icarus RTL AXI bus test PASS + structural shell elaboration PASS**, but **M05.11b genuine Vivado XSim/PS-DMA/HLS integration pending**. Detailed [custom register-map and control lifecycle](M05_11B_AXIL_SESSION_CONTROL_2026_11_08.md), [3-question transport design ADR](M05_11_PS_PL_TRANSPORT_ARCHITECTURE_2026_11_08.md), [evaluation engine evidence history](M05_EVALUATION_ENGINE_EVOLUTION.md). Operator next: `bash scripts/run_m05_11_axil_xsim.sh` in sourced Vivado 2025.2; no board. M05 OPEN, PR #79 DRAFT/UNMERGED.
>
# M05.11 — PS/PL Communication Architecture, Detailed Decisions and Development Record

**Research date:** 2026-11-08  
**Branch:** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`  
**PR:** #79 (DRAFT / UNMERGED)  
**Stage:** M05.11a — *standalone* transport RTL and host packet contract implemented; genuine Vivado XSim, integration with generated HLS RTL, AXI DMA, PS/DDR, routing and physical hardware remain separate gates.

This is the **canonical M05.11 transport/controller decision and development record**. It must be kept in sync with [M05.10 execution controller architecture](M05_EXECUTION_CONTROLLER_DESIGN_2026_11_08.md) and [evaluation-engine optimization evidence](M05_EVALUATION_ENGINE_EVOLUTION.md). Append genuine test dates, exact operator commits, exit results, resource/timing figures and limitations; never overwrite the earlier milestone history.

## 0. Immutable verified starting point

The signed32 `m05_rolling_replay` HLS top is **not modified**. It has three input AXIS ports (128-bit neuron, 192-bit synapse, 128-bit external event), one 192-bit trace AXIS output and an AXI-Lite control interface. Existing streams use `TDATA/TVALID/TREADY`; **no TLAST or TKEEP framing is provided by the HLS core**. One `ap_start` autonomously advances up to 64 logical ticks and up to 4096 signed-W16 deliveries/tick using its exact eight-slot on-chip wheel. Trace rows are **provisional** until `ap_done` and final `ap_return`; a later failure invalidates all previous rows.

**Operator's real M05.9 acceptance:** Vivado 2025.2 direct XSim, original `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T213048Z_241401`, checkout `b8f841ff9585a0e2c479a0eba3578c5fb8a0a1a0`, `exit_status=0`. Same RTL instance, no reset between two HLS calls: status4 after eight provisional rows (0 committed), then status0 after 20 fresh rows (20 committed), clean tick8, 213 stalled output cycles, 11 genuine RAM images staged. The earlier out-of-context placed/routed 6.503ns is **IP-only** and does not apply to these new wrappers or a complete block design.

## 1. QUESTION ONE — How will PS send three inputs and receive the trace?

**DECISION ADR-11.1: prototype with separate concurrently operating AXI DMA directions, all exposing a fixed 256-bit (32-byte) transport beat.**

Proposed first Vivado/PS topology:

```text
   PS / DDR / CPU                  PL transport (NEW)                  PL kernel (UNCHANGED)
   ┌──────────────────┐
   │ ExecutionController / validated RunPlan    AXI-Lite HLS ap_start/args/status
   │ - host buffers/ownership                 ┌────────────────────────────────┐
   │ - 1 session command, at most 64 ticks   │ m05_rolling_replay signed32     │
   │ - provision DMA, check status           │ neurons[127:0]                 │
   └───┬──────────────┘                       │ synapses[191:0]                │
       │                                     │ external[127:0]                │
       │ DDR 256b MM2S neurons ──► [unpad128] ──►                     │
       │ DDR 256b MM2S synapses ─► [unpad192] ──►                     │
       │ DDR 256b MM2S external ─► [unpad128] ──►                     │
       │                                     │ trace[191:0] ───────┐          │
       │                                     └────────────────────┼──────────┘
       │    DDR 256b S2MM ◄─ TLAST footer ◄─ [trace packetizer] ◄───┘
       └── MMIO bridge start/session/expected/finalize (FUTURE M05.11b) ──►
```

- **Three independently managed MM2S source channels** (neurons, synapses, external), plus **one independently managed S2MM destination channel** (trace + terminal footer), all active at run granularity. An initial prototype may use MM2S-only and S2MM-only AXI DMA cores, or an explicitly verified equivalent multi-channel/SG architecture; **no IP count/resource/performance is finalized until Vivado synthesis**.
- Each MM2S source uses one padded 32-byte record: 16 B native neuron + 16 B zeros; 24 B native synapse + 8 B zeros; 16 B native external + 16 B zeros. The 256→128/192-bit `m05_ingress_dma_unpad.v` bridge preserves low HLS bits, verifies high padding=0, full `TKEEP`, and TLAST **exactly on the final expected input beat**. It **consumes** TLAST rather than altering the HLS top. For zero synapses or zero external packets, do **not** arm a zero-length DMA descriptor.
- The 192→256-bit `m05_trace_dma_packetizer.v` forwards each neural trace record in the low 24 bytes of one 32-byte word with zero upper 8 bytes; it forwards immediately under downstream `TREADY`, so long runs do not require holding 65,536 rows in PL memory.
- Transport/memory byte order is specified in [`m05_dma_frame.py`](../src/neuromorphic_accelerator_v1/m05_dma_frame.py) and the proven HLS layout codec `m05_execution_abi.py`. Byte packing and actual PS physical-memory/cache semantics still require live integration proof.
- **Mandatory single-clock assumption for this first isolated RTL bridge:** all its ports are in one clock domain. Full PS fabric design must either use one known clock and reset domain or insert separately validated CDC FIFOs and reset synchronization. Do not directly cross clocks by wiring the new control strobes.

**Why four independent directions first?** It keeps AXI protocol and trace isolation easier to reason about than multiplexing heterogeneous input packets into a single shared stream. Cost and throughput will be measured later; if the four-channel approach is too expensive, consolidate only with a new test and documented equivalent semantics.

## 2. QUESTION TWO — How do we frame output with NO HLS TLAST, especially after errors?

**DECISION ADR-11.2: a 256-bit trace transport whose final beat is a typed terminal footer with TLAST.** The footer is emitted **once per transaction, even if the neural trace is empty**.

Every input and output DMA beat is **32 bytes**, with `TKEEP=0xffffffff`. The trace words carry valid neural data in low 24 bytes and high eight zero bytes. The footer is metadata, **not** a neuron record. The PL trace adapter accepts `finish_valid + finish_status` only after the PS has independently observed genuine HLS `ap_done` and read `ap_return`. On that command, it emits one footer with `TLAST=1`; all previous trace beats have `TLAST=0`. If the DMA sink stalls, footer `TVALID/TDATA/TLAST` are held stable.

Footer field map (256 bits; little-endian lanes):

| Bits | Field | Description |
|---|---|---|
| 63:0 | Reserved | Must equal zero |
| 95:64 | `trace_row_count` | Actual 192-bit HLS trace handshakes accepted by adapter |
| 127:96 | `final_status` | 0..6 copied from PS's observed AXI-Lite `ap_return` |
| 191:128 | `session_id` | Unique 64-bit run ID chosen/checked by PS |
| 255:192 | `magic` | ASCII `M0511END` = `0x4D30353131454E44` |

**Examples:**

- **Success:** N neurons × T ticks => exactly N*T neural words + one terminal footer. Final status 0; host accepts only after full verified length, footer, independent AXI-Lite status and quiescence.
- **Late error:** 8 valid-looking provisional neural words, then status 4; footer contains count8, TLAST=1. DMA completes its packet; **host accepts zero rows** and resets/flushes transport before another run.
- **Early error with no trace:** footer alone, 32 B with status1..6 and TLAST=1. This avoids a *forever-incomplete S2MM descriptor* on a zero-row failure.
- **Malformed claimed success:** if PS sends status0 while adapter counted fewer than N*T rows, adapter substitutes reserved status `0xFFFF0001`; host rejects. Invalid status >6 produces reserved `0xFFFF0002` and is rejected. Overproduction beyond allocated N*T never forwards an extra beat: adapter enters a sticky fault, demanding reset/flush rather than risking a DMA memory overrun.

**Maximum supported receive capacity:** `(N*T + 1) * 32` bytes. At 1024 neurons ×64 ticks, **(65,536+1)×32 = 2,097,184 bytes**. Do **not** use a Micro DMA mode requiring an exact receive packet byte count when the actual count may be shorter on error. AMD PG021 [S2MM_LENGTH](https://docs.amd.com/r/en-US/pg021_axi_dma/S2MM_LENGTH-S2MM-DMA-Buffer-Length-Register-Offset-58h) specifies that non-Micro DMA's available buffer length must cover the *largest* packet, and actual transferred bytes are returned after completion. Final hardware parameter selection and TKEEP/DRE/alignment will require live Vivado verification.

**Host acceptance:** [`accept_dma_frame`](../src/neuromorphic_accelerator_v1/m05_dma_frame.py) refuses any packet unless caller attests actual DMA completed, its TLAST was certified, its reported transfer length matches the byte buffer, transport is quiescent, and independently read HLS `ap_return` matches the footer. It rejects incorrect session ID, magic, reserved fields, padded trace bits, row count, malformed/duplicated trace or status0 with incomplete trace. It feeds original `RollingTraceCommitGate`: nonzero statuses always discard provisional rows. All tests currently use **synthetic host packets**; a future PS backend must supply non-fabricated completion evidence.

### Why not the standard AXI4-Stream FIFO by itself?

AMD's [PG080 AXI4-Stream FIFO core overview](https://docs.amd.com/r/en-US/pg080-axi-fifo-mm-s/Core-Overview) lists supported stream widths 32/64/128/256/512, **not native 192**, and [PG080 protocol](https://docs.amd.com/r/en-US/pg080-axi-fifo-mm-s/Protocol-Description) uses TLAST for packet completion. Simply wiring the existing 192-bit no-TLAST trace to an off-the-shelf packet FIFO/DMA does not solve the end-of-run problem. The explicit 256-bit adapter supplies both the width and framing conversion.

### Important status/protocol limitation (do not claim independently hardware-originated footer status)

The first wrapper's `finish_status` is **supplied by PS software**, not tapped directly from an inaccessible internal HLS control signal. Cross-checking footer with PS `ap_return` detects transport corruption but **cannot detect a PS bug that originally read the wrong status and then copied it into the footer**. The future PS MMIO bridge, generated AXI-Lite address map and driver read-to-clear semantics must be verified independently. This wrapper is not an autonomous PL hardware error detector.

## 3. QUESTION THREE — How will start, completion, DMA and recovery be coordinated?

**DECISION ADR-11.3: PS-managed per-run lifecycle with receive-first arming, concurrent ingress and trace drain, terminal-status handshake, and explicit error quarantine.**

### Nominal successful transaction, exact sequencing

1. **Validate before hardware:** admission using `RunPlan`; allocate **uniquely owned**, correctly aligned DDR buffers. Encode three input arrays using `build_mm2s_buffers` (32 B per element); provision a 32 B-aligned S2MM buffer of at least `32*(N*T+1)`. Configure CPU cache flush/invalidate policy and DMA buffer lifetime explicitly.
2. **Verify previous session is idle and isolated.** Choose a non-reused `session_id`; ensure old DMA completions, FIFOs, clocks and interrupts are not still carrying data. A clean HLS `ap_idle` bit alone does **not** certify all stream queues clean.
3. **Arm S2MM receive channel FIRST** with capacity for maximum success trace + footer. This must be active before HLS can emit data. Program trace packetizer session ID and `expected_rows=N*T` through the **future command MMIO bridge**, wait for acknowledgement. Configure three input unpad shims with input record counts.
4. **Arm MM2S input channels** only for nonzero counts, with BTT `32*count`. Their 256-bit stream words carry exact per-record `TLAST` on last. Use a verified mechanism to preserve per-port order and observe completion/retirement, avoiding cache use-after-free.
5. **Write genuine HLS AXI-Lite registers** (neuron/synapse/external counts, ticks, decay_num/den) using offsets from **the actual Vitis generated `*_hw.h` or control RTL**, not guessed constants. Issue exactly **one** HLS `ap_start` per run.
6. **Service concurrently:** nonblocking progress of input DMA and S2MM; monitor the HLS AXI-Lite `ap_done` and **latch the real `ap_return` once**, respecting any read-to-clear semantics. Never block on S2MM completion before reporting finalization, since S2MM awaits TLAST; never block on `ap_done` *before arming/servicing S2MM*, since trace backpressure can prevent kernel completion.
7. **After HLS final status is observed**, send `finish_valid/status` to packetizer through new MMIO bridge, wait for `finish_ready` acknowledgement. It transmits the final footer beat, asserting TLAST, so S2MM can finish and report actual byte count. For success also ensure every MM2S completed and all shims accepted expected counts.
8. **Check DMA completion + frame:** S2MM finished without error; actual received bytes align to 32; verified last footer/session/status/count; no outstanding ingress buffers; transport quiescent. Only then call the existing host commit gate with status0. **Publish all N*T rows atomically**, then permit another session.

### Expected hardware failure (BAD_EXTERNAL etc.)

- HLS may return nonzero after consuming only a **prefix of input data**; MM2S may still have descriptors waiting for HLS TREADY. **Do not wait forever for all input MM2S to complete.**
- Finalize trace footer using the **real nonzero HLS status**, allowing the S2MM packet to end even if it contains zero or few trace rows. Any provisional neural rows are immediately unpublishable.
- Stop/cancel/flush unfinished MM2S and pending future input data; inspect DMA errors; drain or reset trace queues and wrapper as required. Mark controller **FAULTED** and prohibit reuse until independently verified clean-state recovery. Do not assume M05.9's successful HLS-alone restart implies the *full DMA/interconnect* is clean.
- Do not retry automatically after invalid input/error; a retry would be an explicit new session with new ownership and ID.

### Timeout / transport fault / missing TLAST

- Enforce host-side wall clock and service step deadlines; a blocked or late DMA can defeat simple polling. No part of the controller may block indefinitely on an input or output port.
- Cancel/reset and verify *all* MM2S, S2MM, shims, FIFO descriptors, HLS reset/control, and MMIO command bridge together, in an approved sequence. **Never assert reset while a memory write remains uncontrolled.**
- An incomplete or corrupted footer, DMA error, missing completion, stale session ID, overproduced rows or failed quiescence fence invalidates the run and requires explicit recovery. No result is published.
- The first bridge is single-clock. Cross-clock reset and AXIS CDC need independently verified wrappers before PS/PL clock domain integration.

### Quiescence: what constitutes a run boundary?

The controller's `is_quiescent()` contract **cannot be implemented as merely “HLS ap_done or FIFO empty.”** A future real adapter needs evidence that: HLS is terminal, input DMA channels are completed on success or flushed on error, packetizer footer has handshaked, S2MM reports actual completion/byte count, no outstanding DDR writes remain, and the session ID/descriptor ownership is retired. After faults, a reset-verified isolation fence is required before any new session. This is a hard acceptance gate for a real driver.

### Pending MMIO controller IP

The current `m05_trace_dma_packetizer.v` and `m05_ingress_dma_unpad.v` expose **start/expected/session/finish/status as synchronous CONTROL WIRES, not bus-addressable registers**. M05.11b must implement or integrate an AXI-Lite slave command/status peripheral to drive them and provide acknowledgements/fault/done/counts to PS; this custom control block needs its own address map and verification. No fabricated register offsets are committed. This separation lets us verify the pure datapath *before* creating the full AXI-Lite register machine.

## 4. Implemented files and precise development gates

| File | Exact deliverable | Current evidence |
|---|---|---|
| `rtl/m05_11/m05_trace_dma_packetizer.v` | 192→256 trace, counted stream, session ID, valid status footer, TLAST and sticky overproduction fault | Synthesizable source + source-only native checks; **new direct XSim pending** |
| `rtl/m05_11/m05_ingress_dma_unpad.v` | Parameterized 256→128/192 ingress, fixed 32-B record, last-beat TLAST validation, zero-count support, sticky malformed-beat fault | Source-only checks; **new direct XSim pending** |
| `rtl/m05_11/tb_m05_11_packetizer.sv` | Standalone Verilog directed success, zero-trace error, short claimed success, downstream stalls, overproduction | **Operator XSim pending** |
| `rtl/m05_11/tb_m05_11_ingress.sv` | Standalone 128/192 input identity, real READY stalls, exact TLAST and zero-count, malformed early TLAST | **Operator XSim pending** |
| `src/.../m05_dma_frame.py` | Input fixed-32B-buffer encoding, conservative S2MM footer parser and atomic transaction status/length/session validation | Native host tests, **NOT live DMA** |
| `tests/test_m05_dma_frame.py` | 18 native synthetic packet/ABI/source negative and positive tests | Native CI; not RTL |
| `scripts/run_m05_11_bridge_xsim.sh` | Safely run two standalone bridge RTL XSim testbenches, fresh evidence folder, commit/source hashes | **Operator-run genuine XSim pending** |

No edits to `hls/m05_rolling/m05_rolling.cpp`, its verified Verilog or previous accepted RTL bench. The only new hardware components are stand-alone **transport logic**, not a fully integrated controller. No FPGA, JTAG, Vivado implementation or PS physically touched.

## 5. Acceptance plan — do not collapse test levels

| Gate | Required observation | Status |
|---|---|---|
| **M05.11a** source/host | Native syntax/unit tests and packet parser, exact byte layouts, error quarantine, historical M05/other regressions | In native CI; separate from simulator |
| **M05.11a** standalone RTL | Genuine XSim PASS both new testbenches including no-row TLAST, 128/192 unpad, input/output TREADY stalls and early error | **PENDING operator** |
| **M05.11b** bridge command MMIO | Actual bus-connected session/start/finish/status logic, generated address map and software handshake verified via RTL | PENDING |
| **M05.11c** integrated HLS RTL + bridges | Existing real signed32 generated HLS kernel plus 3 input and 1 output adapters, successful run and late error, backpressure, no stale sessions | PENDING |
| **M05.12** PS+DMA driver/RTL | Real DMA descriptor lifecycle, output TLAST completion and actual-byte checks, cache coherency, abort/reset/quiescence | PENDING |
| **M05.13** K26 full design/board | Whole-PS/PL routed timing/resources, physical transactions and recovery; only with explicit owner approval | PENDING |

**Do not infer full-system timing/BRAM from the earlier signed32 HLS-IP OOC 6.503ns result.** Do not claim AMD IP has been instantiated or that current native tests verify DMA. M05 remains OPEN; PR #79 remains DRAFT/UNMERGED.

## 6. Local reproducibility (Vivado 2025.2 sourced; NO hardware)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
cd Neuromorphic_Accelerator/v1

python3 -m unittest discover -s tests -p 'test_m05_dma_frame.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
bash -n scripts/run_m05_11_bridge_xsim.sh

# Generate fresh evidence only: never overwrite operator's earlier M05 or Loihi logs
bash scripts/run_m05_11_bridge_xsim.sh

export BRIDGE_EVIDENCE="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_11_bridge_* | head -n 1)"
echo "$BRIDGE_EVIDENCE"
cat "$BRIDGE_EVIDENCE/result.txt"
cat "$BRIDGE_EVIDENCE/commit.txt"
tail -n 60 "$BRIDGE_EVIDENCE/04_packetizer_xsim.log" 2>/dev/null || true
tail -n 60 "$BRIDGE_EVIDENCE/04_ingress_xsim.log" 2>/dev/null || true
```

The two standalone XSim tests DO NOT need the original generated HLS kernel or hardware board. If Vivado fails at compilation/elaboration, preserve that evidence and fix only this new transport logic/testbench. Do not label M05.11a RTL acceptance complete until both genuine XSim commands finish with explicit PASS markers and exit0.

## 7. AMD primary references (checked for 2025.2-era design choices)

- [PG021 AXI DMA 7.1, S2MM](https://docs.amd.com/r/en-US/pg021_axi_dma/S2MM) — AXI4-Stream incoming packet ends on TLAST.
- [PG021 Direct Register Mode / Simple DMA](https://docs.amd.com/r/en-US/pg021_axi_dma/Direct-Register-Mode-Simple-DMA) — S2MM channel must be prepared, receive buffer ≥ maximum expected packet, Micro DMA length caveat.
- [PG021 S2MM_LENGTH](https://docs.amd.com/r/en-US/pg021_axi_dma/S2MM_LENGTH-S2MM-DMA-Buffer-Length-Register-Offset-58h) — actual byte count after completion and available-buffer sizing.
- [PG021 DMA feature summary](https://docs.amd.com/r/en-US/pg021_axi_dma/Feature-Summary) — DMA width and PS interconnect options.
- [PG080 AXI4-Stream FIFO core overview](https://docs.amd.com/r/en-US/pg080-axi-fifo-mm-s/Core-Overview) and [protocol](https://docs.amd.com/r/en-US/pg080-axi-fifo-mm-s/Protocol-Description) — supported widths, packet/TLAST semantics; explains why an unmodified 192-bit no-TLAST core cannot simply be dropped onto a packetized FIFO.

These vendor statements are **external design constraints**, not a claim that our chosen block diagram has been synthesized or tested on K26. Actual Vivado 2025.2 IP wizard parameters and PS operating environment must be checked against the installed tool release before hardware deployment.
