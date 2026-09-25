# MNIST-11/12 — Full Matched External-Reference Results

**Status:** Accepted full-test software comparison; final branch regression pending before merge

## Scope

This result uses the frozen `mnist-v1/native-sparse` deployment on the complete official 10,000-image MNIST test split.

Every target receives the same application contract:

```text
28x28 source representation
784 external input axons
10 output neurons
4,086 stored effective connections
16 deterministic presentation ticks
zero recurrent routes
zero initial state
same frozen weights
same spike-count decoder
no retraining or target-specific tuning
```

The full request set was generated deterministically as 100 shards of 100 test images. The archive records the request-index hash and request-manifest SHA-256 so the evaluated scope can be reproduced without committing all large transient request files.

Accepted evidence:

```text
applications/mnist/evidence/mnist-11-12/matched-full-v1/
```

## Result summary

| Target | State/transport result | Spike-vector agreement | Prediction agreement | Accuracy | Evidence class |
|---|---:|---:|---:|---:|---|
| FPGA-v1 golden | project authority | 10,000/10,000 reference | 10,000/10,000 reference | 91.71% | project golden |
| Brian2Loihi 0.5.2 | exact current/voltage/spike trace on 10,000/10,000 | 10,000/10,000 | 10,000/10,000 | 91.71% | matched graph + matched/equivalent dynamics |
| Catalyst N1 graph CPU | internally exact with independent delivered-drive control on 10,000/10,000 | 9,079/10,000 | 9,995/10,000 | 91.74% | matched effective graph + translated dynamics |
| Catalyst N1 delivered-drive CPU | internally exact with graph path on 10,000/10,000 | 9,079/10,000 | 9,995/10,000 | 91.74% | matched delivered drive + translated dynamics |
| Catalyst pinned K26 | matched graph does not fit / no source-supported board-programming path | — | — | — | feasibility boundary only |
| Published Intel Loihi / NxTF | different network/workload | — | — | 99.21% published | unmatched literature reference |

The published Loihi row remains MNIST-10 context. It is not used to calculate a speedup, accuracy advantage, or energy ratio against this frozen application.

## MNIST-11 — Brian2Loihi

Brian2Loihi matched FPGA-v1 exactly across the entire official test split:

```text
case count:                     10,000
project accuracy:               91.71%
Brian2Loihi accuracy:           91.71%
prediction agreement:           10,000 / 10,000
spike-count-vector agreement:   10,000 / 10,000
exact trace agreement:          10,000 / 10,000
all cases passed:               true
```

The per-image runner also verifies the effective Brian2Loihi `w_act` values against the 4,086 frozen project weights before accepting trace comparison.

### Interpretation

For this frozen feed-forward inference application, the project does more than reproduce Brian2Loihi's final accuracy. It reproduces the pinned Brian2Loihi model exactly at the observed effective-weight, current, voltage, spike-set, final spike-count, and decoded-prediction boundary for all 10,000 official MNIST test images.

This is evidence of application-level semantic equivalence for the tested subset, not a claim that FPGA-v1 implements every feature of Loihi. Brian2Loihi is software, not Intel Loihi silicon, and CPU runtime is not a hardware-performance measurement.

## MNIST-12 — Catalyst N1

Both Catalyst constructions were internally trace-identical for all 10,000 images:

```text
Catalyst graph/direct transport consistency: 10,000 / 10,000
transport inconsistencies:                        0
```

The first FPGA-v1/Catalyst state divergence was classified as the predeclared `CATALYST_SUB_REST_CLAMP` in every image:

```text
sub-rest-clamp first divergences: 10,000 / 10,000
other first-divergence classes:        0
```

At the application outputs:

```text
spike-count-vector agreement: 9,079 / 10,000 = 90.79%
spike-vector differences:       921 / 10,000 =  9.21%
prediction agreement:         9,995 / 10,000 = 99.95%
prediction differences:           5 / 10,000 =  0.05%
```

The five official test indices with different decoded predictions are:

```text
1012, 1868, 4548, 6157, 7426
```

Catalyst graph accuracy is `91.74%`, compared with `91.71%` for FPGA-v1/Brian2Loihi. This `+0.03` percentage-point net difference is descriptive only. The experiment is not designed to rank classifiers; it measures sensitivity of the unchanged frozen network to an independently chosen neuron rule.

### Propagation hierarchy

The Catalyst result exposes three distinct comparison levels:

```text
internal voltage semantics differ: 100.00% of images
final spike vector differs:          9.21% of images
decoded class differs:               0.05% of images
```

This is useful because a state-level architectural difference does not automatically imply a different application decision. Here the resting-floor rule is ubiquitous internally, observable in roughly one in eleven spike-count vectors, but changes only five of ten thousand classifications.

## Catalyst physical boundary

The pinned Catalyst K26 wrapper audited in M13.5 provides:

```text
2 cores x 256 neurons/core = 512 configured neurons
```

The graph-preserving matched MNIST construction requires:

```text
784 source neurons + 10 output neurons = 794 neurons
```

Therefore the declared matched graph cannot fit the pinned wrapper. The same pinned source lacks the board XDC, PS/block-design integration, and `write_bitstream` path required for a source-supported programmable KV260 image.

For that reason, MNIST-12 closes the physical sub-gate as **infeasible at the pinned-source boundary**. No Catalyst physical MNIST latency, energy, or classification result is claimed. Building a larger Catalyst configuration and thesis-owned KV260 integration would be a new implementation experiment.

## Thesis-facing conclusion

The matched MNIST experiment now supports three qualitatively different statements:

1. **FPGA-v1 versus Brian2Loihi:** exact application-level behavioral equivalence for this frozen feed-forward inference workload across the complete official test set.
2. **FPGA-v1 versus Catalyst N1:** controlled translated-dynamics comparison in which the first divergence is fully explained by Catalyst's resting-floor semantic rule; output behavior remains highly robust despite universal internal-state divergence.
3. **FPGA-v1 versus published Intel Loihi:** literature context only, because the published NxTF network and workload are not matched to the project deployment.

These statements should remain separate in the thesis. In particular, Brian2Loihi exactness strengthens the Loihi-inspired semantic claim, but neither Brian2Loihi nor Catalyst CPU results constitute execution on Intel Loihi silicon.

## Closure

With the accepted full-test archive:

- **MNIST-11 is complete.**
- **MNIST-12 is complete at the pinned-source boundary.**
- the physical Catalyst matched-graph sub-gates are closed as infeasible/not applicable, not as successful hardware runs;
- a future expanded Catalyst/KV260 implementation should be tracked as a separate milestone if pursued; and
- actual Intel Loihi/Lava execution remains a separate future experiment if authenticated hardware access becomes available.
