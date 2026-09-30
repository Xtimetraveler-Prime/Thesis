# P08.3.4 Accepted-ANN to Converted-SNN Gate

**Status:** Verification candidate after source-backed weight-representation correction  
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

## Loihi weight-representation correction discovered by the first gate

The first P08.3.4 run reached the representation check and failed before any SNN-accuracy evaluation:

```text
observed normalized integer-weight range: [-218, 103]
initial assumed range:                    [-127, 127]
```

That failure exposed an error in the **project representation assumption**, not an ANN or normalization failure. The initial gate had treated an 8-bit Loihi weight as a conventional signed two's-complement `int8`. Loihi's mixed-sign weight mantissa does not use that range.

The source-backed Loihi arithmetic record used by FPGA-v2 (including the Brian2Loihi/M22 evidence in `LOIHI1_TARGET_SPEC.md`) describes the effective weight as a mantissa plus exponent. For mixed-sign 8-bit weights, the mantissa values have a two-count precision step and span:

```text
{-256, -254, ..., -2, 0, 2, ..., 252, 254}
```

Static initialization is represented here with truncation toward zero to the nearest representable step. The historical SNN Toolbox Loihi configuration used for P08 source-style evidence specifies:

```text
numWeightBits = 8
weightExponent = 0
vThMant = 512
```

The threshold and exponent-zero weight paths share the same implicit native Loihi power-of-two scale. FPGA-v2 operates at the normalized architectural integer boundary rather than reproducing those hidden bitfield shifts, so the common scale is not applied a second time. The project therefore continues to store threshold mantissa `512` and the corresponding weight mantissas directly.

This correction was made **before any converted-SNN validation accuracy was observed**. It does not change the ANN checkpoint, calibration corpus, activation lambdas, normalization formula, 100-timestep horizon, reset policy, or decoder, and it is not an accuracy-tuning step.

## FPGA-v2 integer adaptation after correction

The source normalization and FPGA-v2 integer representation remain recorded separately.

For weights:

```text
raw_weight_mantissa = normalized_weight * 512
integer_weight = trunc_toward_zero(raw_weight_mantissa / 2) * 2

sign mode:       mixed
weight bits:     8
weight exponent: 0
representable:   [-256, 254] in steps of 2
threshold:       512
```

For biases, P08 retains the already frozen conservative project adaptation pending any need for a more detailed native-bias audit:

```text
integer_bias = round(normalized_bias * 512)
project bias range = [-2047, 2047]
```

**No clipping is permitted.** A weight or bias outside its accepted representation still causes a hard conversion failure.

The converted artifact explicitly records the weight sign mode, step, rounding policy, exponent, range, and the fact that this representation correction superseded the rejected conventional-int8 assumption.

## Converted graph

The converted P06 graph retains the accepted reconstruction exactly:

```text
neurons:               4,218
expanded connections: 338,880
ANN parameters:        7,006
```

Each output channel remains its own P06 population so its learned integer bias maps directly to the compartment configuration. Every spatial use of a convolution coefficient receives the converted integer value from the corresponding Keras kernel.

The converted graph is compiled through the normal P06 mapper with the already accepted P08 mapping policy (`900` compartments/core). The gate expects five logical cores because the graph has a five-core compartment-count lower bound. This remains the project's P06 mapping, not a claim of equality with NxTF's reported 14-neurocore mapping.

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
- Loihi mixed-sign weight range, step, rounding, and exponent;
- zero-valued integer coefficient counts;
- normalization and bias-adaptation rules;
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
4. every weight is a valid even mixed-sign mantissa in `[-256, 254]` and every bias fits the frozen project range, with no clipping;
5. the converted graph retains 4,218 neurons and 338,880 expanded connections;
6. P06 compiles the exact converted graph to five valid logical cores;
7. serialized conversion/network/deployment fingerprints recompute; and
8. no official-test examples are observed.

P08.3.4 does **not** set or tune an SNN-accuracy acceptance target. Validation-only 100-timestep SNN behavior belongs to the next gate after the conversion artifact itself is frozen.
