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

> **Current phase: P02 — Separate Python manycore golden model**
>
> P01 is complete and merged. The independent v2 Python package, logical
> resource model, packet/core/router/barrier architecture, deterministic
> deployment representation, machine-readable reporting, and software-side
> T1-T9 directed tests are now implemented on `agent/v2-python-manycore`.
> The immediate remaining gate is local regression/behavior verification before
> P02 can be closed.

---

## Phase summary

| ID | Phase | Status | Started | Completed |
|---|---|---|---|---|
| P00 | Preserve and freeze FPGA-v1 baseline | Complete | 2026-09 | 2026-09-25 |
| P01 | Define Loihi-1 target and establish v2 project structure | Complete | 2026-09-28 | 2026-09-28 |
| P02 | Build separate Python manycore golden model | In progress | 2026-09-28 | — |
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

## Achieved deliverables

- Preserved the first MNIST application as `applications/mnist_baseline/`.
- Preserved the first architecture under `Loihi_Digital_Twin/v1/`.
- Archived accepted historical FPGA artifacts.
- Rebuilt HLS/Vivado hardware from a fresh checkout.
- Re-ran rebuilt images on the physical K26.
- Confirmed preserved application behavior after repository reorganization.
- Created the immutable source tag `fpga-v1-mnist-v1-final`.
- Retained the compatibility symlink `Neuromorphic Digital Twin -> Loihi_Digital_Twin/v1`.

## Completion gate

Complete. FPGA-v1 behavior and accepted evidence are historical controls.

---

# P01 — Loihi-1 target definition and v2 project foundation

**Status:** Complete  
**Started:** 2026-09-28  
**Completed:** 2026-09-28

## Goal

Define exactly what this thesis means by a Loihi-1 architectural digital twin
before implementing a new model or new FPGA datapath.

## Achieved deliverables

- Created `Loihi_Digital_Twin/v2/docs/LOIHI1_TARGET_SPEC.md`.
- Added requirement-level citations to primary/reference literature.
- Defined the project as a source-backed architectural digital twin, not a
  transistor-level or timing-exact clone.
- Defined logical Loihi-like resource limits independently from physical FPGA
  instantiation.
- Defined destination-core / destination-axon packet semantics.
- Defined axon-to-synapse expansion and explicit source fanout.
- Defined algorithmic timestep/quiescence/barrier semantics separately from
  physical FPGA clock cycles.
- Defined virtualization invariance and normalized trace requirements.
- Defined Priority-A, deferred, and non-claimed features.
- Defined directed validation tests T1-T10.
- Reorganized the architecture as `Loihi_Digital_Twin/v1/` and `v2/`.
- Moved historical M01-M13 tracking to `Loihi_Digital_Twin/v1/MILESTONES.md`.
- Made this file the active v2 roadmap.
- Verified the relocated v1 and preserved MNIST regression suites locally.
- Merged the accepted P01 branch into `main`.

## Completion gate

Complete. The initial target specification is the architecture authority for
P02 implementation.

---

# P02 — Separate Python manycore golden model

**Status:** In progress — **CURRENT PHASE**  
**Started:** 2026-09-28

## Goal

Create a new executable golden model for the Loihi-like manycore architecture
without extending the v1 `NeuromorphicCore` in place.

The model must embody the target specification directly and must not inherit
v1's single-core execution assumptions accidentally.

## Achieved implementation deliverables

- [x] Created an independent v2 Python package under `Loihi_Digital_Twin/v2/`.
- [x] Defined Loihi-1 logical chip/core resource constants and hard limits.
- [x] Added explicit per-core resource accounting and named capacity failures.
- [x] Defined a versioned project synapse-storage cost model behind an isolated
      interface rather than claiming native Loihi SRAM packing.
- [x] Defined a v2 compartment/neuron state interface.
- [x] Re-versioned the validated v1 neuron arithmetic into v2 without a runtime
      dependency on the v1 package.
- [x] Added dedicated compatibility tests against the frozen v1 neuron step.
- [x] Defined destination-side input-axon bindings.
- [x] Defined reusable synapse templates and explicit expanded-connection counts.
- [x] Defined source-side output routing/fanout entries.
- [x] Defined normalized spike packets containing target timestep, destination
      logical core, destination axon, and optional source metadata.
- [x] Implemented explicit packet queues and traffic accounting.
- [x] Implemented logical-core ingress, axon expansion, accumulation,
      compartment update, spike decision, egress, and completion behavior.
