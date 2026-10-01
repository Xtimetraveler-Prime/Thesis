# Loihi Digital Twin v2 Development Roadmap

## Purpose

This document is the development and acceptance tracker for FPGA-v2. The normative architecture contract remains:

```text
Loihi_Digital_Twin/v2/docs/LOIHI1_TARGET_SPEC.md
```

The preserved FPGA-v1 development history remains under `Loihi_Digital_Twin/v1/`; FPGA-v2 is a separate source-backed architectural twin.

Status meanings:

- **Complete** — all required deliverables and completion criteria are satisfied.
- **In progress** — active work has started, but one or more required deliverables remain.
- **Planned** — agreed work that has not yet started.
- **Blocked** — waiting on an unresolved dependency or decision.
- **Deferred** — intentionally outside the current critical path.

---

## Current phase

> **All planned FPGA-v2 phases P00-P08 are complete.**
>
> P08 closed on 2026-09-30 after independent reproduction of the final P08.5.3
> closure gate. The final run reported 19 passing tests and deterministic closure
> fingerprint
> `135bdc7f64955972cab11472e5b4ada7d16c62a0bbd5ace8051d424988d81cce`.
>
> The final P08 application is a source-bounded reconstruction of the NxTF
> frame-based MNIST benchmark with 4,218 neurons, 7,006 trainable parameters,
> 338,880 expanded convolutional connections, and a 100-timestep primary horizon.
> The accepted converted deployment uses five project logical cores, three
> resident K26 context slots, and one P03-compatible HLS compute engine.
>
> Frozen official-test results are 98.74% ANN accuracy and 98.24% SNN accuracy,
> a 0.50 percentage-point ANN-to-SNN drop. Complete 100-timestep five-over-three
> paging is proven at the compiled architectural boundary. A representative real
> MNIST logical-core-4 state at timestep 99 was physically paged into resident
> slot 0 on the K26 and reproduced all 618 compartment states/traces, packet
> image, and ten-class output evidence exactly.
>
> The final NxTF comparison remains bounded: exact unpublished paper topology,
> native storage equivalence, direct Loihi-vs-K26 energy/latency equivalence,
> physical asynchronous-circuit equivalence, and a complete end-to-end JTAG
> replay are not claimed.

---

## Phase summary

| ID | Phase | Status | Started | Completed |
|---|---|---|---|---|
| P00 | Preserve and freeze FPGA-v1 baseline | Complete | 2026-09 | 2026-09-25 |
| P01 | Define Loihi-1 target and establish v2 project structure | Complete | 2026-09-28 | 2026-09-28 |
| P02 | Build separate Python manycore golden model | Complete | 2026-09-28 | 2026-09-28 |
| P03 | Implement and validate one FPGA-v2 logical core | Complete | 2026-09-28 | 2026-09-28 |
| P04 | Add multicore packet routing and timestep/barrier semantics | Complete | 2026-09-28 | 2026-09-29 |
| P05 | Add logical-core virtualization | Complete | 2026-09-29 | 2026-09-29 |
| P06 | Build deterministic mapper/compiler and deployment format | Complete | 2026-09-29 | 2026-09-29 |
| P07 | Validate deeper mapped multicore SNNs | Complete | 2026-09-29 | 2026-09-29 |
| P08 | Emulate and compare the NxTF frame-based MNIST workload | Complete | 2026-09-29 | 2026-09-30 |

---

# P00 — Preserve and freeze FPGA-v1 baseline

**Status:** Complete  
**Completed:** 2026-09-25

FPGA-v1 and its first MNIST application are preserved as historical controls. The first architecture lives under `Loihi_Digital_Twin/v1/`; the preserved application lives under `applications/mnist_baseline/`; the immutable source tag is `fpga-v1-mnist-v1-final`.

---

# P01 — Loihi-1 target definition and v2 project foundation

**Status:** Complete  
**Completed:** 2026-09-28

P01 established the separate v2 project and the source-backed Loihi-1 target specification. The project explicitly targets architectural fidelity rather than transistor-level or proprietary implementation equivalence. Logical Loihi-like resources, packets, timestep/barrier semantics, virtualization invariance, observability, and unsupported/unknown behavior are defined independently from physical FPGA implementation.

