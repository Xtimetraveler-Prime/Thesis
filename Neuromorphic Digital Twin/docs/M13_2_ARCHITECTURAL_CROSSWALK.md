# M13.2 — Four-way Architectural Feature Crosswalk

**Status:** Complete crosswalk candidate; M13.2 only. No A–H discrepancy adjudication is performed here.

This document compares four deliberately separate evidence columns: **published Loihi information**, **Brian2Loihi 0.5.2**, **the M12-validated project digital twin**, and **Catalyst N1 at the M13.1 pin**. Agreement is evidence of a shared interpretation, not proof of undocumented Intel microarchitecture. Architectural differences are preserved rather than forced into equality.

The machine-readable authority for this document is `references/m13_2_feature_crosswalk.json`. M13.3 may define transforms only after this matrix is reviewed; M13.4 may classify observed differences only after directed probes exist.

## Frozen reference boundary

- Project computational baseline: `80a502ec6dfc4c8d61372089b08c9a584ad65f85` (M12 complete)
- M13.1 merge: `fab362cebdff133e71367c186d8689e332a99a10`
- Brian2Loihi: `d54676cb113e48dc886615a0b589bb0e4bccbca4` / package 0.5.2
- Catalyst N1: `1806bb4b4114d7671e5648fa75b7b83b3a8d5543` / `v2.3-paper` = `n1-final`

## Relationship vocabulary

- `exactly comparable`
- `comparable after a documented transform`
- `similar but architecturally different`
- `unsupported by one implementation`
- `not observable through the available interface`
- `ambiguous in available Loihi evidence`
- `out of project scope`

These are **comparability labels**, not the M13 A–H discrepancy classes. In particular, a row marked `similar but architecturally different` is not a Class-C finding until a later directed comparison establishes a concrete discrepancy.

## Crosswalk summary

