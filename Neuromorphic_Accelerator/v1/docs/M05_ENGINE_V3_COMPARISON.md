# M05 — New streamed evaluation engine versus the historical v3 HLS engine

**Status:** M05 development, host-native functional proof only. HLS synthesis, C/RTL co-simulation, Vivado route and physical KV260 are **NOT RUN**. The new HLS-oriented C++ is not a hardware performance result.

## Actual source and provenance

Historical, project-owned v3 (not edited):
- [v3 arithmetic and full-core HLS top](../../../Loihi_Digital_Twin/v3/hls/core_v2/src/loihi_core_v2.cpp); [type and interface definitions](../../../Loihi_Digital_Twin/v3/hls/core_v2/include/loihi_core_v2.hpp).
- [v3 memory fabric](../../../Loihi_Digital_Twin/v3/rtl/p03_memory_fabric.v), [P05 controller](../../../Loihi_Digital_Twin/v3/rtl/p05_virtualized_controller.v), [P08 paged controller](../../../Loihi_Digital_Twin/v3/rtl/p08_paged_dispatch_controller.v).
- [Accepted source audit](M04_HLS_ENGINE_AUDIT.md), [accepted M04.5 first K26 requirements](M04_5_ENGINE_REQUIREMENTS_AND_M05_HANDOFF.md).

New project-owned code:
- [M02-exact bounded scalar update](../hls/m04_lif_eval/m04_eval.cpp) inside the new [M05 HLS-oriented stream top](../hls/m05_stream_eval/m05_stream.cpp) with [header](../hls/m05_stream_eval/m05_stream.hpp).
- [Native batch protocol test harness](../hls/m05_stream_eval/m05_stream_host_cli.cpp), [host-only sparse event integration](../src/neuromorphic_accelerator_v1/m05_host_runtime.py) and [17 independent-source tests](../tests/test_m05_stream.py).

## Source-backed differences

| Property | Existing v3 loihi_core_v2_tick | New M05 stream evaluator + external scheduler |
| --- | --- | --- |
| Physical work selection | One whole **logical core** per algorithmic timestep, scans all compartments (old maximum 1024 per core). | One explicitly selected **logical neuron update** per request; up to **1024 requests per batch**. Logical neuron ID, resident state block and physical engine are distinct. |
| Stored state | 64-bit state word packs signed 24-bit synaptic current, signed 24-bit voltage, 16-bit refractory. | **Only membrane voltage** is part of M02 neural state; proposed first hardware profile signed **W16**. The stream kernel is *stateless*; host stores voltage until physical memory is built. |
| Leak | Separate current and voltage decay; subtract a sign-ceiling-away rounded removed fraction on a fixed /4096 scale. | Signed rational **truncation toward zero** of prior membrane × numerator / denominator, exactly accepted M02 rev1. No independently decaying synaptic current. |
| Current inputs | Input axon IDs expanded through axon/synapse rows inside the HLS engine, current accumulation separately saturates to 24 bits before integrating membrane. | Already **algebraically summed signed current (i64)** in each request; clamp to W only once **after** decay + bias + complete current sum. The host scheduler currently coalesces events; PL ingress is future work. |
| Spike test | **Strict greater-than** threshold plus refractory suppression. | **Inclusive greater-than-or-equal** threshold, no refractory; spike resets voltage in the same tick. |
| Delays/recurrent spikes | HLS ingress flags nonzero encoded synapse delays unsupported; emitted packets target t+1; older runtime owns routing. | Separate tick-bucket scheduler supports any positive integer synapse delay, parallel edges, self-loops, recurrence; never same-tick propagation. Only the **host** version is currently implemented. |
| Configuration/ports | Packed 128-bit config, nine **ap_memory** banks for state, config, axon, synapses, routes, event ingress, traces and packets; ap_ctrl_hs, ap_vld counts. | Typed **hls::stream** request/response, proposed AXI4-Stream ports, AXI4-Lite batch count/control return. No direct state/axon/synapse BRAM, route output RAM or AXI4 DDR master yet. Bus packing **not frozen**. |
| Memory writes | Whole-core kernel updates packed state *in place* and emits normalized per-compartment traces/route packets. | Evaluator emits {ID,tick,new voltage,spike,status}; a separate owner **must** commit state once/tick and route future synaptic events. The Python host prototype updates lists only (not BRAM/URAM). |
| Sparsity | All compartments updated each kernel call after accumulator clear. | Host scheduler selects old-voltage-nonzero OR bias-nonzero OR any delivery destinations, consistent with **the proven M03 exact-skip lemma**. Silent but decaying/bias-active neurons may not be skipped. |
| Controller | v3 P03/P05/P08 per-core dispatch and barriers, historically coupled to PS paging. | A batch invocation, not per-neuron HLS start; no imposed old logical-core grouping. Current **native test** launches a host process per nonempty tick: this is not a measured reduction in A53 control overhead. |
| FPGA sizing | Historical integrated-shell resource and timing results are **v3-specific**. | K26 `xck26-sfvc784-2LV-c`, 100 MHz/10ns target, single engine, provisional W16 and 4096 arrivals/tick. **No measured resource, achieved II or routed timing.** |

