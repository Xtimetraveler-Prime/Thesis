> **M05.11a ADDENDUM (2026-11-08):** The three unanswered PS/PL communication questions now have specific, cited architecture decisions and **working independently simulated RTL prototypes**. Proposed 3 independent 256-bit MM2S inputs + 1 256-bit S2MM output, with low-128/192-bit unpadding. A separate 192→256-bit trace packetizer emits one 32-byte terminal footer with TLAST on **every completed HLS invocation**, including zero-trace failures; footer carries actual trace count, session ID and PS-supplied HLS ap_return. Application may publish only after true S2MM completion, independently checked HLS AXI-Lite status, exact framing and a verified quiescent fence. Host-controlled MMIO start/finish/status bridge and live DMA/DDR remain unimplemented; do NOT claim physical integration. Original HLS engine unchanged. **Icarus/CI simulated BOTH independent RTL testbenches PASS** at commit `5fa649ddd354e5c36351148af16629a9bccd2227` / M05 workflow `42528838308`; 203 M05 native Python tests PASS separately. **Vivado 2025.2 XSim for these wrappers remains PENDING**, as do MMIO, end-to-end HLS connection and full PS/PL timing. [Complete M05.11 ADR — questions 1–3, architecture diagram, exact field map, sequence/recovery, AMD references, acceptance gates](M05_11_PS_PL_TRANSPORT_ARCHITECTURE_2026_11_08.md). Do not misattribute host-only controller status to hardware, nor previous HLS 6.503ns OOC closure to these wrappers.
>

# M05.10 — Execution Controller: Architecture, Protocol, and Development Record

**Date:** 2026-11-08 · **Branch:** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip` · **PR:** #79, draft/unmerged · **Status:** host-model implementation complete, no physical PS/PL driver implemented. The signed32 rolling RTL kernel is unchanged.

**This is the canonical detailed document for the run-level execution controller.** Maintain it alongside [the separate evaluation-engine optimization ledger](M05_EVALUATION_ENGINE_EVOLUTION.md); append dated evidence for each new controller milestone. Distinguish host unit tests, direct RTL XSim, offline place/route and actual physical K26 measurements. Never relabel host simulation as FPGA execution.

## 1. Operator-confirmed starting point: M05.9 closed

Original **operator-run** Vivado 2025.2 XSim evidence: `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T213048Z_241401`, checkout commit `b8f841ff9585a0e2c479a0eba3578c5fb8a0a1a0`, `exit_status=0`. Generated RTL compiled and elaborated; eleven authentic BRAM initialization .dat files staged. On **the same RTL instance with no reset pulse between runs**:

| Same DUT / separate ap_start | Status | Streamed rows | Accepted after final status | Specific proof |
|---|---:|---:|---:|---|
| Run0, invalid external order 0,4,3 | **4** (BAD_EXTERNAL) | **8 provisional** | **0** | t0 spike was valid; whole failed run discarded |
| Run1, fresh network, 0 synapses, external t1/n1 | **0** (OK) | **20** | **20** | t1/n1 spike, **no stale t8 wheel event** |

**213 output-stall cycles** observed across both. The final Python replay used *actual XSim trace records*, not invented results. This proves directed **RTL kernel transaction reuse** and an **offline** host commit/discard policy, **NOT** real PS DMA recovery. No new bitstream, board programming or new routed clock results were generated. The existing post-route OOC **6.503 ns against 10 ns**, 35 BRAM, 6257 LUT, 6887 FF, 2 DSP is an earlier, independent operator proof.

## 2. Split of responsibilities

The FPGA **evaluation engine** already runs neuron ticks and synaptic recurrence autonomously after **one ap_start per run**. The new **execution controller** belongs conceptually to PS software and handles entire *transactions*, not individual ticks.

```text
   CPU / Zynq Processing System                         PL / programmable fabric
   ┌──────────────────────────────────┐              ┌─────────────────────────────┐
   │ validate network / inputs         │              │ m05_rolling_replay          │
   │ prepare byte-exact input streams  │  AXI-Lite    │ on-chip neuron + wheel RAM │
   │ run-level ap_start/status monitor │ ───────────►│ ap_start, counters, status  │
   │ 3 nonblocking input feeders       │ 3 x AXIS    │ internal event propagation  │
   │ concurrent trace drain            │ ───────────►│ neuron / synapse / external│
   │ provisional trace staging         │ 1 x AXIS    │ trace TDATA/TVALID/TREADY  │
   │ final commit OR abort/flush       │ ◄───────────│                             │
   └──────────────────────────────────┘              └─────────────────────────────┘
           ╰────────────── future transport adapter / DMA/FIFO ──────────────╯
