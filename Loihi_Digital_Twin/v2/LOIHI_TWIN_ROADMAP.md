# Loihi Digital Twin v2 Development Roadmap

## Purpose

This document is the **active development tracker for FPGA-v2**. It records:

- which development phase is currently active;
- which deliverables have been completed in each phase;
- which deliverables remain;
- the completion gate for advancing to the next phase; and
- the architectural and verification rules that apply across the whole v2 program.

The detailed Loihi-1 architectural requirements are defined separately in:

```text
Loihi_Digital_Twin/v2/docs/LOIHI1_TARGET_SPEC.md
```

That specification is the normative architecture contract. This roadmap tracks
**development progress against that contract**.

The preserved FPGA-v1 development history remains in:

```text
Loihi_Digital_Twin/v1/MILESTONES.md
```

---

## Status legend

- **Complete** — all required deliverables and completion criteria are satisfied.
- **In progress** — active work has started, but one or more required deliverables remain.
- **Planned** — agreed work that has not yet started.
- **Blocked** — progress is waiting on an unresolved dependency or decision.
- **Deferred** — intentionally outside the current critical path.

---

## Current phase

> **Current phase: P01 — Loihi-1 target definition and v2 project foundation**
>
> The source-backed architecture specification and repository reorganization are
> complete and have passed local regression verification. The remaining gate is
> final branch acceptance/merge. After that, development moves to **P02 — the
> separate Python manycore golden model**.

---

## Phase summary

| ID | Phase | Status | Started | Completed |
|---|---|---|---|---|
| P00 | Preserve and freeze FPGA-v1 baseline | Complete | 2026-09 | 2026-09-25 |
| P01 | Define Loihi-1 target and establish v2 project structure | In progress | 2026-09-28 | — |
| P02 | Build separate Python manycore golden model | Planned | — | — |
| P03 | Implement and validate one FPGA-v2 logical core | Planned | — | — |
| P04 | Add multicore packet routing and timestep/barrier semantics | Planned | — | — |
| P05 | Add logical-core virtualization | Planned | — | — |
| P06 | Build deterministic mapper/compiler and deployment format | Planned | — | — |
| P07 | Validate deeper mapped multicore SNNs | Planned | — | — |
| P08 | Build and compare NxTF-oriented deep MNIST workload | Planned | — | — |

---

# P00 — Preserve and freeze FPGA-v1 baseline

**Status:** Complete  
**Completed:** 2026-09-25

## Goal

Freeze the validated first-generation architecture and MNIST application before
beginning substantial Loihi-like architectural changes.

FPGA-v1 must remain a reproducible historical control rather than becoming an
implicitly modified foundation for FPGA-v2.

## Achieved deliverables

- Preserved the first MNIST application as `applications/mnist_baseline/`.
- Preserved the first architecture under `Loihi_Digital_Twin/v1/`.
- Archived the accepted historical FPGA artifacts.
- Rebuilt the HLS and Vivado hardware from a fresh source checkout.
- Re-ran rebuilt images on the physical K26.
- Confirmed preserved application behavior after the repository reorganization.
- Created the immutable source tag:

  ```text
  fpga-v1-mnist-v1-final
  ```

- Published/retained preservation bundles and checksum records separately from
  future v2 development.
- Retained the compatibility symlink:

  ```text
  Neuromorphic Digital Twin -> Loihi_Digital_Twin/v1
  ```

## Completion gate

Complete. FPGA-v1 behavior and accepted evidence are now historical controls.
Future changes must not silently alter the v1 implementation to simplify v2.

---

# P01 — Loihi-1 target definition and v2 project foundation

**Status:** In progress — **CURRENT PHASE**  
**Started:** 2026-09-28

## Goal

Define exactly what this thesis means by a Loihi-1 architectural digital twin
before implementing a new model or new FPGA datapath.

The output of this phase must separate:

- source-backed Loihi-1 behavior;
- derived architectural consequences;
- explicit FPGA implementation choices;
- deferred features; and
- behavior that is unknown or not claimed.

## Achieved deliverables

- Created the source-backed architecture contract:

  ```text
  Loihi_Digital_Twin/v2/docs/LOIHI1_TARGET_SPEC.md
  ```

- Added requirement-level citations to the primary/reference literature used to
  justify the target architecture.
