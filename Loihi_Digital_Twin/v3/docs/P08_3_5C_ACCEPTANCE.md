# P08.3.5c Source-Recovered Conversion Acceptance

## Status

**ACCEPTED** — 2026-09-30

P08.3.5c replaces the earlier P08.3.4 blanket-scale conversion as the forward-execution artifact while preserving P08.3.4 for audit history.

The acceptance gate completed with 15 tests passing and with no official MNIST test examples observed.

## Accepted source semantics

```text
calibration examples:            5500
input threshold:                 2040
conv1 threshold:                  556
conv2 threshold:                  512
conv3 threshold:                  672
softmax/readout threshold:     131071
softmax decoder: final membrane voltage argmax
output spike-count decoder:     false
```

The BIAS-style pixel input remains an ingress/encoder concern rather than an additional P06 computational population. The accepted comparison graph therefore remains:

```text
computational neurons:   4218
expanded connections:  338880
P06 logical cores:          5
resident K26 contexts:      3
physical engines:           1
```

## Accepted artifact identities

```text
parameter fingerprint:
9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e

network fingerprint:
6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13

compiled deployment fingerprint:
5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

These identities are the required input to the next validation-only gate. A later conversion must not silently replace them.

## Test-set lock

The accepted run reported:

```text
official_test_used=false
test_examples_observed=0
classification_accuracy_evaluated=false
```

P08.3.5c therefore did not use classification accuracy to select or tune the source-recovered conversion.

## Next gate

P08.3.5d may measure classification behavior only on the frozen 5,000-image validation partition at 100 timesteps. It must:

1. require the exact artifact fingerprints above;
2. preserve the source-recovered BIAS input and per-layer thresholds;
3. decode class from the final conv4 membrane-voltage evidence vector;
4. record ties, confusion matrix, class accuracy, hidden activity, and deterministic fingerprints;
5. use no accuracy threshold for parameter selection; and
6. keep the official 10,000-image MNIST test split locked.
