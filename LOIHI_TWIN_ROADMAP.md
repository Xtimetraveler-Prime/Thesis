# Loihi Twin Endgame Roadmap

## Purpose

This document defines the active post-validation direction of the thesis.

The validated FPGA-v1 platform, M12 physical evidence, M13 cross-implementation
audit, and first MNIST application are now treated as a stable baseline. The
next objective is not to replace that baseline with a collection of unrelated
counterfactual experiments. The objective is to extend the project into a
substantially more complete, transparent Loihi-1 architectural digital twin and
then use a deeper MNIST workload as the final application-level comparison.

The intended progression is:

```text
preserve FPGA-v1 + first MNIST application
        ↓
freeze a source-backed Loihi-1 target architecture
        ↓
build and validate a new FPGA-v2 / manycore twin
        ↓
scale the architecture to deeper mapped SNNs
        ↓
run a deep MNIST workload through the new twin
        ↓
compare against the Rueckauer et al. NxTF Loihi result
```

The proposed experiments in `EXPERIMENTS.md` remain valid follow-on research,
but they are deferred while this endgame path is active.

---

## 1. Preserve the FPGA-v1 / first-MNIST baseline

The first MNIST application is a completed reference experiment, not a disposable
prototype. It must remain reproducible before any directory rename or
architecture-v2 development begins.

### Preservation objectives

Preserve both forms of reproducibility:

1. **Immediate rerun:** an archived, previously verified K26 bitstream/debug
   artifact can be programmed again and used to classify a frozen MNIST input.
2. **Source rebuild:** a clean checkout can regenerate the required HLS IP,
   Vivado project, bitstream, and runtime artifacts using the pinned toolchain.

The current source-controlled `applications/mnist/frozen/mnist-v1/` package
already preserves the accepted checkpoints, deployment images, encoded weight
memories, frozen application contract, hashes, and conformance corpus. The
remaining preservation work is primarily around generated FPGA artifacts,
environment pinning, and one final physical reproduction.

### Preservation actions

Before renaming `applications/mnist/`:

- freeze the current repository identity with a final FPGA-v1/MNIST-v1 tag;
- verify the committed `mnist-v1` package from a clean checkout;
- preserve exact Python/package versions used by the accepted reproduction;
- preserve Vitis/Vivado 2025.2, K26 part, board, and host-environment details;
- archive the accepted MNIST runtime/characterization hardware artifacts,
  including the reusable `.bit` and `.ltx` files and the final
  characterization `.xsa`, routed checkpoint, and implementation reports;
- record SHA-256 hashes for archived binary artifacts;
- physically program the archived runtime image and reproduce at least one
  classification from each frozen profile;
- independently confirm that the same hardware image can still be rebuilt from
  source; and
- create one concise reproduction record containing the exact commands, hashes,
  expected outputs, and artifact location.

The preferred eventual directory name is `applications/mnist_baseline/` or
`applications/mnist_v1/`, because this workload is a completed reference
implementation rather than a temporary test. The rename should use Git history
preserving moves and occur only after the preservation audit closes.

### Baseline immutability rule

The validated FPGA-v1 core, frozen MNIST-v1 deployment, and accepted evidence
must not be silently modified to support the new architecture. Any new core,
routing model, compiler/mapping layer, or application deployment should be
versioned separately. FPGA-v1 remains the historical control.

---

## 2. Define what “Loihi digital twin” means

The project should target a **source-backed architectural digital twin**, not an
unverifiable transistor-level clone.

The working definition is:

> A transparent FPGA implementation that exposes the documented logical
> resources, state transitions, routing behavior, timing/execution semantics,
> and mapping constraints needed to reproduce a defensible subset of Loihi-1
> behavior at neuron, core, and manycore levels.

A literal spatial copy of all Loihi-1 hardware resources is not required if the
K26 cannot support it. Logical resources may be time-multiplexed or virtualized
provided that:

- the virtualization is explicit;
- architectural state remains inspectable;
- timing and ordering rules remain deterministic and documented;
- the logical resource limits are modeled rather than silently ignored; and
- Python-golden and FPGA implementations can be compared at the same logical
  boundary.

This distinction is important. Loihi-1 itself is a manycore architecture whose
neuron updates are time-multiplexed within cores, while communication between
cores is packetized and asynchronous. FPGA resource reuse is therefore
acceptable if it preserves the intended architectural behavior instead of
collapsing the architecture back into a generic dense accelerator.

---

## 3. Evidence base for the target architecture

The architecture definition phase must precede FPGA-v2 implementation.

Primary literature anchors should include at least:

- Mike Davies et al., “Loihi: A Neuromorphic Manycore Processor with On-Chip
  Learning,” *IEEE Micro*, 2018. DOI: `10.1109/MM.2018.112130359`.
- Andrew Lines et al., “Loihi Asynchronous Neuromorphic Research Chip,”
  *ASYNC*, 2018. DOI: `10.1109/ASYNC.2018.00018`.
