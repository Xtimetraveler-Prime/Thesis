# Loihi-1 Twin Target Specification

**Status:** Draft normative architecture contract for FPGA-v2  
**Architecture generation:** v2  
**Purpose:** Define the source-backed logical architecture that the new Python golden model, mapper/compiler, and FPGA implementation must share.  
**Relationship to FPGA-v1:** FPGA-v1 is a preserved historical control and is not modified by this specification.

---

## 1. Scope and claim boundary

FPGA-v2 targets an **architectural digital twin of a defensible subset of Intel Loihi-1**, not a transistor-level or timing-exact clone.

The twin shall reproduce the documented logical resources, state transitions, connectivity model, inter-core event behavior, algorithmic-time synchronization, mapping limits, and observability needed to execute and study multicore spiking neural networks. Physical FPGA resources may be time-multiplexed or virtualized when that preserves the same logical architectural state and externally visible behavior.

The project shall explicitly distinguish:

- **SOURCE-BACKED** — behavior or capacity directly described by published Loihi literature;
- **DERIVED** — a deterministic architectural consequence inferred from multiple source-backed facts;
- **PROJECT CHOICE** — the FPGA/Python mechanism selected to realize a source-backed behavior;
- **DEFERRED** — a documented Loihi feature intentionally excluded from the first v2 implementation; and
- **UNKNOWN / NOT CLAIMED** — behavior for which public sources are insufficient to support an exact equivalence claim.

No requirement marked PROJECT CHOICE shall be described as the physical Loihi implementation.

---

## 2. Source hierarchy

The following sources are the evidence authority for this specification. Citations throughout the document use the short IDs in the first column.

| ID | Source | Role in this specification |
| --- | --- | --- |
| **D18** | M. Davies et al., “Loihi: A Neuromorphic Manycore Processor with On-Chip Learning,” *IEEE Micro*, 38(1), 82–99, 2018. DOI: https://doi.org/10.1109/MM.2018.112130359 | Primary Loihi-1 architecture, connectivity, resource limits, barriers, compartments, delays, learning architecture, and core microarchitecture. |
| **L18** | A. Lines et al., “Loihi Asynchronous Neuromorphic Research Chip,” *2018 IEEE ASYNC*, 2018. DOI: https://doi.org/10.1109/ASYNC.2018.00018 | Primary implementation source for mesh organization, spike-processing pipeline, asynchronous bundled-data design, and Intel’s FPGA-emulation methodology. |
| **D21** | M. Davies et al., “Advancing Neuromorphic Computing With Loihi: A Survey of Results and Outlook,” *Proceedings of the IEEE*, 109(5), 911–934, 2021. DOI: https://doi.org/10.1109/JPROC.2021.3067593 | Later Intel summary used to corroborate Loihi-1 resource organization and event-message behavior. |
| **R22** | B. Rueckauer et al., “NxTF: An API and Compiler for Deep Spiking Neural Networks on Intel Loihi,” *ACM JETC*, 18(3), 2022. DOI: https://doi.org/10.1145/3501770 ; open preprint: https://arxiv.org/abs/2101.04261 | Compiler/mapping constraints, axon and synapse sharing, compression, partitioning, and the final deep-MNIST comparison target. |
| **M22** | C. Michaelis et al., “Brian2Loihi: An emulator for the neuromorphic chip Loihi using the spiking neural network simulator Brian,” *Frontiers in Neuroinformatics*, 16:1015624, 2022. DOI: https://doi.org/10.3389/fninf.2022.1015624 | Independent, hardware-validated clarification of Loihi neuron arithmetic, update order, integer precision, weight representation, and limitations of software emulation. |
| **P13** | `Loihi_Digital_Twin/v1/docs/M13_FINAL_AUDIT_SUMMARY.md` and related M13 evidence | Project authority for what FPGA-v1 already validates and what it explicitly does not claim. |

### 2.1 Evidence precedence

When sources disagree or differ in abstraction:

1. D18 and L18 take precedence for Loihi-1 architectural claims.
2. D21 may clarify but shall not silently override the 2018 primary architecture.
3. R22 is authoritative for the **NxTF mapping problem and workload assumptions**, not for undocumented Loihi internals.
4. M22 is used for neuron-level numerical semantics that it experimentally validates against Loihi; it is not used as evidence for routing/resource behavior that it explicitly does not model.
5. Project sources define the FPGA-v1 baseline only.

---

## 3. Architectural target summary

The initial v2 target is a multicore, event-routed, algorithmic-discrete-time Loihi-1 subset with explicit resource accounting.

