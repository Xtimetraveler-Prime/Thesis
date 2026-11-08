# Neuromorphic Accelerator v1 — Development and Experimental Roadmap

**Status:** **M01 COMPLETE / USER-ACCEPTED 2026-11-07 local (PC-ONLY architecture/model scope)**; **M02 COMPLETE / USER-ACCEPTED (initial v1 neural contract, PC-only)**; **M03 COMPLETE / USER-ACCEPTED (PC-only matched workload and analytical traffic study)**; **M04 IN PROGRESS (v3 HLS audit and bounded host C++ candidate; pending native verification/user acceptance)**; M05–M09 PLANNED. M01 acceptance covers analytical memory-residency tradeoffs; **M02 accepts the first precise LIF software behavior and independently verified dense/event-queued traces**, not any FPGA inference speed, physical DDR measurements, or equivalence to Loihi/YANA silicon. First independent generation in `Neuromorphic_Accelerator/v1/`; **not** `Loihi_Digital_Twin/v4`. Created after the 2026-11-07 research pivot and architecture discussion. This document is a **prospective technical plan**, not a claim of implemented modules, completed native tests, FPGA results, or novel inventions. No KV260 JTAG/DDR writes are authorized here.

## 0. Purpose and research thesis

> **Question 1:** How much performance must we sacrifice to virtualize a larger network, and how much of that cost can sparsity-aware execution recover?

> **Question 2:** How do DDR-backed virtualization and event-driven sparsity interact to determine the performance, scalability, and hardware efficiency of FPGA-based spiking neural network accelerators?

**Central variable:** how many logical LIF neurons / synaptic structures a bounded FPGA working set can execute using **DDR-backed virtualization** while physical compute resources remain controlled. Inference latency, throughput, logical scale, DDR transactions/stalls, on-chip resource use and **active-state locality** are measured separately. Optimizations are hypotheses, not assumed wins. Preserve validated LIF dynamics, but **Loihi architectural restrictions and the v3 fixed 27-logical-core partition are NOT requirements**.

**Working vocabulary:** *logical neuron* = one model LIF unit; *state block* = independently resident/evictable physical-memory working-set group (not automatically a Loihi core); *physical engine* = time-shared HLS/RTL arithmetic pipeline; *scheduler* = work selection/order and residency coordinator; *DDR backing* = canonical nonresident neural/synaptic storage. These are proposed design abstractions, not frozen RTL interfaces.

**Explicit endpoint:** an independently neural-correct FPGA prototype that supports a verified bounded on-chip working set and DDR-backed logical network growth; a reproducible, controlled data set that quantifies (a) **virtualization penalty** relative to a same-workload resident implementation, (b) event-driven **sparsity benefit**, (c) **interaction** between those effects, and (d) when block/cache locality helps versus fails. If the result is slower or cannot scale, an honestly bounded negative result still closes the research question.

## 1. Phases and hard stage gates

| Milestone | Purpose | Depends on | Exit / status |
| --- | --- | --- | --- |
| **M01 — Virtualization architecture trade study** | Compare neuron-granular, block-granular and hybrid placements; pick measurable baseline + alternatives. | New scaffold | **COMPLETE / USER-ACCEPTED** — user-reported 20 native tests PASS, branch CI PASS, provisional block baseline approved; NO FPGA neural/timing results. |
| **M02 — Independent LIF and event-order reference contract** | Define exact numerical/spike semantics and immutable independent oracle; verify sparse equivalence. | M01 interface assumptions | **COMPLETE / USER-ACCEPTED** — 21 M02 + 20 M01 native CI PASS; user reports M02 PC tests PASS and approves this first LIF contract as current baseline; not an FPGA claim. |
| **M03 — Workloads, traffic model and measurement contract** | Trace-driven DDR/cache model, sparsity/locality generators and 4-way comparison rules. | M01 + M02 | **COMPLETE / USER-ACCEPTED** — user-reported native 28 M03 + 21 M02 + 20 M01 tests PASS; source CI PASS; role-isomorphic 4-way PC analytical workload/measurement protocol approved; NO board data. |
| **M04 — v3 HLS neuron-engine reuse feasibility** | Audit arithmetic versus dispatch/controller coupling; decide extract/adapt/new engine from evidence. | M02 + M03 | **IN PROGRESS** — M04.1–M04.2 source/matrix documented; M04.3 host candidate and 12 tests added; M04.4 synthesis NOT RUN; awaiting CI/native verification and user approval. |
| **M05 — Sparse event scheduling and on-chip accelerator prototype** | Implement independent event/worklist processing with bounded on-chip state; correct event/timestep behavior. | M02–M04 | **PLANNED** — software/RTL/HLS parity, no DDR dependency. |
| **M06 — DDR state backing and virtual residency engine** | Add programmable state-block mapping, transfers, eviction/writeback and measurable context stalls. | M05 + M03 | **PLANNED** — correct bounded DDR virtual state. |
| **M07 — Scheduling/cache strategy variants + controls** | Test grouping, batching, locality-aware choices vs no-cache/simple policies and resident controls. | M06 | **PLANNED** — causal ablation readiness. |
| **M08 — KV260 physical benchmark and scaling campaign** | Gate deployment; gather independent neural, clock/latency, DDR and resource measurements at matched workloads. | M05–M07 | **PLANNED** — raw immutable hardware evidence. |
| **M09 — Quantitative characterization and research closeout** | Analyze virtualization penalty/sparsity recovery/locality curves and compare with prior art responsibly. | M08 | **PLANNED** — reproducible final plots, limitations and archived evidence. |

