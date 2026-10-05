# Loihi Digital Twin v3 Development Roadmap

## Purpose

FPGA-v3 is the next research/development line for the Loihi-1 architectural digital twin.

v3 begins from the final accepted FPGA-v2 state at:

```text
a9329caa064fee3876d69fbbe6c626ac035e67b5
Close P08 and complete FPGA-v2 roadmap
```

The v2 tree remains the frozen accepted record. v3 may reuse and modify v2 implementation code, but new v3 results must not retroactively change or weaken the accepted v2 evidence.

The central v3 goal is to move from a host-assisted FPGA execution model to a substantially board-local KV260/K26 execution model while increasing physical test coverage and improving benchmark comparability.

The inherited Loihi-1 architecture contract is initially:

```text
docs/LOIHI1_TARGET_SPEC.md
```

P01 will decide whether v3 needs a separate amendment/addendum for board-local execution and any new modeled Loihi features. Architectural fidelity claims remain distinct from FPGA implementation choices.

## v3 research goals

### 1. Board-local execution

Move algorithmic execution ownership onto the KV260/K26 as far as practical.

The target execution hierarchy is:

```text
PC / development host
  -> provisioning, launch, optional debug, result collection only

KV260 Processing System (PS)
  -> deployment/runtime control
  -> logical-core scheduling
  -> routing/barrier ownership where appropriate
  -> DDR-backed logical-context management

KV260 Programmable Logic (PL)
  -> Loihi-like core execution
  -> resident-context datapath
  -> packet/event datapath
  -> high-throughput DDR movement where justified

K26 DDR4
  -> non-resident logical-core backing contexts
  -> deployment/runtime buffers
  -> test/input/output data as required
```

The external PC must not be required in the algorithmic timestep loop for the final v3 runtime.

### 2. More physical validation

v2 proved the architecture with strong Python/compiled-software validation plus representative physical K26 dispatches. v3 should move substantially more of the regression and application validation onto the board itself.

The target is not to eliminate the Python golden model. The target is to use it to generate/freeze expectations while the KV260 executes most accepted regression/application runs end-to-end.

### 3. Better published benchmark

Select a published MNIST SNN whose architecture is reproducible enough to avoid the ambiguity encountered with the NxTF reconstruction.

The selected benchmark should preferably publish or provide:

- exact input preprocessing/encoding;
- exact layer dimensions;
- exact neuron counts;
- exact connection/synapse structure;
- neuron equations and parameters;
- inference timestep/phase schedule;
- readout rule;
- training procedure;
- source code and preferably reproducible weights/checkpoints;
- accuracy;
- neuromorphic-hardware mapping details where available;
- latency/power/energy methodology where available.

A benchmark is not accepted merely because its headline neuron or parameter count is known.

Initial candidate for source audit, **not yet selected**:

- Alpha Renner et al., "The backpropagation algorithm implemented on spiking neuromorphic hardware," Nature Communications (2024), DOI 10.1038/s41467-024-53827-9.
- The paper describes a cropped-MNIST feed-forward inference module with 400 input neurons, 400 hidden neurons, and 10 output neurons, explicit Loihi CUBA parameters, a four-timestep reduced inference path, published Loihi inference measurements, and public implementation code.
- P06 must independently audit the paper/code before this project treats it as the v3 benchmark.

### 4. Latency, throughput, power, and energy characterization

v3 should measure real board-local inference rather than extrapolating a single core dispatch into sample latency.

Measurements must keep distinct:

- algorithmic timesteps/phases;
- PL clock cycles;
- logical-core dispatch time;
- context page-in/page-out time;
- PS scheduling/routing time;
- complete timestep time;
- complete sample latency;
- steady-state throughput;
- idle/static board power;
- active board power;
- dynamic power when explicitly defined;
- energy per inference.

The KV260 SOM power telemetry may be used for reproducible board-level measurements, with an external meter retained as an optional validation path.

### 5. Multiple physical HLS execution engines — deferred

Multi-engine execution remains a valid v3 optimization direction, but it is
**deferred from the current critical path** until the single-engine DDR-backed
board-local architecture is implemented and characterized.

The reason is not primarily HLS arithmetic cost. Accepted routed evidence
suggests the compute engine itself is modest relative to K26 logic/DSP capacity.
The limiting issue is the resident-context memory architecture:

- the accepted three-context fabric uses true-dual-port URAM banks;
- one port currently services the HLS compute path and the other services
  host/integration/maintenance access;
- a two-engine design could potentially repurpose both ports for compute during
  a parallel wave, but page movement and packet/event maintenance would then
  need explicit arbitration or serialization;
