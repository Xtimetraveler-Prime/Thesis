# P08.3.5d Source-Recovered Validation Gate

## Purpose

P08.3.5d is the first full classification measurement after the public NxTF/SNN-Toolbox normalization behavior was recovered in P08.3.5b and compiled into the project graph in P08.3.5c.

This gate answers one question only:

> What classification behavior does the already-frozen source-recovered conversion produce on the fixed 5,000-image validation partition after exactly 100 timesteps?

It is not a parameter-selection gate and it does not use the official MNIST test split.

## Required conversion identity

P08.3.5d refuses to run unless the local P08.3.5c artifact matches:

```text
parameter fingerprint:
9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e

network fingerprint:
6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13

compiled deployment fingerprint:
5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

The accepted source-recovered thresholds are:

```text
input BIAS threshold: 2040
conv1:                 556
conv2:                 512
conv3:                 672
conv4/readout:       131071
```

Conv4 is decoded by final membrane-voltage argmax, not output spike count.

## Validation data boundary

The gate uses only the frozen 5,000-example validation partition derived from the official 60,000-image MNIST training split.

```text
official_test_used=false
test_examples_observed=0
```

The module imports `prepare_full_training_arrays()`; that boundary does not expose the official 10,000-image test split.

## Input encoding

Intel's public frame-input path normalizes the supplied input array by its maximum, multiplies by 255, and converts it to integer BIAS values.

For P08.3.5d, the normalization maximum is computed once over the complete frozen 5,000-image validation corpus before execution batches are formed. Batch size therefore affects only execution memory/performance and cannot alter encoded pixel values.

The recovered input-layer compartment is then emulated for 100 ticks:

```text
V_candidate = V + pixel_bias
spike       = V_candidate > 2040
hard reset  = 0 on spike
```

The resulting pixel spikes enter the P06 graph through its existing external `pixels` ingress population.

## Hidden execution and readout

The accepted FPGA-v2 hard-reset compartment behavior is retained for conv1 through conv3, with one-tick inter-layer propagation as used in the P08 source-semantics preflight.

Conv4 uses the source-recovered softmax treatment: it accumulates affine membrane evidence and is not expected to emit ordinary output spikes. Classification is:

```text
prediction = argmax(final_conv4_membrane_voltage[0:10])
```

`numpy.argmax` supplies the deterministic lowest-class-index tie break.

## Recorded measurements

The gate records:

- total correct predictions and validation accuracy;
- accepted ANN validation reference accuracy (`0.992600`);
- ANN-minus-SNN validation delta;
- ten-class confusion matrix;
- per-class accuracy;
- readout ties, all-equal evidence examples, and zero-evidence examples;
- final evidence minimum/maximum;
- input/conv1/conv2/conv3 total spikes and active-example counts;
- first-spike ticks and maximum candidate voltages;
- prediction and final-evidence fingerprints; and
- the exact P08.3.5c parameter/network/compiled identities.

Artifacts are written beneath:

```text
applications/mnist_v2_nxtf/artifacts/p08_3_5d_source_recovered_validation/
```

as:

```text
source_recovered_validation_manifest.json
source_recovered_validation_results.npz
```

## Acceptance philosophy

There is deliberately **no classification-accuracy threshold** in P08.3.5d.

The conversion was fixed before this measurement. A low result is therefore evidence to investigate, not permission to tune conversion against validation accuracy and rerun until a target is reached.

The gate only rejects structural degeneracy such as an entirely dead hidden network or identical readout evidence for all 5,000 examples. Those checks distinguish a meaningful classification measurement from the silent-network failure already observed in the superseded P08.3.5 path.

## After the run

The official test split remains locked after the script completes. The measured P08.3.5d result must be reviewed and explicitly accepted before P08.3 is frozen and any P08.4 official-test comparison is considered.
