# M04.5 — Evaluation-engine numerical requirements and M05 implementation handoff

**Decision status:** M04.5 requirements/handoff **COMPLETE as a proposed, host-only engineering specification**, 2026-11-07 local. **Parent M04 remains OPEN, unaccepted and unmerged** until explicit user closure/merge instruction. This document does not authorize FPGA/JTAG or constitute an RTL/physical performance result. Applies to M02 **accepted revision 1**; superseding that numerical contract requires explicit separately versioned approval.

**Source lineage:** `main` M03 merge `2ceac0372ed6ec11fb09c764277e4532b4807e46`; [M02 contract](M02_PROVISIONAL_LIF_CONTRACT.md), [M04 v3 audit](M04_HLS_ENGINE_AUDIT.md), [M03 traffic/measurement contract](M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md), and [M01 residency options](M01_ARCHITECTURE_OPTIONS.md). Historical v3 engine is not a v1 implementation requirement. External hardware and HLS specifications are from AMD DS987 (K26 programmable logic) and UG1399 (2025.2 Vivado IP/AXIS interfaces): https://docs.amd.com/r/en-US/ds987-k26-som/Programmable-Logic and https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/pragma-HLS-interface . No outside source code reused.

## 1. Binding neural invariants (M02 revision 1)

For logical neuron `i` at tick `t`, compute **exactly once**:
```text
d = trunc_toward_zero(previous_v * decay_num / decay_den)
I = sum(all signed external and delayed synaptic currents arriving at (t,i))
u = saturate_W(d + bias[i] + I)      # ONE final saturation, not per event
spike = (u >= threshold[i])          # inclusive
next_v = reset_v[i] if spike else u
```
`4 <= W <= 32` (default 16); signed stored voltage, bias, threshold and reset must lie in W-bit range, threshold > 0, reset < threshold; `0 <= decay_num <= decay_den`, `decay_den >= 1`. M02's rational decay is global per network. **No synaptic-current persistence, refractory, approximate/lazy leak, float arithmetic, same-tick propagation or event-order-dependent clamping**. Every positive-delay recurrent/self edge delivers no earlier than `t+1`. A nonzero prior voltage, nonzero bias or delivery destination is eligible for evaluation; the M03 exact-skip lemma is the only accepted initial elision. Trace comparison is *every tick's full voltage row and sorted spike IDs*, not end-of-run class.

## 2. Chosen first K26 engineering profile — assumptions, not M02 restrictions

| Parameter | M05.1 first-profile assumption | Engineering rationale / review status |
| --- | --- | --- |
| Device/tool | KV260 / K26, `xck26-sfvc784-2LV-c`; Vitis/Vivado **2025.2** where available | Matches old lab tool/part setup; do not execute old v3 scripts. |
| Physical compute | **One** stateless time-shared LIF update pipeline; not 27 logical cores | Small baseline isolates scheduling/memory cost and leaves resources for queue and DDR experiments. More lanes are future controlled variants. |
| Clock | **100 MHz** / 10 ns synthesis goal, 12% requested clock uncertainty | Historically routable shell target; **not** a guarantee of v1 Fmax or timing closure. Require offline csynth and routed reports later. |
| Stored neural values | **W=16** for the initial synthesizable profile; C++ reference stays parameterized `4..32` | Baseline M02 width limits state traffic and arithmetic; W=32 is a later compiled/verified variant, not quietly truncated. |
| Decay ratio | Nonnegative `u32 num/den`, `den>=1` (global per network) | Matches existing M04 C++ request and bounds the 64-bit product; variable integer division may dominate II/area, so measure instead of substituting a rounded reciprocal. |
| Delivery transport | Signed `i64` **already-exact per-(tick,id) aggregate** | Represents bounded algebraic cancellation without clipping; state saturates only after adding decay and bias. |
| Per-tick admitted arrivals | **4096 total signed contributions** across the network for a tick, counting each external current and each delivered synaptic edge separately | Deliberately conservative first on-chip **admission envelope**; **not** inherited as a compulsory v3 logical-core limit. If exceeded, use proved lossless spill/backpressure or mark run invalid; never drop/clamp. Multiple arrival ticks need additional independently bounded queue storage. |
| Logical metadata | `neuron_id:u32`, `neuron_count:u32` (nonzero), `tick:u64`; old `v:i32` and neuron parameters `i32` | Independent of cache block/group and compute engine; the actual physical stream packing is **not frozen**. |
| Memory study starting point | 1024 resident logical neurons, 8-neuron state blocks, **16 bytes/accounted neuron**; 4096×16-byte one-tick delivery-slot *planning illustration* | 16 KiB modeled state + 64 KiB one-tick slots = 80 KiB raw (~18 BRAM36-equivalent capacities **before** bank/port overhead), comfortably smaller than whole K26 PL memory; **not** an implementation/utilization or total future-event-queue bound. Compare different group sizes in M07. |
| Initial output | Echo ID/tick, next voltage, spike bit, status; separate commit stage | Can test stateless arithmetic independently of scheduling, caching, and DDR. Invalid request must not modify neural state. |