| ID | Feature | Published Loihi | Brian2Loihi | Project | Catalyst N1 | Relationship | Common subset? |
|---|---|---|---|---|---|---|---|
| `neuron-state-model` | Point-neuron dynamic state and LIF formulation | **documented** — Loihi publications describe a discrete-time CUBA LIF variant with synaptic response current u and membrane potential v as internal state. (`loihi_davies_2018`, `brian2loihi_michaelis_2022`) | **implemented** — LoihiNeuronGroup exposes dimensionless current I and voltage v with Loihi-style decay parameters and a Brian2 forward-Euler schedule. (`brian_neuron`, `brian_readme`, `project_m03_m08_brian_evidence`) | **physically_validated** — Per-neuron architectural state is signed 24-bit current, signed 24-bit voltage, and unsigned 16-bit refractory_remaining; behavior is frozen by CORE_SPECIFICATION v1 and exact physical M12 traces. (`project_core_spec_m12`, `project_m12_record`) | **implemented** — Pinned RTL stores 24-bit potential and current plus 8-bit refractory state, while the CPU reference exposes potential/refractory and primarily presents a simpler subtractive-leak LIF API. RTL additionally contains an optional CUBA path. (`catalyst_core_rtl`, `catalyst_simulator`) | `similar but architecturally different` | `conditional` |
| `dendritic-compartments` | Dendritic compartments and compartment trees | **documented** — Dendritic compartments are an explicit Loihi architectural feature. (`loihi_davies_2018`) | **unsupported** — The pinned LoihiNeuronGroup is a point-neuron v/I model and does not expose Loihi dendritic compartment trees. (`brian_neuron`, `brian_readme`) | **out_of_scope** — FPGA-v1 is a point-neuron core and has no dendritic compartment tree state or join operations. (`project_core_spec_m12`) | **implemented** — N1 exposes soma plus three dendritic compartments, per-compartment accumulators/thresholds, parent mappings, and join/stack behavior in the pinned RTL. (`catalyst_constants`, `catalyst_core_rtl`) | `out of project scope` | `no` |
| `current-voltage-decay` | Dual current/voltage decay representation, rounding, and update source | **documented** — Available Loihi/Brian2Loihi publications describe separate current and voltage decays on a 12-bit denominator (4096) discrete-timestep model; exact undocumented overflow details remain outside this evidence. (`loihi_davies_2018`, `brian2loihi_michaelis_2022`) | **implemented** — decay_I and decay_v are 0..4096; each decay amount is constructed as sign(x)*ceil(abs(x*d/4096)), i.e. away from zero. The Brian2 equations retain separate I and v state. (`brian_neuron`, `project_m03_m08_brian_evidence`) | **physically_validated** — 0..4096 decay factors use explicit round-away-from-zero. Input is added to current before current decay; voltage uses the pre-decay working current including same-tick input. (`project_core_spec_m12`, `project_m12_record`) | **partial** — Pinned RTL has optional 12-bit decay_u/decay_v and a round-away-from-zero /4096 helper. In CUBA mode current becomes old_current - decay(old_current) + optionally scaled same-tick input, while potential uses decayed old potential plus old current and bias. The pinned CPU simulator's ordinary synchronous LIF path instead uses subtractive leak and does not expose this CUBA state transition through the same API. (`catalyst_core_rtl`, `catalyst_simulator`) | `comparable after a documented transform` | `conditional` |
| `tick-update-order` | Discrete timestep phases and atomic state visibility | **partial** — Loihi is described as a fixed-size discrete timestep model with globally consistent algorithmic time, but the initial publications do not fully specify every intra-timestep software-observable ordering used by this thesis. (`loihi_davies_2018`) | **implemented** — The emulator requires its LoihiNetwork/default clock/schedule to remain unchanged; neuron and synapse equations are placed into that fixed Brian2 schedule. (`brian_readme`, `brian_neuron`, `brian_synapses`, `project_m03_m08_brian_evidence`) | **physically_validated** — Six normative phases A-F latch events, accumulate, update from a common pre-state snapshot, collect spikes, route recurrence, then atomically commit. Hardware cycles inside a tick are non-architectural. (`project_core_spec_m12`, `project_m12_record`) | **implemented** — CPU synchronous mode states DELIVER->UPDATE->LEARN. RTL has explicit delivery/update/learning FSM phases and asserts timestep_done after the state machine completes; Catalyst also has a distinct asynchronous mode. (`catalyst_simulator`, `catalyst_core_rtl`) | `similar but architecturally different` | `conditional` |
| `threshold-reset` | Threshold comparator and spike reset | **partial** — Published descriptions state that a spike is emitted when membrane potential passes/exceeds its firing threshold and that voltage resets after a spike; the precise equality convention is not treated as fully settled by the primary papers alone here. (`loihi_davies_2018`, `brian2loihi_michaelis_2022`) | **implemented** — Threshold is explicitly v > threshold_v_mant*64; a spike resets v to 0. (`brian_neuron`, `project_m03_m08_brian_evidence`) | **physically_validated** — Threshold is strict V_work > T; equality does not spike. Spike commits configurable reset_voltage. Directed physical M12 cases cover threshold equality/over-threshold and reset. (`project_core_spec_m12`, `project_m12_record`) | **implemented** — Both pinned CPU simulator and RTL use >= threshold in their main update paths and reset potential to the configured resting value after a spike. (`catalyst_simulator`, `catalyst_core_rtl`) | `comparable after a documented transform` | `yes` |
| `refractory-semantics` | Refractory entry, countdown, hold, and release convention | **partial** — Loihi supports programmable refractory behavior; secondary Brian2Loihi documentation notes that Loihi uses voltage-register behavior during refractory. Exact countdown representation is not assumed from publications alone. (`brian2loihi_michaelis_2022`) | **implemented** — Refractory is configured as 1..64 Brian2 timesteps; voltage dynamics are disabled while refractory while current continues its equation. Earlier M07 project comparison fixed the project's convention against this observable boundary. (`brian_neuron`, `brian_readme`, `project_m03_m08_brian_evidence`) | **physically_validated** — Spike tick counts as the first configured refractory tick: R_c=3 blocks t+1 and t+2 and releases at t+3; voltage holds reset while current continues to accumulate/decay. (`project_core_spec_m12`, `project_m12_record`) | **implemented** — On spike Catalyst loads the programmed refractory period directly into refractory state; each later refractory update holds/rests potential and decrements by one. This convention is not numerically identical to the project's stored-count convention without a mapping. (`catalyst_simulator`, `catalyst_core_rtl`) | `comparable after a documented transform` | `yes` |
| `weight-encoding` | Static synaptic weight representation and effective-weight reconstruction | **documented** — Secondary published Loihi documentation describes mantissa plus exponent (-8..7), excitatory/inhibitory/mixed sign modes, configurable mantissa precision, initialization quantization toward zero, scaling, and effective-weight clipping/alignment. (`brian2loihi_michaelis_2022`) | **implemented** — Implements sign modes, w_exp -8..7, num_weight_bits 0..8, mode-dependent mantissa bounds, deterministic static quantization/scaling/alignment/clipping, and w_act delivery. (`brian_synapses`, `brian_readme`, `project_m03_m08_brian_evidence`) | **physically_validated** — M08 freezes the same Loihi-style source fields into shared 16-bit format records plus 32-bit CSR synapse records; effective integer weight is deterministically reconstructed and physically consumed without re-quantization. (`project_weight_storage_m12`, `project_core_spec_m12`, `project_m12_record`) | **implemented** — N1 supports signed 16-bit pool weights and optional axon-format decoding with configurable bit width/exponent/sign behavior, plus sparse/dense/population formats. Its native encoding is not field-for-field identical to the Brian2Loihi/project M08 storage profile. (`catalyst_constants`, `catalyst_core_rtl`) | `comparable after a documented transform` | `yes` |
| `synaptic-accumulation` | Fan-in, fan-out, and accumulation of signed synaptic contributions | **documented** — Loihi supports arbitrary sparse connection topologies subject to per-core memory capacity; CUBA input is a weighted sum of delivered spike events. (`loihi_davies_2018`, `brian2loihi_michaelis_2022`) | **implemented** — Each presynaptic event executes I += w_act through Brian2 Synapses; arbitrary connection graphs/fan-in/fan-out are represented at the software-model level. (`brian_synapses`, `project_m03_m08_brian_evidence`) | **physically_validated** — Every event visits the full CSR axon row; mixed signed contributions are summed exactly in a wide temporary before a single 24-bit current-state application. Physical stress includes dense fan-in/fan-out. (`project_core_spec_m12`, `project_weight_storage_m12`, `project_m12_record`) | **implemented** — FIFO-delivered spikes traverse a CSR connectivity index/pool and accumulate per-target signed contributions; sparse/dense/population formats and multicast routing broaden fan-out options. (`catalyst_core_rtl`, `catalyst_constants`) | `comparable after a documented transform` | `yes` |
| `numeric-width-rounding-overflow` | Architectural widths, rounding points, and overflow policy | **ambiguous** — Available sources establish fixed-point/integer implementation and commonly reported current/voltage precision, but the thesis does not treat undocumented overflow/wrap/saturation micro-details as proven by the initial publications. (`loihi_davies_2018`, `brian2loihi_michaelis_2022`) | **partial** — Uses explicit integerized decay/weight calculations but Brian2 state is not a hardware-width-accurate register model; exact Loihi overflow behavior is therefore not a safe emulator claim at the interface used here. (`brian_neuron`, `brian_synapses`) | **physically_validated** — Current/voltage are signed 24-bit with explicit SAT24 saturation at frozen application points and round-away-from-zero decay. Saturation is explicitly a project-specific deterministic FPGA profile, not a Loihi claim. (`project_core_spec_m12`, `project_m12_record`) | **implemented** — RTL stores potential/current in 24-bit memories with 16-bit weights/config interfaces and explicit round-away-from-zero CUBA decay helper; many arithmetic assignments rely on Verilog width behavior rather than the project's explicit SAT24 policy. CPU reference uses NumPy int32 state. (`catalyst_core_rtl`, `catalyst_simulator`, `catalyst_constants`) | `ambiguous in available Loihi evidence` | `conditional` |
| `event-order-multiplicity` | Ordering of coincident events and preservation of repeated events | **ambiguous** — Publications establish packetized spike communication and synchronized algorithmic time, but do not provide the thesis with a complete externally observable total-order contract for coincident spike messages. (`loihi_davies_2018`) | **partial** — Brian2 executes individual synaptic events under a fixed schedule, but the pinned API does not expose a Loihi hardware event FIFO/order trace comparable to the project's ordered axon-event artifact. (`brian_readme`, `brian_synapses`) | **physically_validated** — External events precede recurrent events; multiplicity is preserved; simultaneous recurrent outputs are ordered by ascending source neuron then declaration order. M12 captures the exact sequences. (`project_core_spec_m12`, `project_recurrent_routing_m12`, `project_m12_record`) | **implemented** — Per-core delivery consumes FIFO entries and applies each event/CSR row occurrence. Inter-core ordering is mediated by Catalyst's mesh/FIFO architecture rather than the project's single-core canonical source-ID ordering. (`catalyst_core_rtl`, `catalyst_readme`) | `similar but architecturally different` | `conditional` |
| `recurrent-delivery` | When spikes become synaptic input in recurrent networks | **partial** — Loihi uses discrete algorithmic timesteps and supports nonzero synaptic delays; publications do not justify equating every implementation's internal FIFO phase with one universal recurrence convention without configuration context. (`loihi_davies_2018`) | **implemented** — Recurrent Brian2 Synapses are supported and the emulator paper includes recurrent-network examples; delivery follows the fixed LoihiNetwork/Brian schedule and configured integer delay. (`brian_readme`, `brian_synapses`, `brian2loihi_michaelis_2022`) | **physically_validated** — Spikes from tick t route only into the inactive recurrent bank and can first be consumed at t+1. Same-tick recurrence is structurally excluded and physically validated. (`project_core_spec_m12`, `project_recurrent_routing_m12`, `project_m12_record`) | **implemented** — Catalyst synchronous CPU mode delivers _pending_spikes from the previous timestep before UPDATE and stores new spikes for the next timestep. Its separate asynchronous mode can propagate intra/inter-core activity through micro-steps until quiescence within one requested timestep. (`catalyst_simulator`) | `comparable after a documented transform` | `conditional` |
| `synaptic-delay` | Programmable per-synapse/axon delay beyond the baseline timestep | **documented** — Synaptic delays are an explicit Loihi feature. (`loihi_davies_2018`) | **implemented** — LoihiSynapses exposes integer delay 0..62 timesteps. (`brian_synapses`, `brian_readme`) | **out_of_scope** — FPGA-v1 has no general programmable synaptic-delay field; its recurrent route contract only guarantees next-tick delivery. (`project_core_spec_m12`) | **implemented** — N1 exposes a 6-bit delay field with SDK MAX_DELAY=63 and a 64-bucket delay queue in the reference implementation/RTL. (`catalyst_constants`, `catalyst_simulator`, `catalyst_core_rtl`) | `out of project scope` | `no` |
| `synapse-memory-organization` | Connectivity storage organization and capacity model | **partial** — Loihi publications describe hierarchical/sparse connectivity and finite per-core memory resources, but this crosswalk does not infer undocumented SRAM bit layout from those descriptions. (`loihi_davies_2018`) | **unsupported** — Brian2Loihi models connections as Brian2 Synapses and does not emulate Loihi's physical synapse SRAM organization/capacity layout. (`brian_synapses`) | **physically_validated** — Static synapses use a project-specific CSR row table with shared format records and 32-bit synapse words; recurrent routes use a separate CSR table and two 4096-entry event banks. (`project_weight_storage_m12`, `project_recurrent_routing_m12`) | **implemented** — N1 uses a CSR-style index plus connection pool with sparse/dense/population formats. The pinned top-level RTL default pool depth is 131072 entries/core while the SDK constant uses 32768, an implementation-layer configuration difference that later comparisons must disclose rather than silently reconcile. (`catalyst_core_rtl`, `catalyst_constants`, `catalyst_readme`) | `similar but architecturally different` | `no` |
| `routing-network` | Spike routing and communication hierarchy | **documented** — Loihi has a 128-neuromorphic-core mesh with an asynchronous packet NoC, hierarchical off-chip links, and spike/management/time-synchronization messages. (`loihi_davies_2018`) | **unsupported** — The emulator represents logical synapses but does not model Loihi's physical mesh, packet routing, multicast tables, or off-chip hierarchy. (`brian_readme`, `brian_synapses`) | **out_of_scope** — FPGA-v1 is one physical core with local source-neuron to target-axon recurrent CSR routes; it has no inter-core packet network. (`project_recurrent_routing_m12`, `project_core_spec_m12`) | **implemented** — N1 documents a configurable XY mesh with multicast, up to eight inter-core route slots per source in the SDK constants, hierarchical/global routing, and a multi-chip link/router. (`catalyst_readme`, `catalyst_constants`) | `out of project scope` | `no` |
| `learning-plasticity` | Online synaptic learning and traces | **documented** — Programmable on-chip synaptic learning rules are a defining Loihi feature, using local state/traces and programmable learning behavior. (`loihi_davies_2018`, `loihi_lin_2018`) | **implemented** — Supports user learning-rule expressions over selected pre/post traces and periodic variables; trace and plastic-weight updates include stochastic rounding approximations, which the authors note can differ slightly from Loihi trace realizations. (`brian_synapses`, `brian2loihi_michaelis_2022`) | **out_of_scope** — M12 FPGA-v1 intentionally freezes static weights only; no plastic synaptic state or learning engine is implemented. (`project_weight_storage_m12`, `project_core_spec_m12`) | **implemented** — N1 provides STDP, trace state, two/three-factor paths, eligibility/reward modulation, and a programmable microcode learning engine in the pinned software/RTL. (`catalyst_readme`, `catalyst_simulator`, `catalyst_core_rtl`) | `out of project scope` | `no` |
| `management-host-control` | Configuration, run control, and management processors/interfaces | **documented** — Loihi integrates three embedded x86 management cores and allows host/on-chip management messages to configure/read neuromorphic cores and coordinate execution. (`loihi_davies_2018`, `loihi_lin_2018`) | **unsupported** — Brian2Loihi exposes Python/Brian network construction and run control, not Loihi management cores or host-transport architecture. (`brian_readme`) | **physically_validated** — Research validation uses Python host tooling plus Vivado/JTAG VIO around a K26 PS/PL design. This is an experimental control/trace interface, not an emulation of Loihi x86 management architecture. (`project_m12_record`) | **implemented** — N1 documents an RV32IM RISC-V management cluster and host paths including UART, AXI-Lite/F2, and PCIe MMIO; SDK backends expose common deployment/control APIs. (`catalyst_readme`, `catalyst_constants`) | `similar but architecturally different` | `no` |
| `multicore-noc` | Core count, core capacity, NoC, and multi-chip scaling | **documented** — Loihi integrates 128 neuromorphic cores with asynchronous on-chip communication and hierarchical extension to other chips. (`loihi_davies_2018`) | **unsupported** — The emulator does not expose a physical multicore placement/NoC execution model corresponding to Loihi silicon. (`brian_readme`) | **out_of_scope** — The validated FPGA-v1 implementation is a single core with a physical profile up to 256 neurons, 1024 axons, and local recurrent routing. (`project_recurrent_routing_m12`, `project_m12_record`) | **implemented** — Pinned N1 top-level specification is 128 cores x 1024 neurons = 131072 neurons with configurable mesh multicast and multi-chip routing. The separate K26 reproduction profile is smaller and must not be conflated with the full architecture. (`catalyst_readme`, `catalyst_constants`) | `out of project scope` | `no` |
| `observability-debug` | State, spike, event, and performance observability | **partial** — Published architecture/programming material supports core management/readback and host tooling, but does not provide the same lossless per-tick trace contract defined by this thesis. (`loihi_davies_2018`, `loihi_lin_2018`) | **implemented** — LoihiStateMonitor and LoihiSpikeMonitor expose software state variables and spikes through Brian2, suitable for observable emulator traces but not physical hardware-internal queues. (`brian_readme`) | **physically_validated** — M12 exposes committed tick, ordered external/recurrent/routed events, signed synaptic sums, pre/post state, spikes, queue-bank metadata, faults, and passive cycle characterization through a reproducible physical trace path. (`project_core_spec_m12`, `project_m12_record`) | **implemented** — Pinned core RTL exposes probe IDs for potential, threshold, traces, refractory, accumulators, dendrites, leak/resting, weight, eligibility, current, performance counters, and trace FIFO state; the SDK provides result/spike APIs. (`catalyst_core_rtl`, `catalyst_simulator`) | `comparable after a documented transform` | `conditional` |
| `async-execution` | Asynchronous/event-driven execution versus synchronous algorithmic timestep | **documented** — Loihi combines fixed-size synchronized algorithmic timesteps for SNN dynamics with an asynchronous hardware NoC/implementation methodology; asynchronous physical communication is not equivalent to abandoning algorithmic time. (`loihi_davies_2018`) | **unsupported** — The emulator requires a fixed Brian2 clock and LoihiNetwork schedule and does not model asynchronous NoC/GALS micro-steps. (`brian_readme`, `brian_neuron`) | **out_of_scope** — FPGA-v1 is clocked synchronous RTL implementing an atomic discrete algorithmic tick; event-dependent work is serialized but not asynchronous/GALS. (`project_core_spec_m12`, `project_m12_record`) | **implemented** — Catalyst CPU reference provides both synchronous DELIVER->UPDATE->LEARN and a separate async mode that iterates active cores/micro-steps to quiescence; the architecture also includes asynchronous-style NoC work in dedicated modules. (`catalyst_simulator`, `catalyst_readme`) | `out of project scope` | `no` |