- three or more simultaneous engines would require a deeper memory redesign,
  such as per-slot banking, selective replication, or moving some storage
  classes out of URAM.

Because v3's primary research goal is first to eliminate PC-owned paging and
control, introducing that memory redesign now would mix two independent
questions: **board autonomy** and **compute parallelism**.

The deferred optimization should be reconsidered after P02/P03/P08 measure the
single-engine system and show whether HLS compute serialization is actually a
dominant end-to-end latency term.


---

## Development/acceptance rules

Status meanings:

- **Complete** — deliverables are implemented, reproduced independently, and accepted.
- **In progress** — active work exists but acceptance is pending.
- **Planned** — agreed work not yet started.
- **Blocked** — waiting on a dependency/decision.
- **Deferred** — intentionally outside the current critical path.

For every major sub-milestone:

1. implement on a dedicated branch;
2. run the relevant automated/software/hardware gates;
3. provide exact reproduction commands;
4. stop for independent verification before merge;
5. record acceptance evidence only after independent verification succeeds;
6. merge only after explicit approval.

A passing developer-side test does not by itself close a hardware/software milestone.

---

## Phase summary

| ID | Phase | Status |
|---|---|---|
| P00 | Establish v3 baseline, directory, and roadmap | Complete |
| P01 | Define board-local architecture, ownership, and v3 contract | Complete |
| P02 | Move non-resident logical contexts into K26 DDR | In progress |
| P03 | Build autonomous PS-resident scheduling/routing/barrier runtime | Planned |
| P04 | Add multi-engine parallel logical-core execution | Deferred |
| P05 | Build board-local regression, observability, and data-path hardening | Planned |
| P06 | Audit and freeze an exact published MNIST benchmark | Planned |
| P07 | Execute the frozen benchmark end-to-end primarily on KV260 | Planned |
| P08 | Characterize latency, throughput, power, and energy | Planned |
| P09 | Final source-backed comparison and v3 closure | Planned |

---

# P00 — Establish v3 baseline, directory, and roadmap

**Status:** Complete  
**Accepted:** 2026-10-05

## Goal

Create an isolated v3 development tree from the final accepted v2 implementation without changing the v2 record.

## Deliverables

- copy the accepted `Loihi_Digital_Twin/v2/` tree into `Loihi_Digital_Twin/v3/`;
- preserve the existing v2 source/HLS/RTL/Vivado/test functionality as the initial v3 baseline;
- add this v3 roadmap;
- replace the copied v2 README with a v3 baseline README;
- update the parent `Loihi_Digital_Twin/README.md` to identify v2 as the accepted baseline and v3 as active follow-on development;
- record that inherited package/module names may still contain `v2` until a later deliberate compatibility migration.

## Acceptance

P00 was accepted after independent verification confirmed:

- the copied implementation matches the accepted v2 baseline except for intentional v3 documentation changes;
- all inherited `docs`, `examples`, `hardware`, `hls`, `rtl`, `scripts`, `src`, `tests`, and `vivado` Git subtrees are identical to v2;
- `pyproject.toml` and `.gitignore` are identical to v2;
- no accepted v2 files were modified;
- the inherited v3 regression suite completed at 100% with 67 passing test indicators and no reported failures/errors.

Primary acceptance record: `docs/P00_ACCEPTANCE.md`.

---

# P01 — Board-local architecture, ownership, and v3 contract

**Status:** Complete  
**Accepted:** 2026-10-05

## Research question

What is the cleanest PS/PL/DDR partition that removes the PC from the algorithmic execution loop while preserving v2 architectural semantics?

## Proposed default ownership

Unless measurements justify a different split:

- **PS/A53:** control plane, deployment loading, logical-core scheduling, global barrier, cross-page routing bookkeeping, run control, result collection;
- **PL:** Loihi-like core arithmetic, resident-context memories, packet/event datapath, performance counters, and bulk memory movement support;
- **DDR4:** backing images for non-resident logical cores and runtime buffers;
- **PC:** build/deploy, initial provisioning, optional debugging, and post-run collection only.

This is a project implementation partition, not a claim about Loihi's physical microarchitecture.

## Resolution

P01 closed on the ownership/interface architecture in
`docs/P01_1_BOARD_LOCAL_ARCHITECTURE.md`.

The detailed implementation contracts originally sketched as P01.2/P01.3 are
intentionally re-homed to the phases that implement them:

- **P02.1 — DDR backing-image ABI and coherency contract** will freeze DDR
  layout, context sections/stride/alignment, page-transfer commands, address
  validation, cache-maintenance/ownership rules, and serialization.
