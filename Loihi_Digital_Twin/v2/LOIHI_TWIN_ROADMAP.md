# Loihi Twin Endgame Roadmap

## Purpose

This document defines the active post-validation direction of the thesis.

The FPGA-v1 architecture and first MNIST workload are now preserved historical
baselines. The active objective is a substantially more complete, transparent
Loihi-1 architectural digital twin and a deeper MNIST workload suitable for a
defensible comparison with Rueckauer et al. NxTF.

The progression is:

```text
preserved FPGA-v1 + first MNIST application
        ↓
source-backed Loihi-1 target specification
        ↓
separate Python FPGA-v2 manycore golden model
        ↓
one-core then multicore FPGA-v2 implementation
        ↓
logical-core virtualization + mapper/compiler
        ↓
deep mapped SNN validation
        ↓
NxTF-oriented deep MNIST comparison
```

The proposed studies in `EXPERIMENTS.md` remain useful follow-on work but are
deferred while this architecture/application path is active.

---

## 1. Preserved FPGA-v1 baseline

The first architecture and MNIST application are completed reference results.
Their preservation phase established both archived-artifact reproducibility and
fresh-source rebuild reproducibility, including physical K26 validation.

The immutable pre-v2 source point is tagged:

```text
fpga-v1-mnist-v1-final
```

The repository now separates the generations:

```text
Loihi_Digital_Twin/
├── v1/    preserved FPGA-v1 source, tests, docs, HLS, and RTL
└── v2/    independent Loihi-1 architectural-twin development

applications/
└── mnist_baseline/    preserved first MNIST application/evidence
```

A compatibility symlink named `Neuromorphic Digital Twin` points to
`Loihi_Digital_Twin/v1` so historical commands can continue to resolve. New
work should use the canonical versioned paths.

### Baseline immutability rule

FPGA-v1 behavior and its accepted evidence must not be silently changed to make
FPGA-v2 easier to implement. Reuse is allowed only through explicit,
versioned interfaces with tests. FPGA-v1 remains the historical control.

---

## 2. Definition of the Loihi digital twin

The project targets a **source-backed architectural digital twin**, not a
transistor-level clone.

The working definition is:

> A transparent FPGA implementation exposing the documented logical resources,
> state transitions, routing behavior, algorithmic-time semantics, and mapping
> constraints needed to reproduce a defensible subset of Loihi-1 behavior at
> neuron, core, and manycore levels.

Logical resources may be virtualized or time-multiplexed on the K26 provided
that:

- virtualization is explicit;
- architectural state remains inspectable;
- logical resource limits are enforced;
- packet/timestep ordering rules remain deterministic and documented;
- physical FPGA cycles are distinguished from algorithmic timesteps; and
- Python and FPGA implementations compare at the same normalized boundary.

Physical asynchronous-circuit equivalence is not required. The target is a
synchronous FPGA realization of source-backed event-driven architectural
semantics.

---

## 3. Normative architecture authority

The architecture-definition gate is now represented by:

```text
Loihi_Digital_Twin/v2/docs/LOIHI1_TARGET_SPEC.md
```

That document is the normative authority for FPGA-v2. It records primary
sources and requirement-level citations, distinguishes source-backed behavior
from project implementation choices, defines explicit non-claims, and specifies
the validation tests required before large-network development.

The evidence hierarchy is centered on:

- Davies et al., *Loihi: A Neuromorphic Manycore Processor with On-Chip
  Learning*, IEEE Micro, 2018;
- Lines et al., *Loihi Asynchronous Neuromorphic Research Chip*, ASYNC, 2018;
- Davies et al., *Advancing Neuromorphic Computing With Loihi*, Proceedings of
  the IEEE, 2021;
- Rueckauer et al., *NxTF*, ACM JETC, 2022;
- Michaelis et al., *Brian2Loihi*, Frontiers in Neuroinformatics, 2022; and
- the completed project M13 audit for the FPGA-v1 behavior/scope boundary.

A feature with insufficient public evidence must be marked unknown/not claimed
rather than filled in from assumption.

---

## 4. FPGA-v2 Priority-A architecture

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
- a deterministic mapping/compiler layer producing the configuration consumed
  by both Python and FPGA execution.

The target specification currently treats richer dendritic structures,
programmable delays, broader weight/compression formats, and more detailed
traffic behavior as later fidelity extensions. Learning engines, management
processor emulation, multi-chip routing, and exact asynchronous circuit timing
may remain deferred for the first deep-MNIST comparison.

---

## 5. FPGA-v2 architecture program

### Stage A — separate Python manycore golden model

Create a new v2 package rather than extending the v1 `NeuromorphicCore` in
place. The initial model should represent:

