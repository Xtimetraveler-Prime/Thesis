# P08.3.1 ANN Training and ANN-to-SNN Conversion Freeze

**Status:** Verification candidate  
**Phase:** P08.3 ANN training and ANN-to-SNN conversion  
**Topology:** accepted P08.1 `14 -> 20 -> 12 -> 10` all-convolutional reconstruction  
**Execution path:** accepted P08.2 five logical cores / three resident K26 contexts / one HLS engine  
**Official MNIST test split:** locked

## Purpose

This document freezes the P08 training and conversion rules **before** the first
new training run. It prevents later ANN checkpoint selection, threshold tuning,
conversion calibration, timestep selection, or decoder selection from using the
official 10,000-image MNIST test set.

The policy is executable in:

```text
applications/mnist_v2_nxtf/mnist_v2_nxtf/policy.py
applications/mnist_v2_nxtf/mnist_v2_nxtf/ann.py
```

The paper benchmark does not publish a complete training/configuration record.
Therefore this freeze distinguishes direct source anchors, public NxTF/SNN-Toolbox
style evidence, explicit project reconstruction choices, and unknown/not-claimed
fields.

---

## 1. Source basis

### NxTF paper anchors

The paper directly supports:

- a four-layer CNN trained in Keras;
- rate-based ANN-to-SNN conversion with SNN Toolbox;
- 100 algorithmic timesteps per sample;
- output classification from accumulated spiking evidence;
- approximately 4k neurons and 7k trainable parameters;
- 14 mapped Loihi neurocores;
- ANN error 0.74% and converted-SNN error 0.79%.

The paper does not expose the exact layer-wise training hyperparameters,
checkpoint, quantizer, or complete conversion configuration for its ~7k MNIST
benchmark.

### Surviving public NxTF MNIST tutorial

The public Intel NxTF MNIST tutorial provides source-style evidence for:

- all-convolutional ReLU hidden layers;
- a softmax output convolution;
- learned convolution biases;
- `Dropout(0.1)` after each hidden convolution;
- Adam optimization;
- categorical cross-entropy;
- batch size 32;
- integer Loihi parameters;
- threshold mantissa 512;
- bias exponent 6;
- weight exponent 0; and
- sparse synapse encoding.

Its topology, 33,802 parameters, two-epoch example training run, and 512-timestep
execution are **not** substituted for the paper benchmark.

### Historical SNN Toolbox Loihi example

The 2020-04-22 SNN Toolbox Loihi example at commit
`cc699d761884768077591c39ae50530e63d97677` independently supports a contemporary
Loihi conversion style with:

```text
duration/timesteps:              100
reset mode:                      soft
normalize thresholds:            true
desired threshold/input ratio:  1 soft, 8 hard
weight bits:                     8
weight exponent:                 0
bias bits:                       12
bias exponent:                   6
threshold mantissa:              512
```

It also normalizes ANN inputs by `/255` and uses a deterministic subset of the
training set for normalization/calibration.

---

## 2. Frozen ANN architecture

P08.3 trains only the already accepted P08.1 reconstruction:

```text
28x28x1
 -> Conv2D(14, 5x5, stride 2, valid, ReLU)
 -> Dropout(0.1)
 -> Conv2D(20, 3x3, stride 1, valid, ReLU)
 -> Dropout(0.1)
 -> Conv2D(12, 3x3, stride 2, valid, ReLU)
 -> Dropout(0.1)
 -> Conv2D(10, 4x4, stride 1, valid, softmax)
 -> Flatten(10)
```

All four convolutions use learned biases.

Frozen totals:

```text
trainable parameters: 7,006
hidden/output filters: 14 -> 20 -> 12 -> 10
output classes:        10
```

Dropout is present only during ANN training and disappears from the converted
inference graph.

---

## 3. Dataset and preprocessing freeze

The existing P08 data boundary remains unchanged:

```text
official MNIST training split: 60,000
frozen validation subset:       5,000 stratified samples
ANN training remainder:        55,000
validation seed:               0x4D4E4953
official test split:           10,000 locked samples
input scaling:                 float32 / 255.0
```

The official test split is not supplied to `model.fit`, checkpoint selection,
conversion normalization, threshold calibration, timestep selection, or decoder
selection.

---

## 4. Frozen ANN training policy

| Field | Frozen value | Evidence class |
|---|---|---|
| framework | TensorFlow/Keras `>=2.21,<2.22` | PROJECT_RECONSTRUCTION runtime version |
| hidden activation | ReLU | SOURCED_STYLE_OR_RANGE |
| output activation | softmax | SOURCED_STYLE_OR_RANGE |
| learned biases | yes | SOURCED_STYLE_OR_RANGE |
| dropout | 0.1 after hidden convs | SOURCED_STYLE_OR_RANGE |
| optimizer | Adam | SOURCED_STYLE_OR_RANGE |
| learning rate | 1e-3 | PROJECT_RECONSTRUCTION using conventional Adam default |
| loss | categorical cross-entropy | SOURCED_STYLE_OR_RANGE |
| batch size | 32 | SOURCED_STYLE_OR_RANGE |
| maximum epochs | 30 | PROJECT_RECONSTRUCTION |
| early-stop patience | 5 epochs | PROJECT_RECONSTRUCTION |
| selection metric | maximum validation accuracy | PROJECT_RECONSTRUCTION |
| tie breakers | minimum validation loss, then earliest epoch | PROJECT_RECONSTRUCTION |
| random seed | `0x4D4E4953` | PROJECT_RECONSTRUCTION |
| deterministic TF ops | enabled | PROJECT_RECONSTRUCTION |

