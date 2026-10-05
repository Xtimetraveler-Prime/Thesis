# P08.4.1 Official-Test Evaluation Acceptance

## Status

**Accepted:** 2026-09-30

P08.4.1 is accepted as the first and frozen evaluation of the P08 ANN and
source-recovered SNN on the untouched official 10,000-image MNIST test split.
The test result is evidence only; no checkpoint, conversion, threshold, decoder,
topology, or timestep selection is permitted after observing it.

## Accepted result

```text
examples=10000
timesteps=100
ANN accuracy=0.987400
SNN accuracy=0.982400
ANN-SNN delta=0.005000
```

Agreement breakdown:

```text
both_correct=9797
ann_only=77
snn_only=27
both_wrong=99
```

The SNN readout remained nondegenerate:

```text
ties=1
all_equal=0
zero_evidence=0
evidence_range=[-5542,2233]
```

All 10,000 test samples produced activity at every tracked stage:

```text
stage_total_spikes=[11614721,7914125,4493190,489987]
stage_active_examples=[10000,10000,10000,10000]
```

## Frozen artifact identities

```text
ANN weights:
e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce

source-recovered parameters:
9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e

network:
6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13

compiled deployment:
5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

Deterministic result identities:

```text
ANN predictions:
7f807496616d93cf76a456bb83a97ff17ca39028b894b9398005ff6a88989f0e

SNN predictions:
16910272d13517fd3b67fb205f8773882bbbb8c576d9f63ebe6e350be2b64741

SNN final evidence:
34263540ebb85fb03dcee878b2984e1373aee9ad4e8ad03183c790ee9c8810f4
```

## Test-use boundary

The accepted result records:

```text
official_test_used=true
test_examples_observed=10000
selection_decisions_after_test=0
post_test_tuning=false
```

P08.4 may now use the official test split for reporting and deterministic
conformance corpus construction, but the accepted model/conversion is frozen.
No later official-test observation may feed back into model or conversion
selection.

## Next gate

P08.4.2 must execute the exact accepted compiled deployment through the
packet-level logical/paged execution path and prove equivalence to the accepted
source-recovered software semantics under legal service, packet-drain, and
context-page ordering before the physical K26 conformance run.
