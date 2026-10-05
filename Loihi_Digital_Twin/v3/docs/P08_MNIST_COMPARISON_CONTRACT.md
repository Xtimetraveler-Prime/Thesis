# P08 NxTF MNIST Emulation and Comparison Contract

## Purpose

P08 is the final application phase for FPGA-v2. Its goal is no longer to build an
arbitrary MNIST network with a vaguely similar parameter count. P08 must instead
**emulate the frame-based MNIST work reported by Rueckauer et al. in NxTF as
closely as public source evidence and the FPGA-v2 framework permit**, then make
all unavoidable differences explicit.

The experiment must exercise the architecture already established through P07:

- the P02 manycore architectural model;
- the P03 compartment/axon/synapse execution core;
- the P04 packet/barrier semantics;
- the P05 logical-core virtualization boundary;
- the P06 deterministic mapper/compiler and deployment format; and
- the P07 deeper mapped-network validation path.

P08 may extend those mechanisms where a source-faithful NxTF workload exposes a
real limitation. In particular, the accepted P05 shell's three resident full
contexts are a physical retention limit, **not** permission to shrink the P08
network until it fits three logical cores.

The detailed source audit and reconstruction state are maintained in:

```text
Loihi_Digital_Twin/v2/docs/P08_NXTF_SOURCE_AUDIT.md
```

---

## Primary reference

Bodo Rueckauer, Connor Bybee, Ralf Goettsche, Yashwardhan Singh, Joyesh Mishra,
and Andreas Wild, "NxTF: An API and Compiler for Deep Spiking Neural Networks on
Intel Loihi," ACM Journal on Emerging Technologies in Computing Systems 18(3),
2022. DOI: `10.1145/3501770`. Preprint: `arXiv:2101.04261`.

For the paper's frame-based MNIST experiment, the published material reports:

- a four-layer CNN trained in Keras;
- ANN classification error of 0.74%;
- ANN-to-SNN conversion using the SNN Toolbox rate-based method;
- 100 algorithmic timesteps per MNIST sample on Loihi;
- approximately 4k neurons and 7k trainable parameters in Table 2;
- converted-SNN error of 0.79% in Table 2;
- 14 Loihi neurocores after NxTF mapping;
- 341k discrete convolutional connections versus 6,746 shared weights when
  exploiting connection sharing;
- 0.66 mJ/sample and 6.65 ms/sample for that native-Loihi experiment.

Those values are the primary quantitative anchors for P08. The exact layer-wise
filter counts/kernel sizes/strides for the ~7k-parameter paper benchmark must not
be invented if they cannot be recovered from a source.

Native-Loihi energy and wall-clock latency are retained only as published context.
P08 does not claim direct comparability of those physical measurements to the K26
unless a separate, defensible measurement methodology is established.

---

## Surviving public NxTF MNIST implementation evidence

The public Intel NRC ecosystem repository contains an NxTF MNIST tutorial at:

```text
intel-nrc-ecosystem/models
nxsdk_modules_ncl/dnn/tutorials/a_image_classification_mnist.ipynb
```

That tutorial defines an all-convolutional ANN/SNN:

```text
28 x 28 x 1
  -> Conv2D(16, 5x5, stride 2, ReLU)
       output 12 x 12 x 16
  -> Dropout(0.1) during ANN training
  -> Conv2D(32, 3x3, ReLU)
       output 10 x 10 x 32
  -> Dropout(0.1)
  -> Conv2D(64, 3x3, stride 2, ReLU)
       output 4 x 4 x 64
  -> Dropout(0.1)
  -> Conv2D(10, 4x4, softmax)
       output 1 x 1 x 10
  -> Flatten
```

The notebook reports 33,802 trainable parameters for both the Keras ANN and the
corresponding NxTF model. It includes convolutional biases, converts parameters to
8-bit integers, constructs NxConv2D layers with sparse synapse encoding, and uses
512 timesteps per image in that tutorial run.

Therefore this public tutorial is **not** the same workload as the paper's
~7k-parameter, 100-timestep Table-2 benchmark. P08 may use it as source-backed
evidence of NxTF architectural/conversion style, but it must not silently
substitute the tutorial's quantitative results for the paper benchmark.

---

## Emulation priority rule

P08 should follow this priority order:

1. **Exact paper reconstruction where sourced.** Recover the precise MNIST
   topology, preprocessing, training, conversion, neuron settings, weight/bias
   handling, decoder, and compiler assumptions from the paper, supplementary
   material, author repositories, SNN Toolbox artifacts, or other primary
   source-backed material.
2. **Source-backed nearest reconstruction where exact details are unavailable.**
   When a paper detail remains unknown, use the closest behavior supported by the
   public NxTF/SNN-Toolbox implementation style and document the substitution.
3. **Project-specific adaptation only when required by FPGA-v2.** Any adaptation
   needed because FPGA-v2 lacks a source feature must be isolated, justified, and
   measured. It must not be disguised as an NxTF behavior.
4. **No convenience-driven shrinking.** The network must not be reduced merely
   to fit three resident contexts, one physical engine, or another current K26
   implementation convenience.

A source uncertainty is preferable to an invented exactness claim.

---

## Abandoned candidate history

Before the realignment, P08 explored three hand-designed candidates. They matched
only selected aggregate quantities and are **not accepted P08 architectures**.
Their implementation code is intentionally removed from the active application
tree; these results are retained only as development history.

### Revision 1

```text
28x28
 -> Conv2D(3, 5x5, stride 1)
 -> Conv2D(6, 3x3, stride 2)
 -> Dense(8)
 -> Dense(10)
```

- 2,472 spiking neurons
- 6,125 trainable weights
- best validation accuracy: 88.10% after 50 epochs

This candidate was rejected before conversion or official-test evaluation.

### Revision 2

```text
28x28
 -> Conv2D(12, 5x5, stride 2)
 -> Conv2D(12, 3x3, stride 2)
 -> Dense(20)
 -> Dense(10)
```

- 2,058 spiking neurons
- 7,796 trainable weights
- best validation accuracy: 49.60%

The candidate had been shaped around the existing three-context physical shell
and was rejected.

### Revision 3

```text
28x28
 -> Conv2D(3, 5x5, stride 1)
 -> Conv2D(6, 3x3, stride 2)
 -> Dense(10)
 -> Dense(10)
```

- 2,474 spiking neurons
- 7,597 trainable weights
- best validation accuracy: 69.18% at epoch 22 of 50

Revision 3 confirmed that adding parameters to the dense bottleneck did not solve
the architectural mismatch.

### Lesson from revisions 1-3

The paper benchmark reports approximately 4k neurons, 14 Loihi neurocores, and
341k expanded convolutional connections represented by 6,746 shared weights.
Revisions 1-3 contained only about 2.1-2.5k neurons, were forced into three
logical cores, and used two convolutional stages followed by dense bottlenecks.
Matching only a ~7k parameter count was therefore not a valid resource/architecture
match.

No accepted P08 work has evaluated the official MNIST test set; the topology,
training, and conversion search has remained confined to training/validation
information.

---

## Stable dataset and split contract

Unless stronger source evidence requires a change, P08 uses the standard
TensorFlow/Keras MNIST dataset without cropping:

```text
source image:          28 x 28 uint8
training split:        official 60,000 images
validation selection: deterministic stratified 5,000-image subset of training
training remainder:    55,000 images
official test split:   10,000 images
validation seed:       0x4D4E4953
```

The official test split may not be used for topology selection, checkpoint
selection, conversion-scale/threshold tuning, timestep selection, or decoder
selection.

The current application scaffold retains deterministic MNIST loading,
normalization, split generation, and deterministic rate-encoding helpers. Those
helpers are reusable but remain subordinate to source reconstruction: if exact
NxTF/SNN-Toolbox input encoding differs materially and is recoverable, P08 should
implement the sourced behavior and document the change.

---

## Topology freeze gate

No network is considered the P08 workload until a topology-freeze record answers:

- Which layer dimensions/filter counts/kernel sizes/strides are sourced directly?
- Which layer details, if any, are reconstructed from public implementation style?
- How many neurons/compartments does the network contain?
- How many trainable parameters and learned biases does it contain?
- How many expanded synaptic connections does it represent?
- How many project shared parameters/templates result after P06 compilation?
- How many logical Loihi-like cores does P06 require under unchanged per-core
  capacity rules?
- Which differences from NxTF mapping/resource accounting are unavoidable because
  P06 is not the native NxTF compiler?
- Which source details remain unknown/not claimed?

The topology-freeze artifact must be committed before training resumes.

---

