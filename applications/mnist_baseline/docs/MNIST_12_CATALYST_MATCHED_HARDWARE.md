# MNIST-12 — Catalyst N1 Matched Architecture Experiment

**Status:** Complete at the pinned-source boundary

## Goal

MNIST-12 uses **Catalyst N1**, the same independent Loihi-class architecture audited in core M13, as an application-level comparison target for the unchanged frozen native-sparse MNIST workload.

Catalyst is not Intel Loihi. Its role is to answer:

> If the same frozen effective graph, weights, input events, initial state, and decoder are evaluated under Catalyst N1's independently chosen neuron semantics, where do the two architectures first diverge and how often does that difference propagate into spikes or classification?

The milestone includes a matched Catalyst CPU/reference experiment and an explicit physical-K26 feasibility audit. It does not claim a Catalyst hardware result where the pinned artifact cannot represent the declared graph.

## Frozen upstream reference

```text
repository: catalyst-neuromorphic/catalyst-n1
commit:     1806bb4b4114d7671e5648fa75b7b83b3a8d5543
tag:        v2.3-paper
```

M13 already reproduced the pinned Catalyst CPU/RTL regressions, directed semantic probes, and routed K26-class implementation. MNIST-12 reuses those accepted reference boundaries rather than changing Catalyst source to force application agreement.

## Frozen matched application contract

```text
784 external axons
10 output neurons
4,086 nonzero effective connections
16 deterministic ticks
zero recurrent routes
same effective signed integer weights
same zero initial state
same spike-count decoder
no retraining
```

Both MNIST-11 and MNIST-12 consume the same backend-neutral request data generated from `applications/mnist_baseline/frozen/mnist-v1/`.

## Two independent Catalyst CPU views

### Graph-preserving reference

The generic pinned Catalyst SDK supports 1,024 neurons per software core, so the application is materialized as:

```text
784 source neurons + 10 output neurons = 794 neurons
4,086 exact effective-weight edges
```

Each external axon event drives a threshold-1 source neuron. Catalyst's synchronous source-to-target pipeline is normalized by comparing project canonical tick `k` with Catalyst output tick `k+1`.

Evidence label:

```text
MATCHED EFFECTIVE GRAPH + TRANSLATED DYNAMICS
```

### Delivered-drive reference

A second construction independently collapses every active external axon row into the exact ten per-output fan-in currents and injects those currents directly into Catalyst output neurons.

Because many valid signed-int16 synaptic weights can converge in one tick, the collapsed current is retained as signed 32-bit in the Catalyst CPU simulator. It is not clipped or rescaled to the older M13 hardware-common signed-int16 direct-stimulus envelope.

Evidence label:

```text
MATCHED DELIVERED DRIVE + TRANSLATED DYNAMICS (CPU INT32 CONTROL)
```

The two Catalyst views must match each other at every normalized output voltage vector and spike set. A project/Catalyst difference is scientific evidence; a graph/direct Catalyst mismatch is an adapter failure.

## Predeclared semantic difference

The primary relevant Catalyst N1 difference was identified before application outputs were accepted: Catalyst's simple LIF update floors a sufficiently negative sub-rest membrane state back to its resting value `0`, while FPGA-v1 retains signed negative voltage.

The automated divergence classifier labels a case `CATALYST_SUB_REST_CLAMP` only when:

1. the graph-preserving and delivered-drive Catalyst traces are internally identical;
2. their first mismatch against FPGA-v1 is the same voltage vector; and
3. that candidate vector is exactly the project vector with every negative element replaced by `0`.

Later state/spike differences are treated as downstream effects of that first divergence rather than independently relabeled.

## Accepted results

### Two-image anchor

Indices `3` and `1` established the matched execution path. Both Catalyst constructions were internally trace-identical and produced the same decoded class as FPGA-v1. The first project/Catalyst mismatch in both cases was the predeclared sub-rest clamp.

### Frozen 30-image corpus

```text
cases:                            30
Catalyst internal trace match:    30 / 30
project/Catalyst prediction match:30 / 30
project/Catalyst spike-vector:    26 / 30
first divergence = sub-rest clamp:30 / 30
unexplained first divergences:     0
```

