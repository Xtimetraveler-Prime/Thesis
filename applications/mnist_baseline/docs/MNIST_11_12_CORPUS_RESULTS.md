# MNIST-11/12 — Accepted 30-Image Matched Corpus Results

**Status:** Accepted software/reference evidence

## Scope

The exact frozen 30-image MNIST conformance corpus from `mnist-v1` was replayed through:

1. FPGA-v1 Python golden semantics;
2. pinned Brian2Loihi `0.5.2`;
3. pinned Catalyst N1 generic CPU SDK using the graph-preserving `784 source -> 10 output` construction; and
4. the independent Catalyst delivered-drive CPU control.

All targets consumed the same source-controlled request bundle and unchanged native-sparse deployment:

```text
784 input axons
10 output neurons
4,086 stored effective synapses
16 deterministic ticks/image
zero recurrent routes
same frozen effective weights
same spike-count decoder
no retraining or target-specific tuning
```

The 30-image set is a deliberately selected conformance corpus, not an unbiased accuracy benchmark. Its 17/30 correct project predictions must therefore not be reported as MNIST test accuracy.

Compact evidence is archived under:

```text
applications/mnist_baseline/evidence/mnist-11-12/matched-corpus-v1/
```

## Brian2Loihi result

Brian2Loihi reproduced the project reference exactly on every corpus case:

```text
cases:                         30 / 30
prediction agreement:          30 / 30
final spike-vector agreement:  30 / 30
exact state/spike traces:       30 / 30
case pass:                      30 / 30
```

Each case also reported zero effective-weight mismatches across all 4,086 frozen synapses. Therefore the accepted feed-forward native-sparse workload shows exact agreement with the pinned Brian2Loihi reference at the effective-weight, current, voltage, spike, spike-count, and decoded-prediction boundaries represented by the adapter.

This is stronger than the earlier loose MNIST-10 comparison to a different published Loihi workload. It is still a **software-emulator comparison**, not a measurement on Intel Loihi silicon.

## Catalyst internal-control result

The two independently constructed Catalyst CPU experiments agreed exactly with each other on all 30 images after the declared one-native-tick graph pipeline alignment:

```text
Catalyst transport-consistent cases: 30 / 30
internal voltage/spike trace mismatch: 0 on every case
```

This establishes that the observed FPGA-v1/Catalyst differences are not caused by the 4,086-edge graph translation or by the delivered-drive adapter.

## Catalyst versus FPGA-v1

Catalyst preserved the decoded FPGA-v1 prediction on every corpus image:

```text
graph-preserving prediction agreement: 30 / 30
delivered-drive prediction agreement:  30 / 30
```

However, exact final spike-count vectors agreed on only 26/30 cases:

```text
graph-preserving spike-vector agreement: 26 / 30
delivered-drive spike-vector agreement:  26 / 30
```

The four spike-vector differences occurred at MNIST indices:

```text
3, 7, 30, 149
```

In each case Catalyst produced exactly one additional spike in a **non-winning** output neuron while leaving the decoded class unchanged:

| MNIST index | label | decoded class | FPGA-v1 -> Catalyst spike-count change |
| ---: | ---: | ---: | --- |
| 3 | 0 | 0 | neuron 2: `1 -> 2` |
| 7 | 9 | 9 | neuron 3: `1 -> 2` |
| 30 | 3 | 3 | neuron 7: `5 -> 6` |
| 149 | 2 | 9 | neuron 4: `1 -> 2` |

Index 149 is intentionally one of the frozen both-wrong cases: both systems preserve the same incorrect class `9`. The corpus is designed to exercise behavior, not estimate classifier accuracy.

## Causal divergence classification

All 30 Catalyst cases first diverged from FPGA-v1 for the same predeclared semantic reason:

```text
CATALYST_SUB_REST_CLAMP: 30
EXACT first-divergence cases: 0
OTHER_TRANSLATED_DYNAMICS: 0
TRANSPORT_INCONSISTENT: 0
```

At the first divergent tick, Catalyst replaces negative project membrane values with its resting value `0` while preserving nonnegative values. For example, index 3 begins with:

```text
FPGA-v1: [0, -13888, 2176, -2368, -3840, 192, 3328, 2112, 832, 448]
Catalyst: [0,      0, 2176,     0,     0, 192, 3328, 2112, 832, 448]
```

The same relationship appears in both Catalyst constructions, so later voltage/spike differences are downstream consequences of a known target-native neuron semantic rather than independent unexplained mismatches.

## Interpretation

The corpus supports two distinct claims:

1. **FPGA-v1 vs Brian2Loihi:** exact matched behavior was observed across all 30 selected images under the declared feed-forward common subset.
2. **FPGA-v1 vs Catalyst N1:** the matched effective graph preserves classification on all 30 selected images, while Catalyst's explicit sub-rest membrane clamp changes lower-level state on every image and changes the final spike-count vector on 4/30 without changing the winner.

The result does **not** establish that Catalyst will preserve predictions on the full 10,000-image test set. That is the next useful experiment because the 30-image corpus now demonstrates the adapter is stable and isolates the relevant semantic difference.

## Milestone implications

This evidence closes:

```text
MNIST-11.4 — Frozen 30-image Brian2Loihi corpus
MNIST-12.3 — Catalyst CPU/reference matched experiment
```

MNIST-11.5 remains the full 10,000-image Brian2Loihi evaluation. The same full-test pass is also useful for quantifying the application-level sensitivity to Catalyst's resting-floor rule before the final MNIST-12 comparison matrix is frozen.

Physical graph-preserving Catalyst MNIST remains blocked at the pinned M13.5 K26 boundary: the upstream wrapper configures 512 neurons, while the matched graph materializes 794, and the pinned release does not provide a source-supported programmable KV260 integration.
