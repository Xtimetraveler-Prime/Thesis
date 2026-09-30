# P08 NxTF MNIST Source Audit and Realignment Record

## Status

**Audit state:** open / source reconstruction still required  
**Realignment recorded:** 2026-09-29  
**Active P08 topology:** none; intentionally unfrozen

This document records why the original P08 candidate search was stopped and what
is currently known from the NxTF paper and surviving public implementation. It is
intended to prevent later development from silently reintroducing assumptions
that were convenient for the current K26 shell but not representative of the
reference work.

The normative P08 experiment rules are in:

```text
Loihi_Digital_Twin/v2/docs/P08_MNIST_COMPARISON_CONTRACT.md
```

The active phase tracker is:

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

For the frame-based MNIST experiment, the paper reports the following useful
quantitative anchors:

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

The paper identifies SNN Toolbox rate-based ANN-to-SNN conversion as the MNIST
conversion path.

### Important unresolved paper detail

The currently audited paper text does **not** by itself give enough layer-wise
filter/kernel/stride information to reconstruct the ~7k-parameter MNIST network
without inference. P08 must continue searching primary/surviving source artifacts
before freezing exact dimensions.

Do not choose layer dimensions merely because their parameter sum is close to
7,000 and then call that the NxTF network.

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

The tutorial states that it trains a conventional Keras ANN and converts it into
an NxTF/Loihi spiking model. The Keras topology in the notebook is:

```text
Input: 28 x 28 x 1

Conv2D(
    filters=16,
    kernel_size=(5, 5),
    strides=(2, 2),
    activation='relu'
)
 -> 12 x 12 x 16

Dropout(0.1)

Conv2D(
    filters=32,
    kernel_size=(3, 3),
    activation='relu'
)
 -> 10 x 10 x 32

Dropout(0.1)

Conv2D(
    filters=64,
    kernel_size=(3, 3),
    strides=(2, 2),
    activation='relu'
)
 -> 4 x 4 x 64

Dropout(0.1)

Conv2D(
    filters=10,
    kernel_size=(4, 4),
    activation='softmax'
)
 -> 1 x 1 x 10

Flatten -> 10 outputs
```

The notebook's model summary reports:

```text
conv1:      416 params
conv2:    4,640 params
conv3:   18,496 params
conv4:   10,250 params
---------------------
total:   33,802 params
```

The corresponding NxTF model uses the same four convolutional stages.

Other relevant tutorial settings include:

```text
batch_size = 32
num_training_epochs = 2           # tutorial setting
num_steps_per_img = 512
vth_mant = 2**9
bias_exp = 6
weight_exponent = 0
synapse_encoding = 'sparse'
```

The notebook extracts ANN weights/biases, converts them to 8-bit integers with
`to_integer`, sets those quantized values on the NxTF model, and runs the Loihi
example for 512 timesteps per image.

The saved notebook output reports 98.44% spiking classification accuracy on the
128-image example subset shown there. That tutorial output must not be treated as
the paper's full MNIST benchmark accuracy.

### What the tutorial tells us

The public implementation is strong evidence that an NxTF MNIST workflow can be:

- all-convolutional through the 10-class output;
- trained as a conventional ReLU ANN first;
- regularized with dropout during ANN training;
- represented with learned convolutional biases;
- quantized before Loihi execution; and
- mapped using NxTF convolution-specific layers and sparse/compressed synapses.

### What the tutorial does *not* tell us

The tutorial is not the paper's Table-2 benchmark because it has:

- 33,802 trainable parameters rather than ~7k;
- a 512-timestep example rather than the paper's 100-timestep MNIST result; and
- a notebook example accuracy on 128 images rather than the paper's reported
  full benchmark error.

It is architectural/conversion evidence, not a numerical substitute for the
paper experiment.

---

## 3. P08 candidate history before realignment

The first P08 implementation mistakenly treated a roughly matching parameter
count plus the existing three-context K26 shell as sufficient guidance.

Those experiments were useful diagnostics but are no longer active candidates.
Their implementation files were intentionally removed from the active tree during
the 2026-09-29 realignment.

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

The candidate plateaued after 50 deterministic epochs and was rejected before
ANN-to-SNN conversion or official-test evaluation.

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

