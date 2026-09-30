# P08.3.5b Source-Recovered NxTF Semantics Preflight

**Status:** verification candidate  
**Official MNIST test split:** locked  
**Classification accuracy:** deliberately not evaluated in this gate

## Why this gate exists

P08.3.5a localized the silent-network failure produced by the previously accepted
P08.3.4 project conversion:

```text
100 validation examples, 100 timesteps
input spikes: 1,025,543
conv1 spikes:    73,901
conv2 spikes:        25
conv3 spikes:         0
conv4 spikes:         0
first dead layer: conv3
```

That result showed that the deterministic simulator and input path were active,
but activity collapsed progressively because the converted hidden layers were
severely under-driven.

After that diagnostic, additional public Intel source was recovered from:

```text
intel-nrc-ecosystem/models
nxsdk_modules_ncl/snntoolbox/nx_backend.py
nxsdk_modules_ncl/input_generator/input_generator.py
nxsdk_modules_ncl/input_generator/templates/inject_state.c.template
```

This source establishes that the historical Loihi backend did **not** implement
the P08.3.4 project rule

```text
normalized_parameter_scale = vThMant / DThIR = 512 / 8 = 64
threshold = 512 for every spiking layer
```

Instead, the public backend performs layer-wise dynamic-range normalization.
Therefore the P08.3.4 artifact remains an important historical gate result, but
it is now a **superseded conversion candidate** rather than the final NxTF-style
conversion to use for accuracy comparison.

No official-test accuracy was observed before this source correction.

## Recovered public backend behavior

The public SNN-Toolbox Loihi example enables:

```text
normalize_thresholds = True
desired_threshold_to_input_ratio = 8   # for hard reset
numWeightBits = 8
numBiasBits = 12
biasExp = 6
vThMant = 512                          # configuration seed/reference
weightExponent = 0
```

The Intel backend then performs an additional preprocessing pass.

### Frame input

For ordinary frame data, NxTF creates an `NxInputLayer` in `InputModes.BIAS`.
The host input is normalized to its maximum, scaled to unsigned 8-bit, converted
to integers, and written into the input compartments as bias mantissas. The input
generator installs `biasExp=6` on those compartments.

The normalization emulator represents the same input in mantissa units as:

```text
input_scale = 255
dV/dt_input = normalized_frame * 255
```

P08.3.5b follows that exposed abstract normalization domain. The FPGA-v2
compatibility model does not separately multiply both bias and threshold by the
common Loihi implicit exponent factor.

### Layer parameter scale

The recovered backend defaults to:

```text
parameter percentile = 100%
```

For a layer with floating weights `W` and slope-adjusted bias `b`:

```text
weight_norm = percentile(abs(W), 100)
scale_ratio = percentile(abs(b) / weight_norm, 100)

parameter_scale =
    min(255, 4095 / scale_ratio) / weight_norm    if scale_ratio > 0
    255 / weight_norm                             otherwise
```

The public backend integer conversion is:

```text
round(value * parameter_scale)
clip to [-2**bits, 2**bits - 1]
```

With percentile 100, P08.3.5b requires zero clipping for the accepted ANN.

### Layer threshold normalization

The recovered backend defaults to:

```text
activation percentile = 99.999%
```

For each spiking layer it evaluates integer `dV/dt` on the normalization corpus,
then computes:

```text
dvdt_ref = percentile(nonzero dV/dt, 99.999)
threshold_target = dvdt_ref * DThIR
```

The target is represented using the public backend mantissa/exponent helper:

```text
exp  = ceil(log2(max(abs(target) / 256, 1)))
mant = round(target / 2**exp)
threshold = mant * 2**exp
```

The propagated activation estimate is:

```text
spike_rate = min(dV/dt / threshold, 1)
```

and the slope carried into the next layer is:

```text
slope = parameter_scale * previous_slope / threshold
```

Critically, the next layer's ANN bias is multiplied by `previous_slope` before
its own parameter scale is calculated and before integer conversion.

This is the missing behavior that the P08.3.4 `scale=64 / threshold=512`
approximation did not model.

### Softmax output

The public Intel backend treats a softmax output specially. It quantizes the
output layer parameters but skips ordinary threshold normalization for that
layer; backend comments/readout code use output membrane/readout evidence rather
than requiring conventional output spikes.

P08.3.5b therefore does **not** freeze a final classification decoder yet. It only
requires that the quantized softmax output produces nonzero, class-distinguishing
membrane evidence on the diagnostic sample.

## What P08.3.5b does

The preflight uses:

```text
accepted ANN checkpoint: exact P08.3.3 artifact
normalization corpus:    frozen 55k training remainder, every 10th image
calibration examples:    5,500
activity sample:         first 100 frozen validation images
horizon:                 100 timesteps
official test images:    0
```

It reconstructs:

1. input threshold and input slope;
2. integer conv1 weights/biases, conv1 threshold, conv1 slope;
3. integer conv2 weights/biases, conv2 threshold, conv2 slope;
4. integer conv3 weights/biases, conv3 threshold, conv3 slope; and
5. quantized conv4 softmax-readout weights/biases.

It then runs a hard-reset FPGA-v2 activity preflight with one-tick forwarding
between stages. Frame pixels drive an explicit input integrate-and-fire layer as
bias currents; conv1-3 use their recovered per-layer thresholds; conv4 simply
accumulates affine membrane evidence for this diagnostic.

## Acceptance boundary

P08.3.5b passes only if:

1. the exact accepted P08.3.3 ANN is used;
2. 5,500 training-only calibration examples are used;
3. the recovered 100% parameter percentile and 99.999% activation percentile
   remain fixed;
4. hard-reset DThIR remains 8;
5. source-style integer conversion produces no parameter clipping;
6. the input and conv1, conv2, and conv3 all produce spikes on the fixed
   100-image activity sample;
7. the softmax output produces nonzero and class-distinguishing membrane
   evidence;
8. classification accuracy is **not** evaluated; and
9. `official_test_used=false` / `test_examples_observed=0` remain explicit.

If this gate passes, the next substep is to supersede P08.3.4 with a new
source-recovered converted artifact, rebuild/recompile the five-logical-core
network with per-layer thresholds, and freeze the readout adaptation before
running validation accuracy again.