**Gate discipline:** Each milestone is a distinct branch / draft PR and user-review checkpoint. Parent milestone code is not silently declared accepted from CI; local hardware claims require separate operator-run genuine implementation and independent physical review. No milestones below are complete yet. Changes to architecture, neural arithmetic or measurement boundaries require reapproval and new versioned artifacts rather than rewriting signed data.

## M01 — Virtualization architecture trade study (START HERE)

**2026-11-07/08 accepted M01 scope:** Candidate A/B/C byte-layout and residency contracts, standard-library deterministic [traffic model](src/neuromorphic_accelerator_v1/m01_residency.py), [cluster/dispersed CLI](scripts/m01_explore.py), [24-cell sweep](scripts/m01_sweep.py), 20 native [negative/fairness tests](tests/) and **no-board GitHub Actions** added on the M01 branch. Read the [options/actual PC-only source-run results](docs/M01_ARCHITECTURE_OPTIONS.md) and [exact operator PC runbook](docs/M01_PC_ONLY_REPRODUCIBILITY_RUNBOOK.md). **No LIF semantics, spike events, DDR timing, physical hardware performance or true neuron state layout measured.** **Acceptance obtained:** the user reports native tests PASS and explicitly approves the direction. **Configurable block/group residency is the initial provisional implementation baseline**, with individual-neuron and hybrid controls retained. Neuron-state and synaptic-connectivity placement remain separate design axes. No user-local raw output or SHA256 hash was supplied, so neither is invented; M01 acceptance relies on user-reported native PASS plus source CI and the approved reversible choice. The exact 20 tests and CI workflow are explained in [M01_TESTS_EXPLAINED.md](docs/M01_TESTS_EXPLAINED.md). **M02 must begin on its own branch after this M01 merge.**

**Research target:** decide which *residency/transfer granularity* is useful; do not prematurely assume the neuron group is a Loihi-like core. This is a proposal to **compare established architectural choices**, not claim invention of neuron caching, time-multiplexing or hierarchical memory.

### M01.1 — Candidate A: individual-neuron state virtualization

- Every logical neuron has an independent state identity/DDR address; the on-chip table caches selected states or individual records. Sparse access transfers little unused state but risks many short/random DDR transactions and tag/index overhead.
- Define neuron state tuple, address precision, dirty flags and atomic update hazards. Model bandwidth **and latency** of noncoalesced transfers, not only bytes.

### M01.2 — Candidate B: block/group-based virtualization

- Map configurable-size groups of neurons to contiguous DDR state blocks; a bounded on-chip buffer holds multiple groups. Schedule or batch work by touched group when semantics permit.
- Sweep number of neurons per group and resident block capacity. Measure wasted bytes vs burst efficiency, context count, scheduler costs, cache hit/miss, dirty writeback and group hotness.
- Groups are **storage/scheduling units**, not presumed biological layers or Loihi cores. Start with reproducible contiguous-ID mapping and reserve graph- or activity-based grouping as an explicit later optimization/control.