The four spike-vector differences occurred at official test indices `3`, `7`, `30`, and `149`. In each case Catalyst added exactly one spike to a non-winning output neuron, so the decoded class was unchanged.

### Full official 10,000-image test set

The final matched software experiment produced:

```text
cases:                                  10,000
Catalyst internal transport consistency:10,000 / 10,000
project accuracy:                        91.71%
Catalyst graph accuracy:                 91.74%
prediction agreement:                    9,995 / 10,000  (99.95%)
spike-count-vector agreement:             9,079 / 10,000  (90.79%)
spike-vector differences:                   921 / 10,000  (9.21%)
first divergence = sub-rest clamp:       10,000 / 10,000
other first-divergence categories:            0
transport inconsistencies:                   0
```

The five decoded-prediction differences occur at official MNIST test indices:

```text
1012, 1868, 4548, 6157, 7426
```

The 91.74% versus 91.71% accuracy difference is reported descriptively as `+0.03` percentage points for this frozen test set. It is **not** interpreted as Catalyst being a better classifier: the network was trained for FPGA-v1 semantics, only five predictions changed, and the purpose of the experiment is semantic sensitivity rather than architecture ranking.

The important result is the propagation hierarchy:

```text
known state-level semantic divergence: 100.00% of images
final spike-vector difference:           9.21% of images
decoded-class difference:                0.05% of images
```

Thus Catalyst's resting-floor rule is observable on every image at the internal-state boundary, but the frozen classifier is highly robust to it at the decoded-output boundary.

## Physical K26 feasibility boundary

The pinned M13.5 Catalyst K26 wrapper is not equivalent in capacity to the generic CPU simulator:

```text
configured cores:          2
neurons/core:              256
total configured neurons: 512
matched graph requirement: 794 neurons
```

Therefore the graph-preserving matched MNIST workload does **not** fit the pinned K26 wrapper (`794 > 512`). The same upstream snapshot also lacks the board XDC, PS/block-design integration, and `write_bitstream` programming path required for a source-supported physical KV260 run.

M13 reproduced routed implementation, but that resource/timing evidence is context only. It is not an application-level Catalyst MNIST latency measurement.

A custom expanded Catalyst FPGA configuration and KV260 integration could be built as future thesis-owned work, but that would be a **new implementation experiment** and must not be represented as execution of the pinned upstream artifact used here.

## Interpretation

MNIST-12 establishes a controlled matched-application comparison to an independent neuromorphic architecture:

- graph translation is internally validated by two exact Catalyst constructions;
- the first project/Catalyst divergence is deterministic and explained by a semantic rule declared before full-test results;
- that state difference changes spike-count vectors much more often than it changes decoded classifications; and
- the physical matched-graph comparison is infeasible on the pinned Catalyst K26 artifact and is recorded as such rather than fabricated.

No Catalyst CPU wall time, board TDP, or Vivado power estimate is compared against FPGA-v1 architectural latency or energy.

## Sub-milestone closure

- **MNIST-12.1 — Upstream/K26 feasibility audit:** Complete.
- **MNIST-12.2 — Semantic mapping audit:** Complete.
- **MNIST-12.3 — Catalyst CPU/reference matched experiment:** Complete through the full official 10,000-image test set.
- **MNIST-12.4 — Physical Catalyst N1 K26 run:** Closed as infeasible for the declared matched graph at the pinned-source boundary (`794 > 512` plus missing board programming integration). No physical result is claimed.
- **MNIST-12.5 — Same-K26 characterization:** Closed/not applicable for the matched application because no equivalent Catalyst physical execution boundary exists. M13 routed results remain context only.
- **MNIST-12.6 — Final matched matrix:** Complete.

See also:

```text
docs/MNIST_11_12_ANCHOR_RESULTS.md
docs/MNIST_11_12_CORPUS_RESULTS.md
docs/MNIST_11_12_FULL_TEST_RESULTS.md
applications/mnist_baseline/evidence/mnist-11-12/matched-full-v1/
```