```text
logical chip
├── logical cores
│   ├── compartment state
│   ├── input axon table
│   ├── synapse lists/groups
│   ├── output routing table
│   └── local completion state
├── packet router / event queues
├── timestep-barrier coordinator
├── resource accounting
├── mapper/deployment representation
└── normalized trace plane
```

Reuse the already validated v1 neuron arithmetic only through an explicit
versioned compatibility boundary. The first v2 model must not acquire v1's
single-core execution assumptions accidentally.

Required early directed tests include:

- v1-compatible single-neuron arithmetic;
- two-core feed-forward packet delivery;
- multicast fanout;
- within-timestep packet-order invariance;
- barrier drain/advance behavior;
- cross-core recurrence;
- hard resource-limit rejection;
- connection-sharing/accounting behavior; and
- invariance to different physical/logical scheduling orders.

### Stage B — one FPGA-v2 core

Implement one logical v2 core against the target specification and the new
Python model. Preserve the existing verification discipline:

```text
target specification
        ↓
Python golden model
        ↓
HLS/RTL implementation
        ↓
directed differential tests
        ↓
physical K26 conformance
```

### Stage C — multicore packet routing

Add at least two logical cores and validate local/remote traffic, simultaneous
sources, fan-in/fanout, queue behavior, recurrence, and barrier semantics. The
first divergence must remain traceable to a logical core, packet, and
algorithmic timestep.

### Stage D — logical-core virtualization

Allow more logical cores than physical compute engines. Logical per-core
capacity must remain enforced even when memories and compute engines are shared
physically. Report both logical core count and physical engine/resource count.

A central validation requirement is **virtualization invariance**: changing the
number or service order of physical engines must not change normalized logical
state/spike/packet traces.

### Stage E — mapping/compiler layer

Map trained networks into deterministic v2 deployment artifacts. At minimum the
mapper shall:

- partition populations/compartments across logical cores;
- allocate input axons, synaptic groups, and output routes;
- exploit supported sharing;
- enforce hard resource limits;
- expose capacity headroom and traffic estimates;
- reject invalid mappings explicitly; and
- emit one machine-readable deployment consumed by both Python and FPGA.

---

## 6. Verification strategy

Every architectural addition should be validated at three levels:

1. **Directed unit behavior** — minimal tests isolate one semantic rule.
2. **Mapped-network differential behavior** — Python and FPGA normalized traces
   agree across representative multicore networks.
3. **Physical application behavior** — a K26 deployment reproduces the golden
   workload result.

The v2 trace boundary should expose, when practical:

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

## 7. Deep MNIST / NxTF target

The final application must be substantially deeper than the preserved
single-layer `784 -> 10` baseline and must exercise multicore mapping and
resource constraints.

Rueckauer et al. NxTF is the primary comparison target because it explicitly
studies mapping deep convolutional SNNs onto Loihi's constrained multicore
resources and exploits axon/synapse sharing.

Before final results, freeze a comparison contract covering:

- data/preprocessing;
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

Candidate final measurements include accuracy, logical cores, compartment/axon/
synapse occupancy, sharing effectiveness, packet traffic, FPGA resources,
physical architectural cycles/latency, and mapping/capacity failures.

Energy claims remain out of scope unless a defensible workload-specific
physical measurement method is established.

---

## 8. Documentation structure

- `MILESTONES.md` — historical FPGA-v1 development record;
- `applications/mnist_baseline/` — preserved first application;
- `Loihi_Digital_Twin/v1/` — preserved architecture implementation;
- `Loihi_Digital_Twin/v2/docs/LOIHI1_TARGET_SPEC.md` — normative v2 contract;
- `Loihi_Digital_Twin/v2/` — new golden model and later FPGA-v2 implementation;
- future deep-MNIST application directory — NxTF-oriented workload;
- `LOIHI_TWIN_ROADMAP.md` — high-level active program; and
- `EXPERIMENTS.md` — deferred follow-on studies.

New v2 implementation evidence should live with v2 rather than being appended
to the preserved v1 milestone history.

---

## 9. Immediate next gate

The current gate is **review and local verification of the target specification
and repository reorganization**.

Once the branch is accepted:

1. freeze `LOIHI1_TARGET_SPEC.md` as the initial v2 contract;
2. create the separate `loihi_twin_v2` Python package and tests;
3. implement resource, packet, core, router, and barrier abstractions;
4. pass the directed architecture tests before any v2 HLS/RTL work; and
5. only then begin the one-core FPGA-v2 implementation.

This sequence keeps the new hardware driven by a source-backed executable
contract rather than allowing RTL choices to define the architecture after the
fact.