This revision was specifically optimized around the accepted three-logical-core
mapping boundary. That constraint is now recognized as inappropriate for P08.

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
best epoch:            22 / 50
best validation acc:  69.18%
```

The final ten epochs remained around 68.7-69.4% train/validation accuracy, which
made the architecture limitation obvious rather than suggesting an optimization
problem.

### Data-integrity status

All three rejected revisions used training/validation information only for model
selection. The official 10,000-image MNIST test set has not been used for the P08
architecture search or reported as an accepted result.

---

## 4. Why the original resource match was inadequate

The old candidates were close to one paper number — parameter count — but not to
the overall architecture/resource picture.

| Resource/structure | NxTF paper | Old P08 candidates |
|---|---:|---:|
| Network family | four-layer CNN | 2 conv + 2 dense |
| Neurons | ~4,000 | ~2,058-2,474 |
| Trainable parameters | ~7,000 | ~6,125-7,796 |
| Loihi/logical-core pressure | 14 neurocores | forced to 3 logical cores |
| Expanded connections | 341k | much lower candidate probes |
| Shared weights | 6,746 | only loosely analogous P06 counts |
| Timesteps | 100 | planned 100 |

The parameter-count similarity did not compensate for the much smaller neuron
population, lower connection pressure, different all-conv/dense structure, and
artificial three-core cap.

---

## 5. FPGA-v2 consequence: resident contexts are not logical cores

The accepted P05 K26 implementation contains:

```text
3 resident full logical-context slots
1 physical HLS compute engine
```

P05 already established the architectural rule that logical identity is separate
from physical execution-engine identity. P08 must extend the same principle one
step further if necessary: **logical-core count must also be allowed to exceed the
number of simultaneously resident full contexts.**

The paper's 14 Loihi neurocores are not a requirement that P06 also produce 14;
the compilers/resource models differ. But P08 should allow the source-faithful
workload to determine its real P06 logical-core count.

If that count exceeds three, the preferred path is deterministic context
paging/loading:

```text
many logical cores
    -> backing architectural state / deployment image
    -> 3 resident K26 context slots
    -> 1 physical compute engine
```

The paging layer must preserve logical IDs, events, barriers, and normalized
architectural results. It should be validated for service/page-order invariance
before being used for MNIST evidence.

Do not reduce the reference workload merely to avoid this extension.

---

## 6. Source-reconstruction questions still open

Before a new P08 topology is frozen, continue searching for primary evidence that
answers as many of these as possible:

1. What exact four convolutional layers produced the ~7k-parameter Table-2 MNIST
   benchmark?
2. Were biases enabled in that exact paper model, and how were they represented
   after conversion?
3. What dropout/regularization was used during training?
4. What optimizer, batch size, epoch count, and preprocessing were used for the
   reported 0.74% ANN error?
5. Which SNN Toolbox normalization/conversion options produced the 0.79% SNN
   error at 100 timesteps?
6. What precise output readout/decoder rule was used?
7. Are the paper's ~7k trainable parameters identical to the 6,746 shared-weight
   count, or are those two reported quantities counting slightly different
   objects?
8. Is there a historical model/checkpoint/config artifact in Intel NRC/NxTF,
   SNN Toolbox, author repositories, supplemental data, or archived release tags?
9. Can NxTF mapping reports or layer-partition figures explain how the workload
   reached 14 neurocores?

Each answer should be classified as one of:

```text
SOURCED_EXACT
SOURCED_STYLE_OR_RANGE
PROJECT_RECONSTRUCTION
UNKNOWN_NOT_CLAIMED
```

---

## 7. Next implementation handoff

A new development instance should begin P08.1 with source reconstruction, not
training.

Recommended order:

1. Read this audit and `P08_MNIST_COMPARISON_CONTRACT.md`.
2. Inspect the current P05/P06/P07 architecture/compiler contracts before deciding
   how a larger CNN should map.
3. Search the NxTF paper/preprint, Intel NRC model repository history/tags, SNN
   Toolbox material, and author artifacts for the exact paper MNIST definition.
4. Build a sourced/unknown reconstruction table.
5. Only then freeze a topology in `applications/mnist_v2_nxtf/` and add new
   topology/training/conversion source.
6. Run the P06 structural resource probe before ANN training.
7. If more than three logical cores are required, implement/test context paging
   instead of shrinking the network.
8. Keep the official test set locked until topology/training/conversion are frozen.

The previous revision-1/2/3 code should not be restored except from Git history
for forensic comparison.