```

**M05.10 delivers host orchestration contracts, not a real transport.** No Linux mmap, actual AXI DMA IP, interrupts, physical reset line, Vivado block diagram or PS DDR transfer is implemented yet. Selecting and verifying those belongs to M05.11 onward.

## 3. Source inventory and ownership

| File | Responsibility | Verification |
|---|---|---|
| `src/neuromorphic_accelerator_v1/m05_execution_controller.py` | Immutable validated request objects, `ExecutionTransport` protocol, controller lifecycle, bounded cooperative service, timeout and explicit recovery | Python/native |
| `src/neuromorphic_accelerator_v1/m05_execution_sim.py` | Finite-capacity *scripted fake* with independent ingress/output stalls, early completion, missing rows, error injection and a quiescence delay | Python/native, **not real DMA** |
| `src/neuromorphic_accelerator_v1/m05_execution_abi.py` | Exact observed 128/192/128/192-bit AXIS TDATA field layout and Python pack/decode functions | Native tests using bit offsets validated in earlier real XSim |
| `tests/test_m05_execution_controller.py` | Control-state/transport/admission/error and nonblocking service coverage | Native only |
| `tests/test_m05_execution_abi.py` | Byte offsets, signedness, padding, exact width, trace-decoder-to-host-gate parity | Native only |
| `scripts/m05_controller_native_demo.py` | Deterministic demonstration of status4 abort, explicit fake recovery, status0 success | **SIMULATED** only |
| Existing `m05_trace_commit.py` | Single authority for provisional trace → accepted transaction promotion, reused **unchanged** | Previously verified native + actual XSim transcript replays |

## 4. Immutable RunPlan and admission

`NeuronConfig` accepts signed-W16 voltage/bias/reset, threshold 1..32767, reset below threshold. `SynapseConfig` admits pre/post IDs in [0,1023], signed-W16 weight, synaptic delay 1..8. `ExternalEvent` admits tick 0..63, neuron ID 0..1023, signed-W16 current.

`RunPlan` contains immutable **tuples** of those objects and one-decay-fraction run configuration: 1..1024 neurons; <=4096 synapses; 1..64 ticks; unsigned 32-bit decay parameters satisfying 0<=numerator<=denominator and denominator>0. It validates synapse endpoints, external tick/neuron IDs, **nondecreasing external tick order**, max 4096 *external* events in a single tick and <= ticks*4096 total.

**All request validation happens before calling the transport.** This is a conservative application-facing contract; the RTL diagnostic tests deliberately inject out-of-order events to prove hardware status4. No preflight can guarantee future recurrent fanout does not trigger hardware status5; the controller must handle any returned 1..6.

## 5. ExecutionTransport — mandatory real adapter contract

The new Python type `ExecutionTransport` is a Protocol: it specifies behavior, **not** actual PS/PL calls.

| Method | Exactly required semantics |
|---|---|
| `begin(plan)` | Program generated AXI-Lite parameters, issue exactly one `ap_start`. Must not automatically restart hardware after uncertain failure. |
| `try_send(port,payload) -> bool` | **Nonblocking** one-beat acceptance on exactly one of `neurons`, `synapses`, `external_events`; false means no transfer and the controller must retry the **same** packet. |
| `try_receive() -> row or None` | Nonblocking, strictly ordered capture of one *completed* trace transfer. Must not duplicate data or wait for ap_done before draining. |
| `poll_completion() -> int or None` | None while not done; after terminal `ap_done` and valid 32-bit `ap_return`, return the *latched* status 0..6 stably. Read-to-clear `ap_done` must be cached safely. |
| `is_quiescent() -> bool` | **Hardware-meaningful transport fence** after successful completion: all ingress fully retired, no remaining buffered/in-flight output, and no future beat from that run can appear. FIFO *currently empty* alone is insufficient. |
| `advance()` | Bounded nonblocking service opportunity for DMA completions/interrupts/queue progress. Not an FPGA clock. Must not sleep indefinitely. |
| `reset_and_verify_idle()` | Explicit transport + kernel reset/flush/rearm, with confirmation there are no outstanding DMA descriptors/AXIS beats; raise if unverifiable. |

### The cooperative concurrency decision

`ExecutionController.execute(plan)` is a **synchronous loop** that interleaves all inputs, trace draining and completion polling each service iteration. The future adapter must never implement these methods as blocking per-stream reads/writes.

```text
IDLE -> validated plan -> begin ONE ap_start -> RUNNING
           repeat until bounded budget/deadline:
             try_send(neurons), try_send(synapses), try_send(external)
             try_receive(trace) -> RollingTraceCommitGate.offer_row(...)
             poll_completion()  [not before draining]
             if status0 + all ingress accepted + exact output frame +
                transport-certified quiescent: complete(0), publish, IDLE
             if status nonzero: complete(status), discard all, FAULTED
             advance()
           if wall clock or service-step limit: abort(), FAULTED