## Major findings before normalization

- Catalyst's pinned CPU reference and RTL expose more than one neuron-update regime; M13.3 must choose a comparison boundary rather than treating Catalyst as one undifferentiated model.
- Project and Brian2Loihi use strict threshold > while Catalyst's main pinned CPU/RTL paths use >=.
- Catalyst RTL CUBA current/voltage ordering differs from the project's M12 input-before-decay/current-into-voltage ordering and therefore requires an explicit mapping/probe.
- Project refractory duration and Catalyst's raw refractory register use different entry/countdown conventions; compare next-eligible timestep rather than raw count.
- The project intentionally omits dendritic compartments, programmable delays, learning, multicore NoC, and management processors that Loihi/Catalyst support.
- Catalyst's pinned top-level RTL default synapse pool depth and SDK pool-depth constant differ, so capacity comparisons must identify the exact implementation layer/configuration.
- The project is synchronous at the RTL level and discrete-timestep architecturally; Catalyst additionally exposes asynchronous quiescence execution. Loihi's asynchronous NoC does not by itself imply asynchronous algorithmic neuron time.

## M13.3 handoff by feature

The following actions are intentionally phrased as **normalization questions**, not corrections to any implementation:

- **neuron-state-model** — Normalize a point-neuron state subset and explicitly choose Catalyst simple-LIF versus RTL CUBA mode rather than mixing them.
- **dendritic-compartments** — Exclude dendritic features from common behavioral probes; document as a major scope difference.
- **current-voltage-decay** — Freeze which Catalyst execution boundary represents CUBA comparison and specify the one-tick/current-source mapping before probes.
- **tick-update-order** — Normalize only committed timestep boundaries; do not equate internal phase names or hardware cycle counts.
- **threshold-reset** — Define threshold-unit transforms and preserve the > versus >= convention as an explicit semantic difference for M13.4.
- **refractory-semantics** — Freeze a semantic 'next eligible tick' mapping rather than equating raw refractory register values.
- **weight-encoding** — Normalize by final delivered signed integer contribution first; preserve native encoding metadata separately.
- **synaptic-accumulation** — Use small sparse fan-in/fan-out networks with normalized effective weights and no optional dendritic/graded behavior.
- **numeric-width-rounding-overflow** — Keep ordinary probes away from overflow; treat finite-width boundary probes as architecture-specific comparisons unless stronger Loihi evidence is added.
- **event-order-multiplicity** — Compare multiplicity and final per-target accumulation where deterministic; do not normalize a global total event order unless each backend exposes one.
- **recurrent-delivery** — Use Catalyst synchronous mode for next-timestep recurrence comparisons; treat async quiescence behavior as a separate architecture feature.
- **synaptic-delay** — Exclude programmable delays from common subset; zero/minimal-delay recurrence remains separately comparable.
- **synapse-memory-organization** — Normalize network graphs, not memory addresses/layouts; retain native capacity/configuration metadata for M13.5.
- **routing-network** — Common behavioral tests stay within one logical core unless M13.5 deliberately studies network-level implementation differences.
- **learning-plasticity** — Exclude plasticity from common behavioral subset; discuss it as an intentional scope limitation and broader Catalyst/Loihi capability.
- **management-host-control** — Keep management/control outside neuronal trace normalization; use it only as implementation-context metadata.
- **multicore-noc** — Restrict behavioral common subset to single-core/local behavior; reserve multicore/resource comparisons for M13.5 with explicit capacities.
- **observability-debug** — Normalize only shared architectural quantities while preserving richer native traces from each implementation.
- **async-execution** — Use Catalyst synchronous mode for common-subset behavior; document async mode as an architectural extension rather than trying to emulate it in FPGA-v1.

