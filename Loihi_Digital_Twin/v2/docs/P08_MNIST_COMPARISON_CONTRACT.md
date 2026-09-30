# P08 Deep MNIST / NxTF-Oriented Comparison Contract

## Purpose

P08 is the final application phase for FPGA-v2. It must demonstrate a reproducible
MNIST workload that exercises the P06 mapper, convolution-oriented connection
sharing, multicore routing, P05 virtualization, and physical K26 execution while
supporting a bounded comparison with Rueckauer et al.'s NxTF MNIST result.

This phase is **NxTF-oriented**, not an asserted layer-for-layer reproduction of
the authors' experiment configuration. The paper reports the workload at a useful
aggregate level but does not fully specify every MNIST convolutional layer
dimension/filter count in the text, and the surviving public NxTF repository does
not contain a frozen MNIST model artifact that unambiguously reconstructs the
paper's exact trained network.

The comparison therefore distinguishes directly comparable quantities from
contextual/non-comparable ones rather than silently filling those gaps.

## Reference NxTF facts used by P08

Primary reference:

Bodo Rueckauer, Connor Bybee, Ralf Goettsche, Yashwardhan Singh, Joyesh Mishra,
and Andreas Wild, "NxTF: An API and Compiler for Deep Spiking Neural Networks on
Intel Loihi," ACM Journal on Emerging Technologies in Computing Systems 18(3),
2022. DOI: 10.1145/3501770. Preprint: arXiv:2101.04261.

For the frame-based MNIST experiment, the paper reports:

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

The P08 FPGA project does **not** claim direct comparability of native-Loihi
energy or wall-clock latency. Those values are retained only as published context.

## Candidate history and selection rule

### Revision 1 — rejected before conversion

The initial candidate was:

```text
28x28
 -> Conv2D(3, 5x5, stride 1)
 -> Conv2D(6, 3x3, stride 2)
 -> Dense(8)
 -> Dense(10)
```

It contained 2,472 spiking neurons and 6,125 trainable weights. Deterministic
training used the frozen 55,000/5,000 train/validation split and did not touch the
official test set. After 50 epochs the best validation accuracy was 88.10% at
epoch 49. The final epochs were effectively flat and validation loss began to
rise, so this candidate was rejected as architecture-limited before ANN-to-SNN
conversion or official-test evaluation.

That rejected result is intentionally retained in the P08 development history:
it is evidence that the application topology was revised from validation data
rather than selected after observing the official test set.

### Revision 2 — active candidate

The active candidate redistributes a similar parameter budget into more feature
channels and a wider hidden representation while retaining exactly three logical
cores under the accepted mapper:

```text
input: 28 x 28 x 1 MNIST image
  -> Conv2D: 12 filters, 5x5, stride 2, valid, ReLU, no bias
       output 12 x 12 x 12 = 1,728 neurons
  -> Conv2D: 12 filters, 3x3, stride 2, valid, ReLU, no bias
       output 5 x 5 x 12 = 300 neurons
  -> Dense: 20 ReLU neurons, no bias
  -> Dense: 10 output neurons, no bias
```

Total spiking neurons:

```text
1,728 + 300 + 20 + 10 = 2,058 neurons
```

Trainable weights:

```text
conv1: 5*5*1*12       =   300
conv2: 3*3*12*12      = 1,296
dense1: 300*20        = 6,000
dense2: 20*10         =   200
                           -----
total                     7,796
```

This is close to the published NxTF parameter scale without claiming topology
identity. The active candidate must still pass the same validation-only training
and conversion gates before the official test set is unlocked.

## Frozen structural mapping probe for revision 2

The deterministic fully-nonzero structural probe must compile through P06 to:

```text
logical cores:          3
physical engines:       1
compartments/core:      1024 / 1024 / 10
expanded connections:   81,800
stored shared params:   10,076
static source routes:   1,772
  local:                  812
  remote:                 960
```

Per-core modeled resource use for the probe is frozen as:

| Core | Compartments | Input axons | Output routes | Synapse bytes | Shared params | Expanded connections |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1024 | 473 | 940 | 13,388 | 2,788 | 25,600 |
| 1 | 1024 | 2,099 | 832 | 37,876 | 7,088 | 56,000 |
| 2 | 10 | 20 | 0 | 960 | 200 | 200 |

All remain inside the unchanged logical Loihi-like per-core limits. These are
project sharing/accounting quantities, not a claim that P06 reproduces NxTF's
native connection-compression encoding.

## Dataset and split contract

P08 uses the standard TensorFlow/Keras MNIST dataset without cropping:

```text
source image:          28 x 28 uint8
training split:        official 60,000 images
validation selection: deterministic stratified 5,000-image subset of training
training remainder:    55,000 images
official test split:   10,000 images
validation seed:       0x4D4E4953
```

This reuses the accepted FPGA-v1 split policy while keeping the new application
source separate from `applications/mnist_baseline/`. The official test split may
not be used for checkpoint, topology, conversion-scale, threshold, or timestep
selection.

## ANN training contract

