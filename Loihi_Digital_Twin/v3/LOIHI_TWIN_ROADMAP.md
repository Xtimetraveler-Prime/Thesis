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
- P05 must independently audit the paper/code before this project treats it as the v3 benchmark.

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
| P00 | Establish v3 baseline, directory, and roadmap | In progress |
| P01 | Define board-local architecture, ownership, and v3 contract | Planned |
| P02 | Move non-resident logical contexts into K26 DDR | Planned |
| P03 | Build autonomous PS-resident scheduling/routing/barrier runtime | Planned |
| P04 | Build board-local regression, observability, and data-path hardening | Planned |
| P05 | Audit and freeze an exact published MNIST benchmark | Planned |
| P06 | Execute the frozen benchmark end-to-end primarily on KV260 | Planned |
| P07 | Characterize latency, throughput, power, and energy | Planned |
| P08 | Final source-backed comparison and v3 closure | Planned |

---

# P00 — Establish v3 baseline, directory, and roadmap

**Status:** In progress

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

P00 is complete only after independent verification confirms:

- the copied implementation matches the accepted v2 baseline except for intentional v3 documentation changes;
- the inherited general regression suite still passes from the v3 tree;
- no accepted v2 files were modified;
- the v3 roadmap correctly identifies all later work as new follow-on research rather than unfinished v2 work.

---

# P01 — Board-local architecture, ownership, and v3 contract

**Status:** Planned

## Research question

What is the cleanest PS/PL/DDR partition that removes the PC from the algorithmic execution loop while preserving v2 architectural semantics?

## Proposed default ownership

Unless measurements justify a different split:

- **PS/A53:** control plane, deployment loading, logical-core scheduling, global barrier, cross-page routing bookkeeping, run control, result collection;
- **PL:** Loihi-like core arithmetic, resident-context memories, packet/event datapath, performance counters, and bulk memory movement support;
- **DDR4:** backing images for non-resident logical cores and runtime buffers;
- **PC:** build/deploy, initial provisioning, optional debugging, and post-run collection only.

This is a project implementation partition, not a claim about Loihi's physical microarchitecture.

## Deliverables

- v3 architecture/ownership document;
- explicit host/PS/PL/DDR responsibility table;
- v3 runtime state machine;
- DDR memory map and alignment rules;
- context image ABI/versioning rules;
- packet/event queue ownership rules;
- cache/coherency policy;
- error/status/recovery model;
- timing/measurement boundary definitions;
- determination of whether the inherited Loihi-1 target spec needs a v3 addendum.

## Acceptance

The design must show how a complete inference can advance without PC intervention between timesteps.

---

# P02 — DDR-backed logical-core virtualization

**Status:** Planned

## Goal

Replace PC-RAM backing for non-resident cores with K26 DDR backing.

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

# P04 — Board-local regression, observability, and data-path hardening

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

# P05 — Exact published MNIST benchmark audit and freeze

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

# P06 — Full board-local benchmark evaluation

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

# P07 — Latency, throughput, power, and energy characterization

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

# P08 — Final v3 comparison and closure

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

These are intentionally not prerequisites for the initial v3 roadmap unless later evidence makes them necessary:

- multiple physical HLS compute engines;
- full PL-owned scheduling instead of PS-owned orchestration;
- on-FPGA/on-chip learning;
- Loihi 2 architectural targeting;
- real-time sensor/event input;
- multi-board scaling;
- physically asynchronous FPGA circuitry.
