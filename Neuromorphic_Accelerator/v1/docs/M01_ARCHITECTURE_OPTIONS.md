# M01 — Virtualized Neuron State: Architecture Options and Decision Boundary

**Date:** 2026-11-07 local / 2026-11-08 UTC. **Status:** PC-only candidate trade study; **M01 NOT YET ACCEPTED** (hardware interfaces, LIF semantics and workload assumptions remain undecided). Source branch: `agent/neuromorphic-accelerator-v1-m01-trade-study`. This is a new `Neuromorphic_Accelerator/v1` architecture investigation, not a Loihi-v4 implementation.

## 1. What is and is not being compared

We are comparing **the granularity and residency of logical neuron-state storage**, with a fixed total **on-chip state-data budget** and the **same ordered sequence of write-modifying state-access requests** for all three configurations within each synthetic trace.

- Physical LIF engine count: conceptual **one time-shared engine**; actual HLS/RTL execution and initiation interval are **not modeled yet**.
- DDR: **canonical neuron-state backing** for all models, with a bounded BRAM/URAM-like working set. No actual K26 DDR address, XSA interface, MMIO or memory ownership is programmed.
- An access request is **not** a recorded spike, synaptic operation, timestep, or completed inference. It simply says a neuron state must be read, modified and eventually stored.
- Sparse fanout/weights, firing, timestamps, synaptic accumulation, queue/arbiter stalls, DMA setup, AXI splitting/alignment, coherence, cache tag/control area, physical memory concurrency, DDR timing, energy and accuracy are **out of scope**.
- The model includes **cold loads**, dirty eviction writes, and final dirty flushes, so it does not hide write traffic by stopping at the last request.
- State-block size is configurable; `N` and `N - pinned` must divide exactly into complete blocks for this first model. It **fails closed** instead of silently allowing fractional blocks.

**Consequence:** A model result can be presented as **bytes/idealized transfer transactions under stated assumptions**, never as latency, throughput, energy, real neuromorphic inference, or a validated best hardware architecture.

## 2. Three options and conceptual DDR mappings

Let `N` = logical neuron count, `S` = state bytes/neuron, `C` = total on-chip state-data budget in bytes, `G` = neurons per block, `P` = independently preselected pinned neuron prefix size, and `Q` = max bytes per idealized contiguous transfer. Assume array indexes start at zero and DDR owns a canonical image.

| Option | Logical DDR layout (byte offset within allocated state region) | Resident capacity and access | Hypothesized strength | Main concern |
| --- | --- | --- | --- | --- |
| **A — neuron-granular LRU** | `offset(n) = n*S` | `floor(C/S)` independent neuron records; on a miss read `S` bytes, LRU dirty eviction writes `S` | Little unused-state movement for dispersed activity; fine-grained allocation | Short/random DDR transactions; cache tags, bank conflicts and event-to-state lookup costs |
| **B — fixed group/block LRU** | `g = n//G; offset(g) = g*G*S` | `floor(C/(G*S))` whole groups; reads/writes `G*S` bytes per miss/dirty eviction | Contiguous transfers and burst efficiency for clustered events | Unused-neuron overfetch; many distinct groups and thrashing at dispersed activity |
| **C — hybrid pinned prefix + group LRU** | `0<=n<P`: canonical pinned offset `n*S`; else `g = (n-P)//G; offset(g) = P*S + g*G*S` | Reserve `P*S` data bytes for pinned IDs `0...P-1` plus `floor((C-P*S)/(G*S))` dynamic group slots; prefetch P contiguous states on cold start | Exploits a *predeclared* stable hot set while retaining dynamic block access for the remainder | Requires prior knowledge, reduces dynamic capacity; prefetch wasted when the selected region is cold |

`A`, `B`, and `C` use the **same C-byte data budget**. Each also reports allocation slack; comparison does **not** yet account for extra tag RAM, eviction metadata, address-generation hardware, or P-group scheduling queues. The model uses LRU as a **known baseline policy**, not a novel eviction algorithm.

In **C**, pins are **explicitly neuron IDs 0...P-1**, never selected by reading the evaluation trace; thus the model is not leaking oracle/test information to favor hybrid caching. The pinned region is contiguous and is prefetched using modeled large sequential transfers of at most `Q` bytes, and adjacent dirty pinned states can be flushed together. This avoids arbitrarily penalizing C relative to B by splitting contiguous prefetches into one transaction per neuron. Group memory starts *after* the pinned prefix, avoiding duplicate residency of the same pinned neuron in dynamic blocks.