- **P03.1 — Autonomous runtime contract** will freeze exact run/barrier/error
  transitions, board-local timing/observability boundaries, and the v3
  implementation addendum to the inherited Loihi target specification.

This avoids treating implementation details as completed merely because the
high-level partition is accepted.

## Accepted deliverables

- v3 board-local architecture/ownership document;
- explicit external-host / PS / PL / DDR responsibility table;
- PS-to-PL control-plane direction;
- PL-to-DDR bulk-data-plane direction;
- first non-coherent ownership strategy;
- preservation of logical-core / resident-slot / physical-engine separation;
- preservation of CURRENT/NEXT event causality and global barrier semantics;
- decision that no existing logical Loihi-1 semantic rule needs to change;
- explicit decision to defer multi-engine execution until the memory system and
  single-engine board-local runtime are measured.

## Acceptance

P01 is accepted based on independent design review and explicit approval of the
PS/PL/DDR partition.

This acceptance freezes the architectural direction only. It does **not** claim
that DDR paging or the PS-resident runtime is implemented yet. Those are P02
and P03 respectively.

Primary record: `docs/P01_1_BOARD_LOCAL_ARCHITECTURE.md`.

---

# P02 — DDR-backed logical-core virtualization

**Status:** In progress

## Goal

Replace PC-RAM backing for non-resident cores with K26 DDR backing.

## Sub-milestones

- **P02.1 — DDR backing-image ABI and coherency contract.** **Focused verification passed; phase regression pending.** Freeze layout,
  fixed/variable section sizes, alignment, versioning, address validation,
  page-transfer commands, ownership/cache-maintenance rules, and deterministic
  serialization. Primary records: `docs/P02_1_DDR_ABI.md` and
  `docs/P02_1_VERIFICATION.md`.
- **P02.2 — Software reference and transfer-model validation.** **Complete; accepted 2026-10-05.** Model authoritative DDR records, resident-slot
  materialization, eviction/writeback, runtime metadata refresh, transfer byte
  accounting, and full-versus-mutable-only writeback equivalence. Primary
  records: `docs/P02_2_DDR_TRANSFER_MODEL.md` and
  `docs/P02_2_ACCEPTANCE.md`.
- **P02.3a — Resident-bank page walker and ownership path.** **Verification candidate.**
  Implement the deterministic PL bank walker over the accepted P05 host-side
  memory access boundary, with full/mutable-only transfer sequencing and
  directed RTL verification.
- **P02.3b — AXI DDR master/burst integration.** **Planned.** Connect the
  verified bank walker to the selected PS DDR high-performance path, add burst
  buffering/range checks, and integrate into the Vivado shell.
- **P02.4 — Physical DDR-backed paging acceptance.** Demonstrate that
  non-resident logical contexts live in K26 DDR and are paged into the three
  resident slots without PC RAM participating in the page loop.

## Deliverables

- deterministic `logical_core_id -> DDR backing region` mapping;
- storage for all complete logical context images required by a deployment;
- page-in/page-out between DDR and the three proven resident context slots;
- preserved CURRENT/NEXT event-bank semantics;
- preserved logical destination IDs independent of physical residency;
- explicit dirty/writeback rules;
- context fingerprints/checksums;
- measured page transfer size, latency, and bandwidth;
- PS-copy and/or AXI/DMA implementation chosen from measured evidence rather than assumption.

## Acceptance

At least the accepted v2 five-logical-core / three-resident-context workload must execute with all non-resident context state stored on the KV260 rather than in PC memory, with normalized results matching the v2 golden boundary.

---

# P03 — Autonomous PS-resident runtime

**Status:** Planned

## Goal

Move host-owned algorithmic orchestration onto the KV260 PS.

## First sub-milestone

- **P03.1 — Autonomous runtime contract.** Freeze exact run/barrier/error
  transitions, board-local timer/counter boundaries, recovery behavior, and the
  v3 implementation addendum to the inherited Loihi target specification before
  implementing the PS runtime.

## Deliverables

A board-resident runtime that can:

- load a compiled deployment into DDR;
- initialize resident contexts;
- ingest an input sample;
- schedule logical cores;
- page contexts;
- route local and cross-page packets;
- determine timestep quiescence;
- enforce the global barrier;
- swap CURRENT/NEXT event banks only at the barrier;
- advance the requested number of timesteps/phases;
- return final evidence/results and execution metadata.

## Acceptance

After a start command, the PC must not participate in logical-core scheduling, packet routing, page replacement, or timestep/barrier control.