- Defined the project as a **source-backed architectural digital twin**, not a
  transistor-level or timing-exact clone.
- Defined logical Loihi-like core/resource limits independently from physical
  FPGA resource instantiation.
- Defined destination-core / destination-axon packet semantics.
- Defined explicit axon-to-synapse expansion and outgoing fanout/routing.
- Defined algorithmic timestep/quiescence/barrier semantics separately from
  physical FPGA clock cycles.
- Defined virtualization as permissible only when normalized architectural
  behavior remains invariant.
- Defined transparent state/packet/resource tracing as a first-class
  requirement.
- Defined Priority-A, deferred, and non-claimed features.
- Defined the directed validation cases that the new model must eventually pass.
- Reorganized architecture development into:

  ```text
  Loihi_Digital_Twin/
  ├── v1/    preserved first-generation architecture
  └── v2/    independent Loihi-1 architectural twin
  ```

- Moved the historical M01-M13 tracker to:

  ```text
  Loihi_Digital_Twin/v1/MILESTONES.md
  ```

- Made this roadmap the active v2 development tracker at:

  ```text
  Loihi_Digital_Twin/v2/LOIHI_TWIN_ROADMAP.md
  ```

- Updated top-level documentation to point future development and agents to the
  versioned v1/v2 structure.
- Verified locally that the relocated v1 Python regression suite passes.
- Verified locally that the preserved MNIST regression suite passes.
- Reviewed and accepted the initial target-specification direction.

## Remaining deliverables

- [ ] Merge `agent/loihi1-target-spec` into `main` after final review.
- [ ] Treat the merged `LOIHI1_TARGET_SPEC.md` revision as the initial v2
      architecture contract for P02 implementation.

## Completion gate

P01 is complete when the specification/reorganization branch is merged and the
project can begin a new implementation branch without unresolved repository or
architecture-definition issues.

**Next phase:** P02 — separate Python manycore golden model.

---

# P02 — Separate Python manycore golden model

**Status:** Planned

## Goal

Create a new executable golden model for the Loihi-like manycore architecture
without extending the v1 `NeuromorphicCore` in place.

The model must embody the target specification directly and must not inherit
v1's single-core execution assumptions accidentally.

## Required deliverables

- [ ] Create an independent v2 Python package under `Loihi_Digital_Twin/v2/`.
- [ ] Define explicit logical-chip and logical-core resource objects.
- [ ] Define compartment/neuron state behind a versioned v2 interface.
- [ ] Reuse validated v1 neuron arithmetic only through an explicit compatibility
      boundary with dedicated tests.
- [ ] Define input-axon tables and axon-to-synapse expansion.
- [ ] Define synapse groups/lists and resource accounting.
- [ ] Define output routing/fanout entries.
- [ ] Define normalized spike-packet objects containing logical routing identity.
- [ ] Implement packet/event queues.
- [ ] Implement logical-core execution independent of global matrix operations.
- [ ] Implement timestep/quiescence/barrier coordination.
- [ ] Define normalized architectural traces containing, when applicable:

  ```text
  algorithmic timestep
  logical core
  architectural phase
  packets in / packets out
  axon expansion
  synaptic contributions
  compartment state before / after
  spikes
  local completion
  barrier state
  ```

- [ ] Add machine-readable resource/capacity reporting.
- [ ] Establish minimal deployment/mapping data structures needed to configure
      the golden model; full compiler work remains P06.

## Required directed tests

- [ ] v1-compatible single-neuron arithmetic.
- [ ] Two-core feed-forward packet delivery.
- [ ] Multicast fanout.
- [ ] Within-timestep packet-order invariance.
- [ ] Barrier drain/advance behavior.
- [ ] Cross-core recurrence.
- [ ] Hard resource-limit rejection.
- [ ] Connection-sharing/accounting behavior.
- [ ] Scheduler/service-order invariance at the normalized architectural trace.

## Completion gate

P02 is complete when the Python model can execute representative multicore
networks deterministically and all directed architectural tests pass without
requiring FPGA RTL/HLS.

No FPGA-v2 hardware implementation should begin before this gate closes.

**Next phase:** P03 — one FPGA-v2 logical core.

---

# P03 — One FPGA-v2 logical core

**Status:** Planned

## Goal

Implement one logical v2 neuromorphic core on the K26 against the target
specification and the P02 Python golden model.