The first complete v2 architecture shall provide:

1. multiple logical neuromorphic cores;
2. explicit per-core compartment, input-axon, output-axon, synapse-memory, and routing resources;
3. packetized inter-core spike delivery;
4. deterministic placement and mapping subject to Loihi-like hard resource limits;
5. a timestep/quiescence barrier that prevents advancement while current-timestep spike traffic remains in flight;
6. source-backed neuron arithmetic or an explicitly versioned compatibility profile;
7. Loihi-like resource sharing needed for efficient convolutional mappings;
8. transparent configuration, event, state, routing, and capacity traces; and
9. a clean separation between **logical Loihi resources** and **physical K26 execution resources**.

This target is derived from D18 §§3.1–3.3 and 4.1, L18 §I, and R22 §2.3.

---

## 4. Logical chip organization

### 4.1 Neuromorphic core count

**SOURCE-BACKED.** A Loihi-1 chip contains **128 neuromorphic cores**. D18 §3.1 describes the chip as a manycore mesh of 128 neuromorphic cores plus three embedded x86 processors and off-chip interfaces. L18 independently states 128 custom neuron cores with 1,024 neurons/units each. [D18 §3.1; L18 Abstract/§I]

**Normative v2 rule:**

- the Python architecture shall expose a logical chip with a maximum of **128 logical neuromorphic core IDs**;
- smaller configured logical chips are allowed for unit tests and FPGA deployment;
- the K26 is not required to instantiate 128 physical compute engines.

### 4.2 Management processors

**SOURCE-BACKED but DEFERRED.** Loihi-1 contains three embedded x86 cores and allows host/on-chip management traffic. [D18 §3.1; L18 §I]

**Initial v2 rule:** x86 instruction-set or firmware emulation is out of scope. Equivalent host configuration and inspection functions shall instead be exposed by the project host/debug interface.

### 4.3 Multi-chip hierarchy

**SOURCE-BACKED but DEFERRED.** D18 §3.1 describes hierarchical off-chip communication and addressing beyond one chip.

**Initial v2 rule:** the first v2 architecture models one logical Loihi-1 chip. Multi-chip addressing is reserved in interfaces but is not required for the first deep-MNIST target.

---

## 5. Logical core resource contract

D18 §3.3 gives the architectural resource constraints that govern placement. R22 Table 1 uses the same limits as the compiler’s practical mapping model.

| Resource | Loihi-1 source-backed limit | v2 normative treatment | Evidence |
| --- | ---: | --- | --- |
| compartments / primitive neural units | 1,024 / core | hard logical capacity | D18 §§3.1, 3.3; R22 Table 1 |
| input axon / distribution-list IDs | 4,096 / core | hard logical capacity | D18 §3.3; R22 Table 1 |
| output core-to-core fanout slots | 4,096 / core | hard logical capacity | D18 §3.3; R22 Table 1 |
| synaptic fan-in state | 128 KB / core | hard modeled memory budget, with explicit encoding assumptions | D18 §3.3 |
| practical synapse count | approximately 128k / core under an 8-bit-weight assumption | workload/compiler estimate, not a universal exact count | R22 Table 1 |

### 5.1 Capacity-accounting rule

**Normative:** a network mapping is invalid if any hard logical core capacity is exceeded. The mapper shall fail explicitly and report the exceeded resource rather than silently oversubscribe it.

This follows D18 §3.3, which states that abstract networks are mapped by assigning neurons to cores subject to core resource constraints, and R22 §2.3.4, where violation of a hard resource limit invalidates a partition candidate.

### 5.2 Synapse-memory accounting

**SOURCE-BACKED / PARTIALLY ENCODING-DEPENDENT.** D18 defines a 128 KB synaptic fan-in state budget and notes compression/list-alignment effects. R22 likewise notes that effective synapse capacity depends on compression.

**Normative:** v2 shall account for synaptic storage in an explicit, versioned encoding-cost model. A simple first implementation may conservatively account bytes/words without reproducing every native Loihi compression bitfield, but it must never convert the 128 KB limit into an unconstrained Python list.

The exact native SRAM encoding is **not claimed** until independently specified and tested.

---

## 6. Connectivity and axon semantics

### 6.1 Directed multigraph model

**SOURCE-BACKED.** D18 §3.3 defines the mapped network as a directed multigraph. A synapse has source/destination identities and state including weight, delay, and tag.

**Normative:** the v2 golden model shall represent arbitrary directed connections, including recurrence, subject to core resource limits.

### 6.2 Destination-side axon IDs

