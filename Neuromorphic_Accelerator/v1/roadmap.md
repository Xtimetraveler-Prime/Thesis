# Neuromorphic Accelerator v1 — Research Roadmap (M01–M09)

**Current status: M01–M06 COMPLETE in their separately accepted scopes (November 10, 2026). M07 is IN PROGRESS (M07.1 first source-only cache-policy baselines on a separate unmerged branch); M08 and M09 are planned.** **New-chat development entry:** [M07 handoff / workflow and first steps](docs/M07_NEXT_CHAT_HANDOFF_2026_11_10.md). The active project is an independently versioned SNN/FPGA research effort, not Loihi Digital Twin v4. This document records **current decisions and future gates** rather than daily engineering logs. The complete original milestone journal is preserved in [Git at the pre-cleanup revision](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/v1/roadmap.md); experiment-specific evidence remains in linked acceptance reports and under the owner's immutable local evidence directory.

## 1. Research question and experimental contract

**Question 1:** How much latency and hardware overhead does virtualizing more logical neurons than resident on-chip state permit, and how much of that penalty can sparse execution recover?

**Question 2:** How does event-driven sparsity interact with external-state residency and active-group locality to affect FPGA performance, capacity and hardware efficiency?

The scientific variables are on-chip state budget, logical network size, update/scheduling strategy, active-group locality, event rate, connectivity and placement of state versus synapses. The objective is **a measured, independently correct tradeoff**, not a predetermined speedup or a novel claim for time-multiplexing or caching.

**Four-way matched control design:**

| | Entire state on chip | DDR-style state backing |
| --- | --- | --- |
| Timestep-driven | Baseline control A | Virtualized control C |
| Event-driven | Sparse control B | Sparse + virtualized control D |

Initially use the same numerical contract, network, input stream, clock/compute assumptions and workloads across configurations **where all four fit**. A too-large network has no valid all-on-chip control at the same resource budget: report its scaling separately. At fixed total event and synaptic work, deliberately vary the number/placement of active groups to separate locality from sparsity.

**Metrics:** independently checked spike/state/trace output; complete sample latency and throughput; on-chip LUT/FF/BRAM/URAM/DSP and achieved clock; neuron/synapse work; transferred DDR bytes and transactions; page hit/miss, fill/dirty eviction, queue backpressure and idle cycles; calibrated PS/scheduler/service overhead; variability and measurement boundary. Mark physical quantities **NOT MEASURED** until independently observed on actual hardware.

## 2. Milestone overview

