# P08.3.4 Accepted-ANN to Converted-SNN Gate

**Status:** Verification candidate after source-bounded DThIR/Loihi representation corrections  
**Input checkpoint:** accepted P08.3.3 ANN only  
**Official MNIST test split:** locked

## Purpose

P08.3.4 converts the exact accepted P08.3.3 ANN into the integer spiking-network parameter set consumed by FPGA-v2. The conversion artifact is frozen before any converted-SNN validation accuracy or official-test accuracy is observed.

Accepted ANN identity:

```text
selected-weight fingerprint:
e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce

checkpoint SHA-256:
61f60eaa789dcf04131f658edb86db880999a5f0ad2c8f1bd06426d464dba7d2
```

## Calibration and floating normalization

Calibration uses only the deterministic 55,000-image training remainder. Every tenth retained training image is used, yielding 5,500 calibration examples. Validation labels and the official 10,000-image test split are not used.

The floating network uses the already accepted Rueckauer-style normalization:

```text
W_l(normalized) = W_l * lambda_(l-1) / lambda_l
b_l(normalized) = b_l / lambda_l
normalization percentile = 100% (maximum activation)
```

This policy remains unchanged by the integer-representation corrections below.

## What the two failed gates established

The first P08.3.4 run failed before any SNN accuracy evaluation because the project incorrectly treated an 8-bit Loihi weight as conventional signed `int8`:

```text
observed: [-218, 103]
incorrect assumed range: [-127, 127]
```

Loihi mixed-sign 8-bit weights instead use even mantissas spanning approximately:

```text
{-256, -254, ..., 0, ..., 252, 254}
```

with static quantization represented in FPGA-v2 as rounding toward zero to a step of two.

After correcting that representation, the second gate still failed:

```text
observed: [-276, 210]
Loihi mixed-sign range: [-256, 254]
```

This exposed a second project error: the converter multiplied every normalized parameter directly by `vThMant=512` even though the P08.3.1 hard-reset conversion policy had already frozen:

```text
desired_threshold_to_input_ratio = 8
```

Published Loihi conversion descriptions define DThIR as the fixed ratio between incoming neuron input and membrane threshold and state that conversion normalizes weights and biases to the hardware dynamic range while satisfying this ratio. The historical SNN Toolbox hard-reset example used DThIR `2**3 = 8` together with `vThMant=512`, `numWeightBits=8`, and `weightExponent=0`.

The exact historical NxSDK backend formula is not public. Therefore FPGA-v2 makes the following explicit **PROJECT_RECONSTRUCTION**, fixed before any SNN validation accuracy is observed:

```text
effective normalized-parameter scale
    = threshold_mantissa / desired_threshold_to_input_ratio
    = 512 / 8
    = 64
```

This interpretation directly applies the already-frozen DThIR rather than selecting a new scale after seeing accuracy.

## Final integer adaptation under test

Weights:

```text
raw_weight = normalized_weight * 64
integer_weight = trunc_toward_zero(raw_weight / 2) * 2

sign mode:       mixed
weight bits:     8
weight exponent: 0
range:            [-256, 254]
step:             2
clipping:         forbidden
```

Biases use the same DThIR-derived scale so the affine layer is not rescaled inconsistently relative to its synaptic inputs:

```text
integer_bias = round(normalized_bias * 64)
project bias range = [-2047, 2047]
clipping: forbidden
```

The exact native Loihi bias exponent/bitfield representation remains outside the equivalence claim.

Neither correction changes the ANN checkpoint, 5,500-image calibration corpus, activation lambdas, floating normalization formula, hard-reset neuron semantics, primary 100-timestep horizon, input encoding, decoder, or official-test lock.

## Converted graph and mapping boundary

The learned converted graph retains the accepted reconstruction:

```text
neurons:               4,218
expanded connections: 338,880
ANN parameters:        7,006
```

The graph is compiled through P06 with the accepted `900` compartments/core project mapping policy. The gate currently expects five project logical cores. This remains explicitly different from NxTF's reported 14 Loihi neurocores and will be reported as a compiler/resource-model discrepancy rather than presented as equivalent.

## Generated local artifacts

On success:

```text
applications/mnist_v2_nxtf/artifacts/p08_3_4_conversion/
├── converted_parameters.npz
├── conversion_manifest.json
├── converted_network.json
├── compiled_deployment.json
└── gate_result.json
```

The manifest records the accepted ANN identity, calibration fingerprints, activation lambdas, floating and integer ranges, DThIR=8, derived parameter scale=64, Loihi mixed-sign weight semantics, graph/deployment fingerprints, and explicit `official_test_used=false` / `test_examples_observed=0` fields.

## Acceptance boundary

P08.3.4 passes only if:

1. the exact P08.3.3 ANN checkpoint and manifest are used;
2. calibration remains the fixed 5,500-image training-only corpus;
3. all activation lambdas are finite and positive;
4. DThIR remains 8 and the derived parameter scale is exactly 64;
5. every weight is an even mixed-sign mantissa in `[-256, 254]`, every bias fits the frozen project range, and no clipping occurs;
6. the learned graph retains 4,218 neurons and 338,880 expanded connections;
7. P06 compiles the exact converted graph to five valid project logical cores;
8. serialized conversion/network/deployment fingerprints recompute; and
9. no official-test examples are observed.

P08.3.4 still does **not** set or tune an SNN-accuracy target. Validation-only 100-timestep SNN behavior belongs to the next gate after this conversion artifact is independently accepted.