### M01.3 — Candidate C: hybrid memory residency / placement

- Keep a restricted active/subset of neuron states resident on-chip while backing the full logical state (or overflow) in DDR; study whether synaptic adjacency/weights should separately live in DDR or local memory.
- Distinguish a **true capacity-limited DDR-backed virtual state** policy from a network whose complete state fits on-chip. Compare at equal memory budgets; no hidden unlimited on-chip exception.
- This design space is related to known mixed on/off-chip memories; for example **HiAER-Spike** uses external HBM for connectivity and FPGA-local memory for neuron state, but **our dynamic DDR-neuron residency comparison is a proposed adaptation, not its claimed invention**.

### M01 exit evidence

- A versioned architecture options memo: diagram of data ownership, group and neuron lookup/address calculation, choices for state vs synapse storage, event buffering and PS/PL split.
- A **rough, reproducible analytic or trace-based** DDR transaction/bytes/stall cost estimate for the three approaches at the SAME network, exact event trace, hypothetical working-set budget, and grouped versus scattered event locality; not labeled as KV260-measured performance.
- Record a provisional baseline and at least one retained alternative; justify what is postponed based on risk/cost. Freeze only the interfaces needed by M02/M03, and explicitly record what remains unresolved.
- **No board run / no speedup claim.** M01 passes only after documented user review of mapping and numerical implications.

## M02 — Independent LIF / event-order reference (REQUIRED)

**2026-11-07/08 accepted M02 software-reference scope:** Draft [exact numerical and timestamp contract](docs/M02_PROVISIONAL_LIF_CONTRACT.md), [dense scalar independent oracle](src/neuromorphic_accelerator_v1/m02_dense_reference.py), [structurally separate event-bucket cross-check](src/neuromorphic_accelerator_v1/m02_event_reference.py), [strict shared input/network validation](src/neuromorphic_accelerator_v1/m02_types.py), curated absolute golden fixtures and seeded recurrent/delayed differential tests. A safe [PC-only 54-case report CLI](scripts/m02_reference_check.py) produces per-case source/trace hashes; [full 21-test explanation](docs/M02_TESTS_EXPLAINED.md) and [operator native verification runbook](docs/M02_PC_ONLY_VERIFICATION.md) explain gates. Neither model skips quiet-neuron updates; both use the **initial user-accepted v1 LIF functional reference contract (revision 1)**, not Loihi silicon fidelity, YANA's lazy updates, or a physical hardware result. **User independently reports M02 tests PASS and approves this reference for now**, so M02 is CLOSED in its PC-only semantics and verification scope. User-local original SHA256 of generated reports was not furnished; do not invent one. Any later change to numerical semantics must have an explicit new contract version and fixture/test review.

**M01 EXIT GATE PASSED:** user-approved provisional configurable block-state residency, individual/hybrid comparison controls, synaptic placement kept separate. This completes **M01 PC-only research**, not a neural/FPGA architecture freeze. The new M02 reference arithmetic and event semantics require their own independent testing and review, now underway in the separate M02 branch.

**Decision:** A **new, small software reference IS REQUIRED** even though v1 is not a Loihi digital twin. Its purpose is independent functional correctness and fair workload equivalence, *not* fidelity to Loihi silicon. v3's verified arithmetic/oracles are reusable **test vectors and design knowledge**, but copying the v3 executor as the only expected-result source risks a common-mode bug.

**Deliverables:**

- Write an architecture-independent, readable **dense timestep scalar LIF reference** (e.g. simple Python/NumPy, no cache/pipeline assumptions), plus a logically separate sparse/event-scheduled functional model or trace checker; ensure both read an identical, versioned network/event format.
- Define exact signed widths, rounding, saturation, leak, bias, synaptic current accumulation, threshold/reset and refractory behavior; input event timestamp and tie order, axonal/synaptic delay and repeated spikes, and deterministic output order. Set whether recurrent nets are in scope for the first implementation.
- **Important correctness hazard:** a neuron receiving zero spikes may still require a state update or autonomous spike due to bias/dynamics. Lazy LIF decay as in YANA can differ from repeated fixed-point rounding, saturation and leak; either prove bit-exact under chosen restrictions or document and verify a separately frozen v1 numerical rule. Never claim automatic Loihi equivalence or transplant YANA's leak LUT without attribution/licensing.
- Independent golden fixtures: a single LIF neuron, zero/single/duplicate spikes, long idle intervals, negative weights, max/min/saturation, threshold equality, reset, time boundary, delayed events, tiny feedforward and recurrent tests if supported; property/differential tests against v3 for the precise overlapping arithmetic subset only.