Frozen revision-2 training policy:

```text
framework:        TensorFlow/Keras 2.21.x
input scaling:    uint8 / 255.0 -> float32 [0, 1]
optimizer:        Adam
learning rate:    1e-3
loss:             sparse categorical cross entropy
batch size:       128
maximum epochs:   50
model selection:  highest validation accuracy, then earliest epoch on ties
layer biases:     disabled
```

Disabling biases keeps the trained graph exactly representable by the current
P06 projection/compiler contract rather than introducing an FPGA-only bias
translation path during the final application phase.

The active candidate is rejected or revised again if validation-selected ANN
accuracy is not sufficient for a useful MNIST comparison. Any further topology
revision must be documented here before becoming accepted.

## ANN-to-SNN conversion contract

P08 uses rate-based conversion consistent in purpose with the NxTF reference but
implemented against the validated FPGA-v2 compartment arithmetic.

- The trained floating-point topology is unchanged structurally during conversion.
- Weights are converted deterministically to signed integer weights.
- Per-layer SNN thresholds/scales are selected using the 5,000-image validation
  split only.
- Converted neurons use the validated FPGA-v2 single-compartment primitive with
  persistent membrane voltage, hard reset to zero, no refractory hold, and no bias.
- Input images use deterministic rate encoding rather than stochastic Poisson
  input so repeated runs produce identical event schedules.
- The primary comparison horizon is 100 algorithmic timesteps, matching the NxTF
  MNIST experiment.
- Accuracy is also reported at 16, 32, and 64 timesteps to characterize the
  accuracy/compute tradeoff without choosing a test-specific stopping time.
- Decoder: `argmax(output spike count)`, with lowest output ID breaking ties.

The exact accepted integer scales/thresholds and calibration algorithm must be
recorded in the frozen exported model artifact and may not be tuned on the
10,000-image official test split.

## Mapping contract

The converted graph is expressed as a normal P06 `NetworkSpec` with explicit
convolution-derived projection edges. It must pass through `compile_network`; no
manually authored FPGA mapping is allowed.

The physical target remains the accepted three-context shell:

```text
logical Loihi capacity/core: unchanged
resident logical contexts:   3
physical compute engines:     1
```

P08 must record logical placement, per-resource occupancy/headroom, expanded and
stored-shared connection counts, static local/remote route estimates, observed
packet traffic for characterized samples, and any mapping-capacity failure.

## Accuracy and physical validation contract

P08 separates full-corpus software accuracy from physical differential evidence.

1. Freeze topology, checkpoint, conversion calibration, and timestep policy using
   training/validation data only.
2. Evaluate the selected floating-point ANN on the untouched 10,000-image test set.
3. Evaluate the frozen integer SNN model on the same test set in software (or a
   vectorized evaluator regression-tested against the exact golden model).
4. Run a deterministic representative physical K26 corpus through the same
   compiled deployment and compare normalized state/spike/packet behavior against
   Python.
5. Record K26 PL cycles separately from algorithmic timesteps.
6. Do not extrapolate native-Loihi energy or latency from FPGA measurements.

A complete 10,000-image physical K26 run may be added if practical but is not
required for architectural conformance when full software accuracy and a
representative physical differential corpus are both reported explicitly.

## Comparison boundary

| Quantity | NxTF reference | P08 treatment |
|---|---|---|
| Dataset | MNIST 28x28 | directly comparable |
| Task/classes | 10-class digit recognition | directly comparable |
| Network family | four-layer CNN | comparable in purpose; topology documented separately |
| ANN->SNN method | rate-based conversion | comparable in purpose; implementation differs |
| Algorithmic horizon | 100 timesteps | directly reported at 100; shorter horizons contextual |
| ANN accuracy/error | reported | directly report our own value |
| SNN accuracy/error | reported | directly report our own value |
| Neuron count | ~4k | report our mapped count |
| Trainable/shared parameters | ~7k / 6,746 shared | report our trained and project-sharing counts |
| Discrete connectivity | 341k without sharing | report our expanded connections |
| Logical core count | 14 Loihi neurocores | contextual: mapper/resource models differ |
| Energy/sample | 0.66 mJ on Loihi | reference context only unless FPGA energy is measured defensibly |
| Wall-clock latency | 6.65 ms on Loihi | not directly comparable to VIO/JTAG-controlled FPGA validation |
| FPGA PL cycles | n/a | project implementation metric only |
| FPGA resource use | n/a | project implementation metric only |

## Acceptance gates

The candidate becomes the accepted P08 application only after:

1. deterministic topology/resource audit passes;
2. ANN training reaches a defensible validation-selected MNIST accuracy;
3. conversion calibration is frozen without test-set tuning;
4. P06 mapping succeeds with explicit occupancy/sharing reports;
5. software SNN accuracy is measured on the official test split;
6. representative Python/FPGA conformance passes on the physical K26;
7. physical cycle/resource metrics and mapping headroom/failures are recorded;
8. the final NxTF comparison table labels directly comparable versus contextual
   metrics exactly as defined above.