The public tutorial's two epochs are treated as an example setting rather than an
exact benchmark training rule. P08 therefore permits up to 30 epochs but freezes
checkpoint selection to validation data only. The epoch count is not tuned against
the official test split.

---

## 5. Conversion calibration freeze

Conversion calibration uses only the 55,000-image training remainder. A
deterministic every-tenth-sample subset is reserved as the first normalization
corpus, mirroring the historical SNN Toolbox example's training-subset style.

```text
calibration source:  training remainder only
calibration stride:  10
expected size:        5,500 samples
```

Validation data may be used later to characterize converted-SNN behavior and
choose among conversion parameters **only if those parameters are already listed
as tunable in the frozen policy**. The official test split remains unavailable.

---

## 6. Frozen integer/conversion boundary

P08 uses SNN-Toolbox-style rate conversion as the conceptual source model but
must emit parameters compatible with the accepted FPGA-v2 arithmetic.

Frozen first-pass settings:

```text
weight precision:             signed 8-bit project quantization
project range:                -127 .. +127
weight exponent reference:    0
bias precision:               signed 12-bit project quantization
project range:                -2047 .. +2047
source bias-exp reference:     6
threshold mantissa:           512
threshold normalization:      enabled
primary horizon:              100 timesteps
characterization horizons:    16, 32, 64, 100
```

The project signed ranges are explicit reconstruction choices. They are not
claimed to reproduce every detail of native Loihi/NxTF weight-mantissa packing.
The packed FPGA-v2 synapse/state fields are wider, but conversion intentionally
constrains learned parameters to these frozen narrower ranges before packing.

The exact activation-normalization and per-layer scaling calculation will be
implemented under this frozen boundary and recorded alongside the trained
checkpoint. It may use only the frozen calibration/validation data sources.

---

## 7. Reset/leak discrepancy and adaptation

The historical SNN Toolbox Loihi example uses **soft reset** (reset by
subtraction), which is source-style evidence for the conversion family.

The accepted FPGA-v2 P03 compartment implementation currently performs a hard
reset to `reset_voltage` after a spike. P08.3 will not silently modify the
already-validated neuron/HLS arithmetic during application training.

The frozen P08 adaptation is therefore:

```text
reset mode:                       hard reset to zero
reset voltage:                    0
refractory ticks:                 0
current decay:                    4096
voltage decay:                    0
desired threshold/input ratio:   8
```

In the v2 arithmetic, `current_decay=4096` clears transient current after each
step while `voltage_decay=0` leaves membrane voltage non-leaky between spikes.
The threshold/input ratio of 8 is taken from the historical SNN Toolbox hard-reset
branch and is `SOURCED_STYLE_OR_RANGE`, while the decision to use hard reset is a
`PROJECT_RECONSTRUCTION` forced by the accepted FPGA-v2 execution profile.

This difference must appear in the final NxTF comparison because it can affect
converted-SNN accuracy.

---

## 8. Input encoding and output decoding

### Input

P08 uses deterministic evenly distributed rate spikes. A pixel value is converted
to an integer event count for the requested timestep horizon and those events are
distributed as evenly as possible across the run.

This is a project adaptation chosen to remove stochastic scheduling noise from
Python/FPGA differential validation. The pixel-rate relationship remains monotonic
and rate based, but exact stochastic equivalence to every SNN Toolbox input
backend is not claimed.

### Output

The primary decoder is:

```text
predicted class = argmax(total output spikes accumulated over 100 timesteps)
```

A count tie resolves to the lowest class index for deterministic behavior. The
spike-count decision is source backed; the tie rule is a project choice.

The characterization horizons `(16, 32, 64, 100)` may be reported, but 100
remains the fixed primary comparison horizon and must not be replaced based on
official-test accuracy.

---

## 9. Evidence classification summary

| Field | Classification |
|---|---|
| four-layer CNN / Keras ANN | SOURCED_EXACT |
| rate-based SNN Toolbox conversion | SOURCED_EXACT |
| 100-timestep primary horizon | SOURCED_EXACT |
| output spike evidence | SOURCED_EXACT |
| ReLU/softmax/bias/dropout style | SOURCED_STYLE_OR_RANGE |
| Adam / categorical cross-entropy / batch 32 | SOURCED_STYLE_OR_RANGE |
| 8-bit weights / 12-bit biases / threshold 512 | SOURCED_STYLE_OR_RANGE |
| threshold normalization | SOURCED_STYLE_OR_RANGE |
| historical soft reset | SOURCED_STYLE_OR_RANGE |
| 30-epoch validation-only training rule | PROJECT_RECONSTRUCTION |
| deterministic split/seeds | PROJECT_RECONSTRUCTION |
| symmetric project integer ranges | PROJECT_RECONSTRUCTION |
| FPGA-v2 hard reset | PROJECT_RECONSTRUCTION |
| deterministic input spike schedule | PROJECT_RECONSTRUCTION |
| exact paper optimizer/checkpoint/quantizer | UNKNOWN_NOT_CLAIMED |

---

## 10. P08.3.1 completion gate

P08.3.1 is ready for acceptance when:

1. the executable policy validates without drift;
2. the Keras builder produces the accepted `14 -> 20 -> 12 -> 10` graph;
3. the model reports exactly 7,006 trainable parameters;
4. no test or preflight loads or evaluates the official test split;
5. TensorFlow deterministic-op setup succeeds in the P08 environment; and
6. the source-style versus project-reconstruction distinctions above are accepted.

After this gate, P08.3.2 may train the ANN and select one checkpoint using only the
55k/5k training-validation boundary. P08.3.3 will then convert and validate the
selected checkpoint under the frozen conversion rules before the official test
split is unlocked for P08.4.