Primary record: `docs/LOIHI1_TARGET_SPEC.md`.

---

# P02 — Separate Python manycore golden model

**Status:** Complete  
**Completed:** 2026-09-28

P02 established the independent Python manycore architecture package under `src/loihi_twin_v2/`, including explicit logical cores, axons, shared synapse templates, output routes, spike packets, event queues, resource limits, deterministic traces, deployment serialization/fingerprints, and barrier semantics. Directed architecture tests T1-T9 passed before hardware work; T10 was completed physically during P03.

Primary records: `docs/P02_IMPLEMENTATION_NOTES.md` and `docs/P02_DEPLOYMENT_SCHEMA.md`.

---

# P03 — One FPGA-v2 logical core

**Status:** Complete  
**Completed:** 2026-09-28

P03 implemented one full-capacity FPGA-v2 logical core around the source-backed Python boundary and validated it physically on the K26. The accepted hardware profile uses signed 24-bit saturating compartment state and retains transparent host/debug access to the hardware memory image. The accepted directed physical corpus matched Python state, traces, packets, spike counts, packet counts, and status.

Primary records: `docs/P03_ONE_CORE_HARDWARE_BOUNDARY.md`, `docs/P03_VIVADO_IMPLEMENTATION.md`, and `docs/P03_INTEGRATION_CHALLENGES.md`.

---

# P04 — Multicore packet routing and timestep/barrier semantics

**Status:** Complete  
**Completed:** 2026-09-29

P04 added explicit multicore packet routing, simultaneous source handling, backpressure, local/remote traffic accounting, and quiescence/barrier semantics. The resource-scaled physical validation shell preserved the full logical capacity contract and passed directed K26 conformance under legal packet-service orderings.

Primary records: `docs/P04_MULTICORE_ARCHITECTURE.md`, `docs/P04_INTEGRATION_IMPLEMENTATION.md`, and `docs/P04_INTEGRATION_CHALLENGES.md`.

---

# P05 — Logical-core virtualization

**Status:** Complete  
**Completed:** 2026-09-29

P05 separated logical-core identity from physical compute-engine identity and built the accepted K26 virtualization shell with three independently retained full logical contexts over one HLS compute engine. The final shell uses 47 URAM288s, two BRAM tiles, and two DSPs, and preserves logical state/packet semantics under legal context-service orders.

Primary records: `docs/P05_VIRTUALIZATION_ARCHITECTURE.md` and `docs/P05_INTEGRATION_CHALLENGES.md`.

---

# P06 — Deterministic mapper/compiler and deployment format

**Status:** Complete  
**Completed:** 2026-09-29

P06 established the deterministic high-level network-to-deployment compiler. It partitions populations, allocates compartments/axons/routes/synapse templates, enforces modeled Loihi-like capacities, records placement and occupancy, emits deterministic fingerprints, and feeds the same deployment to Python and FPGA image generation.

The project synapse-storage model is explicitly project-defined and is not claimed to be native Loihi SRAM packing.

Primary records: `docs/P06_MAPPING_COMPILER.md` and `docs/P06_MAPPING_COMPILER_CHALLENGES.md`.

---

# P07 — Deeper mapped multicore SNN validation

**Status:** Complete  
**Completed:** 2026-09-29

P07 demonstrated a compiler-generated six-layer/12-neuron SNN across three logical cores, including local and remote traffic, supported sharing, deterministic placement, expected capacity rejection, legal service-order invariance, and physical K26 conformance. All 42 directed physical ticks passed.

Primary records: `docs/P07_DEEP_SNN_VALIDATION.md` and `docs/P07_DEEP_SNN_CHALLENGES.md`.

---

# P08 — NxTF frame-based MNIST emulation and comparison

**Status:** Complete  
**Started:** 2026-09-29  
**Realigned:** 2026-09-29  
**Completed:** 2026-09-30

## Goal