- [x] Implemented a centralized logical drain/advance barrier.
- [x] Implemented chip-level logical-core scheduling independent of packet
      delivery order.
- [x] Defined normalized core/chip traces containing packet, axon-expansion,
      synaptic-contribution, state, spike, and barrier information.
- [x] Added deterministic deployment fingerprints and minimal deployment data
      structures sufficient to configure the golden model.
- [x] Added JSON-serializable deployment/capacity reports with per-core headroom.
- [x] Added JSON-serializable architecture trace reports.
- [x] Added a runnable two-core feed-forward example.
- [x] Added `docs/P02_IMPLEMENTATION_NOTES.md` documenting project choices and
      claim boundaries.

## Directed tests implemented

- [x] **T1** — v1-compatible single-neuron/compartment arithmetic.
- [x] **T2** — two-core feed-forward packet delivery.
- [x] **T3** — multicast fanout.
- [x] **T4** — within-timestep packet-order invariance.
- [x] **T5** — barrier drain/advance behavior.
- [x] **T6** — cross-core recurrence.
- [x] **T7** — hard rejection of compartment, input-axon, output-route, and
      synapse-memory capacity overflow.
- [x] **T8** — connection-sharing/resource-accounting behavior.
- [x] **T9** — logical service-order / packet-drain-order invariance at the
      normalized architecture boundary.
- [ ] **T10** — Python/FPGA normalized trace comparison. This belongs to the
      later hardware phases and is not required to close the software-only P02
      gate.

## Verification still required before P02 completion

- [ ] Install the independent v2 package in a clean/current project environment.
- [ ] Run the complete P02 Python test suite locally with zero failures.
- [ ] Run the two-core example and inspect its deployment/resource and trace
      output for the expected one-boundary feed-forward causality.
- [ ] Re-run the preserved v1 and MNIST regressions if the local environment or
      editable installations were changed in a way that could affect them.
- [ ] Resolve any defects exposed by local execution without weakening the
      target specification.

## Completion gate

P02 is complete when the Python model executes representative multicore
networks deterministically and all software-side directed architectural tests
(T1-T9) pass without requiring FPGA RTL/HLS.

No FPGA-v2 hardware implementation begins before this gate closes.

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
- [ ] Implement quiescence/completion detection and timestep advancement.
- [ ] Support cross-core recurrence without execution-order dependence.
- [ ] Expose packet/core/timestep/barrier state in normalized traces.

## Required validation

- [ ] Two-core feed-forward network.
- [ ] Bidirectional/recurrent two-core network.
- [ ] Multiple simultaneous packet producers.
- [ ] Multicast to local and remote destinations.
- [ ] Different legal packet-service orders produce identical normalized results.
- [ ] A timestep cannot advance while current-timestep traffic remains pending.

## Completion gate

P04 is complete when multicore hardware execution is deterministic at the
normalized architectural boundary and independent of incidental FPGA service
ordering.

**Next phase:** P05 — logical-core virtualization.

---

# P05 — Logical-core virtualization

**Status:** Planned

## Goal

Support more logical Loihi-like cores than physically instantiated FPGA compute
engines while preserving visible architecture and logical limits.

## Required deliverables

- [ ] Separate logical-core state from physical execution-engine identity.
- [ ] Store independent compartment/axon/synapse/routing state per logical core.
- [ ] Add a deterministic scheduler for logical-core service.
- [ ] Preserve logical per-core resource limits when memories are physically shared.
- [ ] Report both logical core count and physical engine count.
- [ ] Report physical FPGA occupancy separately from logical Loihi occupancy.
- [ ] Maintain transparent logical-core-to-engine mapping.

## Required validation

- [ ] Run the same network with different physical-engine counts.
- [ ] Run the same network with different legal logical-core service orders.
- [ ] Confirm identical normalized logical state/spike/packet traces.
- [ ] Confirm logical capacity errors cannot be bypassed by physical sharing.

## Completion gate

P05 is complete when **virtualization invariance** is demonstrated.

**Next phase:** P06 — deterministic mapper/compiler.

---

# P06 — Deterministic mapper/compiler and deployment format

**Status:** Planned

## Goal

Map trained networks onto modeled Loihi-like resources and emit one
deterministic deployment consumed by both Python and FPGA execution.

## Required deliverables

- [ ] Finalize the machine-readable deployment schema.
- [ ] Partition populations/compartments across logical cores.
- [ ] Allocate input axons, synapse groups/lists, and output routes.
- [ ] Implement supported connection sharing/compression or the explicit
      project-defined equivalent.
