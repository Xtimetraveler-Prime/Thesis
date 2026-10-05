# P08.3.5b Source-Semantics Preflight Acceptance

**Status:** ACCEPTED  
**Accepted:** 2026-09-30  
**Official MNIST test split:** locked

## Independent verification result

P08.3.5b independently passed on the project workstation:

```text
11 passed in 3.04s
input threshold: 2040
conv1: scale=230.034 threshold=556 slope=0.051716263502468586 W=[-255,120] B=[-3,2]
conv2: scale=243.296 threshold=512 slope=0.024574926063267756 W=[-255,186] B=[-2,3]
conv3: scale=301.249 threshold=672 slope=0.01101664035937617 W=[-255,185] B=[0,4]
conv4: scale=248.038 softmax readout W=[-255,195] B=[-1,1]
```

The 100-example validation-only activity preflight reported:

```text
input spikes: 114617
conv1 spikes: 78775
conv2 spikes: 44857
conv3 spikes: 4833
first dead stage: None
softmax evidence nonzero examples: 100 / 100
softmax evidence distinct examples: 100 / 100
softmax evidence range: [-4333, 1754]
```

No classification accuracy was evaluated and the official test split remained unused:

```text
official_test_used=false
test_examples_observed=0
classification_accuracy_evaluated=false
```

## What this accepts

P08.3.5b accepts the source-recovered conversion semantics derived from Intel's public NxTF/SNN-Toolbox backend:

- unsigned 8-bit frame input scaling (`255`);
- BIAS-driven frame input with a calibrated input threshold;
- per-layer parameter scaling;
- `99.999`-percentile nonzero dV/dt threshold normalization;
- hard-reset desired threshold/input ratio `8`;
- previous-layer slope propagation into following-layer bias scaling; and
- softmax output as membrane/readout evidence rather than an ordinary hidden-layer spike-count threshold.

The earlier P08.3.4 `blanket scale=64, threshold=512` reconstruction is retained for audit history but is **superseded for forward P08 execution** by this recovered source behavior.

## Interpretation of the earlier P08.3.5 failure

The earlier validation run produced zero output spikes because the project reconstruction applied one parameter scale and one fixed threshold to every layer. P08.3.5a localized the resulting activity collapse to conv3. P08.3.5b changed only source-semantics reconstruction and restored activity through conv3 without observing classification accuracy.

This is evidence that the silent-network result was caused by an incomplete conversion model rather than by the accepted ANN checkpoint or the basic FPGA-v2 hard-reset compartment primitive.

## Next gate

P08.3.5c freezes a new source-recovered conversion artifact, constructs the exact 4,218-neuron convolution graph with recovered per-layer thresholds, represents the softmax output with maximum-threshold voltage readout semantics, and compiles that graph through P06. It must not evaluate classification accuracy or use the official test split.