**K26 physical context (device totals, not available-to-this-IP budgets):** AMD DS987 lists 117,120 CLB LUTs, 234,240 CLB FFs, 144 BRAM36 blocks, 64 UltraRAM blocks, and 1,248 DSP slices. K26 SOM has DDR4 backing; the actual PS/Linux reservations, memory ownership, AXI path and achievable DDR bandwidth are **not** established by these totals. First synthesis should report isolated engine versus full integrated shell, not equate capacity with usable allocations. The 80 KiB illustration includes neither routes nor multi-tick pending deliveries, and does not assert BRAM mapping.

## 3. Numeric range proof and explicit admissibility

**Accepted M02 itself is unbounded** in event count and Python-integer `I`, and does not bound rational numerator/denominator. The first hardware profile is a **subset of legal M02 workloads**, not a modification of M02. To admit a deployment, validate all standard M02 conditions **and**:

1. `state_bits=16` for the first synthesized image (or an explicitly compiled separately tested alternate width `4..32`), `0 <= num <= den <= 2^32-1`, `neuron_count <= 2^32-1`, and all tick IDs fit unsigned 64 bits. Neuron parameters and each individual weight/current fit signed W bits per M02.
2. Every tick must receive at most **4096 individual contributions in total**, regardless of whether their sum cancels. Count external pulses **and** scheduled synaptic edges, including parallel edges; horizon-exceeding future deliveries are not applied to the requested finite run. Runtime/unseen inputs also need an online capacity check, not only offline trace preflight.
3. Under these premises, at W<=32, `|I| <= 4096 * 2^31 = 2^43`; signed **i64** covers all aggregates. `|old_v * num| <= 2^31*(2^32-1) < 2^63`; signed i64 covers the leak product. Because `num<=den`, `|trunc(old_v*num/den)| <= 2^31`; adding `bias` and `I` remains below `2^43 + 2^32` in magnitude, safely within signed i64. For negative values use truncation **toward zero**. Then clamp once to signed W, compare inclusively and reset. This is exact mathematical parity in the admitted domain, independent of arrival ordering.
4. **Fail-closed boundary:** if input ratio, ID, tick, event count, queue capacity, aggregation representation or memory mapping is invalid, raise a sticky explicit error and declare the run **invalid**; no partial inference or synthetic PASS. Before hardware commit, do not write a state update for a rejected request. On-the-fly overflow may halt/drain a run; its recovery protocol is an M05 integration test, not accomplished by host admission.
5. The existing C++ `m04_eval_one` already supports W `4..32`, unsigned-32-bit rationals and `i64` aggregated current; its existing tests do **not** prove an upstream queue can hold 4096 contributions or reject all overflow. New host preflight in `m04_profile.py` is a **workload screening tool using accepted M02 traces**; **not** an implemented scheduler/hardware guard.

This profile avoids the subtle, invalid shortcut of clipping each incoming weight before a later negative event cancels it. To support larger event streams, **increase buffer/spill capacity with a proven exact sum** or explicitly apply to extend the hardware admission profile; do not revise the accepted M02 equation silently.

## 4. Proposed v1 engine interface and schedule contract

Use the [existing M04 typed request/response fields](../hls/m04_lif_eval/m04_eval.hpp) as the **semantic/host-test ABI**, not a frozen bus-bit layout. For M05.1, prefer a **ready/valid request and response stream** (Vitis HLS `hls::stream` / AXI4-Stream candidate, or equivalent internal FIFO with an adapter) plus **one operation per accepted transaction**. If downstream blocks assert backpressure, hold the entire response intact; if upstream is stalled, accept no half-transaction. A per-neuron A53 `ap_start` command is not allowed in the first performance baseline. Treat HLS `ap_ctrl_hs` per *batch* or explicit `ap_ctrl_none` as a later *tool-verified* top-level choice; AMD UG1399 warns `ap_ctrl_none` can restrict C/RTL co-simulation. Avoid assuming `ap_ctrl_none` is always simpler.

