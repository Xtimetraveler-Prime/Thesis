# P08 Deep MNIST / NxTF-Oriented Comparison Contract

## Purpose

P08 is the final application phase for FPGA-v2. It must demonstrate a reproducible
MNIST workload that exercises the P06 mapper, convolution-oriented connection
sharing, multicore routing, P05 virtualization, and physical K26 execution while
supporting a bounded comparison with Rueckauer et al.'s NxTF MNIST result.

This phase is **NxTF-oriented**, not an asserted layer-for-layer reproduction of
the authors' unpublished experiment configuration. The paper reports the workload
at a useful aggregate level but does not fully specify every MNIST convolutional
layer dimension/filter count in the text, and the surviving public NxTF repository
does not contain a frozen MNIST model artifact that unambiguously reconstructs the
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

## Candidate P08 network

The initial P08 candidate deliberately targets the same workload class while
remaining within the physically accepted three-context K26 shell:

```text
input: 28 x 28 x 1 MNIST image
  -> Conv2D: 3 filters, 5x5, stride 1, valid, ReLU, no bias
       output 24 x 24 x 3 = 1,728 neurons
  -> Conv2D: 6 filters, 3x3, stride 2, valid, ReLU, no bias
       output 11 x 11 x 6 = 726 neurons
  -> Dense: 8 ReLU neurons, no bias
  -> Dense: 10 output neurons, no bias
```

Total spiking neuron populations after conversion:

```text
1,728 + 726 + 8 + 10 = 2,472 neurons
```

Trainable weights:

```text
conv1: 5*5*1*3      =    75
conv2: 3*3*3*6      =   162
dense1: 726*8       = 5,808
dense2: 8*10        =    80
                         -----
total                    6,125
```

This is not selected because 6,125 is meant to equal NxTF's reported parameter
count. It is selected because it has two genuine convolutional stages, similar
order-of-magnitude neuron/parameter pressure, and can in principle fit the three
full logical contexts already validated on the K26. The candidate is provisional
until mapping and training gates pass.

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

This intentionally reuses the accepted FPGA-v1 split policy while keeping the
new application source separate from the frozen `applications/mnist_baseline/`.
The official test split must not be used for checkpoint or conversion-parameter
selection.

## ANN training contract

Initial frozen training policy:

```text
framework:        TensorFlow/Keras 2.21.x
input scaling:    uint8 / 255.0 -> float32 [0, 1]
optimizer:        Adam
learning rate:    1e-3
loss:             sparse categorical cross entropy
batch size:       128
maximum epochs:   20
model selection:  highest validation accuracy, then earliest epoch on ties
layer biases:     disabled
```

Disabling biases keeps the trained graph exactly representable by the current
P06 projection/compiler contract rather than introducing an FPGA-only bias
translation path during the final application phase.

The candidate topology is rejected or revised if its validation-selected ANN
accuracy is not sufficient to support a useful MNIST comparison. Any topology
revision must update this contract before becoming accepted.

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
- Accuracy is also reported at shorter fixed horizons where practical to show the
  accuracy/compute tradeoff rather than selecting a test-set-specific stopping time.
- Decoder: `argmax(output spike count)`, with lowest output ID breaking ties.

The exact accepted integer scales/thresholds and calibration algorithm must be
recorded in the frozen exported model artifact and may not be tuned on the
10,000-image official test split.

## Mapping contract

The converted graph is expressed as a normal P06 `NetworkSpec` with explicit
convolution-derived projection edges. It must then pass through
`compile_network`; no manually authored FPGA mapping is allowed.

The initial physical mapping target is the accepted three-context shell:

```text
logical Loihi capacity/core: unchanged
resident logical contexts:   3
physical compute engines:     1
```

P08 must record:

- logical core count and placement by layer;
- compartment, axon, route, and modeled synapse-memory occupancy/headroom;
- expanded connection count;
- stored shared-parameter count and expansion/sharing ratio;
- static local/remote route estimates;
- observed packet traffic for characterized samples;
- any mapping-capacity failure.

If the trained candidate cannot fit three logical contexts under the real P06
resource rules, P08 must record that failure before deciding whether to revise
the topology or add a new physical context-paging mechanism.

## Accuracy and physical validation contract

P08 separates full-corpus software accuracy from physical differential evidence.

1. Evaluate the selected floating-point ANN on the untouched 10,000-image test set.
2. Evaluate the frozen integer SNN model on the same test set in the software
   execution path (or a mathematically equivalent vectorized evaluator whose
   equivalence is regression-tested against the exact golden model).
3. Run a deterministic representative physical K26 corpus through the exact same
   compiled deployment and compare normalized state/spike/packet behavior against
   Python.
4. Record K26 PL cycles for physical samples separately from algorithmic timesteps.
5. Do not extrapolate native-Loihi energy or latency from FPGA measurements.

If a complete 10,000-image physical K26 run is practical it may be added, but it
is not required to establish Python/FPGA architectural conformance if the full
software accuracy and representative physical differential corpus are both
reported explicitly.

## Comparison boundary

| Quantity | NxTF reference | P08 treatment |
|---|---|---|
| Dataset | MNIST 28x28 | directly comparable |
| Task/classes | 10-class digit recognition | directly comparable |
| Network family | four-layer CNN | comparable in purpose; topology documented separately |
| ANN->SNN method | rate-based conversion | comparable in purpose; implementation differs |
| Algorithmic horizon | 100 timesteps | directly reported at 100; shorter horizons contextual |
| ANN accuracy/error | reported | directly report our own value, no winner claim |
| SNN accuracy/error | reported | directly report our own value, no winner claim |
| Neuron count | ~4k | directly report our mapped count |
| Trainable/shared parameters | ~7k / 6,746 shared | report our trained and stored-sharing counts |
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
