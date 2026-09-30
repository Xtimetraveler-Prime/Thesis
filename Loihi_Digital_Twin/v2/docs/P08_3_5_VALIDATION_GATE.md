# P08.3.5 Validation-Only Converted-SNN Gate

**Status:** Verification candidate  
**Accepted conversion:** P08.3.4 DThIR-aware artifact  
**Primary horizon:** 100 algorithmic timesteps  
**Official MNIST test split:** locked

## Purpose

P08.3.5 measures the first classification accuracy of the frozen converted SNN. It consumes only the deterministic 5,000-image validation partition that was separated from the official MNIST 60,000-image training split. The official 10,000-image MNIST test split remains unavailable.

The gate is bound to the independently accepted P08.3.4 identities:

```text
conversion:
686e801cf2459d66772a3517cfff0411746ce97d7a84fb45554ca3ee8345cb75

converted network:
4f7dc2b2ecfd4db7c347fc8c846aed3ad5f03d57ceb48ed973530e77865bc211

compiled deployment:
1dc5191354566e9e40cdfe624ff6fc48528d1b78a91d2a16a4336d12b1a4296c
```

A different conversion artifact is rejected before evaluation.

## Input spike encoding frozen before accuracy observation

The P08.3.1 policy specifies deterministic evenly distributed rate input. P08.3.5 makes that rule executable before observing SNN validation accuracy.

For a normalized input pixel `x` and `T=100`:

```text
spike_count = floor(x * T + 0.5)
```

The exact number of spikes is distributed with a zero-initialized Bresenham accumulator. Equivalently, a source spikes at tick `t` when:

```text
floor((t + 1) * spike_count / T) > floor(t * spike_count / T)
```

This produces exactly `spike_count` input events in the 100-tick window without stochastic sampling.

No extra pipeline-flush timesteps are appended after tick 99. The measured horizon is exactly 100 algorithmic timesteps.

## Execution semantics

The validator uses a vectorized TensorFlow implementation of the already accepted FPGA-v2 compartment profile. For the frozen P08 parameters:

```text
current_decay      = 4096
voltage_decay      = 0
threshold          = 512
reset_voltage      = 0
refractory_ticks   = 0
```

the generic compartment primitive reduces exactly to:

```text
candidate_voltage = previous_voltage + synaptic_input + bias
spike             = candidate_voltage > threshold
next_voltage      = 0 if spike else candidate_voltage
```

The strict `>` threshold comparison and hard reset match `loihi_twin_v2.compartment.step_compartment`.

Convolutional stage outputs are routed to the next stage one algorithmic tick later, matching the logical packet-routing contract. Therefore conv1 spikes generated at tick `t` can affect conv2 at tick `t+1`, and similarly for later layers.

TensorFlow convolution is used only as a vectorized way to sum the same integer kernel contributions. Converted weights, biases, threshold, reset policy, and tick ordering are not changed.

## Decoder

For each validation image, the ten conv4 output neurons accumulate spike counts over the 100-timestep run.

```text
prediction = argmax(total output spike count)
```

NumPy/TensorFlow first-index `argmax` implements the already frozen lowest-class-index tie break.

The artifact also records:

- number of examples with no output spikes;
- number of examples tied at the maximum output spike count;
- total output spike activity;
- confusion matrix and per-class accuracy; and
- deterministic prediction fingerprint.

## Accuracy policy

P08.3.5 deliberately has **no accuracy acceptance threshold**. The purpose of this gate is to measure the behavior of the conversion that was frozen before SNN accuracy was visible.

A low result is therefore not automatically "fixed" by retuning DThIR, normalization, quantization, input phase, timestep count, or reset behavior. If the measured result is unexpectedly poor, the next action is an explicit diagnosis against the accepted semantics, not post-hoc tuning.

The accepted ANN validation reference remains:

```text
ANN validation accuracy = 0.992600
```

P08.3.5 reports both SNN validation accuracy and `ANN - SNN` validation-accuracy difference.

## Generated local artifacts

On success:

```text
applications/mnist_v2_nxtf/artifacts/p08_3_5_validation/
├── validation_manifest.json
└── validation_predictions.npz
```

The prediction archive contains the 5,000 labels, decoded predictions, ten output spike counts per image, and the 10x10 confusion matrix. Generated artifacts remain Git-ignored.

## Acceptance boundary

The P08.3.5 verification gate passes only if:

1. the exact accepted P08.3.4 conversion/network/deployment fingerprints are present;
2. all 5,000 frozen validation examples are evaluated;
3. the execution horizon is exactly 100 timesteps with zero flush timesteps;
4. the frozen deterministic rate encoder and lowest-index spike-count decoder are used;
5. the converted network produces output activity;
6. prediction/confusion artifacts cover all 5,000 examples and their fingerprint recomputes;
7. no SNN accuracy threshold or conversion retuning is introduced; and
8. `official_test_used=false` and `test_examples_observed=0` remain explicit.

After independent verification, the measured SNN validation result will be reviewed before the official test split is unlocked.