## Required deliverables

- [ ] Define the FPGA-v2 one-core hardware boundary.
- [ ] Implement per-core compartment state.
- [ ] Implement input-axon lookup.
- [ ] Implement synapse traversal/accumulation.
- [ ] Implement output spike generation and routing-entry traversal.
- [ ] Implement the v2 configuration/state loading interface.
- [ ] Implement normalized trace/state inspection at the same semantic boundary
      as the Python model.
- [ ] Add resource/capacity guards for one logical core.
- [ ] Add differential Python-vs-HLS/RTL tests.
- [ ] Synthesize/implement on the K26 target.
- [ ] Perform physical directed conformance against the Python model.

## Verification discipline

```text
LOIHI1_TARGET_SPEC.md
        ↓
Python v2 golden model
        ↓
HLS/RTL one-core implementation
        ↓
directed differential tests
        ↓
physical K26 conformance
```

## Completion gate

P03 is complete when one hardware core reproduces the normalized golden-model
state/spike behavior for the one-core directed suite on the physical K26.

**Next phase:** P04 — multicore packet routing and barrier semantics.

---

# P04 — Multicore packet routing and timestep/barrier semantics

**Status:** Planned

## Goal

Extend FPGA-v2 from an isolated logical core to a true multicore architectural
model with explicit inter-core communication and deterministic algorithmic-time
completion semantics.

## Required deliverables

- [ ] Instantiate or schedule at least two logical cores.
- [ ] Implement destination-core / destination-axon packet delivery.
- [ ] Implement local versus remote routing behavior.
- [ ] Support simultaneous packet sources.
- [ ] Support fan-in and fanout across cores.
- [ ] Define and implement packet queue behavior required by the target spec.
- [ ] Implement quiescence/completion detection.
- [ ] Implement timestep/barrier advancement.
- [ ] Support cross-core recurrence without execution-order dependence.
- [ ] Expose packet, core, timestep, and barrier state in normalized traces.

## Required validation

- [ ] Two-core feed-forward network.
- [ ] Bidirectional/recurrent two-core network.
- [ ] Multiple simultaneous packet producers.
- [ ] Multicast to local and remote destinations.
- [ ] Different legal packet-service orders produce identical normalized results.
- [ ] A timestep cannot advance while current-timestep traffic remains pending.
- [ ] First divergence remains attributable to a logical core, packet, and
      algorithmic timestep.

## Completion gate

P04 is complete when multicore execution is deterministic at the normalized
architectural boundary and independent of incidental FPGA service ordering.

**Next phase:** P05 — logical-core virtualization.

---

# P05 — Logical-core virtualization

**Status:** Planned

## Goal

Support more logical Loihi-like cores than physically instantiated FPGA compute
engines while preserving the same visible architecture and logical limits.

## Required deliverables

- [ ] Separate logical-core state from physical execution-engine identity.
- [ ] Store independent compartment/axon/synapse/routing state per logical core.
- [ ] Add a deterministic scheduler for logical-core service.
- [ ] Preserve logical per-core resource limits even when memories are physically
      shared.
- [ ] Report both logical core count and physical engine count.
- [ ] Report physical FPGA memory/logic occupancy separately from logical Loihi
      resource occupancy.
- [ ] Maintain transparent mapping from logical core to physical service engine.

## Required validation

- [ ] Run the same network with different physical-engine counts.
- [ ] Run the same network with different legal logical-core service orders.
- [ ] Confirm identical normalized logical state/spike/packet traces.
- [ ] Confirm that logical capacity errors are not bypassed by physical sharing.

## Completion gate

P05 is complete when **virtualization invariance** is demonstrated: changing the
number or service order of physical engines does not change logical results.

**Next phase:** P06 — deterministic mapper/compiler.

---

# P06 — Deterministic mapper/compiler and deployment format

**Status:** Planned

## Goal

Create the software layer that maps trained networks onto the modeled Loihi-like
resources and emits one deterministic deployment consumed by both Python and
FPGA execution.

## Required deliverables

- [ ] Define the machine-readable v2 deployment schema.
- [ ] Partition neuron/compartment populations across logical cores.
- [ ] Allocate input axons.
- [ ] Allocate synapse groups/lists.
- [ ] Allocate output routing entries.
- [ ] Implement supported connection sharing/compression or the explicit
      project-defined equivalent.