## Source registry

Every crosswalk cell cites one or more stable source IDs below. Repository sources are commit-pinned; published sources use DOI identity. Source-code readings are labeled as implementation inference in the JSON rather than silently promoted to published architectural fact.

### `loihi_davies_2018`

- Identity: loihi_davies_2018: DOI 10.1109/MM.2018.112130359
- Evidence type: `published_documentation`
- Locator: Sections 2.1 and 3.1
- Role: Primary Loihi architecture source: CUBA LIF with current/potential state, fixed discrete timesteps, 128 neuromorphic cores, asynchronous NoC, hierarchical connectivity, dendritic compartments, synaptic delays, programmable learning, and embedded x86 management.

### `loihi_lin_2018`

- Identity: loihi_lin_2018: DOI 10.1109/MC.2018.157113521
- Evidence type: `published_documentation`
- Locator: architecture/programming discussion
- Role: Primary published programming/toolchain context for Loihi management, configuration, and programmable learning.

### `brian2loihi_michaelis_2022`

- Identity: brian2loihi_michaelis_2022: DOI 10.3389/fninf.2022.1015624
- Evidence type: `published_documentation`
- Locator: Sections 2.2, 3.1, 4.1 and Appendix
- Role: Secondary published source for Loihi/Brian2Loihi discrete current/voltage equations, weight mantissa/exponent/sign/precision behavior, refractory representation, and emulator validation.