**SOURCE-BACKED.** D18 §3.3 states that fanout edges are projected into core-to-core edges and assigned an `axon_id` unique to the destination core. The destination core expands that axon ID into the associated local synaptic list. L18 §I similarly describes an incoming spike as encoding an axon index pointing to a variable-length synapse list.

**Normative packet-to-synapse behavior:**

1. an inter-core spike event identifies a destination logical core and destination-side axon ID;
2. the destination core resolves the axon ID to one or more local synaptic entries;
3. those entries identify destination compartments and their synaptic parameters;
4. contributions are accumulated into destination compartment input state.

### 6.3 Output routing

**SOURCE-BACKED.** D18 §3.2 states that the NoC itself performs unicast delivery; multicast fanout is realized by the source core iterating over destination cores and sending a spike for each destination core. L18 §I describes the end of the neuron-core pipeline walking a variable-length destination-core/axon list for a firing neuron.

**Normative:** v2 shall make fanout routing explicit. A firing logical neuron may create zero, one, or multiple destination-core packet events. Fanout shall not be implemented as an implicit global broadcast invisible to the architectural trace.

### 6.4 Packet format boundary

**SOURCE-BACKED semantics; UNKNOWN physical bitfield.** Published sources establish packetized spike messages, destination addressing, and axon semantics, but this project does not have sufficient public evidence to claim an exact reproduction of every Loihi-1 packet bitfield.

**PROJECT CHOICE:** the v2 internal spike-packet object shall contain at minimum:

- algorithmic timestep / epoch identity used by the emulator;
- destination logical core ID;
- destination axon ID;
- optional source metadata for debugging; and
- packet class/type.

The FPGA implementation may encode these fields differently as long as Python and FPGA traces normalize to the same logical packet.

---

## 7. Routing fabric

### 7.1 Loihi source behavior

**SOURCE-BACKED.** D18 §3.1 describes an asynchronous NoC carrying spike, barrier, management-read/write, and response messages. D18 §3.2 states that spike traffic uses dimension-order routing and that spike sequence order within an algorithmic timestep is not semantically significant. L18 §I describes the physical 8×4 router mesh with each router attached to four local neuron cores. [D18 §§3.1–3.2; L18 §I]

### 7.2 v2 logical routing requirement

The initial v2 shall model a **logical routed inter-core fabric** with explicit packet queues and destination resolution.

The first FPGA realization does **not** need to physically reproduce the 8×4 asynchronous router layout if a virtualized fabric preserves:

- destination correctness;
- packet conservation (no loss or duplication except intentional multicast expansion);
- within-timestep order independence;
- barrier/quiescence correctness;
- observable traffic counts; and
- explicit capacity/backpressure behavior where modeled.

This is a PROJECT CHOICE that preserves the D18/L18 logical behavior while separating it from the K26 physical topology.

### 7.3 Determinism requirement

D18 §3.2 states that SNN computation does not depend on spike sequence ordering within a timestep.

**Normative testable property:** for configurations that do not use order-sensitive unsupported features, permuting the delivery order of same-timestep packets must not change normalized state/spike results at the next architectural boundary.

---

## 8. Algorithmic time and barrier semantics

### 8.1 Algorithmic time is not hardware clock time

**SOURCE-BACKED.** D18 §2.1 states that Loihi approximates continuous dynamics using fixed-size discrete timesteps and explicitly distinguishes algorithmic time from hardware execution time.

**Normative:** all v2 APIs and traces shall distinguish:

- `algorithmic_timestep` — Loihi-style model time; and
- `physical_cycles` — implementation cost on FPGA or emulator work count.

A faster/slower FPGA schedule must not alter algorithmic results.

### 8.2 Two-phase barrier meaning

**SOURCE-BACKED.** D18 §3.2 describes barrier synchronization after a core finishes its compartments: barrier messages first flush spikes in flight and then propagate timestep advancement. A core begins the next timestep only after the second phase permits it.

**Normative logical barrier:** no logical core may begin its `t+1` compartment update while any packet generated for timestep `t` remains capable of affecting architectural state for that boundary.

### 8.3 Inter-core causality

**DERIVED from D18 §3.2 and L18 §I.** L18 describes incoming spike contributions being accumulated while the core iterates neurons using accumulated weights from the previous timestep. D18 states that all cores execute timestep `t`, distribute resulting spikes, flush them, and only then advance.

**Initial v2 contract:** a spike generated by a compartment during evaluation of timestep `t` is delivered/accumulated for the destination’s subsequent architectural update, not used to retroactively modify a destination compartment already evaluated for timestep `t`.