## Logical-core and physical-residency contract

The accepted P05 implementation provides:

```text
logical Loihi capacity/core: unchanged
resident full K26 contexts:  3
physical HLS compute engines: 1
```

These three quantities must remain separate.

The paper's NxTF MNIST result maps to 14 Loihi neurocores. P08 does not assume our
P06 mapper will also produce exactly 14 logical cores, because native NxTF mapping
and FPGA-v2 resource models are different. However, a source-faithful workload is
expected to place materially more pressure on the logical architecture than the
abandoned three-core candidates.

If P06 requires more than three logical cores, P08 must not shrink the workload
simply to regain three-core residency. Instead, P08 should add a deterministic
context paging/loading layer above the accepted P05 retained-context mechanism.
The extension must preserve:

- logical core IDs independent of resident slot/physical engine;
- full independent architectural state for every logical core;
- hard per-logical-core capacity enforcement;
- deterministic service and context-swap ordering;
- current/next-timestep event-bank semantics;
- destination-core/destination-axon packet identity;
- quiescence/barrier semantics across resident and nonresident contexts;
- normalized Python/FPGA state/spike/packet traces; and
- explicit reporting of logical core count, resident-context count, and physical
  engine count.

Any context paging mechanism becomes part of P08 validation and must have directed
invariance tests before application acceptance.

---

## Training contract after topology freeze

The exact training policy must be frozen after source reconstruction and before a
new candidate run. At minimum it must record:

```text
framework/version
input scaling/preprocessing
optimizer
learning rate/schedule
loss
batch size
maximum epochs
model-selection rule
bias handling
regularization/dropout
random seeds/determinism controls
```

Where the exact NxTF paper training choice is known, P08 should match it unless the
framework makes that impossible. Where it remains unknown, use a conventional
source-compatible choice, state that it is a reconstruction decision, and do not
attribute it to the paper.

Training and model selection use only the training/validation split.

---

## ANN-to-SNN conversion contract

The paper uses SNN Toolbox rate-based ANN-to-SNN conversion and evaluates the
frame-based MNIST network for 100 algorithmic timesteps. P08 should reproduce that
conversion behavior as closely as the FPGA-v2 neuron model permits.

Before conversion is accepted, freeze and record:

- float-to-integer weight quantization method and bit range;
- bias representation or an explicit, measured bias adaptation;
- layer/weight/activation normalization;
- threshold selection;
- membrane-state initialization and reset behavior;
- refractory/leak settings;
- input spike/rate encoding;
- output decoding;
- primary 100-timestep policy; and
- any shorter/longer characterization horizons.

Conversion calibration may use only training/validation data. The 10,000-image
official test split remains locked until this contract is frozen.

FPGA-v2 does not claim transistor-level or timing-exact Loihi equivalence; the
comparison target is source-backed architectural/event behavior under the v2
normalized boundary.

---

## Mapping and connection-sharing contract

The frozen converted graph must enter FPGA-v2 as a normal P06 `NetworkSpec` and
pass through `compile_network`; no hand-authored FPGA placement is allowed.

P08 must report separately:

- high-level trainable parameters;
- learned biases;
- expanded logical synaptic connections;
- project-defined stored shared parameters/templates;
- per-core compartments/input axons/output routes/synapse bytes;
- logical core count;
- resident K26 context count;
- physical engine count;
- static local/remote route estimates;
- observed packet traffic for characterized samples; and
- mapping failures/headroom.

The paper's `341k discrete connections` and `6,746 shared weights` are reference
metrics. P06's normalized sharing model is not claimed to reproduce NxTF's native
Loihi connection-compression encoding byte-for-byte.

---

## Accuracy and physical validation contract

After topology/training/conversion are frozen:

1. Evaluate the selected floating-point ANN on the untouched 10,000-image test
   split.
2. Evaluate the frozen integer/rate SNN on the same full test split in software,
   primarily at 100 algorithmic timesteps.
3. Compile the exact converted deployment through P06.
4. Demonstrate deterministic logical execution independent of legal service and,
   if added, context-page order at the normalized trace boundary.
5. Run a deterministic representative physical K26 corpus through the same
   compiled deployment.
6. Compare physical state, spikes, packets, routed events, barriers, status, and
   identity against Python expectations.
7. Record synchronous K26 PL cycles separately from algorithmic timesteps.
8. Record FPGA utilization separately from logical Loihi-like occupancy.

