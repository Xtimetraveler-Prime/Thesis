# P08.3.4 Acceptance Record

**Accepted:** 2026-09-30  
**Gate:** `scripts/run_p08_3_4_conversion.sh`  
**Official MNIST test split:** not used

P08.3.4 is accepted from Diego's independent local verification.

Verified result:

```text
22 passed
threshold mantissa:        512
hard-reset DThIR:          8
parameter scale:           64
weight representation:     Loihi mixed-sign 8-bit mantissa
weight range:              [-256, 254]
weight step:               2
weight rounding:           toward zero
weight exponent:           0
clipping:                  none
logical cores:             5
resident K26 contexts:     3
physical compute engines:  1
expanded connections:      338880
official_test_used:        false
test_examples_observed:    0
```

Observed converted ranges:

```text
conv1: weights [-26, 12], biases [-2, 2]
conv2: weights [-30, 22], biases [-1, 3]
conv3: weights [-24, 18], biases [ 0, 3]
conv4: weights [-34, 26], biases [-1, 1]
```

Accepted identities:

```text
conversion:
686e801cf2459d66772a3517cfff0411746ce97d7a84fb45554ca3ee8345cb75

converted network:
4f7dc2b2ecfd4db7c347fc8c846aed3ad5f03d57ceb48ed973530e77865bc211

compiled deployment:
1dc5191354566e9e40cdfe624ff6fc48528d1b78a91d2a16a4336d12b1a4296c
```

Two earlier P08.3.4 gate failures are retained as useful engineering evidence. The first rejected the project's incorrect conventional signed-int8 assumption. The second showed that Loihi mixed-sign mantissas alone were insufficient because the converter was not applying the already-frozen hard-reset DThIR=8. Both corrections were made before any converted-SNN validation accuracy was observed.

P08.3.5 may therefore measure validation-only SNN behavior using exactly the identities above. No conversion parameter may be changed in response to that measurement without opening a new, explicitly documented policy decision.