**Acceptance:** bit-exact state/spike trace parity for chosen v1 specification (or an explicit, approved numerical tolerance + accuracy test if arithmetic differs), with negative tests that catch altered event ordering and context state. The reference is the immutable neural truth for M05–M09, not the optimizer's performance oracle.

## M03 — Reproducible workload, memory-traffic model and metrics

**2026-11-07/08 M03 PC-only accepted scope:** Deterministic [role-isomorphic synthetic networks and signed current streams](src/neuromorphic_accelerator_v1/m03_workloads.py) isolate active-neuron-ID locality without changing fanout, weights or exact neural behavior; [M03 exact sparse zero-state safe-skip reference](src/neuromorphic_accelerator_v1/m03_sparse_reference.py) is bit-exact against **both accepted M02 independent evaluators**. [Four-way analytical model](src/neuromorphic_accelerator_v1/m03_traffic.py) separately counts neuron updates, synapse traversals, hypothetical state/synaptic DDR bytes/transactions, group touches, and conceptual pending event deliveries; onchip rows become **UNAVAILABLE** when the state footprint exceeds capacity. Reproducible [matched pair](scripts/m03_explore.py) and [36-pair two-seed workload sweep](scripts/m03_sweep.py), [28 native M03 tests](tests/) and source-only no-board CI added. Detailed [model/future physical measurement contract](docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md), [actual tests](docs/M03_TESTS_EXPLAINED.md) and [operator local test runbook](docs/M03_PC_ONLY_VERIFICATION.md). **Hardware RTL, real DDR timing, HLS reuse, accelerator performance, trained-model accuracy and physical energy remain UNMEASURED.** User reports native tests passing and explicitly authorizes M03 closure and merger. M03 is **complete for its source-only research/evaluation-plan deliverables**, not physical performance. User-local original JSON SHA256s or raw test logs were not furnished; no individual original-user receipt is claimed. Source CI confirms all three native suites and the 36-paired-workload generated report.

**Deliverables:**

- Deterministic synthetic graph/event generator with frozen seeds and exact SHA for networks/weights/input streams; independent knobs for logical neurons N, fanout/connectivity sparsity, temporal event rate, and **active-group locality at fixed total event/synaptic work** (clustered, scattered, adversarial). Add a small genuine trained benchmark later with test split/provenance and accuracy recorded.
- Build a **functional abstract memory model** of the M01 placements: explicit transaction count/size, DDR bytes/read/write, active block count, cache hit/miss, evictions, dirty writebacks, queue occupancy and reordering. Distinguish cycle/latency *estimates* from real KV260 counters; avoid invented achieved transfer rates.
- Freeze comparison rules: equal logical network, fixed-point semantics, weights, input events, group organization (unless deliberately swept), functional outputs, declared cache capacity and comparable compute resources. When smaller on-chip controls no longer fit, report DDR scalability **separately**, never extrapolate a resident control to large N.
- Predefine service boundary (A53 input submission through final output and optional initialization policy), per-phase A53 vs PL timer calibration, warm/cold cache policy, frequency, repetition unit, uncertainty/p95 and planned hardware independent-session protocol. No headline speedup against unlike v3 A/B models or published YANA numbers.

**Acceptance — PASSED for PC-only scope:** the same signed fixtures produce the same neural truth, role-normalized full voltage/spike trace hashes and reproducible memory-traffic accounting under all available analytical placement models. User-reported local test PASS and acceptance of milestone scope; CI artifact verifies source-run. No hardware-derived latency or energy claim. **M04 is the next separate branch milestone, not started by this merge.**

## M04 — Existing HLS evaluation engine audit / reuse or rewrite gate

