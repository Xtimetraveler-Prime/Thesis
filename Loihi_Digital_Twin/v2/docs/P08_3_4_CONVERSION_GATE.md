# P08.3.4 Accepted-ANN to Converted-SNN Gate

**Status:** Verification candidate  
**Input checkpoint:** accepted P08.3.3 ANN only  
**Official MNIST test split:** locked

## Purpose

P08.3.4 converts the exact P08.3.3 ANN into the integer spiking-network parameter set consumed by FPGA-v2. This gate freezes conversion artifacts before any official-test evaluation and before validation accuracy is used to judge the converted SNN.

The accepted ANN identity is:

```text
selected-weight fingerprint:
e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce

checkpoint SHA-256:
61f60eaa789dcf04131f658edb86db880999a5f0ad2c8f1bd06426d464dba7d2
```

P08.3.4 refuses to convert a different checkpoint.

## Calibration boundary

Calibration uses only the deterministic 55,000-image training remainder. Following the already frozen P08.3.1 policy, every tenth retained training image is used, yielding exactly 5,500 calibration examples.

No validation labels are used by parameter normalization, and the official 10,000-image test split remains unavailable to the conversion pipeline.

## Floating ANN normalization

The project uses the Rueckauer et al. data-normalization relationship:

```text
W_l(normalized) = W_l * lambda_(l-1) / lambda_l
b_l(normalized) = b_l / lambda_l
```

where `lambda_l` is the measured activation scale of layer `l` on the calibration corpus.

P08.3.4 resolves the previously unspecified normalization percentile before observing converted-SNN accuracy:

```text
normalization percentile = 100% (maximum activation)
```

This is deliberately not tuned after conversion. The hidden-layer lambdas are measured from the ReLU outputs of `conv1`, `conv2`, and `conv3` with dropout inactive. The ANN's final softmax is not itself converted to a spiking operation; `conv4` is calibrated as its affine output followed by ReLU, and classification remains the frozen output-spike-count readout.

## FPGA-v2 integer adaptation

The source normalization and FPGA-v2 integer representation are recorded separately.

The normalized mathematical SNN has threshold 1. FPGA-v2 uses the accepted integer threshold mantissa 512, so P08.3.4 applies:

```text
integer weight = round(normalized weight * 512)
integer bias   = round(normalized bias   * 512)
threshold      = 512
```

The frozen project ranges remain:

```text
weight: [-127, 127]
bias:   [-2047, 2047]
```

**No clipping is permitted.** If any accepted normalized parameter exceeds these ranges, conversion fails. A later policy change would have to be documented explicitly rather than silently saturating parameters.

This integer step is a `PROJECT_RECONSTRUCTION`; it is not claimed to reproduce undocumented NxTF/NxSDK fixed-point packing bit-for-bit.

## Converted graph

The converted P06 graph retains the accepted reconstruction exactly:

```text
neurons:               4,218
expanded connections: 338,880
ANN parameters:        7,006
```

Each output channel remains its own P06 population so its learned integer bias maps directly to the compartment configuration. Every spatial use of a convolution coefficient receives the converted integer value from the corresponding Keras kernel.

The converted graph is compiled through the normal P06 mapper with the already accepted P08 mapping policy (`900` compartments/core). The gate expects five logical cores because the graph has a five-core compartment-count lower bound and the converted/shared representation cannot require more storage than the coefficient-identity structural probe merely because equal quantized values share more readily.

## Generated local artifacts

On success the gate promotes:

```text
applications/mnist_v2_nxtf/artifacts/p08_3_4_conversion/
├── converted_parameters.npz
├── conversion_manifest.json
├── converted_network.json
├── compiled_deployment.json
└── gate_result.json
```

The generated directory remains Git-ignored.

The conversion manifest records:

- accepted ANN identities;
- training/calibration dataset and split fingerprints;
- activation lambdas;
- per-layer floating/normalized/integer ranges;
- zero-valued integer coefficient counts;
- normalization and quantization rules;
- converted parameter fingerprint;
- converted P06 network fingerprint;
- compiled deployment fingerprint;
- logical/resident/physical counts; and
- explicit `official_test_used=false` / `test_examples_observed=0` fields.

## Acceptance boundary

P08.3.4 passes only if:

1. the accepted P08.3.3 checkpoint and manifest identities match exactly;
2. the fixed 5,500-image training-only calibration corpus is used;
3. all activation lambdas are finite and positive;
4. all normalized weights/biases quantize without clipping or overflow;
5. the converted graph retains 4,218 neurons and 338,880 expanded connections;
6. P06 compiles the exact converted graph to five valid logical cores;
7. serialized conversion/network/deployment fingerprints recompute; and
8. no official-test examples are observed.

P08.3.4 does **not** set or tune an SNN-accuracy acceptance target. Validation-only 100-timestep SNN behavior belongs to the next gate after the conversion artifact itself is frozen.