| Milestone | Scope and purpose | Accepted status / next gate |
| --- | --- | --- |
| **M01 — Architecture alternatives** | Compare per-neuron, block/group and hybrid residency; choose reversible baseline | **COMPLETE (PC-only).** Configurable block residency provisionally selected, other controls retained. [Options and limits](docs/M01_ARCHITECTURE_OPTIONS.md) |
| **M02 — Independent LIF neural contract** | Fixed-point/integer dynamics, dense oracle and independently implemented event-bucket checker | **COMPLETE (PC-only).** Neural and event-order contract accepted. [Numerical reference](docs/M02_PROVISIONAL_LIF_CONTRACT.md) |
| **M03 — Workloads and traffic** | Role-isomorphic generated workloads, safe-sparse equivalence, modeled state/synapse traffic | **COMPLETE (PC-only).** [Matched measurement contract](docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md) |
| **M04 — Existing engine audit** | Determine arithmetic reuse and hardware interface requirements | **COMPLETE (host/audit scope).** V3 HLS reuse decision and bounded host candidate; no M04 synthesis required. [Audit](docs/M04_HLS_ENGINE_AUDIT.md) |
| **M05 — Sparse/on-chip engine prototype** | Signed32 rolling event processing, HLS/RTL stream and control integration | **COMPLETE (offline FPGA-targeted scope, PR #79 merged).** [Accepted original toolchain evidence](docs/M05_ACCEPTANCE_REVIEW_2026_11_09.md) |
| **M06 — State residency and fault containment** | Paged canonical memory, original HLS+AMD AXI interconnect, dirty eviction, numerical parity and quarantine/restore | **COMPLETE (offline connected original-RTL simulation, PR #80 merged).** [Five-archive original XSim acceptance review](docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md). **No physical PS DDR** |
| **M07 — Policies and ablations** | Fair cache/no-cache, scheduling and locality experiments | **IN PROGRESS / NOT ACCEPTED.** M07.1 direct-fetch versus M06 LRU, M07.2 M03-matched four-way logical controls and M07.3 fixed-byte-budget/block/locality source-only grid with independent M02/M03/M06 oracle checks and source artifacts/CI added on development branch. Queue/service-timing, optional scheduler and owner acceptance remain open |
| **M08 — Physical KV260 benchmarking** | Carefully authorized integration, genuine DDR, full-system timing/resources, repeatability | **PLANNED, separately gated.** No JTAG or physical DDR approval implicit here |
| **M09 — Analysis and research closeout** | Virtualization/sparsity interaction, negative results, prior-art comparison and thesis plots | **PLANNED** after reproducible M08 evidence |

**Milestone discipline:** one new branch per milestone; test explanations and local verification commands are mandatory; source CI is not a substitute for actual original vendor, full RTL or physical proof. Merge only after independent owner review and explicit approval. M01–M06's completion is *scope-bounded*, not a blanket claim of physical FPGA inference.

## 3. Accepted foundations (M01–M06)

### M01 — Residency design alternatives (PC only)

Compare **A: neuron-granular**, **B: block/group-based**, **C: hybrid on-chip/DDR** state residency. State placement and synapse placement are separate architectural axes. Deterministic source models/sweeps tested transfer and context granularity, grouping and locality. **The user accepted configurable blocks as the provisional baseline**, keeping neuron/hybrid controls for future experiments—not a claim of an optimal cache or measured DDR speed. See [M01 design memo](docs/M01_ARCHITECTURE_OPTIONS.md), [PC-only commands](docs/M01_PC_ONLY_REPRODUCIBILITY_RUNBOOK.md) and [test explanation](docs/M01_TESTS_EXPLAINED.md).

### M02 — Numerical and temporal correctness (PC only)

Use an exact integer/signed LIF specification with bias/leak, time-step state transitions, spike threshold, signed individual synaptic contributions, recurrent/delayed events and deterministic ordering. Dense scalar and independent event-bucket implementations must agree on golden and randomized workloads. **Quiet neurons must still receive correct time advancement**; lazy decay is a proposed optimization, not a proven equivalent. See [M02 numerical contract](docs/M02_PROVISIONAL_LIF_CONTRACT.md), [independent tests](docs/M02_TESTS_EXPLAINED.md), [native verification](docs/M02_PC_ONLY_VERIFICATION.md).

### M03 — Reproducible workloads and analytical memory traffic (PC only)

Generate role-isomorphic networks varying **active-neuron locality without changing the total neural work**, compare an independently checked safe-sparse reference with M02 outputs and model four strategies with state/synapse bytes and transactions kept distinct. An on-chip control is **unavailable** if the state footprint does not fit. Model-derived DDR bytes are not physical interface traces or clock measurements. See [M03 workload and measurement contract](docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md), [28-test explanation](docs/M03_TESTS_EXPLAINED.md) and [sweep scripts](scripts/m03_sweep.py).

### M04 — HLS arithmetic feasibility (host audit scope)

Audit self-authored v3 LIF arithmetic and control boundaries before considering reuse; demonstrate a bounded compatible native LIF candidate and document first K26 design requirements. Avoid porting old fixed-core sequencing and uncredited third-party code. M04 includes an M04.5 requirements handoff, but **no synthesis requirement or deployed FPGA result was accepted**. [Engine reuse analysis](docs/M04_HLS_ENGINE_AUDIT.md), [engineering handoff](docs/M04_5_ENGINE_REQUIREMENTS_AND_M05_HANDOFF.md), [test explanations](docs/M04_TESTS_EXPLAINED.md).

### M05 — On-chip event-engine reference (offline original HLS/RTL)

Build correctness-first event scheduling with bounded rolling temporal buckets, sorted deliveries, exact signed accumulation, backpressure handling, completion/status and output quarantine. The accepted signed32 rolling HLS engine and integrated stream/control shell were verified with genuine original Vitis/Vivado tools and independent neural checks. The accepted scope does **not** imply measured full-device performance, physical DMA, or PS DDR. [Formal M05 acceptance](docs/M05_ACCEPTANCE_REVIEW_2026_11_09.md), [engine evolution and source proof](docs/M05_EVALUATION_ENGINE_EVOLUTION.md), [controller contract](docs/M05_EXECUTION_CONTROLLER_DESIGN_2026_11_08.md).

### M06 — Canonical virtual residency (offline original HLS+AMD RTL)

Verify one-slot and bounded-slot paging of a logical image larger than the resident state, actual original HLS reads/writes through original AMD SmartConnect/data-width converters, high canonical addresses, dirty eviction and write-B-before-following-read ordering. Require exact independent M02/M03 multi-tick trace/state parity.

A separate fail-closed **G4** safety contract observes genuine read-R and write-B 'SLVERR', withheld memory B response/timeout, independent supervisor poison, output embargo, and a later positive run after explicitly resetting and fully rewriting an independently controlled **64 KiB simulation image**. The last test verifies 16 clean six-field trace records and one metrics word released **only after commit**.

Five original Vivado 2025.2 archived experiments are accepted: G3.3 32 neurons ×4 ticks and the four G4 tests. Original generated 40 HLS RTL, 14 initialization files and 67 AMD source manifests match across runs; original AMD XCI checks pass. Historical stalled-B testbench failures remain preserved, not counted as passes. Full original SHA ledger, tool stages, caveats and exact local tests: [M06 acceptance review](docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md).

**M06 limit:** This is an **offline DDR-style 64 KiB memory model**, not physical PS DDR access, physical DMA, an automatic crash-atomic rollback mechanism, placed/routed system timing, a physical KV260 run or energy proof. The externally commanded reset/rewrite in XSim is not automatically handled by FPGA hardware.

## 4. M07 — Scheduling/cache policy variants and ablation controls

**Goal:** Quantify, with independently correct outputs, when locality-aware grouping and sparse scheduling change virtualized state-access overhead.

**Work packages (within M07, not pre-approved new milestones):**

1. **Baseline first.** Implement a no-cache/direct-fetch or minimal deterministic fixed-residency policy; implement one simple FIFO/LRU-class cache policy. Only then consider **at most one** activity-/locality-aware group scheduler. A complex adaptive scheduler is not presumed beneficial.
2. **Fair policy comparisons.** Create same-workload timestep/on-chip, event/on-chip, timestep/DDR-style and event/DDR-style configurations where resource budgets permit. Maintain identical neural semantics and disclose any compute, clock, memory placement or resource differences.
3. **Independent experimental axes.** Sweep resident slots, neuron block size, mapping, fanout representation and event batching; vary **locality at fixed event count**, not just sparse-versus-dense workload.
4. **Instrumentation and neural checks.** Capture cache hits/misses, burst/byte counts, page movements, B-before-AR fences, outstanding requests, queue stalls and complete run duration under a clearly identified *simulated or physical* timing boundary. Cross-check with M03 abstract traffic and M02 neural oracle. Make failures and unmeasured quantities visible.

**Acceptance:** reproducible policy implementation, per-policy counters, independently matching neural outputs and honest matched ablations. A null or slower policy result is acceptable; no claimed speedup is required.

### M07.1 — initial implementation on separate branch (November 10, 2026; not accepted)

Development branch `agent/neuromorphic-accelerator-v1-m07-cache-baselines` was created from the then-current main HEAD `a33c717f4101e248dd56637e5188682872fe83c6`. First deliverable is **host-only direct-fetch state residency versus the existing M06 LRU** on the exact M06 signed16 paged replay, using M03 role-isomorphic generated networks and M02 independent dense/queued plus M03 safe-sparse references. Direct fetch holds one emulated page for a paired neuron read/write, commits its dirty full-page write through M06, and invalidates it before the next evaluation. This makes it a scientifically interpretable no-inter-evaluation-reuse baseline while retaining M06's ownership/version/fault checks. Neither M02 numerics nor accepted M05/M06 HLS/RTL is changed.

Added `src/neuromorphic_accelerator_v1/m07_policy_baseline.py`, `tests/test_m07_policy_baseline.py`, `scripts/m07_cache_baseline.py`, `docs/M07_TESTS_EXPLAINED.md`, `docs/M07_PC_ONLY_VERIFICATION.md` and `.github/workflows/neuromorphic_accelerator_m07_host_only.yml`. Model traffic uses M06 full-block bytes and `ceil(page_bytes/max_model_transfer_bytes)` transfers. M06 hit/miss counts are per **read or write** (two calls per neural evaluation); direct invalidations are **not** capacity evictions. Synapse DDR traffic and hardware queue/AXI/service timing are unmodeled and reported as missing, not zero. Four-way fair control integration, larger sweeps and one optional scheduler remain separate uncompleted M07 work packages; no physical or original vendor-tool claim follows from this work.

**Acceptance remains OPEN** pending exact-head CI review, owner replication, subsequent M07 deliverables, and explicit approval. Consult the test ledger for verification status and limitations.

### M07.2 — matched four-way PC-model controls and full-suite regression repair (2026-11-10; not accepted)

Added `src/neuromorphic_accelerator_v1/m07_matched_controls.py`, `tests/test_m07_matched_controls.py` and `scripts/m07_four_way.py`. Both M07 direct-fetch and accepted M06 LRU now have the four M03 **logical** controls: timestep/onchip, event/onchip, timestep/DDR-style and event/DDR-style on the same role-isomorphic synthetic network. Independent M02 dense/queued/M03 exact-sparse functional parity is mandatory; the event/DDR-style path runs M06's real Python paged neural replay and checks exact final canonical voltage/tick watermarks. The timestep/DDR-style control is an **M02-oracle-guided actual M06 Python cache state-movement replay**, not a separately implemented dense LIF computation engine. M03 synapse bytes/transactions remain explicitly distinct **analytical estimates**; M06 Python replay does not issue those DDR-style synapse transfers. On-chip comparators are **UNAVAILABLE** if logical state exceeds declared full-resident capacity. DDR-style cache budget is smaller than the declared on-chip comparator capacity, so this is not yet equal FPGA resource utilization or a speedup comparison. No B-before-AR cycle timing, AXI outstanding queue count, RTL service clock, physical DDR bytes, K26 resources or latency is claimed.

The local all-suite M06 paged HLS test import failure reported by the owner came from two deliberately distinct scripts both named `prepare_hls_config.py`, and Python's shared `sys.modules` import cache resolving the M05 version during combined unittest discovery. The M06 test now loads its actual M06 helper by unique file path and includes a collision regression. Both M05/M06 production helper source files, top whitelists and accepted vendor HLS configuration remain **unchanged**. The M07 no-board CI now runs the full v1 unittest discovery after its focused tests, making a future import-order recurrence visible.

**M07 remains IN PROGRESS / NOT ACCEPTED:** the initial matched synthetic controls and policy comparison do not fulfill the final resident-budget/mapping/batching ablation grid, possible activity-aware scheduling, queue/service-time modeling, owner-local verification, or explicit M07 acceptance/merge approval. Do not rerun original M05/M06 owner HLS/AMD gates for this source-only work.

### M07.3 — byte-controlled cache/locality ablation and prior-art tracking (2026-11-10; owner review open)

New `src/neuromorphic_accelerator_v1/m07_ablation_sweep.py`, `scripts/m07_ablation.py`, `tests/test_m07_ablation_sweep.py`, `docs/M07_PRIOR_ART_CONFIGURATION_COMPARISON.md`, and mandatory M07 test explanations/owner verification commands. The default deterministic synthetic grid `M07.3-GRID-A` comprises **two PC seeds × three resident byte budgets (128,256,512) × three neuron block sizes (2,4,8) × two M03 clustered/dispersed placements × two cache policies (direct/LRU) × four M03 logical controls** = **18 parameter configurations and 288 model rows**, not 288 board trials. For every budget/block choice, resident slots are derived from `budget/(state_record_bytes × neurons_per_block)` and a nonintegral allocation is rejected; this holds the declared data-cache budget **in bytes**, not nominal slots, across the block-size axis. Entire image/read/write record, signed16 neural numerics, role workload SHA and emitted/delivered/synaptic event work are independently verified invariant within each seed. The timestep/DDR-style state transfer stream is still M02-oracle-driven, while the event/DDR-style path executes M06 Python paged LIF. M03 DDR-style synapse read bytes are **analytical and not actually issued by the pager**. Missing original AXI bus timing, service queues, stall cycles, PPA or actual physical DDR are reported as unmeasured, not zero.

The comparability ledger documents where YANA's event-responsive hot-neuron worklist and LUT-deferred leak, SENECA's time-multiplexed state hierarchy, and HiAER-Spike's distinct neuron-state/synapse placement relate to our experiments **as architectural precedents, not matched performance baselines**. An additional separately labeled **M07.3-YANA-COUNT-ONLY** source-model test uses **1024 logical neurons**, matching only the maximum neuron-count parameter cited for a single YANA core. It has a 16KiB software canonical-state image, 256B modeled cache, and unavailable full-onchip comparator under a declared 2048B state budget; it is **NOT** a YANA neural, hardware, network or performance replication. Record experiment IDs, full geometry/precision/workload, the publication and non-equivalent features before calling any future configuration 'YANA-like'. No named accelerator's source code has been reused.

**M07.3 is source-developed, pending latest SHA-bound CI and owner-local verification; NOT ACCEPTED or MERGED.** Still open: controlled event batching, additional placement/policy axis if scientifically warranted, queue/backpressure/service-time and B-before-AR fence accounting or explicitly unavailable measurements, optional single activity-aware scheduler only if baseline evidence justifies it, plus independent M07 final acceptance. The full source regression and no-board CI exercise only existing local RTL/Icarus where applicable; original vendor evidence and physical operations remain separately gated.

## 5. M08 — Physical KV260 implementation and measurement

**Entry is independently gated.** Source CI or M06's original-Vivado simulation is insufficient to authorize JTAG, physical DDR writes or PS/PL deployment. Require genuine build/synthesis/place-route timing, explicit memory ownership/isolation plan, source/XSA/bitstream/ELF SHA pinning, operator-controlled preflight and **a separate session-specific physical authorization**.

Measure true sample-to-output service latency, steady-state throughput and variation; PL compute versus PS control, DMA and DDR transaction costs; physical cache/page hit/miss and stall counts; final LUT/FF/BRAM/URAM/DSP, routed timing, and power/energy **only if measurement equipment and boundaries are validated**. Distinguish FPGA logic execution, PS orchestration and end-to-end user-visible service; count physical repeated coldboots separately from analysis of the same capture.

**Acceptance:** every plotted hardware point is reproducible from genuine SHA-pinned raw evidence with independent neural correctness; do not extrapolate PC model performance to physical DDR or assume an achieved clock. Preserve separate original evidence for each run, including failures. Power-cycle after JTAG attempts; do not resume a halted Linux image.

## 6. M09 — Quantitative study and thesis closeout

At *matched* neural workload, precision and measurement boundary, estimate:

- **Virtualization penalty:** 'T_DDR / T_onchip' for a fixed timestep or event strategy where both are feasible.
- **Sparsity benefit:** 'T_timestep / T_event' separately for on-chip and virtualized memory.
- **Interaction/recovery:** whether event-driven DDR-style execution reduces the virtualization penalty relative to timestep-driven DDR-style execution, with uncertainty rather than a presumed win.
- **Locality penalty:** transferred bytes/transactions and time as the number/order of active groups varies at fixed total events and synaptic work.
- **Correctness, hardware cost and limits:** independently identical neural traces, resource/performance tradeoffs, negative cases and principled comparison to the literature.

**Deliverables:** reproducible graphs/tables and raw-data manifests, exact SHA provenance, confidence/variation, matched-hardware comparator table, thesis-ready limitations and explicit final owner review. A sound negative result closes a research question.

## 7. Prior art, novelty and source licensing

**Do not claim novelty for** virtual neurons/time multiplexing, caching/blocks, sparse event pipelines, deferred leak or off-chip synapses as general mechanisms. Attribution and code licensing are distinct: acknowledge the concept even when independently implementing it; reuse outside RTL/software only with review of the *specific upstream commit and LICENSE*, proper attribution and notices.

| Prior work | Relevant boundary |
| --- | --- |
| [SENECA (Tang et al., 2023)](https://doi.org/10.3389/fnins.2023.1187252) | Time-shared digital neuron design and state-memory tradeoffs |
| [YANA (Pachideh et al., 2026)](https://arxiv.org/abs/2604.03432) | Sparse events, hot-neuron scheduling, deferred leak and asynchronous-inspiration; not a source of freely copyable hardware. Check separate hardware/software licenses before reuse |
| [HiAER-Spike (Frank et al., 2026)](https://doi.org/10.1038/s44335-026-00062-8) | Event-driven hierarchical processing, off-chip synaptic storage |
| [Ansari & Wielgosz (2026)](https://arxiv.org/abs/2608.00595) | Time-multiplexed FPGA SNN and pipelined readout |

The project novelty to **test** is a controlled interaction analysis of independent neural work, memory-state locality, cache/group policy, and sparse execution within a bounded FPGA target—not a broad "first neuromorphic accelerator" claim. Maintain module-level origins, author/license notices and independent correctness tests. Consult [full literature review](../../LitReview.md) for the expanded bibliography and study notes.

## 8. Reproducibility, branching and safety

Use a new branch based on the latest accepted 'main' for every active milestone. Include executable unit/integration tests, a mandatory milestone 'docs/MXX_TESTS_EXPLAINED.md' explaining expected inputs/outputs and limitations, and exact VS Code terminal verification commands. Keep vendor-generated HLS/AMD originals and SHA-pinned owner logs under **~/Thesis_Evidence/** outside the checkout, with immutable timestamped directories; **never overwrite a failed first run or claim a source-only test proves real toolchain execution**.

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
~~~

**Safety/research safeguards:** physical JTAG, Linux halt, PL programming, new boot ownership and memory overwrites require explicit per-session operator authorization and power cycle after JTAG. Official MNIST TEST stays sealed until approved. Do not assert Loihi/YANA silicon fidelity, real asynchronous hardware, energy gains without sensors, 1023 analyzed images as 1023 independent coldboots, or unmatched-network acceleration.

**Source history preserved:** [pre-cleanup full 202,554-character roadmap with complete dated milestone troubleshooting](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/v1/roadmap.md). This new working roadmap is deliberately shorter. See [cleanup provenance](docs/REPOSITORY_DOCS_CLEANUP_2026_11_10.md).