**M04 working branch (not merged):** `agent/neuromorphic-accelerator-v1-m04-hls-audit`, cut from accepted main merge commit `2ceac037`. Audit actual self-authored v3 HLS arithmetic/control/interfaces, and determine extract/wrap/new engine feasibility without copying old fixed-core sequencing or YANA code. Read the [authoritative original M04 handoff](docs/M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md), [source-backed audit and decision matrix](docs/M04_HLS_ENGINE_AUDIT.md), [12-test explanation](docs/M04_TESTS_EXPLAINED.md) and [VS Code no-board verification runbook](docs/M04_PC_ONLY_VERIFICATION.md). **M04.1/M04.2 analysis recorded, M04.3 bounded host-only candidate committed, M04.4 synthesis NOT RUN; no user verification/acceptance yet.** The stateless candidate is not a streaming RTL kernel or full-domain M02 proof.

**Deliverables:**

- Inspect actual v3 P02/P03 LIF arithmetic, HLS source, AXI/memory interfaces, per-core dispatch contract, state layout, timing report, resource estimates and source/ELF/bitstream lineage. **Do not** infer reuse suitability from v3 correctness or single dispatch alone.
- Build a tiny standalone spike/LIF functional interface specification and compare: (A) extract verified arithmetic while replacing control, (B) wrap the existing engine with a buffering layer, and (C) new streaming update datapath. Assess initiation interval, multi-port hazards, local state access and synthesis feasibility on current K26 resource limits.
- Demonstrate host-only verification for a spike/update packet → LIF state update contract and HLS/RTL simulation; if possible perform **genuine local Vitis HLS/Vivado synthesis** with clearly labeled post-synthesis resource estimates. Do not claim a physical clock/throughput from CI.

**Provisional engineering decision (not accepted):** implement a fresh minimal per-neuron datapath; reuse v3 lessons about saturation, trace and memory decoupling, **not** its different leak/current/refractory/threshold math or old per-core per-step A53 command path. Exact M02 neural behavior verified by host differential tests **only over the explicitly bounded request domain** once the new test suite passes; legal M02 inputs beyond uint32 decay and int64 aggregate capacity remain unproven. No measured II/latency/resources/Fmax; optional offline Vitis synthesis requires available tools and separate evidence. **Acceptance pending** independent user native verification, bounded-domain review and explicit merge permission.

## M05 — Event scheduler + on-chip processing prototype

**Deliverables:**

- Implement an event FIFO/temporal worklist, sparse fanout traversal, per-neuron or per-block accumulation and a bounded physical LIF update engine, initially with on-chip state and no DDR virtual paging. Define event ordering, duplicate/merge behavior, backpressure/overflow and timestep completion/barrier contract.
- Use simple correctness-first schedules: fixed-time bucket ordering with deterministic within-bucket grouping where numerically safe. Track active neurons; avoid work on quiet neurons only when M02 proves legal. A53 should launch/configure a workload, **not** service each spike in the critical path.
- Simulate independently against M02 for small dense/sparse feedforward and selected recurrent cases; assert no dropped/double events, proper idle bias/leak behavior, and bounded queue behavior. Record HLS/RTL synthesis / timing estimates if toolchain available.

**Acceptance:** independently checked on-chip event-driven run with known counters and no DDR dependency; document differences from YANA rather than claiming ownership of hot-neuron and deferred-leak ideas.

## M06 — DDR-backed residency and transfer engine

**Deliverables:**

- Map canonical logical neuron state to DDR and bounded BRAM/URAM working set (or select another M01-proven option); define clean/dirty state, ownership, page identity, last-update times, eviction/restore consistency and crash/failure visibility.
- Integrate a bulk/AXI transfer method and address-boundary checks; instrument bytes, bursts, transactions, read/write latency, stalls, working-set misses/evictions, and queue backpressure. Never assume isolated memory ownership (Linux/FSBL/RPU/DMA).
- Software and PL simulation negative tests: wrong page IDs, double misses, dirty eviction, interrupted transfer, stale state, overcapacity, wraparound, out-of-range DDR, unexpected simultaneous requests and exact numerical parity across eviction.

**Acceptance:** original signed neural fixture parity when working set is forcibly smaller than the logical network, replayable DDR/eviction logs and independent evidence. Prior to ANY physical KV260 JTAG/DDR test: distinct explicit operator authorization, no destructive overlap, original source/ELF/bitstream checks, disposable boot and mandatory physical post-attempt power-cycle.