### `project_core_spec_m12`

- Identity: project_core_spec_m12: `Xtimetraveler-Prime/Thesis@80a502ec6dfc4c8d61372089b08c9a584ad65f85` `Neuromorphic Digital Twin/docs/CORE_SPECIFICATION.md`
- Evidence type: `published_documentation`
- Role: Normative M10/M12 project behavioral contract.

### `project_weight_storage_m12`

- Identity: project_weight_storage_m12: `Xtimetraveler-Prime/Thesis@80a502ec6dfc4c8d61372089b08c9a584ad65f85` `Neuromorphic Digital Twin/docs/FPGA_WEIGHT_STORAGE.md`
- Evidence type: `published_documentation`
- Role: Frozen M08 static-weight encoding and CSR storage profile.

### `project_recurrent_routing_m12`

- Identity: project_recurrent_routing_m12: `Xtimetraveler-Prime/Thesis@80a502ec6dfc4c8d61372089b08c9a584ad65f85` `Neuromorphic Digital Twin/docs/M11_5_4_RECURRENT_ROUTING.md`
- Evidence type: `direct_observation`
- Role: Validated CSR route ordering, multiplicity, double-buffer queues, and next-tick recurrence.

### `project_m12_record`

- Identity: project_m12_record: `Xtimetraveler-Prime/Thesis@80a502ec6dfc4c8d61372089b08c9a584ad65f85` `MILESTONES.md`
- Evidence type: `direct_observation`
- Role: Physical FPGA conformance and characterization record through M12.

