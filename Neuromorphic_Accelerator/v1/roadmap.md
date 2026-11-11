# Neuromorphic Accelerator v1 — Research Roadmap (M01–M09)

**Current status (November 10, 2026): M01–M07 COMPLETE within separately scoped acceptances; M08 IN PROGRESS. M08.2 first original Vivado 2025.2 PS→PL identity BD failure has been DIAGNOSED from owner-uploaded log and the Tcl project-before-IP-catalog ordering fixed in source, but genuine vendor revalidation remains OPEN until a new original local run. M09 remains planned.** **Authoritative next-chat entry:** [M08.2 first failed Vivado run, diagnostic and repair handoff](docs/M08_2_BD_FAILURE_NEXT_CHAT_HANDOFF_2026_11_10.md). The active project is an independently versioned SNN/FPGA research effort, not Loihi Digital Twin v4. This document records **current decisions and future gates** rather than daily engineering logs. The complete original milestone journal is preserved in [Git at the pre-cleanup revision](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/v1/roadmap.md); experiment-specific evidence remains in linked acceptance reports and under the owner's immutable local evidence directory.

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
| **M07 — Policies and ablations** | Fair cache/no-cache, scheduling, locality, batching and clearly labeled service-model experiments | **COMPLETE (PC-only/model scope, final CI/merge gate).** M07.1 direct vs LRU; M07.2 matched four-way logical controls; M07.3 fixed-byte-budget locality; M07.4 single causal history candidate; M07.5 bounded synthetic queue/timing, event batching and hypothetical synapse record sensitivity. [Acceptance review](docs/M07_ACCEPTANCE_REVIEW_2026_11_10.md). **No hardware timing, AXI measurement, real DDR or resource-matched FPGA design** |
| **M08 — Physical KV260 benchmarking** | Physical K26/PS-PL integration, kernel-owned DDR, independent neural trace, routed timing and repeatability | **IN PROGRESS (M08.1 read-only entry, no hardware run yet).** Owner authorizes KV260 operations for M08, but physical status, current boot, driver memory isolation and complete BD remain unverified. [M08 phased plan](docs/M08_PHASED_HARDWARE_PLAN.md), [operator runbook](docs/M08_FIRST_PC_KV260_RUNBOOK.md), [test explanations](docs/M08_TESTS_EXPLAINED.md) |
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

**Historical M07.2 checkpoint:** later M07.3–M07.5 work, source-only CI and the owner's merge authorization close these source-model requirements. Refer to the M07 acceptance review for final boundaries. Do not rerun original M05/M06 owner HLS/AMD gates for this source-only work.

### M07.3 — byte-controlled cache/locality ablation and prior-art tracking (2026-11-10; owner review open)

New `src/neuromorphic_accelerator_v1/m07_ablation_sweep.py`, `scripts/m07_ablation.py`, `tests/test_m07_ablation_sweep.py`, `docs/M07_PRIOR_ART_CONFIGURATION_COMPARISON.md`, and mandatory M07 test explanations/owner verification commands. The default deterministic synthetic grid `M07.3-GRID-A` comprises **two PC seeds × three resident byte budgets (128,256,512) × three neuron block sizes (2,4,8) × two M03 clustered/dispersed placements × two cache policies (direct/LRU) × four M03 logical controls** = **18 parameter configurations and 288 model rows**, not 288 board trials. For every budget/block choice, resident slots are derived from `budget/(state_record_bytes × neurons_per_block)` and a nonintegral allocation is rejected; this holds the declared data-cache budget **in bytes**, not nominal slots, across the block-size axis. Entire image/read/write record, signed16 neural numerics, role workload SHA and emitted/delivered/synaptic event work are independently verified invariant within each seed. The timestep/DDR-style state transfer stream is still M02-oracle-driven, while the event/DDR-style path executes M06 Python paged LIF. M03 DDR-style synapse read bytes are **analytical and not actually issued by the pager**. Missing original AXI bus timing, service queues, stall cycles, PPA or actual physical DDR are reported as unmeasured, not zero.