## M07 — Scheduling/virtualization configurations and controlled ablations

**Deliverables:**

- Implement **baseline first**: no-cache/direct state fetch or minimal fixed-residency policy; one simple cache policy (FIFO/LRU or equivalent), and at most one candidate activity-/locality-aware group scheduler. Do not commit to a complicated adaptive scheduler before observing baseline counters.
- Provide a reproducible parameter matrix for **(1) timestep/on-chip, (2) event/on-chip, (3) timestep/DDR, (4) event/DDR** under a size where all configurations fit and same neural semantics; adjust architecture if a fair on-chip control requires a different physical layout and disclose any unequal resource utilization.
- Candidate optimization variables: state-block size, on-chip budget, cache policy, group mapping, event batching, fanout format, locality. Factor experiments so group locality and total event count are independently varied; use near-identical compute and clocks or report differences.
- Cross-check cache/performance counters with PC abstract model and functional oracle. Do not treat an estimate, FPGA simulated cycle count and real A53/PL clock-domain boundary as the same metric.

**Acceptance:** honest ablation implementation with measurable per-policy counts and independently matching neural outputs; a candidate optimization is optional, and a negative result is acceptable.

## M08 — Real KV260 physical measurement campaign

**Entry gates:** M02 original functional fixtures PASS, M05 on-chip neural/trace parity, M06 DDR residency/memory safety PASS, M07 matched controls and instrumentation documented, genuine Vivado/Vitis route/synthesis accepted, operator preflight and separately scoped destructive physical approval. **Neither source CI nor this document authorizes JTAG.**

**Measure:**

- Real exact firmware/source/XSA/bitstream/route/report SHAs, target clock frequency, complete image/sample service latency with documented initialization/cache policy, throughput and run-to-run variability.
- Timed compute, PS command overhead, queue/scheduler and DDR transfer phases (properly calibrated across clock domains); physical transferred bytes, transactions, hit/miss/evictions and engine idle/stall counters.
- FPGA LUT/FF/BRAM/URAM/DSP post-route resources and achieved timing; energy/power **ONLY** if a sensor boundary and repeatable measurement protocol are actually established (otherwise mark NOT MEASURED).
- Repeat independently accepted runs at a declared unit (whole sample for within-run distribution; independent coldboots for run variation). Fresh external immutable per-run directories, raw capture retention, original neural independent rereview and no original MNIST TEST access unless separately approved.

**Acceptance:** every plotted point can be traced to original SHA-pinned raw captures + independent neural PASS and metadata. Distinguish correctness PASS from inference-speed claims, and never count a PC rereview of one capture as a new hardware run.

## M09 — Quantitative virtualization / sparsity characterization and closeout

**Main contrasts (same neural network, precision and timing scope where all alternatives fit):**

- **Virtualization penalty:** `T_DDR / T_onchip`, for matched event or timestep strategy with explicit DDR-residency policy. State ratio scope; large N does not have an on-chip control if it cannot fit.
- **Sparsity benefit:** `T_timestep / T_event`, evaluated separately for on-chip and DDR-backed implementations.
- **Interaction / recovery:** whether event-driven DDR reduces the virtualization penalty relative to timestep DDR; report the four-way interaction as ratios or differences with uncertainty, not automatically a speedup.
- **Locality penalty:** time/DDR traffic at **fixed total event and synaptic work** as distinct active groups, group size, cache size and event order vary. Characterize crossover points where sparsity no longer pays for DDR transaction latency.
- **Accuracy and overhead:** verify same outputs where promised; for any accuracy-changing pruning or model change report accuracy versus measured latency. Hardware utilization/throughput scaling and measurement limits explicitly disclosed.

**Deliverables:** reproducible plot scripts/tables, data manifest with source/build/report SHAs, full protocol, negative outcomes, benchmark comparability table (e.g., YANA/HiAER where truly matched), and thesis-ready discussion of what virtualization enables and what it costs.

**Acceptance / endpoint:** a defensible quantitative statement describing performance/capacity tradeoffs with confidence/variation and caveats, not a predetermined win. Archival and user review; retain source/raw accepted evidence immutable.

## 2. Prior art, credit and code provenance — mandatory review before implementation