This rule shall be validated with cross-core feed-forward and recurrent tests before the FPGA implementation is considered architecture-complete.

### 8.4 Quiescence implementation

**PROJECT CHOICE:** a synchronous FPGA may use a centralized barrier/quiescence coordinator, distributed completion counters, or an equivalent handshake. It need not reproduce Loihi’s physical asynchronous barrier wires/messages exactly.

The implementation must prove the same logical invariant: all required current-timestep traffic is drained and all participating logical cores are complete before advancing algorithmic time.

---

## 9. Core execution pipeline

### 9.1 Source pipeline

**SOURCE-BACKED.** L18 §I gives a compact spike lifecycle:

- incoming spike encodes an axon index;
- axon index points to a variable-length synapse list;
- list entries may encode weight, delay, destination compartment, and tag;
- synaptic weights are accumulated at destination compartments;
- neuron/compartment state is updated for the next timestep;
- firing neurons walk destination core/axon lists to emit spikes.

D18 §4.1 describes four major core operating modes: input spike handling, compartment updates, output spike generation, and synaptic updates. Its Figure 4 identifies SYNAPSE, DENDRITE, AXON, and LEARNING roles.

### 9.2 v2 staged core interface

The v2 logical core shall expose separable architectural stages even if one physical engine time-multiplexes them:

1. **ingress / synapse stage** — receive packet and expand `axon_id`;
2. **accumulation stage** — add synaptic contributions to destination input state;
3. **compartment-update stage** — evolve compartment current/voltage/state;
4. **spike-decision stage** — determine which root/soma compartments fire;
5. **egress / axon stage** — expand firing sources into destination-core packets;
6. **completion stage** — report local quiescence for barrier logic.

A later learning stage may be added without changing these interfaces.

---

## 10. Compartment and neuron model

### 10.1 Compartment primitive

**SOURCE-BACKED.** D18 §3.1 states that each core implements 1,024 primitive spiking neural units called compartments. Compartments may be grouped into trees representing neurons. D18 describes current-like and voltage-like state and thresholded spike generation. [D18 §§2.1, 3.1]

### 10.2 Dendritic trees

**SOURCE-BACKED but initially DEFERRED.** D18 describes configurable trees of compartments in which only the root/soma emits output spikes and child/root state may be combined by configurable join functions.

**Initial v2 profile:** one logical compartment per neuron. The data model shall reserve parent/root identity so multi-compartment neurons can be added without redesigning routing/mapping interfaces.

### 10.3 Numerical update behavior

**SOURCE-BACKED / project-validated subset.** D18 §2.1 defines a CUBA-style LIF model and discrete timestep approximation. M22 §§2.2–2.3 reports that Loihi’s neuron behavior can be exactly reproduced for tested single-neuron and recurrent cases using forward-Euler-style integer updates, Loihi-specific operation order, and round-away-from-zero behavior for synaptic-input and voltage updates.

FPGA-v1 already has a frozen neuron arithmetic contract and M13 differential evidence. [P13]

**Normative migration rule:** v2 shall not invent a new neuron arithmetic model merely because the architecture is new. The first v2 golden model shall import or re-express the **validated v1 neuron-step semantics behind a versioned compartment interface**, then add Loihi-specific extensions only when source-backed and independently tested.

This preserves known-good arithmetic while separating it from the v1 single-core architecture.

### 10.4 Refractory/reset and thresholds

The initial v2 implementation shall support the frozen v1 behavior required by current conformance tests. Richer Loihi refractory, adaptive-threshold, stochastic, and compartment-tree features are Priority-B extensions unless a final workload requires them earlier. [D18 §2.4; M22 §§2–4; P13]

---

## 11. Synaptic representation

### 11.1 Required logical synapse fields

D18 §3.3 models a synapse with source/destination plus `wgt`, `dly`, and `tag` state. L18 §I states that synaptic list entries may encode weight, delay, destination compartment, and tag.

The v2 logical model shall therefore reserve at least:

- destination compartment ID;
- static/effective weight representation;
- delay field;
- optional tag/auxiliary field; and
- synaptic-format/encoding metadata where needed for capacity accounting.

Fields may be disabled in the first execution profile but shall not require a routing redesign when enabled later.

### 11.2 Weight precision

**SOURCE-BACKED.** D18 describes variable synaptic weight precision from 1 to 9 bits, signed or unsigned. M22 §3.1 provides a more detailed software-emulation description of mantissa, exponent, sign modes, precision, and initialization behavior.