### `brian_readme`

- Identity: brian_readme: `sagacitysite/brian2_loihi@d54676cb113e48dc886615a0b589bb0e4bccbca4` `README.md`
- Evidence type: `published_documentation`
- Role: Pinned emulator API, supported Loihi parameters, monitor model, and schedule constraints.

### `brian_neuron`

- Identity: brian_neuron: `sagacitysite/brian2_loihi@d54676cb113e48dc886615a0b589bb0e4bccbca4` `loihi_neuron_group.py`
- Evidence type: `implementation_inference`
- Role: Pinned point-neuron equations: v/I state, decay round-away-from-zero construction, strict threshold, hard reset, and refractory scheduling.

### `brian_synapses`

- Identity: brian_synapses: `sagacitysite/brian2_loihi@d54676cb113e48dc886615a0b589bb0e4bccbca4` `loihi_synapses.py`
- Evidence type: `implementation_inference`
- Role: Pinned static/plastic weight encoding, sign modes, exponent, precision, clipping, delays, traces, and synaptic delivery.

### `catalyst_readme`

- Identity: catalyst_readme: `catalyst-neuromorphic/catalyst-n1@1806bb4b4114d7671e5648fa75b7b83b3a8d5543` `README.md`
- Evidence type: `published_documentation`
- Role: Pinned top-level N1 specifications, NoC/management/host architecture, learning claims, FPGA targets, and SDK backends.