**Key distinction: concept attribution and code licensing are different obligations.** Use sources explicitly for ideas and paper descriptions; **independent implementation of an established idea is not plagiarized when properly attributed**, but it is also not automatically novel. Do not clone third-party RTL/software, copy schematics/figures, or translate code without inspecting the original LICENSE and retaining applicable notices/conditions. Keep a provenance ledger of which file/module and test concept was independently authored, adapted from v3, or derived from an external work; include upstream repository/commit/license and permission review for any code-derived implementation.

| Candidate mechanism / M01 option | Prior-art basis and appropriate credit | What is our *proposed experiment*, not a novelty claim |
| --- | --- | --- |
| Neuron-by-neuron state virtualization | Shared/time-multiplexed neurons and state load/store overhead are explicit in **SENECA (Tang et al., 2023)** and broader digital neuromorphic architectures; individual-addressed state is a general design option. | Measure fine-grained K26 DDR transactions vs batching, at fixed neural work; we do **not** claim to invent per-neuron virtualization. |
| Group/block-based residency and scheduling | Blocks/pages, working-set caching and locality are established computer-architecture concepts; logical/physical neuron sharing predates this project. Loihi-inspired v3 has historical fixed DDR contexts. | Make state block size and event locality **independent measurable axes** without Loihi's fixed logical-core mapping; do **not** claim generic blocking/caching is new. |
| Hybrid on-chip state / DDR synapses (or DDR overflow states) | **HiAER-Spike (Frank et al., 2026)** uses external high-bandwidth synaptic storage and on-chip neuron state, among other hierarchical memory approaches. This is **not a mechanism uniquely taken from YANA**. | Isolate *neuron-state* DDR virtualization versus synaptic placement and dynamic bounded cache; eventual optimization only claimed after measured results. |
| Active-neuron worklists, sparse event pipeline | **YANA (Pachideh et al., 2026 arXiv; also Brain Informatics 2025 work)** uses a five-stage pipeline, hot-neuron FIFO, temporal/spatial sparsity and event-driven LIF updates. Other sparse/event accelerators exist. | Explore our own PL control and DDR-aware active-group coalescing; **cite YANA prominently and do not reproduce its exact implementation/diagram without proper rights/credit**. |
| Deferred leakage with last-update timestamps/LUT | Explicitly implemented and described by **YANA**. Forward-Euler quantization and lazy decay are **not guaranteed equivalent to repeated fixed-point v3 dynamics**. | Optional reference-verified optimization only, not a requirement and not an original invention claim. |
| Time-multiplexed FPGA LIF, pipelined readout | **Ansari & Wielgosz (2026)** and other prior implementations; not a new algorithmic principle. | Reuse locally developed v3 arithmetic only after an independent interface and validation review; no uncredited external pipeline or datapath reuse. |

**Primary citations and origin points:**

- Pachideh, B., et al. (2026 arXiv posting). *YANA: Bridging the Neuromorphic Simulation-to-Hardware Gap*. https://arxiv.org/abs/2604.03432 ; upstream https://github.com/fzi-forschungszentrum-informatik/yana . At review on 2026-11-07, upstream publicly displays **CERN-OHL-W-2.0 hardware** and **EUPL-1.2 software** license files: both must be checked at a specific commit *if any code is reused*. Bibliography/proceedings year should be checked before thesis publication.
- Tang, G., et al. (2023). *SENECA: building a fully digital neuromorphic processor, design trade-offs and challenges*. https://doi.org/10.3389/fnins.2023.1187252 .
- Frank, G., et al. (2026). *HiAER-spike software-hardware reconfigurable platform for event-driven neuromorphic computing at scale*. https://doi.org/10.1038/s44335-026-00062-8 .
- Ansari, R., & Wielgosz, M. (2026 preprint). *A Time-Multiplexed Spiking Neural Network Accelerator with Pipelined Readout for FPGA Inference*. https://arxiv.org/abs/2608.00595 .
- Existing expanded thesis bibliography and detailed summaries: [`../../LitReview.md`](../../LitReview.md). Prior project-owned sources and evidence: [`../../Loihi_Digital_Twin/v3/`](../../Loihi_Digital_Twin/v3/).

**Credit checklist per implementation PR:** link relevant literature in the design note; label *known prior art / own design choice / measured new result* separately; identify code/data/images reused and upstream commit/license; check hardware license compatibility; supply independent oracle cases and negative tests; avoid verbatim source-derived text/figures; distinguish a derived implementation from a new contribution in the thesis.