Emulate the frame-based MNIST workload reported in Rueckauer et al. NxTF as closely as public evidence and FPGA-v2 permit, run that workload through the deterministic P06 → Python → FPGA path, and make a bounded source-aware comparison of accuracy, topology/resource pressure, connection sharing, logical/physical virtualization, traffic, FPGA execution observations, and implementation resources.

P08 is not a claim of exact unpublished-model reproduction. Source fidelity and explicit uncertainty take priority over forcing numerical agreement.

Primary experiment/source records:

```text
docs/P08_MNIST_COMPARISON_CONTRACT.md
docs/P08_NXTF_SOURCE_AUDIT.md
docs/P08_NXTF_RECONSTRUCTION.md
```

## Published NxTF anchors

The NxTF paper reports for its frame-based MNIST benchmark:

- four convolutional layers;
- approximately 4k neurons and 7k trainable parameters;
- approximately 341k discrete convolutional connections represented by 6,746 shared weights;
- 14 Loihi neurocores after NxTF mapping;
- SNN Toolbox rate-based ANN→SNN conversion;
- 100 algorithmic timesteps/sample;
- 0.74% ANN error and 0.79% converted-SNN error;
- 0.66 mJ/sample and 6.65 ms/sample on native Loihi.

The surviving public Intel NxTF tutorial is a different 16→32→64→10, 33,802-parameter, 512-timestep example and is used only as source-style evidence.

## P08.1 — NxTF source reconstruction and experiment freeze — **Complete**

Accepted source-bounded project reconstruction:

```text
28x28x1
 -> Conv2D(14, 5x5, stride 2, valid) -> 12x12x14
 -> Conv2D(20, 3x3, stride 1, valid) -> 10x10x20
 -> Conv2D(12, 3x3, stride 2, valid) ->  4x4x12
 -> Conv2D(10, 4x4, stride 1, valid) ->  1x1x10
```

Accepted totals:

```text
neurons:                 4,218
convolution weights:     6,950
bias parameters:            56
trainable parameters:    7,006
expanded connections: 338,880
primary timesteps:          100
```

The exact unpublished NxTF benchmark layer dimensions/checkpoint were not recovered and remain `UNKNOWN_NOT_CLAIMED`.

## P08.2 — FPGA-v2 adaptation and context paging — **Complete**

The frozen graph compiles through P06 under unchanged logical per-core limits to:

```text
logical/backing cores: 5
resident K26 contexts: 3
physical HLS engines:  1
expanded connections: 338,880
external ingress routes: 2,187
P06 stored shared parameters: 64,235
static output routes: 7,860
```

The deterministic paging layer preserves logical IDs, backing state, current/next event semantics, packet destination identity, and the global algorithmic barrier independently from physical residency. The host owns cross-page routing and the global barrier.

The NxTF paper's 14 Loihi neurocores and the project's five P06 logical cores remain intentionally contextual because P06 is not the NxTF compiler and the project's storage/sharing model is not native Loihi packing.

## P08.3 — ANN training and source-recovered ANN→SNN conversion — **Complete**

The accepted ANN checkpoint achieved:

```text
validation accuracy: 0.992600
best epoch:          13
semantic weights fingerprint:
e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce
```

Source recovery of Intel's public NxTF/SNN-Toolbox backend established the required per-layer parameter/threshold normalization and softmax voltage-readout behavior.

Accepted source-recovered thresholds:

```text
input BIAS threshold: 2040
conv1 threshold:       556
conv2 threshold:       512
conv3 threshold:       672
conv4 readout:         final membrane voltage
conv4 suppress-spike threshold: 131071
```

Accepted converted artifact identities:

```text
parameters = 9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e
network    = 6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13
compiled   = 5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

Frozen validation measurement:

```text
examples:      5,000
timesteps:     100
SNN accuracy:  0.984400
ANN reference: 0.992600
delta:         0.008200
ties:          0
```

No official-test examples were used during P08.3.

## P08.4 — Official-test evaluation and K26 conformance — **Complete**

Official test result:

```text
examples:            10,000
ANN accuracy:        0.987400
SNN accuracy:        0.982400
ANN-SNN delta:       0.005000
SNN readout ties:    1
post-test selection: 0
```

Representative official-test frame fixed by index:

```text
test index: 0
label:      7
timesteps:  100
```

Unpaged logical execution, forward paging, and reverse paging produced identical normalized trace fingerprint:

```text
a81844443b6e5f6c278167a4aafc46dcfd74f7df5498179312b1fc39edba09d6
```

and identical final evidence:

```text
[-284, -1203, 104, 109, -2253, -599, -2659, 1446, -436, -63]
```

Paging/traffic observations:

```text
forward page loads/evictions: 497 / 497
reverse page loads/evictions: 499 / 499
ingress packets:              2,382
internal packet traffic:     17,910
```

The host-paged K26 shell routed at the requested 100 MHz with:

```text
WNS:  +0.734 ns
WHS:  +0.010 ns
URAM: 47
logical backing contexts: 5
resident context slots:   3
physical engines:         1
```

Accepted physical artifacts:

```text
bitstream SHA-256 = 3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83
probes SHA-256    = e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
```

The representative physical MNIST run paged logical core 4 into resident slot 0 at timestep 99 and observed:

```text
input events:           2
compartments checked: 618
dispatch cycles:     3,865
state/trace exact:   true
packet image exact:  true
output evidence exact:true
prediction:             7
```

P08.4 proves complete 100-timestep paging semantics in compiled software plus physical conformance of a real deep-network page replacement/dispatch on the K26. It does **not** claim that the complete approximately-500-dispatch representative inference was replayed end-to-end over JTAG.

Primary records: `docs/P08_4_ACCEPTANCE.md`, `docs/P08_4_3A_ACCEPTANCE.md`, and `docs/P08_4_3B_ACCEPTANCE.md`.

## P08.5 — NxTF comparison and closure — **Complete**

### P08.5.1 — Comparison ledger and comparability classification — **Complete**

Independent reproduction passed with six tests. Accepted ledger fingerprint:

```text
574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d
```

The 24-row ledger freezes these comparison classes:

```text
DIRECTLY_COMPARABLE=3
COMPARABLE_WITH_RECONSTRUCTION_CAVEAT=7
CONTEXT_ONLY=2
PROJECT_SPECIFIC=10
NOT_COMPARABLE=2
```

Energy/latency, shared-weight accounting, mapped-core accounting, dispatch latency scope, full-JTAG-replay scope, and post-test-tuning guardrails are enforced programmatically.

### P08.5.2 — Final comparison table and quantitative interpretation — **Complete**

Independent reproduction passed with 13 tests. Accepted report fingerprint:

```text
d3d47e95f928f0de77d2c1b59c2c16f5becdf5dd443f6600c187d3f56e1e68a0
```

Accepted reconstruction-bounded quantitative differences:

```text
ANN test-error gap:              0.52 percentage points
SNN test-error gap:              0.97 percentage points
ANN-to-SNN conversion-loss gap: 0.45 percentage points
```

The approximately 4k-neuron, 7k-parameter, and 341k-connection paper values are treated as scale correspondence only. NxTF shared-weight counts and Loihi neurocore counts remain contextual because their representation/compiler boundaries differ from P06.

Native-Loihi 0.66 mJ/sample and 6.65 ms/sample remain published context; no direct FPGA-versus-Loihi energy or latency conclusion is drawn.

### P08.5.3 — Final P08 closure — **Complete**

Independent reproduction passed with 19 tests. Accepted closure fingerprint:

```text
135bdc7f64955972cab11472e5b4ada7d16c62a0bbd5ace8051d424988d81cce
```

The pre-acceptance closure candidate intentionally recorded `p08_complete=false`; independent reproduction satisfied that final condition, and `docs/P08_5_3_ACCEPTANCE.md` is the authoritative post-reproduction acceptance record.

The final non-claim set remains:

```text
exact_paper_topology = false
native_storage_equivalence = false
energy_direct = false
latency_direct = false
shared_weight_ratio = false
mapped_core_ratio = false
dispatch_is_sample_latency = false
full_jtag_replay = false
physical_async_equivalence = false
post_test_tuning = false
```

## Stable P08 data boundary

```text
MNIST source image:       28 x 28 uint8
official training split:  60,000 images
validation split:          deterministic stratified 5,000 images
training remainder:        55,000 images
official test split:       10,000 images
validation seed:           0x4D4E4953
primary horizon:           100 algorithmic timesteps
```

The official test split was not used for topology selection, checkpoint selection, conversion calibration, threshold selection, timestep selection, or decoder selection.

## P08 completion gate

**Satisfied.** P08 closes with all eight completion conditions met:

1. the paper workload is reconstructed as far as public evidence supports and remaining gaps are explicitly labeled;
2. the source-bounded graph compiles through P06 under unchanged logical limits;
3. five-over-three context paging is explicitly implemented and proven invariant;
4. ANN training and ANN→SNN conversion are frozen without official-test tuning;
5. full official-test ANN and SNN accuracy are recorded;
6. exact compiled paging conformance and representative physical K26 conformance pass;
7. logical occupancy, residency/engine count, sharing/accounting, traffic, FPGA cycles/resources, and relevant capacity boundaries are reported; and
8. the final comparison distinguishes direct measurements, sourced reference facts, reconstruction choices, project-specific implementation quantities, contextual values, and non-comparable metrics.

---

# Cross-phase architectural requirements

The accepted v2 architecture retains:

- multiple explicit logical neuromorphic cores;
- per-core compartment, input-axon, synapse, and routing resources;
- enforced Loihi-like logical capacity limits;
- destination-core / destination-axon packets;
- inter-core fanout and routing;
- deterministic placement and mapping;
- algorithmic timestep/barrier semantics independent of raw FPGA clock cycles;
- supported sharing or an explicitly modeled project equivalent;
- inspectable configuration/state/packet/spike/resource traces;
- deeper mapped feed-forward SNN execution; and
- one deterministic compiler/deployment artifact consumed by both Python and FPGA.

The project remains a **source-backed architectural digital twin**, not a transistor-level clone. Physical asynchronous-circuit equivalence, proprietary NxSDK/NxTF micro-encoding, exact native-Loihi memory packing, and undocumented implementation details are not claimed.

---

# Deferred/follow-on fidelity extensions

The following are now follow-on research opportunities rather than unfinished P00-P08 work:

- richer dendritic/multi-compartment structures;
- broader programmable delays;
- broader native weight/compression formats;
- more detailed congestion/asynchronous/quiescence models;
- on-chip learning/plasticity;
- management-processor emulation;
- chip-to-chip scaling;
- equivalent end-to-end K26 energy/latency instrumentation;
- complete physical replay of every paged dispatch for the representative MNIST sample; and
- recovery of any additional unpublished NxTF benchmark details if they become available.

Insufficiently evidenced features remain unknown/not claimed.

---

# Final documentation and evidence structure

```text
Loihi_Digital_Twin/v2/
├── LOIHI_TWIN_ROADMAP.md
├── docs/
│   ├── LOIHI1_TARGET_SPEC.md
│   ├── P02...P07 phase records
│   ├── P08_MNIST_COMPARISON_CONTRACT.md
│   ├── P08_NXTF_SOURCE_AUDIT.md
│   ├── P08_NXTF_RECONSTRUCTION.md
│   ├── P08_2_ACCEPTANCE.md
│   ├── P08_3_ACCEPTANCE.md
│   ├── P08_4_ACCEPTANCE.md
│   ├── P08_5_1_ACCEPTANCE.md
│   ├── P08_5_2_ACCEPTANCE.md
│   └── P08_5_3_ACCEPTANCE.md
├── src/loihi_twin_v2/
├── hls/core_v2/
├── rtl/
├── vivado/
├── hardware/
│   └── evidence/
├── tests/
├── scripts/
└── examples/

applications/
├── mnist_baseline/
└── mnist_v2_nxtf/
```

Accepted FPGA-v2 evidence is referenced from the corresponding phase records and does not rewrite the frozen FPGA-v1 history.

---

# Advancement rule

All planned P00-P08 phases are complete. There is no active unfinished phase in this roadmap. Any subsequent architecture extensions, measurements, or experiments should begin as explicitly named follow-on work rather than silently reopening a completed phase.