- [ ] Enforce hard per-core limits during mapping.
- [ ] Reject invalid mappings with explicit diagnostics.
- [ ] Make mapping deterministic for a fixed network/configuration.
- [ ] Report per-core capacity use and remaining headroom.
- [ ] Estimate/report expected packet traffic where meaningful.
- [ ] Hash/version deployment artifacts.
- [ ] Load the same deployment artifact into both Python and FPGA paths.

## Required validation

- [ ] Repeated mapping of the same model produces the same deployment.
- [ ] Boundary cases correctly fill/reject compartment, axon, synapse, and route
      resources.
- [ ] Mapped small networks reproduce hand-constructed expected placements.
- [ ] Python and FPGA consume the same configuration semantics.

## Completion gate

P06 is complete when networks can be mapped deterministically into inspectable,
resource-valid deployments without hand-editing FPGA-specific configuration.

**Next phase:** P07 — deeper mapped SNN validation.

---

# P07 — Deeper mapped multicore SNN validation

**Status:** Planned

## Goal

Demonstrate that FPGA-v2 supports networks that genuinely exercise multicore
mapping, routing, sharing, and capacity constraints before using MNIST as the
final comparison workload.

## Required deliverables

- [ ] Select/build a deeper feed-forward SNN with multiple mapped layers.
- [ ] Map the network through the P06 compiler rather than manual placement.
- [ ] Exercise multiple logical cores.
- [ ] Exercise inter-core packet traffic.
- [ ] Exercise supported connection sharing/resource optimization.
- [ ] Compare Python and FPGA normalized traces on representative cases.
- [ ] Validate physical K26 execution.
- [ ] Record logical resource occupancy and physical FPGA utilization.
- [ ] Record mapping/capacity failures for intentionally oversized networks.

## Completion gate

P07 is complete when a nontrivial deeper SNN executes reproducibly through the
full specification → mapper → Python → FPGA flow and agrees at the normalized
architectural boundary.

**Next phase:** P08 — NxTF-oriented deep MNIST comparison.

---

# P08 — NxTF-oriented deep MNIST comparison

**Status:** Planned

## Goal

Build a substantially deeper MNIST workload that exercises the new multicore
architecture and supports a defensible comparison with Rueckauer et al. NxTF.

The preserved `784 -> 10` FPGA-v1 baseline remains useful historical context,
but it is not sufficient as the final FPGA-v2 application because it does not
exercise the manycore mapping problem.

## Required deliverables

- [ ] Select a deeper MNIST topology comparable in purpose and mapping pressure
      to the NxTF workload.
- [ ] Freeze the data/preprocessing contract.
- [ ] Freeze the training/conversion procedure.
- [ ] Freeze the neuron and weight-representation contract.
- [ ] Freeze the number of algorithmic presentation timesteps.
- [ ] Map the network with the P06 compiler.
- [ ] Record logical placement/core count.
- [ ] Record compartment/axon/synapse/routing occupancy.
- [ ] Record sharing/compression effectiveness.
- [ ] Record packet traffic.
- [ ] Validate Python-vs-FPGA inference behavior.
- [ ] Run the physical K26 workload.
- [ ] Measure/report accuracy.
- [ ] Measure/report physical architectural cycles and latency with a clearly
      stated boundary.
- [ ] Record FPGA LUT/register/BRAM/URAM/DSP utilization.
- [ ] Record mapping failures/headroom where relevant.
- [ ] Build an explicit NxTF comparison table that distinguishes directly
      comparable quantities from contextual/non-comparable quantities.

## Comparison contract

Before final results, explicitly freeze:

- dataset and preprocessing;
- topology;
- training/conversion procedure;
- neuron model;
- algorithmic presentation timesteps;
- weight representation;
- logical placement/core count;
- sharing/compression model;
- decoder and accuracy metric;
- latency boundary; and
- quantities that cannot be matched to the paper.

Energy claims remain out of scope unless a defensible workload-specific physical
measurement method is established.

## Completion gate

P08 is complete when the deep MNIST workload has been mapped, executed on the
K26, quantitatively characterized, and compared to NxTF using an explicitly
bounded comparison contract.

This is the primary end-state of the current v2 thesis roadmap.

---

# Cross-phase architectural requirements