## 3. Open decisions to settle during M01/M02 (do not assume these are settled)

1. **Reference neural semantics:** exact v1 LIF equations/precision, bias/refractory/saturation, when spikes are emitted, whether lazy decay is allowed, and which recurrent/delayed networks must work. Prefer a correctness-first *dense scalar reference* plus independent event checker.
2. **Unit of virtualization:** per-neuron state, fixed/tunable block, or hybrid and **whether synapses are separate from state**. Resource budget and whether a block is a cacheline versus a logical scheduling group.
3. **Scheduling time model:** time-bucketed deterministic SNN events versus fully asynchronous timestamp queue; handling zero-input decay, event duplicates/order, backpressure and recurrent causality.
4. **DDR/PS/PL hardware budget:** actual K26 BRAM/URAM, target PL clock and realistic DDR access patterns; source of true DDR counters and AXI DMA choice; A53 participates only in control if possible.
5. **First workloads:** small interpretable synthetic SNN and a realistically trained event dataset; fixed accuracy acceptance target and official MNIST TEST seal, reproducible event ordering.
6. **Control and statistical plan:** fixed resident capacity and comparable physical engines across policies; define independent physical run repetitions, sample timing scope, warm-up/cache policy and hardware version pins.
7. **Attribution boundary:** if any upstream YANA/other RTL/software is considered, confirm licenses, code lineage and correct citation **before** incorporation; papers alone do not authorize copying code.

**Recommended first approval:** agree on M01 candidate metrics and M02 LIF reference contract before writing an HLS or RTL engine. Keep a path open for surprising M01 results; change this roadmap with an explicit versioned review rather than retroactively calling an unsuccessful configuration a design failure.

## 4. Development workflow, file structure and non-destructive first commands

**Version root:** `Neuromorphic_Accelerator/v1/`. M01 created PC-only state-residency models, M02 added the accepted dense and queued LIF revision-1 software references, and M03 added neural-isomorphic synthetic workloads, an exact sparse safe-skip checker, four-way analytical traffic accounting and source-only sweeps in `src/`, `scripts/`, `tests/` and `docs/M0*_*.md`. **No v1 HLS/RTL/Vivado board implementation or genuine DDR/FPGA latency result exists yet.** Keep Loihi_Digital_Twin/v3/ frozen and separately versioned.

PC checkout of **accepted M03 after merging PR #77** to `main`, before the next M04 branch is created:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
ls -l Neuromorphic_Accelerator/v1/
sed -n '1,120p' Neuromorphic_Accelerator/v1/roadmap.md
git status --short
```

**Milestone branch discipline:** create a new branch from the latest user-accepted `main` for each milestone; keep implementation work unmerged until the user independently verifies the relevant tests and explicitly authorizes closure/merge. Run local nonhardware tests and source-only CI, and provide exact VS Code terminal checkout, build/simulation and test commands with every substantive code change. **Mandatory milestone test explanation:** for every MXX, add/update `Neuromorphic_Accelerator/v1/docs/MXX_TESTS_EXPLAINED.md` before seeking acceptance. Document each actual test's purpose, inputs/fixtures, how it works, expected outcome, negative cases, source/CI and user-native verification, and limitations of what a PASS does NOT demonstrate. Link the explanation from the roadmap, current handoff seed and local verification runbook. Even if the milestone is documentation/audit-only, explain its read-only source/consistency checks rather than falsely claiming functional tests. Keep new actual source/ELF/bitstream/raw evidence outside repository and `/tmp`, under an immutable timestamped path such as `$HOME/Thesis_Evidence/`. Never silently reuse accepted v3 evidence as a new accelerator run. FPGA JTAG, Linux halt, PL programming, DDR overwrites and boot ownership require **new session-specific operator authorizations**, and a physical power-cycle after **every** JTAG attempt; no physical execution is part of this roadmap creation.

**Scientific safeguards:** official MNIST TEST sealed; no measured energy without sensor/boundary; no asserted match to Loihi/YANA silicon; no inferred PL-only speedup from A53 service; no 1023 images confused with independent physical coldboot repetitions; no network-size-mismatched accelerator comparison.
