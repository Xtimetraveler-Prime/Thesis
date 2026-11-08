# Neuromorphic Accelerator v1 — Architecture Trade Study (NOT DECIDED)

**Status:** Discussion prompts and candidate experiments, not a frozen spec, implementation, thesis novelty claim or proven performance result. Discuss and choose before creating new code or hardware. Keep the original LIF reference independently verifiable.

## A. What is virtualized?

1. **Individual neuron states:** small variable-size work items; potentially sparse DDR/cache accesses and many random transactions. Does this become transaction-latency limited?
2. **Neuron groups / working-set blocks:** fixed or tunable contiguous ranges of neuron state, metadata and optional partial synaptic state. Can a residency buffer capture locality without loading unused neurons?
3. **Connectivity / synaptic fanout:** sparse edges are potentially much larger than LIF neuron state. Should weights and adjacency be DDR resident while frequently active membrane states remain on-chip? Test this as a separate memory-placement axis.
4. **Processing pipelines:** one or more physical synaptic-update and LIF functional units, time-shared independently of any logical network partition. Separate a **hardware engine** from a **memory-residency group** and from a logical/model layer.

Do not assume a logical group must be a Loihi-like **core**. Existing neuromorphic processors, including YANA and HiAER-Spike, still call some hardware engines **cores**, so the useful question is whether logical model groups must coincide with a physical core: **they need not**.

## B. Proposed (not selected) baseline execution flow

Input timestamped spikes → event FIFO → sparse fanout lookup → destination-neuron activation/accumulation → group residency scheduler (on-chip working-set cache backed by DDR) → pipelined LIF state update → emitted spikes / future events.

Design-critical choices still open:
- **Fanout traversal:** outgoing adjacency lists (CSR), incoming/group-indexed lists, sparse matrix layout, or hybrid; DMA burst efficiency and pointer-chasing on real K26 DDR.
- **Group mapping:** contiguous neuron IDs, graph partitions/edge-cut locality, activity-aware clusters; configurable group sizes and cache capacity to measure effects.
- **Scheduling:** immediate per-event, coalesced by destination neuron or group, time-bucketed ordering and barriers, deterministic tie breaking; queue pressure/overflow/backpressure correctness.
- **LIF semantics:** zero-input decay, impulse arrival ordering, accumulated current, leak/threshold/reset with fixed-point rounding and saturation, refractory/delays, timestamp wrap; dormant neurons may need autonomous spikes from bias currents.
- **PS/PL boundary:** A53 deployment/control vs on-fabric per-event scheduling; avoid returning each spike to A53. Determine AXI4/AXI-Lite/DMA/coherent interfaces using measured traffic, not the old design by default.
- **Physical compute:** investigate whether original v3 HLS dispatch/LIF datapath can be reused as an arithmetic correctness scaffold; do not carry forward its command-per-core/per-timestep interface without benchmarking. A new streaming event/synapse pipeline may be more appropriate.
- **Cache policy:** fixed map, no-cache, LRU/FIFO, locality/activity-aware admission/eviction, batched dirty writeback, eviction correctness, multi-ported state hazards and cache hit/byte accounting.
- **Model/network scope:** first known feedforward/recurrent small test plus same model across controls, trained network/dataset and exact model precision. Define event arrival/time domains and reproducible input spikes.

## C. A targeted first experiment

Use **the same neural network and spike stream** under a small four-way baseline:

| Execution | Working state | What it isolates |
| --- | --- | --- |
| Timestep-driven | On-chip | Reference full state/tick work |
| Event-driven | On-chip | Sparse computation savings |
| Timestep-driven | DDR-backed | Residency / transaction cost |
| Event-driven | DDR-backed | Combined sparse + virtualized implementation |

Use a network that fits on-chip for the **four-way controlled comparison**, then scale the DDR design separately. Do not equate 1023 input frames with 1023 independent physical boots.

**Key locality control:** Fix total spike/edge work but vary **number of distinct DDR-backed groups touched** and order (clustered vs scattered). Sweep group size, cache size and activation fraction; record bytes transferred, burst length, transactions, group hit/miss/eviction and dirty writeback count, event queue occupancy/backpressure, LIF parity, PL cycles, complete sample latency, throughput, LUT/FF/BRAM/URAM/DSP resources. Power only with a validated measurement contract.

## D. Prior art and review entry points

- [YANA, Pachideh et al., 2026 preprint](https://arxiv.org/abs/2604.03432): five-stage sparse event pipeline, hot-neuron tracking, elapsed-time leak and time-multiplexed physical compute using local memories. Hardware processing **cores** exist; not the same as historical v3 logical core pages.
- [SENECA, Tang et al., 2023](https://doi.org/10.3389/fnins.2023.1187252): neuron time-multiplexing and state movement is established; scalability/performance/memory tradeoffs are real.
- [HiAER-Spike, Frank et al., 2026](https://doi.org/10.1038/s44335-026-00062-8): sparse address-event routing and HBM-based synaptic storage with on-chip neural state; separates physical processing cores from network-level grouping.
- [Root literature review](../../../LitReview.md): detailed existing bibliography and novelty limits.

**Design success criterion:** identify a demonstrably correct, resource-realistic mechanism that improves a *measured virtualization cost* under defined sparsity and locality patterns, including honest failure regions. This document is deliberately a question list rather than a commitment to any selected architecture.