### `catalyst_constants`

- Identity: catalyst_constants: `catalyst-neuromorphic/catalyst-n1@1806bb4b4114d7671e5648fa75b7b83b3a8d5543` `sdk/neurocore/constants.py`
- Evidence type: `implementation_inference`
- Role: Pinned SDK capacities, formats, delay range, learning constants, and command IDs.

### `catalyst_simulator`

- Identity: catalyst_simulator: `catalyst-neuromorphic/catalyst-n1@1806bb4b4114d7671e5648fa75b7b83b3a8d5543` `sdk/neurocore/simulator.py`
- Evidence type: `implementation_inference`
- Role: Pinned Catalyst CPU reference: synchronous DELIVER->UPDATE->LEARN mode, separate asynchronous quiescence mode, refractory/threshold behavior, pending-spike delivery, and learning.

### `catalyst_core_rtl`

- Identity: catalyst_core_rtl: `catalyst-neuromorphic/catalyst-n1@1806bb4b4114d7671e5648fa75b7b83b3a8d5543` `rtl/scalable_core_v2.v`
- Evidence type: `implementation_inference`
- Role: Pinned N1 core RTL: 24-bit neuron/current memories, 16-bit data/weights, optional 12-bit CUBA decays/bias, CSR synapses, compressed formats, FIFO delivery, refractory/threshold rules, probes, traces, and learning FSMs.