- Bodo Rueckauer et al., “NxTF: An API and Compiler for Deep Spiking Neural
  Networks on Intel Loihi,” *ACM Journal on Emerging Technologies in Computing
  Systems*, 2022. DOI: `10.1145/3501770`.
- the existing M13 source manifest, architectural feature crosswalk,
  normalization specification, and final audit summary.

The M13 audit already identifies eight explicit FPGA-v1 scope limits:

```text
dendritic compartments
programmable synaptic delays beyond the baseline recurrent rule
native Loihi/Catalyst synapse-memory layout equivalence
inter-core routing / packet NoC
online learning / plasticity
Loihi-like embedded management processors
multicore scaling
asynchronous / quiescence execution
```

These are the starting architecture-gap list, not an automatic requirement that
all eight be implemented before the next useful result.

### Architecture-definition deliverable

Create a source-backed **Loihi-1 Twin Target Specification** before RTL/HLS
changes begin. For every candidate feature it should record:

- published evidence and confidence;
- exact behavior/resource limit that can be defended;
- whether the feature is required for the final deep-MNIST comparison;
- whether FPGA-v1 already implements it;
- Python-golden representation;
- intended FPGA representation;
- observability/trace requirements;
- validation strategy; and
- explicit unsupported or ambiguous behavior.

This specification becomes the authority for FPGA-v2 in the same way the M10
contract became the authority for FPGA-v1.

---

## 4. Feature priorities

The new architecture should be developed in priority order rather than trying to
implement every Loihi feature simultaneously.

### Priority A — required for the deep-MNIST end goal

These features are the minimum architectural expansion expected to materially
change the final thesis comparison:

- multiple logical neuromorphic cores;
- explicit per-core neuron, axon, synapse, and routing resources;
- inter-core spike packet routing;
- deterministic logical core placement and connection mapping;
- support for deeper feed-forward SNN graphs;
- Loihi-like axon/synapse sharing or an explicitly modeled equivalent needed to
  represent convolutional connectivity efficiently;
- per-core resource-capacity accounting;
- a timestep/quiescence or barrier mechanism that separates algorithmic time
  from raw FPGA clock cycles;
- transparent host loading, execution, and state/spike observation; and
- a compiler/mapping layer that transforms a trained network into the logical
  manycore deployment.

These capabilities are central to reproducing the kind of multicore,
resource-constrained deep SNN mapping studied by NxTF.

### Priority B — important architectural fidelity

Implement after the Priority-A manycore path is stable unless the target
specification shows that the final workload requires them earlier:

- programmable synaptic delays;
- richer compartment relationships / dendritic structures;
- broader connection-format and weight-format support;
- more faithful event scheduling under simultaneous traffic;
- congestion/backpressure behavior where source evidence is sufficient;
- expanded reset/refractory/threshold configurability; and
- more detailed asynchronous/quiescence behavior.

### Priority C — valuable but not required for the first deep-MNIST comparison

These features may be deferred unless they become necessary for the thesis
claim:

- on-chip learning/plasticity;
- embedded management-processor emulation;
- full chip-to-chip scaling;
- exact physical asynchronous-circuit implementation; and
- undocumented proprietary microarchitectural details.

The thesis should prefer a well-validated transparent manycore subset over a
broader but weakly supported imitation.

---

## 5. FPGA-v2 architecture program

FPGA-v2 should be developed beside FPGA-v1 rather than by mutating the validated
baseline.

A likely structure is:

```text
Loihi-like logical chip
├── logical core 0
│   ├── compartment/neuron state
│   ├── axon table
│   ├── synapse memory
│   ├── routing table
│   └── local event queues
├── logical core 1
├── ...
├── packet router / NoC model
├── timestep or quiescence coordinator
├── configuration / mapping loader
└── trace and instrumentation plane
```

Physical FPGA memories and compute engines may service multiple logical cores
through time-division multiplexing. The logical architecture, not the number of
physically duplicated compute blocks, defines fidelity.

### Stage A — new golden model

Extend or create a Python architecture model that explicitly represents:

- core identity;
- per-core resource tables;
- packetized spike destinations;
- local event queues;
- inter-core delivery;
- per-timestep completion/quiescence;
- mapping constraints; and
- deterministic trace output.

Before hardware work, reproduce existing FPGA-v1 single-core behavior as a
degenerate one-core configuration where appropriate.

### Stage B — one logical FPGA-v2 core

Implement one new logical core using the target specification. Preserve the
existing validation discipline:

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

Do not scale to many cores until the one-core architectural contract is stable.

### Stage C — multicore routing

Add at least two logical cores and validate:

- local versus remote spike delivery;
- fan-in/fan-out across cores;
- simultaneous source spikes;
- deterministic packet destinations;
- next-timestep or documented delivery timing;
- queue limits and overflow behavior;
- core completion/barrier semantics; and
- complete traceability of the first divergence.

### Stage D — scalable logical-core virtualization

Introduce the scheduler/memory organization needed to represent more logical
cores than can be physically duplicated.