The representative five-over-three 100-timestep workload must complete board-locally and match the normalized v2/Python architectural result.

---

# P04 — Multi-engine parallel logical-core execution

**Status:** Deferred

## Motivation

Replicating the P03-compatible HLS evaluation engine remains attractive because
independent logical cores in the same algorithmic timestep can, in principle,
consume frozen CURRENT state concurrently and produce NEXT-timestep traffic.
That could reduce the serialized compute portion of inference latency.

Accepted routed evidence also indicates that the compute logic itself is not the
obvious K26 bottleneck:

```text
P05 one-engine / three-full-context shell:
  LUTs       5,062
  registers  7,686
  DSPs       2
  URAM       47

P04 resource-scaled two-engine shell:
  LUTs       7,059
  registers  9,980
  DSPs       4
```

The two shells are not otherwise identical, so these numbers are **not** an
exact per-engine cost model. They do support the narrower conclusion that v2's
full-capacity scaling problem was dominated by retained memory rather than by
the HLS arithmetic datapath.

## Why it is deferred

The current three-full-context memory fabric is built from true-dual-port URAM
banks. In the accepted one-engine design:

- one memory side services the HLS compute path;
- the second side services host/integration functions such as packet access,
  next-event writes, and context maintenance.

A plausible two-engine design would consume both memory ports for compute during
a parallel wave:

```text
resident context A <-> port A <-> engine 0
resident context B <-> port B <-> engine 1
resident context C remains retained
```

That creates a new arbitration problem: page movement, packet draining, and
event maintenance can no longer freely use the second port while both engines
are active. The first implementation would therefore have to serialize those
operations around compute or redesign the resident-memory access fabric.

The problem becomes more fundamental at three or more engines. Three resident
slots do **not** imply three independent memory read/write ports. Supporting
3+ simultaneous engines would likely require one or more of:

- per-slot memory banking;
- selective replication of read-mostly configuration/axon/synapse/route banks;
- relocation of trace/packet/event storage to other memory classes;
- additional AXI/interconnect arbitration;
- a different resident-context organization altogether.

Those choices can increase URAM/BRAM usage and routing pressure enough to change
the physical architecture that P02/P03 are trying to stabilize.

## Why deferral is preferable

The central v3 research question is first whether the KV260 can execute the
virtualized architecture independently of PC RAM and PC-owned timestep control.

Adding multi-engine execution before that is proven would couple two separate
research problems:

1. **memory/control localization** — DDR-backed paging plus PS/PL ownership;
2. **compute parallelization** — multiple engines and a multiported/banked
   resident-memory system.

Keeping P04 deferred lets P02/P03 establish a clean single-engine baseline. P08
can then quantify how much complete-inference time is actually spent in HLS
compute versus DDR paging, packet routing, PS control, and barriers.

If compute serialization is a dominant measured term, P04 should be reactivated
with an evidence-based engine-count target.

## Preserved design rules for later reactivation

Any future multi-engine implementation must preserve:

- logical-core ID independent of engine ID;
- one engine may own at most one resident logical context at a time;
- two engines may never write the same resident context concurrently;
- CURRENT inputs remain frozen for the entire algorithmic timestep;
- generated traffic is committed only to NEXT-timestep state;
- all engines and all packet/page work must quiesce before the global barrier;
- physical engine/wave assignment is excluded from normalized logical traces;
- one-engine and multi-engine normalized results must be identical.

A future two-engine experiment should measure actual complete-inference speedup;
an assumed 2x speedup is not a valid result.

## Reactivation trigger

Reconsider P04 after the single-engine board-local implementation has accepted
measurements for:

- HLS dispatch time;
- DDR page-in/page-out time;
- packet drain/routing time;
- PS scheduling/barrier overhead;
- complete timestep latency;
- complete inference latency;
- routed resource/timing margin.

---

# P05 — Board-local regression, observability, and data-path hardening

**Status:** Planned

## Goal

Make the KV260 the primary execution target for accepted regression evidence.

## Deliverables

- board-resident regression runner;
- compact test-vector/deployment loading format;
- device-side pass/fail summaries and deterministic fingerprints;
- directed tests for arithmetic, routing, fanout, backpressure, barriers, paging, page replacement, and service-order invariance;
- full-run trace/checksum capture at selected observation points;
- hardware counters for core dispatches, page loads/evictions, DDR bytes moved, packet counts, barrier waits, PL cycles, and PS/runtime timing;
- failure diagnostics that identify the first mismatching logical core/timestep/state class.

## Acceptance

The major v3 architecture regression corpus must be physically executed on the KV260, with the Python model used as the reference/oracle rather than as the primary execution path.