**Initial deep-MNIST profile:** support an explicitly defined static **8-bit Loihi-oriented mapping profile**, because R22’s resource estimates and NxTF mapping discussion use 8-bit weights. General 1–9-bit mixed-format support is Priority B.

The project shall report whether a comparison uses:

- native-style mantissa/exponent encoding;
- an equivalent effective integer weight; or
- a compatibility transform.

It shall not label an effective-weight encoding “native Loihi” without matching the source-backed native format.

### 11.3 Synaptic delays

**SOURCE-BACKED but initially DEFERRED beyond baseline.** D18 §4.1 states that Loihi supports a minimum delay capacity of eight delay units and may support values up to 62 depending on compartment use; D18 also lists configurable synaptic/axon/refractory delays.

The v2 data structure shall carry a delay field from the beginning, but the first multicore milestone may restrict mapped networks to the delay profile needed by the validation corpus. Programmable delay validation is a Priority-B gate.

### 11.4 Learning state

**SOURCE-BACKED but DEFERRED.** Loihi includes programmable synaptic learning, traces, tags, and epoch-based updates. [D18 §§2.3, 3.4; M22 §3]

Online learning is not required for the first v2 deep-MNIST comparison. Static inference mappings must not depend on the learning engine.

---

## 12. Compression, sharing, and convolutional connectivity

### 12.1 Native architecture motivation

D18 §§3.1 and 3.3 describe sparse compression, variable synaptic formats, and population-based hierarchical connectivity for reducing connectivity storage. R22 §2.3 shows that practical deep-network mapping depends strongly on sharing axons and synapses.

### 12.2 NxTF resource sharing

**SOURCE-BACKED for the target comparison.** R22 §2.3.1 describes populations sharing output axons, input axons, and synapse groups. R22 §2.3.2 notes an important limitation: axons may be shared for a population when targeting a compatible core mapping, while fanout crossing core boundaries can require duplicated/discrete routing resources.

**Normative v2 requirement:** the mapper shall have an explicit representation for reusable connection templates / shared synapse groups sufficient to map convolutional layers without materializing every repeated kernel connection as an independent stored weight.

The first implementation may use a project-defined logical sharing structure rather than native Loihi SRAM bit packing, provided:

- sharing changes capacity accounting explicitly;
- expansion semantics are deterministic;
- Python and FPGA use the same normalized mapping; and
- reported results distinguish logical shared parameters from expanded effective connections.

### 12.3 Compression formats

R22 §2.3.5 discusses sparse, dense, and run-length synapse compression in Loihi.

Exact reproduction of all native compression encodings is Priority B. The mapper must nevertheless expose which compression/accounting model was used for every deployment.

---

## 13. Mapping/compiler contract

### 13.1 Mapping is part of the architecture

The network-to-core mapping shall not be treated as an offline convenience. D18 §3.3 makes placement subject to hard resource constraints, and R22 is explicitly a compiler for partitioning deep SNNs onto Loihi’s multicore resources.

### 13.2 Mapper inputs

The v2 mapper shall consume a backend-neutral network description containing at least:

- populations/layers and logical neurons;
- directed synaptic connectivity;
- weights and optional delays;
- candidate sharing groups/templates;
- requested compartment model/profile; and
- input/output endpoint definitions.

### 13.3 Mapper outputs

A successful mapping shall emit a deterministic deployment containing:

- logical chip/core assignment per compartment;
- per-core compartment table;
- per-core input-axon table;
- per-core synapse lists/groups;
- per-neuron output routing entries;
- resource-usage report;
- capacity headroom report;
- normalized packet/routing configuration; and
- a mapping manifest with version and hashes.

### 13.4 Hard and soft constraints

R22 §2.3.4 distinguishes hard hardware constraints from soft optimization costs.

**Normative:**

- hard capacity violations must fail mapping;
- optimization may minimize core count, synaptic use, axon use, or traffic;
- the initial mapper may use a deterministic greedy strategy rather than reproduce NxTF’s exact optimizer;
- the cost function and tie-breaking rules must be recorded so mappings are reproducible.

### 13.5 Deep-MNIST relevance

R22 reports a converted four-layer MNIST CNN mapped to **14 Loihi neurocores**, with sharing reducing the number of stored/shared weights dramatically relative to a fully discrete connection representation, and runs it for 100 algorithmic timesteps per sample. [R22, MNIST evaluation section]

This is a motivation/benchmark target, not a requirement that v2 reproduce NxTF’s proprietary/native deployment byte-for-byte.

---

## 14. Logical versus physical execution resources

### 14.1 Source precedent for time multiplexing