- **Ingress/aggregation owner (M05.2):** coalesce all tick-`t` signed external and delayed events *exactly*, count each contribution, check capacity, submit at most one request per selected `(tick, id)`. Maintain a barrier so tick `t` results cannot contribute to tick `t` itself; all edge delays `>=1`.
- **State/residency owner (M05.3):** read the authoritative old voltage and parameter row *before* evaluation, ensure one writeback/commit per ID/tick, preserve state across cache eviction and DDR reload, and avoid RAW/WAW hazards under stalls. Read/modify/write may be in separate stages; the neural evaluator is deliberately **stateless**.
- **Response/commit owner (M05.3):** check status and metadata match; write new state, emit at most one spike, then schedule each outgoing synapse at `t+delay`; enforce queue capacity and global tick-completion before publishing next-tick state. Reorder internal dispatch if desired, but compare canonical `(tick,id)` trace and sorted spike outputs.
- **Invalid and overflow:** no silent packet loss, duplicate evaluation, truncated aggregate, stale result, or partial state publication. A failed run is excluded from speedup/accuracy calculations, and error counters are separate from useful-work metrics.
- **Queue sizing:** 4096 counts *arrivals in one tick*, **not** concurrent pending events for all future ticks. Future queue depth, long-delay storage, time buckets, spill to DDR and event-transport backpressure remain explicit **M05 decisions**.

**Interface choice rationale:** streaming isolates the one-neuron arithmetic kernel from worklist policy and on-chip/DDR placement. AXIS ready/valid offers a natural testable backpressure contract; AXI4 `m_axi` for DDR, AXI4-Lite registers, and any processor-driven setup stay in surrounding shell, not inside the LIF math. Synthesis must determine whether struct/parameter transport should be flattened, split into configuration registers, or packed into a narrower stream; preserve the tested *semantics* in every variant.

## 5. M05.1–M05.4 measurable gates; no premature architecture freeze

| Phase | Required functional and evidence gates | Performance hypothesis, **not** promised achievement |
| --- | --- | --- |
| **M05.1 — Streamed evaluator** | Keep M02 full-voltage/spike parity for admitted W16 cases, signed boundaries and stress cancellation; HLS C sim + csynth/C-RTL co-sim when available; **isolated engine** version/part/clock/source/report SHAs; errors/backpressure and exact once-per-request tested. | 100 MHz requested target, first report measured estimated **II and latency**. Try II<=1 for an isolated arithmetic stream, **not** required for functional signoff; rational integer division may force II>1 or area changes. |
| **M05.2 — Sparse events** | Exact-skip eligibility, active + biased neurons, delayed/self recurrence, duplicate/canceling events, >=4096 cap edge, >=4097 reject or lossless spill; no same-tick feedthrough; positive-delay horizon. | Worklist/queue/aggregation cost and stalls measured separately from neuron arithmetic. |
| **M05.3 — Integrated bounded on-chip prototype** | One pipeline, bounded resident state, full tick barrier, backpressure, cache block independence and per-tick M02 parity across admission cases; compare resident versus paged contracts without changing numerical work. | Track read/write stalls and state-update throughput; do not conflate engine II with useful network inference time. |
| **M05.4 — Offline HLS/RTL verification** | Real tool availability; `xck26-sfvc784-2LV-c`, Vitis 2025.2 (record actual versions), 10 ns target, independent C/RTL vectors, exported source/config/report hashes and utilization; if unavailable say **NOT RUN**. | Collect estimated II/latency/LUT/FF/BRAM/URAM/DSP; post-route timing and physical board performance require separate new approval and physical evidence. |

**Acceptance separation:** M04.5 is a *completed, documented requirements decision*. M05 owns actual hardware engine development, tested FIFO behavior, event scheduling, synthesis, resource fit, and integration. M04 is **not closed** merely because this M04.5 handoff is complete. Git branch and PR remain unmerged pending express user approval.

## 6. Traceability, decision risks and unresolved items

- **Known prior art:** LIF stepping, time-multiplexing, event FIFOs, cache blocks and AXIS ready/valid are standard. The project contribution will be measured interactions of virtualization/sparsity/locality, not novelty of integer LIF or a queue.
- **Risks:** exact variable-denominator division and 64-bit transport can affect LUTs/II; BRAM port conflicts and long-delay queues can dominate; a single 100 MHz engine may be bandwidth-bound; real 4 GB DDR is shared with the PS; erroneous burst/queue counts can invalidate benchmarks. These are M05–M08 research questions.
- **Unfrozen:** AXIS packing width, divider implementation, state memory format, long-delay queue organization/spill, AXI/HP port, PS/Linux ownership, cache replacement, runtime deployment compiler, energy boundary and II/Fmax targets beyond first hypothesis.
- **No evidence invented:** new M04.5 unit checks establish bounds and *source-side* admission over M02 traces; no new Vitis HLS, Vivado route, board, network accuracy, DDR bandwidth, power or speedup test was run here.

**Native verification:** [M04_TESTS_EXPLAINED.md](M04_TESTS_EXPLAINED.md) and [M04_PC_ONLY_VERIFICATION.md](M04_PC_ONLY_VERIFICATION.md); original (read-only) v3 sources were not modified.