- [ ] Enforce hard per-core limits during mapping.
- [ ] Reject invalid mappings with explicit diagnostics.
- [ ] Make mapping deterministic for a fixed network/configuration.
- [ ] Report per-core use/headroom and expected traffic where meaningful.
- [ ] Hash/version deployment artifacts.
- [ ] Load the same deployment artifact into Python and FPGA paths.

## Completion gate

P06 is complete when networks can be mapped deterministically into inspectable,
resource-valid deployments without hand-editing FPGA-specific configuration.

**Next phase:** P07 — deeper mapped SNN validation.

---

# P07 — Deeper mapped multicore SNN validation

**Status:** Planned

## Goal

Demonstrate that FPGA-v2 supports networks that genuinely exercise multicore
mapping, routing, sharing, and capacity constraints before final MNIST work.

## Required deliverables

- [ ] Select/build a deeper feed-forward SNN with multiple mapped layers.
- [ ] Map through the P06 compiler rather than manual placement.
- [ ] Exercise multiple logical cores and inter-core traffic.
- [ ] Exercise supported connection sharing/resource optimization.
- [ ] Compare Python and FPGA normalized traces on representative cases.
- [ ] Validate physical K26 execution.
- [ ] Record logical occupancy, physical FPGA utilization, and capacity failures.

## Completion gate

P07 is complete when a nontrivial deeper SNN executes reproducibly through the
specification → mapper → Python → FPGA flow and agrees at the normalized
architectural boundary.

**Next phase:** P08 — NxTF-oriented deep MNIST comparison.

---

# P08 — NxTF-oriented deep MNIST comparison

**Status:** Planned

## Goal

Build a substantially deeper MNIST workload that exercises the new multicore
architecture and supports a defensible comparison with Rueckauer et al. NxTF.

## Required deliverables

- [ ] Select a deeper MNIST topology comparable in purpose/mapping pressure to
      the NxTF workload.
- [ ] Freeze data/preprocessing, training/conversion, neuron, weight, timestep,
      and decoder contracts.
- [ ] Map the network with the P06 compiler.
- [ ] Record logical placement/core count and per-resource occupancy.
- [ ] Record sharing/compression effectiveness and packet traffic.
- [ ] Validate Python-vs-FPGA inference behavior.
- [ ] Run the physical K26 workload.
- [ ] Measure/report accuracy, architectural cycles/latency, and FPGA resources.
- [ ] Record mapping failures/headroom where relevant.
- [ ] Build an explicit NxTF comparison table separating comparable from
      contextual/non-comparable quantities.

Energy claims remain out of scope unless a defensible workload-specific physical
measurement method is established.

## Completion gate

P08 is complete when the deep MNIST workload has been mapped, executed on the
K26, quantitatively characterized, and compared to NxTF under an explicitly
bounded comparison contract.

---

# Cross-phase architectural requirements

These requirements apply throughout P02-P08. Normative definitions and source
citations live in `docs/LOIHI1_TARGET_SPEC.md`.

## Priority-A requirements

The first complete v2 architecture must support:

- multiple logical neuromorphic cores;
- explicit per-core compartment, input-axon, synapse, and output-routing resources;
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

---

# Deferred fidelity extensions

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
- undocumented implementation details unsupported by public evidence.

A feature with insufficient public evidence remains **unknown/not claimed**.

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
    │   ├── LOIHI1_TARGET_SPEC.md  normative architecture contract
    │   └── P02_IMPLEMENTATION_NOTES.md
    ├── src/loihi_twin_v2/         separate Python golden model
    ├── tests/                      directed architecture tests
    └── examples/                   minimal runnable architecture examples

applications/
├── mnist_baseline/                preserved FPGA-v1 application
└── <future deep MNIST app>/       FPGA-v2 / NxTF-oriented workload
```

New FPGA-v2 implementation evidence belongs with v2 and should be referenced
from the corresponding roadmap phase. It must not be appended to preserved v1
milestone history.

`EXPERIMENTS.md` remains a repository-level collection of deferred/follow-on
studies and is not the active implementation tracker while this roadmap is in
progress.

---

# Advancement rule

Only one phase should normally be marked **In progress** at a time.

Before moving to the next phase:

1. mark completed deliverables in the active phase;
2. record validation evidence needed by that phase;
3. verify its completion gate;
4. change that phase to **Complete** with its completion date; and
5. change the next phase from **Planned** to **In progress** with its start date.

This keeps v2 driven by an explicit source-backed contract and makes project
status recoverable directly from this file without reconstructing intent from
commit history or conversation context.