**The name 'virtual state block' is a proposed implementation abstraction, not a Loihi logical core, a guaranteed application partition, or a physical compute engine.** Physical engines and residency units must be separable.

## 3. Illustrative reproducible synthetic setup — strictly NOT physical results

Run the standalone Python source in `../src/neuromorphic_accelerator_v1/m01_residency.py` via `../scripts/m01_explore.py` (no third-party dependencies):

| Parameter | Example value | Why it is not a device claim |
| --- | ---: | --- |
| Logical neuron count | 4,096 | Chosen synthetic scale, not a trained checkpoint |
| Per-neuron state footprint | 16 bytes | **Provisional**; real fields/precision require M02 design |
| On-chip state-data budget | 2,048 bytes | **Provisional**; no K26 BRAM/URAM budget committed |
| Virtual block size | 16 neurons (256 bytes) | Hypothesis being swept |
| Hybrid pinned records | 32 neuron IDs | Predeclared prefix, **not** activity-trained hot-set selection |
| Maximum contiguous transfer | 256 bytes | Accounting simplification, **not** verified AXI/DDR burst capability |
| State access requests | 512 | One request = one write-modifying state access, **not** a timestep or spike |
| Distinct active neuron IDs | 64 | Identical update multiplicities; only addresses/locality differ |
| Seed | 1 | Fixes deterministic shuffled role ordering |
| Cold/warm and flush | Cold start + final dirty flush | Initialization and writeback both included |

The generator creates the same shuffled role sequence for two **ID mappings**: **clustered** (the first 64 neuron IDs, four adjacent blocks) and **dispersed** (64 IDs spaced across all 4,096 neurons, touching 64 distinct 16-neuron blocks). Each role has the same frequency under both mappings and each architecture receives the same exact trace within a scenario. We are controlling the **distribution of state accesses**, NOT running two identical neural networks with equivalent weight matrices or predicting their outputs; that stronger experimental claim belongs to M02/M03.

### Source-tested illustrative accounting (no-board CI at SHA `ea2cbc2d8...`, updated burst accounting)

| Synthetic state-access locality | Residency model | Read bytes | Write bytes | Total modeled transactions | Cache misses | Dirty evictions |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Clustered | A — individual | 1,024 | 1,024 | 128 | 64 | 0 |
| Clustered | B — block | 1,024 | 1,024 | 8 | 4 | 0 |
| Clustered | C — hybrid | 1,024 | 1,024 | 8 | 2 + pinned prefetch | 0 |
| Dispersed | A — individual | 1,024 | 1,024 | 128 | 64 | 0 |
| Dispersed | B — block | 115,456 | 115,456 | 902 | 451 | 443 |
| Dispersed | C — hybrid | 116,992 | 116,496 | 913 | 455 + pinned prefetch | 449 |

**What this actually shows under our assumptions:** a 16-neuron block requires **16× fewer modeled transfers than individual access for clustered activity** (8 versus 128), despite moving equal total bytes. But for dispersed access, the very same group cache moves **112.75× as many bytes** as individual-state caching (230,912 versus 2,048 total). The different active-group cardinality makes a fundamental difference. This is a *model illustration*, not a hardware-measured effect; actual request concurrency/AXI/DMA overhead may change which implementation is fastest. The hybrid prefix is especially ineffective in the dispersed scenario because only one of the 32 pinned neuron IDs is active and most prefetched state is unused.

The optional `--illustrative-transaction-overhead-ns` and `--illustrative-bandwidth-mbps` flags permit a **user-specified serial memory-time proxy**; there are **no default assumed DDR timings**, and the output explicitly labels that proxy hypothetical.

### Broader no-board sweep

`scripts/m01_sweep.py` runs a deterministic **3 capacity × 4 block-size × 2 locality = 24-cell** grid, with three strategies in each cell:

- Budgets: **1,024, 2,048, 4,096 bytes**
- Block sizes: **4, 8, 16, 32 neurons**
- 4,096 logical neurons; 64 active; 512 requests; 16 state bytes; pinned prefix 32; seed 1
- Every policy inside a cell uses the *same state budget* and access trace; **no invalid grid cells silently skipped**. Both locality patterns use the same seed and request role counts.
- Generated raw study JSON and sweep JSON are preserved as downloadable GitHub Actions artifacts when CI runs, or externally with an exclusive-create filename when run on the user's PC.