D18 §3.1 states that compartment state within each Loihi core is updated in a time-multiplexed, pipelined manner each algorithmic timestep. The architecture therefore already separates logical neuron count from fully spatial neuron hardware.

### 14.2 FPGA virtualization rule

**PROJECT CHOICE:** FPGA-v2 may implement fewer physical core engines than logical cores. A physical engine may service multiple logical cores by loading their architectural state from BRAM/URAM.

Virtualization is acceptable only if:

1. every logical core retains independent architectural state;
2. per-core Loihi-like capacities are enforced before virtualization;
3. packet source/destination identities remain logical-core identities;
4. barrier semantics are evaluated at the logical-core level;
5. execution order cannot alter normalized architectural results; and
6. performance reports distinguish logical core count from physical engine count.

### 14.3 Virtualization invariance test

A required v2 validation shall map the same small network onto the same logical cores and execute it with different physical-engine counts/schedules. Normalized spike/state traces must match exactly.

---

## 15. Physical synchrony versus architectural asynchrony

### 15.1 Loihi silicon

**SOURCE-BACKED.** L18 describes Loihi as a digital asynchronous design generated from CSP into two-phase bundled-data pipelines. D18 likewise describes the chip as digital, deterministic, event driven, and implemented with asynchronous bundled-data logic. [L18 Abstract/§II; D18 §§3.1, 4.2]

### 15.2 FPGA-emulation precedent

**SOURCE-BACKED and especially important to this project.** L18 §II states that alternate pipeline controllers wait on a positive-edge clock so the design can be mapped to an FPGA for emulation; the FPGA uses the same logical netlist/features but differs in precise timing.

### 15.3 v2 claim language

The K26 implementation shall therefore be described as:

> a **synchronous physical FPGA realization of Loihi-like event-driven architectural semantics**.

It shall not be described as a physically asynchronous Loihi clone unless the implementation actually adopts asynchronous circuitry and validates it.

The architectural twin shall reproduce observable event-driven/quiescence behavior; it does not need to reproduce Loihi’s exact bundled-data delays, latch timing, or circuit-level handshake latencies.

---

## 16. Host/configuration/observability contract

L18 §I states that embedded/off-chip CPUs can configure and inspect neuron-core state. Exact x86/host protocol emulation is deferred, but transparency is central to the thesis.

The v2 implementation shall provide a host/debug interface capable of:

- loading a mapping manifest and static core memories;
- injecting external spikes/events with algorithmic timestamps;
- starting/resetting execution;
- observing emitted spikes;
- reading selected compartment current/voltage/state;
- reading packet counts and queue/barrier state;
- reporting per-core resource occupancy; and
- reporting physical cycle counts independently of algorithmic timesteps.

A result that can only be observed through final classification accuracy is insufficient for architecture validation.

---

## 17. Initial implementation profile (v2.0)

The following profile is the minimum target for the first separate v2 Python model and its first FPGA implementation.

### Required in v2.0

- configurable multiple logical cores, max logical ID space corresponding to one 128-core chip [D18];
- 1,024-compartment hard capacity per core [D18/R22];
- 4,096 input-axon IDs per core [D18/R22];
- 4,096 output routing slots per core [D18/R22];
- explicit 128 KB synaptic-memory accounting model [D18];
- single-compartment neurons using the versioned validated neuron-step contract [D18/M22/P13];
- static synapses;
- destination-core + axon-ID packet routing [D18/L18];
- explicit fanout route lists [D18/L18];
- packet queues and observable traffic counts;
- algorithmic timestep separate from physical cycles [D18];
- barrier/quiescence synchronization [D18];
- deterministic mapping and hard-capacity rejection [D18/R22];
- logical connection/synapse sharing sufficient for convolutional reuse [D18/R22];
- deterministic host loading and trace capture; and
- logical-core virtualization independent of physical-engine count [PROJECT CHOICE, justified by D18 time multiplexing and L18 FPGA-emulation precedent].

### Reserved in data structures but not necessarily executable in v2.0

- programmable synaptic delay;
- compartment parent/root relationships;
- tag/learning metadata;
- packet payload extensions;
- multi-chip destination information.

### Deferred beyond v2.0

- full dendritic-tree behavior;
- general 1–9-bit mixed synaptic format support;
- exact native synaptic compression bit packing;
- plasticity and learning microcode;
- stochastic traces/noise;
- embedded x86 management-processor emulation;
- chip-to-chip routing;
- exact Loihi physical asynchronous circuit timing.

---

## 18. Separate v2 Python golden model

