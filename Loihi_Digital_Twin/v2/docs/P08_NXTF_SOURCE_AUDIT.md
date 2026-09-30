# P08 NxTF MNIST Source Audit and Realignment Record

## Status

**Audit state:** P08.1 primary-source search completed; reconstruction proposed  
**Realignment recorded:** 2026-09-29  
**Active/frozen P08 topology:** none; proposal awaits Diego's acceptance

This document records why the original P08 candidate search was stopped, what is
known from the NxTF paper and surviving public implementation, and what the P08.1
source search did and did not recover.

Detailed field-by-field evidence classification and the current reconstruction
proposal are in:

```text
Loihi_Digital_Twin/v2/docs/P08_NXTF_RECONSTRUCTION.md
```

The normative experiment rules remain in:

```text
Loihi_Digital_Twin/v2/docs/P08_MNIST_COMPARISON_CONTRACT.md
```

The active phase tracker remains:

```text
Loihi_Digital_Twin/v2/LOIHI_TWIN_ROADMAP.md
```

---

## 1. Reference paper

Primary reference:

Bodo Rueckauer, Connor Bybee, Ralf Goettsche, Yashwardhan Singh, Joyesh Mishra,
and Andreas Wild, "NxTF: An API and Compiler for Deep Spiking Neural Networks on
Intel Loihi," ACM Journal on Emerging Technologies in Computing Systems 18(3),
2022.

- DOI: `10.1145/3501770`
- Preprint: `arXiv:2101.04261`

For the frame-based MNIST experiment, the paper reports:

| Quantity | Published value |
|---|---:|
| Network family | four-layer CNN |
| ANN error | 0.74% |
| Converted-SNN error | 0.79% |
| Algorithmic timesteps/sample | 100 |
| Neurons | ~4k |
| Trainable parameters | ~7k |
| Loihi neurocores | 14 |
| Discrete convolutional connections | 341k |
| Shared weights | 6,746 |
| Native-Loihi energy/sample | 0.66 mJ |
| Native-Loihi latency/sample | 6.65 ms |

The paper states that the ANN was trained with Keras and converted using SNN
Toolbox rate-based conversion. It also states that SNN Toolbox performs parameter
normalization and describes the classification decision as accumulating evidence
in output spikes over the run.

### Unrecovered paper detail

The paper/preprint does **not** publish the layer-wise filter counts, kernel sizes,
strides, checkpoint, or full training/conversion configuration for this benchmark.
Those details must not be invented and labeled as NxTF facts.

---

## 2. Surviving public Intel NxTF MNIST tutorial

Public repository:

```text
https://github.com/intel-nrc-ecosystem/models
```

Relevant notebook:

```text
nxsdk_modules_ncl/dnn/tutorials/a_image_classification_mnist.ipynb
```

The public tutorial's Keras topology is:

```text
28 x 28 x 1
 -> Conv2D(16, 5x5, stride 2, ReLU) -> 12 x 12 x 16
 -> Dropout(0.1)
 -> Conv2D(32, 3x3, stride 1, ReLU) -> 10 x 10 x 32
 -> Dropout(0.1)
 -> Conv2D(64, 3x3, stride 2, ReLU) -> 4 x 4 x 64
 -> Dropout(0.1)
 -> Conv2D(10, 4x4, softmax) -> 1 x 1 x 10
 -> Flatten
```

The notebook reports 33,802 trainable parameters. Other public tutorial settings
include:

```text
batch_size = 32
num_training_epochs = 2          # tutorial/example run
num_steps_per_img = 512
vth_mant = 2**9
bias_exp = 6
weight_exponent = 0
synapse_encoding = 'sparse'
```

The notebook extracts ANN weights and biases, converts them to integer NxTF
parameters, and installs them into convolution-specific NxTF layers.

The saved notebook reports 98.44% spiking accuracy on the displayed 128-image
example subset. This is not the paper's Table-2 result.

### What the tutorial supports

It is useful source evidence for an NxTF MNIST design style that is:

- all-convolutional through the 10-class output;
- trained first as a conventional ReLU ANN;
- capable of using dropout during ANN training;
- built with learned convolutional biases;
- quantized before Loihi execution; and
- mapped with convolution-aware NxTF layers and sparse/shared connectivity.

### What it does not support

It does not establish the paper benchmark's exact layer dimensions because it has:

```text
33,802 trainable parameters vs paper ~7k
512 timesteps              vs paper 100
128-image saved example    vs paper benchmark result
```

---

## 3. SNN Toolbox / historical Loihi evidence

P08.1 also inspected:

```text
https://github.com/NeuromorphicProcessorProject/snn_toolbox
examples/mnist_keras_loihi.py
```

A historical revision from 2020-04-22
(`cc699d761884768077591c39ae50530e63d97677`) is particularly relevant because
it predates the NxTF preprint and already uses:

```text
duration / timesteps:             100
reset mode:                        soft
normalize thresholds:             enabled
desired threshold/input ratio:    0.75
weight bits:                       8
bias bits:                         12
bias exponent:                     6
threshold mantissa:                512
synapse encoding:                  sparse
```

This is strong source evidence for contemporary SNN Toolbox/Loihi conversion
style, but its ANN graph does not match the paper's ~4k-neuron/~7k-parameter
benchmark. These values therefore remain `SOURCED_STYLE_OR_RANGE` unless the
paper directly fixes the same field.

