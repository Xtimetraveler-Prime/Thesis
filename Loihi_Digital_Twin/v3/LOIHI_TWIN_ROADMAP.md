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

### 5. Multiple physical HLS execution engines

v3 should no longer assume that one physical HLS engine is the final execution
topology. Once DDR-backed contexts and the autonomous board runtime are proven,
the PL execution plane should be scaled so independent logical cores from the
same algorithmic timestep can be evaluated concurrently.

The first acceptance target is **two simultaneously active
`loihi_core_v2_tick`-compatible engines**. A third or larger engine count is a
measurement-driven extension, not a pre-committed requirement.

The reason for this staged target is architectural as well as physical:

- accepted v2 invariance already permits physical-engine count to differ from
  logical-core count;
- same-timestep logical cores consume frozen CURRENT inputs and produce NEXT
  traffic, so independent cores can be serviced concurrently without changing
  logical causality;
- the routed one-engine/three-context P05 shell used 5,062 LUTs, 7,686
  registers, and 2 DSPs, while the routed resource-scaled two-engine P04 shell
  used 7,059 LUTs, 9,980 registers, and 4 DSPs;
- v2's scaling problem was dominated by full retained context memory, not by
  arithmetic-engine DSP/LUT demand;
- the current resident-memory fabric is true-dual-port, which gives a practical
  first path to two compute engines but not an unconstrained number of
  simultaneous engines without further banking.

The performance goal is reduced compute serialization, not an assumed 2x
end-to-end speedup. DDR paging, packet drain/routing, barrier work, unequal core
sizes, and PS overhead must be measured separately.

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
| P01 | Define board-local architecture, ownership, and v3 contract | In progress |
| P02 | Move non-resident logical contexts into K26 DDR | Planned |
| P03 | Build autonomous PS-resident scheduling/routing/barrier runtime | Planned |
| P04 | Add multi-engine parallel logical-core execution | Planned |
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

**Status:** In progress

## Research question

What is the cleanest PS/PL/DDR partition that removes the PC from the algorithmic execution loop while preserving v2 architectural semantics?

## Proposed default ownership

Unless measurements justify a different split:

- **PS/A53:** control plane, deployment loading, logical-core scheduling, global barrier, cross-page routing bookkeeping, run control, result collection;
- **PL:** Loihi-like core arithmetic, resident-context memories, packet/event datapath, performance counters, and bulk memory movement support;
- **DDR4:** backing images for non-resident logical cores and runtime buffers;
- **PC:** build/deploy, initial provisioning, optional debugging, and post-run collection only.

This is a project implementation partition, not a claim about Loihi's physical microarchitecture.

## Sub-milestones

- **P01.1 — Board-local ownership and interface architecture.** Freeze the PC/PS/PL/DDR responsibility split and the intended PS↔PL / PL↔DDR interface directions before implementation.
- **P01.2 — DDR backing-image ABI and coherency contract.** Freeze DDR layout, context sections/stride/alignment, page-transfer command format, address validation, cache-maintenance/ownership rules, and machine-checkable serialization.
- **P01.3 — Runtime state machine, observability, and v3 target addendum.** Freeze exact run/barrier/error transitions, timing boundaries, and the v3 implementation addendum to the inherited Loihi target specification.

P01.1 is currently a verification candidate in `docs/P01_1_BOARD_LOCAL_ARCHITECTURE.md`.

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

# P04 — Multi-engine parallel logical-core execution

**Status:** Planned

## Goal

Increase physical compute parallelism without changing logical-core identity,
capacity, timestep causality, or normalized results.

The initial target is two simultaneous P03-compatible HLS evaluation engines
sharing the existing three resident full-context slots. More engines are
permitted only after measured resource/timing/memory-port evidence supports
them.

## Architectural model

With `E` physical engines, the PS scheduler services each algorithmic timestep
in **waves** of up to `E` independent logical cores:

```text
timestep t CURRENT state/events are frozen

wave 0:
    engine 0 -> resident logical core A
    engine 1 -> resident logical core B
    wait for both dispatches to finish
    drain/commit A and B packets into NEXT state

wave 1:
    page/prepare contexts as required
    engine 0 -> logical core C
    engine 1 -> logical core D
    ...

final wave:
    remaining logical cores

global barrier:
    only after every logical core is complete and all NEXT traffic is committed
```

Engine assignment is implementation-only metadata. Packets and traces continue
to use logical core IDs.

## Resident-memory consequence

The current P05/P08 resident memory fabric uses true-dual-port memories with one
side serving the single HLS engine and the other serving host/integration
traffic. The first two-engine design should therefore investigate reusing the
two memory ports as two compute ports during a parallel dispatch wave.

During that wave:

- engine 0 owns compute port A;
- engine 1 owns compute port B;
- page movement and packet-maintenance access to the affected shared banks are
  paused/arbitrated until the wave completes;
- packet draining/routing happens after the engines complete, before those slots
  may be reused.

This is the least invasive path to real parallelism. It intentionally does not
promise concurrent DDR paging plus two-engine compute in the first
implementation.

Three or more simultaneous engines would require a different resident-memory
organization, such as per-slot banks or selective replication/migration of
memory classes. That option must be justified by post-route resource and
performance data because naive per-slot separation can materially increase
UltraRAM usage.

## Deliverables

- parameterized physical-engine count in the v3 execution scheduler/control
  interface;
- two instantiated P03-compatible HLS engines;
- resident-slot-to-engine assignment logic;
- dual-engine start/done/status/cycle accounting;
- arbitration/ownership rules between compute, packet maintenance, and page
  transfer;
- parallel-wave scheduler support in the PS runtime;
- normalized invariance tests comparing one-engine and two-engine execution;
- simultaneous-producer packet tests;
- routed timing/resource evidence for the two-engine shell;
- measured one-engine versus two-engine dispatch/timestep/full-inference
  performance on at least one representative multicore deployment.

## Acceptance

P04 is complete when:

1. two different logical cores can physically execute at the same time on two
   HLS engines;
2. normalized architectural results match the accepted one-engine execution;
3. same-timestep CURRENT/NEXT causality and the global barrier remain exact;
4. routed K26 timing closes at the accepted target clock or any changed clock is
   explicitly justified;
5. resource use is reported separately for engines, resident contexts, and DDR
   paging infrastructure;
6. measured latency shows where parallelism helps and where paging/routing/
   synchronization remains the bottleneck.

A theoretical 2x speedup is not an acceptance criterion.

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

These are intentionally not prerequisites for the initial v3 roadmap unless later evidence makes them necessary:

- full PL-owned scheduling instead of PS-owned orchestration;
- on-FPGA/on-chip learning;
- Loihi 2 architectural targeting;
- real-time sensor/event input;
- multi-board scaling;
- physically asynchronous FPGA circuitry.