FPGA-v2 shall use a **new model**, not a mutation of the v1 `NeuromorphicCore` architecture.

Recommended logical module boundaries:

```text
v2/
├── docs/
│   └── LOIHI1_TARGET_SPEC.md
├── src/
│   └── loihi_twin_v2/
│       ├── chip.py
│       ├── core.py
│       ├── compartment.py
│       ├── axon.py
│       ├── synapse.py
│       ├── packet.py
│       ├── router.py
│       ├── barrier.py
│       ├── mapping.py
│       ├── resources.py
│       └── trace.py
├── tests/
├── rtl/
├── hls/
└── scripts/
```

The initial implementation should begin with `resources`, `packet`, `core`, `router`, and `barrier` abstractions before attempting a deep application.

### 18.1 v1 reuse boundary

Code reuse from v1 is allowed only for behavior that is intentionally retained, especially validated neuron arithmetic and utility functions. Reuse should occur through an explicit compatibility module or copied/re-versioned primitive with tests; v2 must not depend on hidden mutable global state inside the v1 package.

---

## 19. Required directed architecture tests

The specification is not complete merely when classes exist. The following tests are required before large-network work.

### T1 — single-core neuron compatibility

Run frozen v1 directed neuron cases through the v2 compartment primitive and require exact normalized agreement for the retained neuron profile. [P13/M22]

### T2 — two-core feed-forward packet

Core 0 fires one mapped neuron; exactly one destination packet is produced; Core 1 expands its axon ID and receives the expected synaptic contribution on the next architectural update.

### T3 — multicast fanout

One source neuron targets multiple logical cores. Verify explicit packet expansion and per-core axon resolution. [D18 §3.2]

### T4 — within-timestep order invariance

Permute multiple same-timestep packet arrival orders and require identical next-boundary compartment/spike state. [D18 §3.2]

### T5 — barrier drain

Artificially delay one packet. No logical core may advance until the packet is consumed and barrier completion criteria are met. [D18 §3.2]

### T6 — recurrent cross-core causality

Build Core 0 → Core 1 → Core 0 recurrence and verify deterministic one-boundary progression independent of physical scheduling order.

### T7 — hard resource rejection

Construct mappings exceeding each of the four key resource limits and require explicit mapper failure identifying the violated resource. [D18 §3.3; R22 §2.3.4]

### T8 — sharing/accounting

Map a repeated convolution-like kernel with and without sharing. Verify identical logical synaptic effects but different reported resource occupancy. [D18 §3.3; R22 §2.3.1]

### T9 — virtualization invariance

Execute the same logical mapping using one and multiple physical core-engine schedules. Require exact normalized state/spike/packet traces.

### T10 — Python/FPGA normalized trace

For a small multicore corpus, compare normalized per-timestep packets, compartment state, spikes, barrier boundaries, and capacity configuration between Python and FPGA.

---

## 20. Trace schema requirements

Every architecture-validation run shall be capable of producing a normalized trace with at least:

```text
algorithmic_timestep
logical_core_id
phase / architectural stage
packet_in[]
axon_expansions[]
synaptic_contributions[]
compartment_state_before[]
compartment_state_after[]
spikes_out[]
packets_out[]
local_done
barrier_state
physical_cycle (FPGA only or optional emulator work counter)
```

Large runs may use compact counters instead of full arrays, but directed tests shall retain enough detail for deterministic differential debugging.

---

## 21. Capacity and performance reporting

Every mapped workload shall report at least:

- logical cores used;
- compartments used and peak/core;
- input axon IDs used and peak/core;
- output routing slots used and peak/core;
- synaptic memory bytes/words used and peak/core;
- shared versus expanded synaptic parameter counts;
- packet count by timestep and core pair;
- barrier/quiescence work;
- physical FPGA cycles and latency;
- FPGA LUT/FF/BRAM/URAM/DSP utilization; and
- mapping failures or forced partition decisions.

This is required so the eventual NxTF comparison is architectural rather than merely an accuracy comparison. [R22 §§2.3, 3]

---

## 22. Explicit non-claims

Unless a later revision adds source-backed implementation and tests, FPGA-v2 does **not** claim:

- transistor-level equivalence to Loihi-1;
- exact bundled-data asynchronous timing;
- exact NoC router latency or congestion timing;
- exact native packet bit encoding;
- exact native synaptic SRAM bit packing;
- embedded x86 compatibility;
- exact on-chip learning random-number behavior;
- full dendritic/threshold-adaptation behavior;
- complete chip-to-chip protocol equivalence; or
- undocumented proprietary Loihi implementation details.