The surviving Intel `nx_backend.py` also confirms support for threshold
normalization, integer weight/bias conversion, configurable reset behavior,
frame input, and output/readout handling. Backend capability/defaults are not
silently promoted to exact benchmark settings.

---

## 4. Repository/history/author search result

P08.1 searched the Intel repository history, the public SNN Toolbox history,
Bodo Rueckauer's public repositories including `rbodo/models`, and exact aggregate
terms such as `6746` and `341k` for a paper-specific MNIST checkpoint/config.

No separate public benchmark graph/checkpoint/config was recovered. Rueckauer's
visible `models` fork contains the same public tutorial family, not a second
~7k-parameter MNIST artifact.

This does not prove that no private or later-removed artifact ever existed. It
does establish the boundary of the primary evidence recoverable in this P08.1
pass. Exact filter/kernel/stride dimensions therefore remain:

```text
UNKNOWN_NOT_CLAIMED
```

rather than being reverse-engineered and called sourced.

---

## 5. P08 reconstruction decision

After exhausting those primary-source avenues, P08.1 defines an explicitly
project-owned proxy in `P08_NXTF_RECONSTRUCTION.md`.

The reconstruction keeps the public Intel tutorial's four-convolution spatial
scaffold and deterministically searches only the three hidden channel counts
against the paper's aggregate anchors. The current proposal is:

```text
28x28x1
 -> Conv2D(14, 5x5, stride 2, valid)
 -> Conv2D(20, 3x3, stride 1, valid)
 -> Conv2D(12, 3x3, stride 2, valid)
 -> Conv2D(10, 4x4, stride 1, valid)
```

with:

```text
neurons:                 4,218
kernel coefficients:     6,950
bias parameters:            56
trainable parameters:    7,006
expanded connections: 338,880
```

This graph is labeled:

```text
PROJECT_RECONSTRUCTION
```

It is **not** labeled "the NxTF topology."

The active application marker intentionally remains:

```text
TOPOLOGY_STATUS = "UNFROZEN_NXTF_EMULATION_REALIGN"
```

until Diego verifies and accepts the P08.1 proposal.

---

## 6. P06 consequence discovered by the structural probe

The proposed graph is expanded through the existing P06 compiler boundary using
one population per convolution output channel. This preserves a future location
for each learned Conv2D channel bias and avoids forcing a whole convolution layer
to share one compartment bias.

A default 1,024-compartment first-fit placement is expected to exceed the
project's logical synapse-memory capacity on an intermediate core. A mapping-only
probe at 900 compartments/core preserves the graph and fits it into five logical
cores while respecting current P06 limits.

Five logical cores is also the minimum possible from compartment count alone:

```text
ceil(4218 / 1024) = 5
```

The deterministic expected P06 totals are:

```text
logical cores:                 5
external ingress routes:       2,187
expanded connections:        338,880
P06 stored shared parameters: 64,235
static output routes:           7,860
```

P06's 64,235 stored shared parameters are **not** compared as if they were the
same representation as NxTF's 6,746 shared weights. The project compiler uses a
different normalized template/resource model.

Because five logical cores exceed P05's three resident K26 contexts, P08.2 must
add deterministic context paging/loading. The network must not be reduced to
avoid that architecture work.

---

## 7. Rejected pre-realignment candidates

The earlier candidates remain rejected and their executable implementation was
intentionally removed from the active tree.

### Revision 1

```text
28x28
 -> Conv2D(3, 5x5, stride 1)
 -> Conv2D(6, 3x3, stride 2)
 -> Dense(8)
 -> Dense(10)
```

```text
spiking neurons:      2,472
trainable weights:    6,125
best validation acc:  88.10%
```

### Revision 2

```text
28x28
 -> Conv2D(12, 5x5, stride 2)
 -> Conv2D(12, 3x3, stride 2)
 -> Dense(20)
 -> Dense(10)
```

```text
spiking neurons:      2,058
trainable weights:    7,796
best validation acc:  49.60%
```

This revision was strongly shaped around fitting exactly three logical cores.

### Revision 3

```text
28x28
 -> Conv2D(3, 5x5, stride 1)
 -> Conv2D(6, 3x3, stride 2)
 -> Dense(10)
 -> Dense(10)
```

```text
spiking neurons:      2,474
trainable weights:    7,597
best epoch:           22 / 50
best validation acc:  69.18%
```

The lesson remains unchanged: matching approximately 7k parameters by itself is
not an architecture/resource match. The paper also reports approximately 4k
neurons, 14 native Loihi neurocores, 341k expanded connections, and 6,746 shared
weights, and the surviving public NxTF style is all-convolutional.

The official MNIST test set was not used to select any of those rejected models.

---

## 8. Acceptance / next stage

P08.1 should be accepted only after Diego independently runs the reconstruction
preflight and reviews the source classification and proposed topology.

If accepted:

1. record the P08.1 completion/freeze in the roadmap and application config;
2. begin P08.2 deterministic context paging for five logical cores over three
   resident K26 context slots;
3. preserve logical IDs, per-core state, resource limits, event-bank semantics,
   routes, packets, barriers, and normalized trace equivalence;
4. do **not** begin ANN training until the execution path can host the frozen
   graph; and
5. keep the official 10,000-image MNIST test set locked until the later
   training/conversion policy is frozen.