Do **not** interpret 24 sweep cells as 24 physical KV260 experiments or as 24 independent scientific replicates.

## 4. What we can decide from this without inventing conclusions

**Provisional baseline recommendation:** Develop a **parameterized block cache (B)** as the most straightforward future DDR-transfer baseline *after* the neural reference (M02) and actual K26 interface constraints are specified. Keep **A** as the neuron-granular adverse-locality control and **C** as the bounded hybrid/residency control. This is a **reversible design starting point**, not a declaration that blocks are always faster. Any cacheline or group definition should be hardware-independent metadata to facilitate fair swaps.

**Do not decide yet:**

1. **State tuple precision and bytes (`S`):** M02 must decide membrane/current/last-update/bias/threshold/refractory/delay and whether fixed-point lazy leak is bit-exact; 16 B is not a verified data layout.
2. **Synaptic connectivity in DDR:** This model counts **only neuron state**. Fanout index/weights may dominate actual memory traffic. M01 must record possibilities: (a) all neuron state DDR-backed, adjacency on chip; (b) state cached from DDR, adjacency/weights separately in DDR; (c) mostly resident neuron state and external sparse synapses (like HiAER's high-level division). Choose after profiling workload/size and M03 traffic.
3. **Event-order semantics and how many updates are needed:** No correct on-chip update skipping can be inferred from this traffic model. M02 dense timestep oracle must decide zero-input updates, biases, leakage, output timing, duplicate events, refractory, fixed-point rounding/saturation.
4. **Actual AXI/DDR and on-chip budgets:** Confirm real KV260 BRAM/URAM constraints, data alignment, burst setup, outstanding transfers, PS/PL control and memory security/ownership. **PC-only M01 is not hardware authorization.**
5. **Group-to-neuron mapping and hot-set selection:** Begin contiguous IDs for repeatability, then compare graph-aware partitioning or hot-set profiling on **independent calibration traces**, not the evaluation trace. Pinning here is static to prevent leakage.
6. **Compute/communication overlap:** Fixed CPU-driven core dispatch from v3 must not automatically survive into v1; M04 should measure LIF arithmetic reuse vs streaming control separately.
7. **Experiment acceptance:** Hold physical speedups, scalability limits, model accuracy and energy claims for independent v1 M02–M09 tests. This model is not a substitute.

## 5. Provenance and credit

- **Neuron multiplexing and state loading costs** are established prior art (e.g. SENECA, Tang et al., 2023; https://doi.org/10.3389/fnins.2023.1187252).
- **Hot-neuron scheduling, five-stage sparse event flow, and elapsed-time LIF leak** are discussed in YANA (Pachideh et al.; https://arxiv.org/abs/2604.03432) and must be credited if inspiration is used. This model **does not implement or copy YANA's hot-neuron pipeline**, just generic grouped state-access traffic.
- **Hybrid external connectivity plus on-chip neural state** has related prior art in HiAER-Spike (Frank et al., 2026; https://doi.org/10.1038/s44335-026-00062-8).
- **LRU, cachelines and memory paging** are established computer architecture concepts; neither the principle nor these three categories are claimed as invented here.
- This study's Python source and synthetic traffic accounting were newly authored for the project, using no copied third-party HDL or software. Review any future upstream YANA/other software or RTL implementation license independently before reuse. Full bibliography: [root `LitReview.md`](../../../LitReview.md).

## 6. M01 acceptance checklist (not yet closed)

- [x] Candidate A/B/C mappings, memory state, ownership and memory budget explicitly documented.
- [x] Reproducible **no-board** synthetic read/write/transfer accounting, no implicit hardware timing.
- [x] Negative/fairness tests for budget conservation, deterministic location controls, dirty writeback, pin prefetch, invalid segmentation and exclusive-create outputs.
- [x] 24-cell capacity/granularity/locality synthetic sweep CLI and native GitHub Actions job.
- [ ] User runs native PC tests and reviews original generated SHA-pinned JSON; reports output/SHAs.
- [ ] User reviews whether B is a sensible *provisional* implementation baseline and whether state and synapses should be jointly or separately virtualized.
- [ ] M02 contract draft formally chooses exact state tuple, LIF time semantics and supported network scope. **No code/hardware launch is authorized by M01.**

M01's important output is an **architecture and experiment choice with stated risks**. It must not be marked accepted solely because the analytic code passes its own self-tests. The next distinct milestone is the independent M02 neural reference, subject to user verification.