These exclusions are part of the specification, not shortcomings to hide.

---

## 23. Open questions requiring experiments or further source evidence

The following must remain explicit until resolved:

1. **Native weight profile for final MNIST.** Determine whether final comparison benefits from exact mantissa/exponent encoding or whether an equivalent 8-bit effective-weight profile is sufficient.
2. **Synaptic memory cost model.** Define a conservative first byte/word accounting formula and then decide whether sparse/dense/run-length native-style encoding is necessary for credible NxTF comparison.
3. **Programmable delays.** Decide whether final deep MNIST requires delays beyond the baseline feed-forward timestep relationship.
4. **Physical routing topology.** Determine whether a centralized virtual NoC remains sufficiently transparent for thesis claims or whether a mesh of physical/virtual routers adds useful experimental value.
5. **Barrier implementation.** Choose a hardware mechanism that is simple to verify while preserving two-phase logical drain/advance behavior.
6. **Physical engine count.** Measure K26 resource/timing tradeoffs for one versus multiple physical core engines after the golden model is stable.
7. **Core-sharing semantics.** Define a minimal sharing representation that captures the resource benefit seen by NxTF without overclaiming native SRAM-format equivalence.

---

## 24. Phase exit criteria

The architecture-definition phase is complete when:

- this specification is reviewed and accepted as the v2 contract;
- every Priority-A behavior has a source classification and explicit claim boundary;
- unresolved public-information gaps are labeled UNKNOWN rather than guessed;
- the v2 Python package skeleton is separate from v1;
- the mapper resource model is defined;
- packet and barrier semantics are unambiguous enough to write T1–T9 without interpretation disputes; and
- no v2 code is required to modify the preserved v1 behavior.

The next implementation phase shall then build the separate Python manycore golden model against this document.

---

## 25. Source-to-requirement crosswalk

| Requirement | Classification | Primary support |
| --- | --- | --- |
| 128 logical neuromorphic cores/chip | SOURCE-BACKED | D18 §3.1; L18 Abstract |
| 1,024 compartments/core | SOURCE-BACKED | D18 §§3.1, 3.3; R22 Table 1 |
| 4,096 input axons/core | SOURCE-BACKED | D18 §3.3; R22 Table 1 |
| 4,096 output routing slots/core | SOURCE-BACKED | D18 §3.3; R22 Table 1 |
| 128 KB synaptic fan-in storage/core | SOURCE-BACKED | D18 §3.3 |
| packetized inter-core spikes | SOURCE-BACKED | D18 §§3.1–3.2; L18 §I |
| destination axon ID expands to local synapse list | SOURCE-BACKED | D18 §3.3; L18 §I |
| explicit per-destination-core fanout | SOURCE-BACKED | D18 §3.2; L18 §I |
| same-timestep spike order not semantically significant | SOURCE-BACKED | D18 §3.2 |
| barrier flush then timestep advance | SOURCE-BACKED | D18 §3.2 |
| algorithmic timestep distinct from hardware execution time | SOURCE-BACKED | D18 §2.1 |
| compartment time multiplexing | SOURCE-BACKED | D18 §3.1 |
| synchronous FPGA realization may preserve logical features while changing precise timing | SOURCE-BACKED precedent | L18 §II |
| integer Loihi neuron arithmetic and operation ordering | SOURCE-BACKED / independently validated | M22 §§2–4; P13 |
| 1–9-bit configurable weights | SOURCE-BACKED | D18 §3.1; M22 §3.1 |
| convolutional sharing is mapping-critical | SOURCE-BACKED for NxTF workload | R22 §2.3 |
| hard-capacity-aware compiler | SOURCE-BACKED for mapping model | D18 §3.3; R22 §2.3.4 |
| fewer physical FPGA engines than logical cores | PROJECT CHOICE | permitted by project claim boundary; motivated by D18 time multiplexing and L18 FPGA-emulation precedent |
| centralized FPGA barrier/router implementation | PROJECT CHOICE | must satisfy D18 logical behavior |
| exact Loihi packet/SRAM bitfields | UNKNOWN / NOT CLAIMED initially | public evidence insufficient for exact equivalence |

---

## 26. Revision policy

Changes to a SOURCE-BACKED normative rule require one of:

- a stronger primary Loihi-1 source;
- reproducible Loihi-1 hardware evidence; or
- correction of a documented interpretation error.

PROJECT CHOICE implementation details may evolve freely as long as the normalized architecture behavior and tests remain unchanged.

Any v2 behavior that intentionally departs from this specification must be versioned and documented rather than silently changing the golden model.