The comparability ledger documents where YANA's event-responsive hot-neuron worklist and LUT-deferred leak, SENECA's time-multiplexed state hierarchy, and HiAER-Spike's distinct neuron-state/synapse placement relate to our experiments **as architectural precedents, not matched performance baselines**. An additional separately labeled **M07.3-YANA-COUNT-ONLY** source-model test uses **1024 logical neurons**, matching only the maximum neuron-count parameter cited for a single YANA core. It has a 16KiB software canonical-state image, 256B modeled cache, and unavailable full-onchip comparator under a declared 2048B state budget; it is **NOT** a YANA neural, hardware, network or performance replication. Record experiment IDs, full geometry/precision/workload, the publication and non-equivalent features before calling any future configuration 'YANA-like'. No named accelerator's source code has been reused.

**Historical M07.3 checkpoint:** subsequent M07.4 and M07.5 completed the single activity-aware candidate and model-only event batching/queue/service experiments, respectively. The final M07 source-only acceptance review supersedes this earlier work-in-progress status. The full source regression and no-board CI exercise only existing local RTL/Icarus where applicable; original vendor evidence and physical operations remain separately gated.

### M07.4 — bounded causal activity-history eviction pilot (2026-11-10; NOT ACCEPTED)

New `src/neuromorphic_accelerator_v1/m07_activity_cache.py`, `src/neuromorphic_accelerator_v1/m07_activity_study.py`, `scripts/m07_activity_pilot.py` and `tests/test_m07_activity_history.py` (plus M07.1's optional activity-policy hook). M06 already processes eligible neurons in **ascending logical neuron ID**, which automatically groups ascending whole-block page IDs within each tick. A second within-tick "page batching" sort of the same neuron set would not change the execution order; no invented sorting gain or neural reorder is claimed. Instead the **single** M07.4 candidate retains a bounded history of last N completed read/write neuron-evaluation page IDs (default N=4/16/32) and chooses on a miss the resident page with the fewest historical accesses, LRU tie-breaking. The inherited M06 cache still performs **all** checked reads, page fills, ownership/version checks, dirty writebacks, transfer acknowledgements and poison quarantine. No future events, oracle outputs or cross-tick work rearrangement is used; independent M02/M03 reference traces and final canonical tick watermarks must match.

The default matched study `M07.4-HISTORY-A`: N128/K16/T8, seeds 17/23, clustered/dispersed event layouts, 16B state records, four fixed (neurons/block,budget bytes) geometries (4,128)/(4,256)/(8,256)/(8,512), three history depths, compared against unchanged direct and LRU controls. It generates 8 seed/geometry cases and **48** source-model activity-vs-LRU comparisons. Policy extra **page-ID history RAM and victim scan metadata are *not charged* to the declared cache DATA byte budget**, and there is no resource-matched FPGA implementation or measured latency/speedup. Host-only victim decision counts and scanned candidates are exposed separately. All signed byte changes (wins/ties/losses) are retained; two **non-neural** directed traces demonstrate that history can improve or worsen model cache misses compared with LRU while producing identical canonical state. The YANA comparison ledger classifies this as a **weak architectural analogy**, not a YANA hot-neuron FIFO or LUT-leak emulation, matched precision/SHD network, KR260 area/latency or physical speedup.

**M07.4 outcome:** complete under independently checked source scope; the owner reports local verification PASS. Do not promote the activity-history eviction candidate to HLS/RTL until full metadata/queue hardware resource costs can be assessed. M07.5 subsequently documented modeled queue/backpressure/service timing without claiming physical DDR. **No M05/M06 vendor/RTL code or original owner evidence is modified and no physical operations are authorized.**

### M07.5 — bounded batching, adjacency-representation and service-model closeout (2026-11-10)

**COMPLETE within a source-only, clearly labeled model boundary.** Added `src/neuromorphic_accelerator_v1/m07_service_model.py`, `scripts/m07_service_closeout.py`, `tests/test_m07_service_model.py` and `docs/M07_ACCEPTANCE_REVIEW_2026_11_10.md`; all M07 test explanations, Linux runbook, CI and prior-art comparability ledger updated. A passive subclass of the existing accepted M06 canonical software image records **successfully completed** sequential full-page read/write operations and verifies exact M06 bytes/transactions. It counts an M06 write-function-return before the next read as a **software sequence fence**, not a real observed AXI B-before-AR waveform. An explicitly hypothetical serialized cost model adds declared per-event enqueue/batch and bounded FIFO consumer cycles, per-LIF costs, per-chunk read/write and write acknowledgment costs; reports modeled queue depth, dispatches, producer stalls, assumed complete-run cycles, and explicit **null** for actual AXI/clock/DDR/FPGA runtime. The saturated slower-consumer negative fixture proves model backpressure can be nonzero. M07.5 also sweeps *input ingress batch width* 1/4 and *hypothetical M03 external synapse record width* 4B/8B without changing the neural inputs, M06 in-memory adjacency or accepted M02/M03/M06 behavior; the sizes are not actual synapse encoding RTL. Default 2 seeds ×2 locality layouts ×3 cache policies ×2 batches ×2 hypothetical synapse widths = **48 matched source-only results**. One affected cache model counts physical resource overhead only as **NOT MEASURED**; no useful speedup is asserted.

**Source-only final M07 disposition:** M07.1–M07.5, reproducibility, model counters, neural correctness and negative cases close the specified M07 PC research phase. Original HLS/Vivado/AMD evidence remains accepted from M05/M06 and untouched. No real hardware resource equality, DDR/AXI B/AR timing, latency, throughput or energy claim is made. The physical integration and hardware cost/benefit of the experimental activity-history policy belong **only in separately authorized M08**. [Scope-bounded acceptance and limitations](docs/M07_ACCEPTANCE_REVIEW_2026_11_10.md). GitHub PR #82 is the M07 delivery; latest-HEAD CI must pass before merge.

## 5. M08 — Physical KV260 implementation and measurement

### Current gate: M08.2 first original Vivado failure diagnosed; corrected source awaits genuine local rerun

**Owner-run evidence, 2026-11-10 22:56 America/Denver / 2026-11-11 05:56 UTC**: from `~/Git/Thesis/Neuromorphic_Accelerator/v1`, the owner sourced **`/home/dna/Vivado/2025.2/Vivado/settings64.sh`** and **`/home/dna/Vivado/2025.2/Vitis/settings64.sh`**. Actual `vivado -version` reported **v2025.2 (64-bit), SW build 6299465, IP build 6300035**, so real Vivado was callable in that terminal. Separate `vitis_hls -version` returned **command not found**, an unresolved tool-path/installation issue **not sufficient to explain** this isolated BD run: the current script does not call `vitis_hls`.

`bash scripts/run_m08_identity_bd.sh` **created a fresh original owner folder**:
`/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T055614Z_B7OyfZ`
and printed `M08_VIVADO_BD_ORIGINAL_FAILED exit_status=1`. This means the original **Vivado batch invocation returned nonzero** and the runner exited before independent successful-BD acceptance; no complete BD PASS, XSA, bitstream, JTAG, PS MMIO, hardware inference or physical DDR is established. **The owner has now supplied the original** `01_vivado_identity_bd.log`, `result.txt` and before/after SHA manifests. The first error is **`ERROR: [Common 17-53] User Exception: No open project`** at the initial `get_ipdefs -all -quiet $vlnv` catalog probe, *before* `create_project`. Before/after source SHA files match exactly: no recorded source change during failure. This is an evidenced Tcl initialization-order defect; it is not an AXI slave functional result or a demonstrated unsupported IP. The project-before-catalog check has been corrected in source, with a Tcl mock regression that reproduces the first error boundary. Do not delete the original failure folder, fabricate vendor evidence, or weaken assertions. The separate owner report confirms KV260 Linux boots normally using `sudo xmutil unloadapp`, so boot recovery is not the issue.

**Next acceptance gate:** after the narrow Tcl fix, focused regression, source tests and all eight M01–M08 exact-head workflows pass, the owner should perform **one fresh** offline Vivado 2025.2 BD validation in a different auto-created evidence directory and share raw log, result, source hashes, and (if present) BD report/export/audit. The earlier failed run remains immutable. Success is NOT presumed; diagnose any new first error independently. Keep PR #83 draft/unmerged. [Authoritative failure handoff and evidence packaging](docs/M08_2_BD_FAILURE_NEXT_CHAT_HANDOFF_2026_11_10.md). Do not proceed to bitstream/neural integration/real DDR until this entry gate actually passes.



**Status:** STARTED M08.1 (2026-11-10), branch `agent/neuromorphic-accelerator-v1-m08-kv260-bringup` from merged M07 main `c1223149d7884958984cdb77b37fc50201c3061f`. The owner has **standing authorization for KV260 hardware activity during this milestone** (no repeated permission prompts required). However real physical DDR writes still require an independently proved kernel-owned DMA buffer, address mask/coherency, actual completed BD, valid bitstream/DT and known-good boot/rollback route. Authorization does not imply the board is presently accessible, memory isolation is valid, or original toolchain simulation constitutes a physical result. Source or CI output alone cannot close physical M08.

**Stages:** [Full M08 phase-by-phase acceptance plan](docs/M08_PHASED_HARDWARE_PLAN.md). M08.1 read-only PC/original-M06-SHA and boot/UART/board identity captures. M08.2 original HLS+AMD interconnect live K26 BD, PS controls/HP DMA, integrated supervisor/quarantine, genuine placed/routed timing, raw IP/resource warning review, exact source/XSA/bitstream SHA. M08.3 Linux kernel DMA buffer ownership, coherence and AXI address/width checks, real PS/PL driver. M08.4 initial on-chip M05 (signed32) smoke, followed by separate M06 signed16 physical pager and exact original M02/M03 source-matched state/spike/recurrent traces. **Do not directly claim M05 signed32 and M06 signed16 are matched hardware four-way controls.** M08.5 actual resource-matched timestep/onchip, event/onchip, timestep/DDR and event/DDR where possible, with N/K/geometry/locality and batching fixed-work controls. M08.6 source-hashed device/PS/end-to-end timing, true page transfers/queue stalls, repeated runs and accurate routed resources; power/energy only if equipment and measurement boundaries exist. M08.7 owner acceptance/M09 handoff.

**Standalone M08.2 hardware candidate:** `rtl/m08/m08_axil_readonly_identity.v` is a read-only AXI4-Lite *slave* with known magic/version, placeholder build-tag fields, no DMA master and SLVERR for all writes, plus first-party Icarus functional TB and `m08_identity_client.py` read-only mock host protocol. It is not yet in a real K26 BD and has no physical MMIO address, XSA, bitstream, kernel adapter or proven PS/PL communication. Original AMD/HLS RTL untouched.

**M08.1 owner input accepted (host evidence only, 2026-11-10):** uploaded inventory receipt SHA256 `2c4276c13e3adb21721b8b49e027aa94cbe1e51cf592d402272684bc518606e0` passed independent receipt integrity check and all **five original accepted M06 owner ZIPs MATCH**. FT4232H USB VID:PID 0403:6011 appears. Vivado/Vitis commands missing from current shell `PATH` (not necessarily uninstalled). Local checkout contains untracked original Loihi evidence folders and Vivado logs—preserve, do not clean. The owner confirms normal KV260 Linux boot and the established `sudo xmutil unloadapp` procedure. `xmutil listapps/boardid/bootfw_status/platformstats` are now read-only capture allowlist commands. The Loihi v2 project `docs/P08_4_ACCEPTANCE.md` and `P08_4_3B_ACCEPTANCE.md` already establish a distinct routed K26 host-paged bitstream and exact **real** JTAG/VIO neural dispatch proof, **not** M08 physical performance, bitstream, or DDR allocation. [Detailed evidence crosswalk](docs/M08_1_OWNER_EVIDENCE_AND_LOIHI_REUSE_2026_11_10.md).

**M08.2 original local-Vivado trial FAILED (exit1; first genuine log now diagnosed); Tcl project-first correction committed, new owner vendor run PENDING:** `scripts/m08_identity_ps_bd_candidate.tcl` connects the standalone first-party no-DMA identity AXI4-Lite slave to the actual K26 PS `M_AXI_HPM0_FPD` through a single AMD SmartConnect, using PS PL clock/reset and original reset polarity conditioner; Vivado itself assigns the **real BD address** and must validate the actual IP/interface. `scripts/run_m08_identity_bd.sh` creates a fresh immutable SHA-before/after report/log directory and `m08_identity_bd_audit.py` requires genuine vendor status and nonphysical scope. All source-only test fixtures must be distinguished from genuine original tool output. No real PS address, bitstream, XSA or Linux driver is claimed. **Next owner-needed evidence:** `vivado -version`, `vitis_hls -version` after proper `settings64.sh`, `bash scripts/run_m08_identity_bd.sh` original readback/log or exact failed IP/error report. Do not integrate real DDR until kernel-owned memory and routed hardware verified.

**First source deliverable (M08.1):** `src/neuromorphic_accelerator_v1/m08_entry.py`, `m08_receipt_audit.py`, `scripts/m08_capture_readonly.py`, `scripts/m08_audit_readonly.py`, tests and `.github/workflows/neuromorphic_accelerator_m08_host_preflight.yml`. They only perform allowlisted host or on-board Linux **read-only** commands, preserve evidence/sha in new folders and reject physical assertions/guessed DDR addresses. The current machine's actual Vivado version, original five M06 ZIPs, current board boot status, existing full-system XSA/.xpr/.bit and kernel DMA ownership have yet to be supplied. [Exact Linux and UART operator commands](docs/M08_FIRST_PC_KV260_RUNBOOK.md).

Measure true sample-to-output service latency, steady-state throughput and variation; PL compute versus PS control, DMA and DDR transaction costs; physical cache/page hit/miss and stall counts; final LUT/FF/BRAM/URAM/DSP, routed timing, and power/energy **only if measurement equipment and boundaries are validated**. Distinguish FPGA logic execution, PS orchestration and end-to-end user-visible service; count physical repeated coldboots separately from analysis of the same capture.

**Acceptance:** every plotted hardware point is reproducible from genuine SHA-pinned raw evidence with independent neural correctness. Do not extrapolate PC model performance to physical DDR or assume achieved clock. Preserve separate original evidence for each run, including failures. Power-cycle after invasive JTAG/debug attempts; do not resume a halted Linux image.

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

**Safety/research safeguards:** M08 has standing owner authorization for KV260 hardware operations. Physical JTAG, Linux halt, PL programming, boot ownership and memory writes still require a verified live board, known-good boot/recovery and genuine driver/allocator isolation; power-cycle after invasive JTAG. Never silently overwrite Linux-owned physical DDR, corrupt QSPI, or treat permission as proof of safety. Official MNIST TEST stays sealed until approved. Do not assert Loihi/YANA silicon fidelity, real asynchronous hardware, energy gains without sensors, 1023 analyzed images as 1023 independent coldboots, or unmatched-network acceleration.

**Source history preserved:** [pre-cleanup full 202,554-character roadmap with complete dated milestone troubleshooting](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/v1/roadmap.md). This new working roadmap is deliberately shorter. See [cleanup provenance](docs/REPOSITORY_DOCS_CLEANUP_2026_11_10.md).