FAULTED -> explicit recover() -> reset_and_verify_idle() -> IDLE
            (if recovery raises, remain FAULTED; no automatic retry)
```

The trace remains **provisional** until all conditions for status0 acceptance hold. Observing an early status0 does **not** mean the last trace beat has been drained; the controller deliberately continues servicing. The accepted result contains at most **1024*64=65536** rows staged by the existing bounded host receiver.

### Why we quarantine even an expected hardware status4

M05.9 genuinely proved the HLS **kernel itself** can restart after a handled status4 without a PL reset. However, a real DMA bridge may still contain prefetched invalid input, residual output or stale descriptors. M05.10 therefore **blocks subsequent runs after any failure** until explicit `recover()` succeeds. A future adapter may replace a full reset with a **separately proven error-quiescence/flush fence**, but cannot assume that from the kernel RTL proof alone.

### Timeouts, status and error semantics

`execute(..., max_service_steps=100000, wall_timeout_s=30.0)` uses two bounded limits. A service step is a **CPU loop opportunity**, not a fabric cycle, latency benchmark, HLS initiation interval or throughput. An implementation that blocks indefinitely inside a transport call violates the contract (and may defeat the wall timeout).

Result `ExecutionReport` exposes `TraceRunResult`, the status (or None if unobserved), ingress counts, service steps and `needs_recovery`. On a bad status, malformed stream row, count mismatch, timeout, unknown/inconsistent status or transport exception, it publishes **zero accepted rows** and quarantines. **No automatic retries** and no partial inference visibility.

## 6. Exact generated-TDATA ABI (not generic C/DMA ABI)

Derived from bit offsets tested in the original direct RTL XSim testbenches:

| Stream | Verilog TDATA | Python little-endian logical layout | Key offsets |
|---|---:|---|---|
| neuron input | 128 bits / 16 B | `<iiii` | Four signed 32-bit fields: initial voltage/bias/threshold/reset |
| synapse input | 192 bits / 24 B | `<IIi4xQ` | pre, post, signed weight, **32 bits C padding**, 64-bit delay |
| external-event input | 128 bits / 16 B | `<QIi` | tick (u64 low bits), neuron ID (u32), signed current (i32) |
| trace output | 192 bits / 24 B | `<QIiBB2xI` | tick, neuron ID, signed voltage, spike, evaluated, **16 bits padding**, delivered_count |

`decode_trace` returns `RollingTraceRow`, and the existing commit gate performs the strict voltage/spike/delivery/framing validation. C padding in returned trace is **ignored** (not treated as semantically zero); newly generated input words set padding to zero.

**Critical limitations:** The Python pack formats describe logical TDATA lanes seen in **one proven generated RTL snapshot**. A future DMA descriptor, PS physical memory byte order, stream width converter, cache mapping or another Vitis revision can change what is actually transported. Before implementing the live adapter, compare **the real generated port widths / bitfield signals and registers** and validate with an independent hardware or RTL bridge test. Never silently assume this codec alone proves real DMA ABI.

### Blocking system-integration risk: no TLAST signal

The existing HLS-generated AXIS ports in the verified RTL had **TDATA, TVALID, TREADY** only. **No TLAST/TKEEP packet framing was demonstrated.** Common AXI DMA S2MM completion paths use TLAST as end-of-packet. It is **unsafe to wire the existing trace stream to an assumed packetized DMA and expect completion** without an explicit framing design.

M05.11 must select and prove one of the following: an explicit-length AXIS receive FIFO/PS bridge with a full transaction-quiescence fence; a PL wrapper generating correct TLAST and failure/partial-frame abort semantics; or another length-counted transport that does not require TLAST. Success expects exactly `neuron_count*ticks` trace beats; **failed runs have unknown partial lengths**. Any wrapper must handle an arbitrary prefix and clear it safely before the next transaction. A new wrapper requires **new RTL stress tests and full-system timing/resource validation**; the earlier 6.503 ns OOC top-only result is not transferable to the larger system.

Other M05.11 gates: choose exact K26 PS/PL clock/reset distribution, AXI-Lite map via actual Vitis `*_hw.h`, 3 H2C + 1 C2H flow, cache coherency/DDR buffer ownership, interrupts vs polling, reset and error fences, and trace session identification. Do not infer a particular Vivado block diagram has already been built.

## 7. Verification inventory and explicit evidence categories

**New M05.10 tests** cover: valid/invalid RunPlan width/shape and sorted events; bounded input FIFOs with actual fake backpressure; independent 3-port ingress; output drain while sending inputs; hardware completion observed before last buffered output; exact frame and transport quiescence; missing/excess/invalid rows; late hardware statuses; unknown/inconsistent completion; transport I/O failures; step-budget timeout; explicit recovery and failed reset; exact 16/24/16/24 byte lane encoding. All **native Python only**.

The native `ScriptedTransport` deliberately never computes a neural graph, never drives AXI signals and is not a throughput model. It is a fault-injectable contract test double. The operator's previous genuine XSim runs remain independent proof for **the evaluation engine**, not proof for this new PS controller.

Reproduce locally without Vivado:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05_execution*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
python3 scripts/m05_controller_native_demo.py
```