## What was reused and what was deliberately replaced?

**Reused ideas, not old source logic:** independent memory/compute boundaries, widening intermediates before saturation, transparent trace and status interfaces, time-multiplexing and fail-closed guards. The accepted M04 code `m04_eval_one` is invoked by the new kernel for mathematically correct fixed-domain M02 results.

**Not reused:** v3 `step_compartment`, `decayed_state`, old current saturation, 24+24+16 state packing, refractory handling, strict spike threshold, core/axon/route command interface or host per-core service architecture. An unmodified v3 wrapper would *not* meet M02 reference behavior.

**Not yet implemented:** AXI4-Stream hardware ready/valid and backpressure, bounded event FIFO, programmable long-delay buckets, on-chip neural memory read/write and hazards, 1K state-block/DDR residency, output packet delivery, PS/PL integration, and measurable throughput. The native queue shim is **unbounded std::queue** for functional tests; it cannot certify real AXIS behavior.

## HLS and scaling caveats

- The current request sends prior voltage, per-neuron parameters, global decay, ID/tick and aggregate **per work item**. The first physical interface may be unnecessarily wide. M05.3 must benchmark shared config/state BRAM and a narrower update stream without changing numerical behavior.
- Dynamic signed division is costly; `#pragma HLS PIPELINE II=1` is an **optimization request**, not a measured achieved II. Explicit Vitis HLS reports and C/RTL cosim are required before claiming timing or resource fit.
- The 4096 limit counts **individual delivered signed contributions per algorithmic tick**, not total outstanding events at all future timestamps. At count >4096 the host run fails, but no hardware overflow guard exists.
- Per-tick sparse worklists plus batches are **not timestamp-free asynchronous execution**. No energy/accuracy or matched v3-v1 inference speedup is established.
- LIF, FIFOs, time-multiplexing, and caches are established prior art; new research claims will focus on measured virtualization/sparsity/locality interactions, with YANA and other work appropriately credited.

## Evidence and open gates

Source-only CI passed **17 M05 and 91 accepted M01–M04** methods at code SHA `cd483fe5`, [workflow 42454758437](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42454758437). See [tests explained](M05_TESTS_EXPLAINED.md) and [local verification](M05_PC_ONLY_VERIFICATION.md). The staged [HLS config](../hls/m05_stream_eval/m05_hls_config.cfg) and [C simulation testbench](../hls/m05_stream_eval/m05_hls_csim_tb.cpp) have **not** been run in Vitis. M05.1 is **host-proven but HLS-unverified**, M05.2 is **host-proven but lacks PL scheduler**, M05.3 and M05.4 are **OPEN**, and M05 remains an unmerged draft.