---

# P06 — Exact published MNIST benchmark audit and freeze

**Status:** Planned

## Goal

Select one publication that supports a substantially tighter reconstruction/comparison than the NxTF benchmark.

## Candidate audit requirements

For each candidate, classify each important field as:

- directly source-backed;
- recoverable from public source code;
- reproducible project choice;
- ambiguous;
- unavailable/not claimed.

Audit at minimum:

- dataset preprocessing;
- input dimensions and encoding;
- full layer topology;
- neuron count;
- synapse/connection count;
- weight precision/quantization;
- neuron model/parameters;
- timestep/phase schedule;
- readout;
- training method;
- checkpoint/weight availability;
- published accuracy;
- published hardware resource/mapping data;
- published latency/power/energy methodology;
- public code/license/reproducibility.

## Acceptance

Before official-test evaluation:

- one benchmark is selected and frozen;
- exact known quantities are recorded;
- remaining unknowns are explicit;
- the benchmark is representable by the v3 architectural contract, or any required v3 extension is separately justified and accepted;
- model/conversion/timestep/readout choices are frozen before using official-test results for comparison.

---

# P07 — Full board-local benchmark evaluation

**Status:** Planned

## Goal

Run the frozen benchmark through the complete compiler/runtime/KV260 path and make the FPGA, not the PC, the primary inference executor.

## Deliverables

- deterministic compiler/deployment artifact;
- board-local DDR/context image;
- full end-to-end physical execution;
- accuracy evaluation;
- selected exact trace/state comparisons against Python;
- traffic/page/dispatch statistics;
- full-sample execution evidence rather than only representative logical-core dispatches;
- official-test protocol with zero post-test model-selection decisions.

## Preferred acceptance target

If runtime and storage permit, execute the complete MNIST official test set on the KV260. If a smaller physical set is necessary, the reason and statistical/coverage limits must be frozen before viewing comparative results.

---

# P08 — Latency, throughput, power, and energy characterization

**Status:** Planned

## Goal

Produce defensible board-level performance measurements with clearly defined boundaries.

## Latency/throughput measurements

Measure separately:

- PL logical-core dispatch latency;
- DDR page-in/page-out latency;
- routing/barrier overhead;
- complete algorithmic timestep latency;
- complete sample latency from board-local input start to final result;
- steady-state samples/second where batching or repeated execution is meaningful.

Report distributions, not only a single best observation.

## Power/energy measurements

Establish a repeatable protocol using the KV260/K26 telemetry path where suitable:

- board/SOM idle baseline;
- configured-but-idle baseline;
- active board-local inference;
- sampling cadence;
- warm-up duration;
- temperature/thermal state;
- average/median/variation;
- energy-per-inference integration over a defined interval.

If idle power is subtracted, label the result explicitly as dynamic/incremental energy rather than total board energy.

An external inline power meter may be used to validate the onboard telemetry path.

## Comparison rule

Published Loihi power/latency values may only be compared directly when workload and measurement boundaries are genuinely aligned. Otherwise they remain contextual reference values.

---

# P09 — Final v3 comparison and closure

**Status:** Planned

## Goal

Close v3 with a reproducible evidence chain covering architecture, board autonomy, physical correctness, application accuracy, and measured performance.

## Required closure evidence

- source-backed architecture contract plus any v3 addendum;
- exact accepted repository commit;
- compiled-deployment fingerprints;
- board-local runtime fingerprint/version;
- bitstream/probes identities;
- regression acceptance;
- benchmark source audit;
- official benchmark result;
- physical trace/conformance evidence;
- latency/throughput report;
- power/energy report;
- comparison ledger distinguishing source-backed facts, project reconstruction choices, direct project measurements, contextual comparisons, and unsupported/non-comparable claims.

## Final claim boundary

v3 should improve autonomy and physical evidence, but it still must not silently claim:

- transistor-level Loihi equivalence;
- physically asynchronous-circuit equivalence;
- proprietary NxSDK/NxTF binary/microcode equivalence;
- native Loihi SRAM packing unless separately proven;
- direct energy/latency superiority from unlike measurement boundaries.

---

## Deferred/future directions

- multi-engine physical execution pending single-engine latency characterization;

These are intentionally not prerequisites for the initial v3 roadmap unless later evidence makes them necessary:

- full PL-owned scheduling instead of PS-owned orchestration;
- on-FPGA/on-chip learning;
- Loihi 2 architectural targeting;
- real-time sensor/event input;
- multi-board scaling;
- physically asynchronous FPGA circuitry.