These requirements apply throughout P02-P08. They are summarized here for
planning; the normative definitions and source citations live in
`docs/LOIHI1_TARGET_SPEC.md`.

## Priority-A requirements

The first complete v2 architecture must support:

- multiple logical neuromorphic cores;
- explicit per-core compartment, input-axon, synapse, and output-routing
  resources;
- Loihi-like hard capacity accounting;
- destination-core / destination-axon spike packets;
- explicit inter-core fanout and packet routing;
- deterministic placement and mapping;
- algorithmic timestep/quiescence barriers independent of FPGA clock cycles;
- convolution-oriented axon/synapse sharing or a clearly modeled equivalent;
- transparent configuration, state, packet, spike, and resource traces;
- deeper feed-forward SNN graphs; and
- one deterministic mapping/compiler layer used by both Python and FPGA.

## Digital-twin boundary

The project targets a **source-backed architectural digital twin**, not a
transistor-level clone.

Logical resources may be virtualized or time-multiplexed on the K26 only when:

- virtualization is explicit;
- architectural state remains inspectable;
- logical resource limits are enforced;
- packet/timestep ordering rules remain deterministic and documented;
- physical FPGA cycles are distinguished from algorithmic timesteps; and
- Python and FPGA implementations compare at the same normalized boundary.

Physical asynchronous-circuit equivalence is not required. FPGA-v2 is a
synchronous FPGA realization of source-backed event-driven architectural
semantics.

---

# Cross-phase verification policy

Every architectural addition should be validated at three levels whenever the
relevant implementation layer exists:

1. **Directed unit behavior** — minimal tests isolate one semantic rule.
2. **Mapped-network differential behavior** — Python and FPGA normalized traces
   agree across representative multicore networks.
3. **Physical application behavior** — a K26 deployment reproduces the golden
   workload result.

The normalized v2 trace boundary should expose, when practical:

```text
algorithmic timestep
logical core
architectural phase
packets in / packets out
axon expansion
synaptic contributions
compartment state before / after
spikes
local completion
barrier state
physical FPGA cycle
```

External emulators such as Brian2Loihi remain supporting references only where
their modeled boundary is actually comparable.

---

# Deferred fidelity extensions

The following features are valuable but are not currently required to complete
P08 unless the target specification or application work shows that they become
necessary.

## Priority B — later architectural fidelity

- richer dendritic/multi-compartment structures;
- programmable synaptic delays;
- broader native weight/compression formats;
- more detailed event scheduling/queue/congestion behavior when source-backed;
- richer configuration/state behavior; and
- more detailed asynchronous/quiescence modeling at the architectural level.

## Priority C — non-critical-path fidelity

- on-chip plasticity/learning engines;
- management-processor emulation;
- chip-to-chip routing;
- exact physical asynchronous circuit behavior; and
- undocumented implementation details that cannot be supported by public
  evidence.

A feature with insufficient public evidence must remain **unknown/not claimed**
rather than being filled in from assumption.

---

# Documentation and evidence structure

```text
Loihi_Digital_Twin/
├── v1/
│   ├── MILESTONES.md              historical M01-M13 development record
│   └── ...                        preserved implementation/evidence
│
└── v2/
    ├── LOIHI_TWIN_ROADMAP.md      active phase/status tracker
    ├── docs/
    │   └── LOIHI1_TARGET_SPEC.md  normative architecture contract
    └── ...                        new model/HLS/RTL/evidence as phases advance

applications/
├── mnist_baseline/                preserved FPGA-v1 application
└── <future deep MNIST app>/       FPGA-v2 / NxTF-oriented workload
```

New FPGA-v2 implementation evidence should live with v2 and should be referenced
from the corresponding roadmap phase. It should not be appended to the preserved
v1 milestone history.

`EXPERIMENTS.md` remains a repository-level collection of deferred/follow-on
studies and is not the active implementation tracker while this roadmap is in
progress.

---

# Advancement rule

Only one phase should normally be marked **In progress** at a time.

Before moving to the next phase:

1. mark completed deliverables in the active phase;
2. record the validation evidence needed by that phase;
3. verify its completion gate;
4. change that phase to **Complete** with its completion date; and
5. change the next phase from **Planned** to **In progress** with its start date.

This keeps the v2 architecture driven by an explicit source-backed contract and
makes project status recoverable directly from this file without reconstructing
intent from commit history or conversation context.