A complete 10,000-image physical K26 run may be added if practical but is not
required for architectural conformance when full software accuracy and a
representative physical differential corpus are both reported explicitly.

---

## Comparison boundary

| Quantity | NxTF reference | P08 treatment |
|---|---|---|
| Dataset | MNIST 28x28 | match unless sourced preprocessing says otherwise |
| Task/classes | 10-class digit recognition | directly comparable |
| Network family | four-layer CNN | emulate as closely as sourced |
| ANN architecture | partially reported in paper | exact where recovered; unknowns labeled |
| Public NxTF tutorial | 16→32→64→10 all-conv, 33,802 params | architectural evidence, not paper benchmark |
| ANN→SNN method | SNN Toolbox rate conversion | emulate as closely as v2 permits |
| Algorithmic horizon | 100 timesteps | primary P08 horizon |
| ANN error | 0.74% reported | report P08 independently |
| SNN error | 0.79% reported | report P08 independently |
| Neuron count | ~4k | target source-faithful scale; report exact P08 count |
| Trainable parameters | ~7k | target source-faithful scale; report exact P08 count |
| Shared weights | 6,746 | compare cautiously to P06 stored/shared accounting |
| Discrete connectivity | 341k | report P08 expanded logical connections |
| Loihi neurocores | 14 | contextual; P06 core model/compiler differ |
| Resident FPGA contexts | n/a | report separately; currently 3 before paging extension |
| Physical FPGA engines | n/a | report separately; currently 1 |
| Energy/sample | 0.66 mJ Loihi | published context only absent defensible FPGA energy method |
| Wall-clock latency | 6.65 ms Loihi | not directly comparable to debug-controlled FPGA run |
| FPGA PL cycles | n/a | project implementation metric only |
| FPGA resource use | n/a | project implementation metric only |

---

## P08 sub-milestones

### P08.1 — NxTF source reconstruction and experiment freeze

- audit the paper, preprint, surviving NxTF code, and relevant SNN Toolbox source;
- recover exact paper MNIST architecture/conversion details where available;
- maintain a sourced/unknown/reconstructed table;
- remove abandoned candidate assumptions from the active implementation;
- freeze the topology and experiment contract before further training.

### P08.2 — FPGA-v2 architecture adaptation for the source-faithful workload

- compile the frozen graph through P06 and determine real logical resource demand;
- do not cap the model at three logical cores for convenience;
- if logical cores exceed resident contexts, implement deterministic context
  paging/loading with directed invariance tests;
- preserve unchanged per-core limits and normalized semantics.

### P08.3 — ANN training and ANN-to-SNN conversion

- train the frozen topology using training/validation data only;
- freeze the accepted ANN checkpoint from validation performance;
- calibrate/quantize/convert without official-test feedback;
- demonstrate validation behavior at the primary 100-timestep horizon.

### P08.4 — Full software evaluation and physical K26 conformance

- evaluate ANN and SNN on the untouched official test split;
- compile the frozen deployment through P06;
- run representative physical K26 differential evidence;
- record logical occupancy, resident/engine counts, traffic, cycles, and FPGA
  utilization.

### P08.5 — Final NxTF comparison and closure

- produce an explicit comparison table;
- distinguish direct measurements, contextual values, project-specific metrics,
  reconstructed assumptions, and unknowns;
- archive all accepted software/physical evidence and fingerprints.

---

## Acceptance gates

P08 is complete only after:

1. P08.1 source reconstruction and topology freeze are documented;
2. abandoned revision-1/2/3 candidate code is absent from the active application;
3. the source-faithful workload compiles under unchanged logical per-core limits;
4. any required >3-context paging/virtualization extension passes directed
   invariance and capacity tests;
5. ANN training reaches a defensible validation-selected MNIST result;
6. ANN-to-SNN conversion is frozen without test-set tuning;
7. full official-test ANN and SNN accuracy are recorded;
8. P06 mapping/occupancy/sharing/traffic reports are archived;
9. representative Python/FPGA physical K26 conformance passes;
10. physical cycle/resource metrics and mapping headroom/failures are recorded;
11. the final NxTF comparison clearly labels sourced, reconstructed, directly
    comparable, contextual, and non-comparable quantities.

Energy claims remain out of scope unless a defensible workload-specific physical
measurement method is established.