### `project_m03_m08_brian_evidence`

- Identity: project_m03_m08_brian_evidence: `Xtimetraveler-Prime/Thesis@80a502ec6dfc4c8d61372089b08c9a584ad65f85` `MILESTONES.md`
- Evidence type: `direct_observation`
- Locator: M03-M08 completion evidence, especially M05, M07, and M08.3
- Role: Project-owned direct observations against Brian2Loihi: M05 current-decay ordering probe; M07 12/12 directed current/voltage/spike conformance across 34 ticks; M08.3 15/15 encoded-weight conformance including direct w_act comparison.

## Scope conclusions from M13.2

The four-way common subset is narrower than any one implementation. Point-neuron LIF behavior, threshold/reset/refractory behavior, static signed synaptic drive, sparse fan-in/fan-out, and synchronous multi-tick recurrence are plausible common comparison targets, but several require explicit transforms. The project deliberately does not claim Loihi/Catalyst parity for dendritic trees, programmable delays, online learning, multicore NoC, management processors, or asynchronous quiescence execution.

Catalyst must not be treated as one undifferentiated reference model: the pinned CPU simulator and RTL expose different update/configuration surfaces, and the RTL itself contains both a simple subtractive-leak path and an optional CUBA path. M13.3 must therefore name the exact Catalyst boundary used by each normalized behavior.

The strongest semantic questions handed to M13.3/M13.4 are the current/voltage update ordering, strict `>` versus Catalyst `>=` threshold comparison, refractory-count convention, native weight encoding transforms, and what event-order information can be compared without inventing a global ordering contract.

## M13.2 pass boundary

M13.2 is ready to close when this generated document and its machine-readable source agree, all 15 milestone feature classes are present, every one of the four columns is source-backed in every row, and the full project regression suite remains green. No behavioral differential result is required by M13.2 itself.