The implementation must report:

- number of logical cores represented;
- physical compute/memory resources used;
- cycles required per logical timestep;
- resource occupancy per logical core;
- packet/event load; and
- any capacity limit that prevents a mapping.

A failed mapping because of a modeled architectural limit is a valid result.
Silently exceeding logical Loihi-style resources is not.

### Stage E — mapping/compiler layer

The final platform needs a deterministic mapping path from a network description
to FPGA-v2 deployment artifacts. At minimum it should:

- partition neurons/compartments across logical cores;
- assign axons and synapses;
- exploit supported sharing/compression;
- build routing entries;
- reject mappings that exceed declared resources;
- emit a machine-readable placement report; and
- generate the exact configuration consumed by both Python golden and FPGA
  execution.

This mapping layer is essential to making the architecture useful beyond
handwritten directed tests.

---

## 6. Verification strategy

The project’s strongest methodological advantage is its existing transparent
verification workflow. FPGA-v2 should preserve it.

Every architectural addition should be validated at three levels:

1. **Directed unit behavior** — minimal cases isolate one semantic rule.
2. **Network differential behavior** — Python golden and FPGA traces match over
   representative mapped networks.
3. **Physical application behavior** — a real K26 deployment reproduces the
   golden application result.

Where an external reference such as Brian2Loihi is actually comparable, it may
remain a supporting reference. It should not be treated as universal Loihi
ground truth where M13 already established scope or modeling differences.

The FPGA-v2 validation record should preserve:

- first state-divergence tick;
- first spike-divergence tick;
- logical core and neuron IDs;
- packet/event traces;
- per-core resource tables;
- deployment hashes;
- bitstream/toolchain identity; and
- physical-versus-golden result summaries.

---

## 7. Deep MNIST / NxTF comparison target

The final application should be qualitatively deeper than the current
`784 -> 10` classifier and should exercise the new manycore architecture.

Rueckauer et al. is the primary comparison target because NxTF specifically
addresses mapping deep convolutional SNNs onto Loihi’s multicore,
resource-constrained architecture and exploits Loihi connectivity/weight
sharing.

The experiment should reproduce the published workload as closely as public
information and the new architecture permit, while clearly separating exact
matches from translated or unavailable details.

### Comparison contract to freeze before results

Record before running the final comparison:

- MNIST source data and preprocessing;
- network topology;
- training/conversion method;
- neuron dynamics;
- presentation timestep count;
- weight precision/representation;
- logical core count and placement;
- axon/synapse sharing strategy;
- decoder;
- accuracy metric;
- latency boundary;
- resource-accounting boundary; and
- any quantity that cannot be matched to the paper.

No target-specific retuning should be introduced after comparison results are
observed without creating a new experiment version.

### Candidate final measurements

The strongest defensible comparison is expected to include:

- classification accuracy;
- timestep count;
- logical core count;
- neurons/compartments per core;
- axon and synapse occupancy;
- sharing/compression effectiveness;
- packet/event traffic;
- FPGA resource use;
- FPGA architectural cycles and latency; and
- mapping failures or capacity bottlenecks.

Energy/inference should remain outside the claim set unless a defensible
workload-specific physical power-measurement method is established.

### Final thesis question

A useful thesis-level framing is:

> Can a transparent FPGA implementation of a documented Loihi-like manycore
> architecture execute a deep spiking workload comparable to one previously
> mapped to Intel Loihi, and what architectural, resource, and performance
> differences emerge from that implementation?

The result should emphasize architectural correspondence and transparent
measurement rather than a simplistic FPGA-versus-Loihi winner/loser claim.

---

## 8. Documentation structure

The repository should separate completed history from the active research
direction:

- `MILESTONES.md` — historical FPGA-v1 platform-development record;
- current `applications/mnist/` — first application, to be frozen/renamed as a
  baseline after preservation;
- `LOIHI_TWIN_ROADMAP.md` — active high-level direction and phase plan;
- future target specification — normative source-backed FPGA-v2 architecture
  contract;
- future FPGA-v2 docs — implementation and validation evidence;
- future deep-MNIST application directory — final NxTF-oriented workload; and
- `EXPERIMENTS.md` — deferred counterfactual experiments available after the
  architecture/application endgame path.

Numbered milestones are not required for the new phase unless a later
development problem benefits from that level of project-management detail.
Research gates and versioned architecture specifications are preferred.

---

## 9. Immediate next action

The next active task is the **FPGA-v1/MNIST-v1 preservation audit**.

Do not rename the MNIST application or begin FPGA-v2 implementation until the
audit establishes that:

```text
frozen software package validates
accepted runtime bitstream is archived and hashed
accepted runtime bitstream can still execute on the K26
source can regenerate the required HLS/Vivado hardware
tool/environment versions are recorded
reproduction commands and expected outputs are documented
```

Once those conditions are satisfied, freeze/tag the baseline, rename the
application as a historical baseline, and begin the source-backed Loihi-1 target
architecture study.