Demo output is intentionally labeled **SIMULATED**. It proves the host contract only; it does not contact Vivado or the K26.

## 8. Incremental controller roadmap — update this table with each real gate

| Increment | Concrete objective | Required evidence | Status |
|---|---|---|---|
| **M05.9** | Two `ap_start` calls on one RTL instance after late failure without hardware reset | Genuine direct XSim 8+20 rows, status4 then status0, t8 clean | **VERIFIED** |
| **M05.10** | Transport-agnostic host controller with atomic commit, validated ABI, bounded three-stream pump, explicit recovery model | Native tests, source version hashes, documented state/transport contract | **HOST IMPLEMENTATION BUILT** |
| **M05.11** | Choose/implement PS/PL stream bridge and frame/no-TLAST policy | Generated-IP map + new RTL bridge test, including failed partial stream | **PENDING** |
| **M05.12** | Connect host controller to a real/non-mock transport and exercise DMA, completion/IRQ, quiescence, error/timeout reset | Independent full-stack RTL/PS interface test | **PENDING** |
| **M05.13** | Full Vivado PS/PL design routed timing; physical K26 only with owner authorization | Operator logs with hardware resource, clock/timing and live transactions | **PENDING** |
| **M05.14** | Identical-workload throughput, DDR transfer, power/energy experiments | Actual counters and platform measurements | **PENDING** |

M05 **OPEN**, PR #79 **DRAFT / UNMERGED**. No source changes to the signed32 evaluation HLS top, no physical device operations and no edits/deletion of the existing operator-original `~/Thesis_Evidence` folders or Loihi/v2 Vivado journals.
