# MNIST-12 — Catalyst N1 Matched Architecture Experiment

**Status:** In progress — MNIST-12.1 through MNIST-12.3 complete; pinned physical K26 path blocked; full-test sensitivity and final matrix remain

## Goal

MNIST-12 uses **Catalyst N1**, the same independent Loihi-class architecture audited in core M13, as an application-level comparison target for the unchanged frozen native-sparse MNIST workload.

Catalyst is not Intel Loihi. Its role is to test the same effective graph and inputs under an independently designed fixed-point/event-driven LIF architecture and to separate graph/transport effects from neuron-model effects.

## Frozen upstream reference

```text
repository: catalyst-neuromorphic/catalyst-n1
commit:     1806bb4b4114d7671e5648fa75b7b83b3a8d5543
tag:        v2.3-paper
```

M13 already established:

- 25/25 pinned Catalyst RTL regressions;
- 56/56 Catalyst CPU tests;
- directed project/Brian/Catalyst semantic probes;
- routed Catalyst K26-class Vivado implementation; and
- the strongest source-supported K26 hardware boundary.

MNIST-12 reuses those authorities rather than altering Catalyst to look like FPGA-v1.

## Frozen matched workload

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

Brian2Loihi and Catalyst consume the same immutable matched request data.

## Two independent Catalyst CPU views

### Graph-preserving reference

The generic pinned SDK exposes `1024` neurons/core, so the software reference can materialize:

```text
784 source neurons + 10 output neurons = 794 neurons
4,086 exact effective-weight edges
```

Each source event produces a Catalyst source-neuron spike and traverses Catalyst's own compiler/adjacency path. Because synchronous Catalyst delivers newly generated source spikes on the following native timestep, comparison uses:

```text
project canonical tick k <-> Catalyst native output tick k+1
```

Evidence label:

```text
MATCHED EFFECTIVE GRAPH + TRANSLATED DYNAMICS
```

### Delivered-drive reference

The same axon schedule is independently collapsed to the exact ten per-output fan-in sums for each tick. The pinned Catalyst CPU simulator represents injected current and its synchronous soma accumulator with signed 32-bit arrays, so fan-in sums wider than signed int16 are preserved exactly. Individual stored synaptic weights remain signed-int16-compatible.

This control uses:

```text
strict FPGA-v1 V > T -> Catalyst V >= T+1
project R=1 reference -> Catalyst refrac=0
zero bias/reset
same exact fan-in delivered current
```

Evidence label:

```text
MATCHED DELIVERED DRIVE + TRANSLATED DYNAMICS (CPU INT32 CONTROL)
```

The graph and delivered-drive traces must be identical after pipeline alignment. A disagreement between them is an adapter/transport failure; a common disagreement with FPGA-v1 is an architecture result.

## Confirmed semantic divergence: sub-rest membrane clamp

Catalyst's simple LIF update floors sufficiently negative membrane results to its resting value `0`. FPGA-v1 preserves negative membrane state. This difference was identified before the corpus results and is classified as:

```text
sub_rest_negative_voltage -> UNREPRESENTABLE
```

The accepted anchor and 30-image corpus confirm the effect directly. At each case's first divergence, Catalyst's output voltage vector equals the FPGA-v1 vector with negative entries replaced by zero, while nonnegative entries remain unchanged.

Because the graph-preserving and delivered-drive Catalyst paths are trace-identical, this is not a graph-translation artifact.

## Accepted 30-image result

The frozen 30-image conformance corpus produced:

```text
Catalyst internal transport consistency:       30 / 30
Catalyst prediction agreement with FPGA-v1:    30 / 30
graph spike-vector agreement with FPGA-v1:     26 / 30
direct spike-vector agreement with FPGA-v1:    26 / 30
first divergence = sub-rest clamp:              30 / 30
other first-divergence categories:               0 / 30
```

The four final spike-vector differences occur at MNIST indices:

```text
3, 7, 30, 149
```

In all four cases Catalyst adds exactly one spike to a non-winning output neuron while preserving the decoded class:

| MNIST index | label | decoded class | FPGA-v1 -> Catalyst |
| ---: | ---: | ---: | --- |
| 3 | 0 | 0 | output 2: `1 -> 2` |
| 7 | 9 | 9 | output 3: `1 -> 2` |
| 30 | 3 | 3 | output 7: `5 -> 6` |
| 149 | 2 | 9 | output 4: `1 -> 2` |

The corpus is deliberately selected and must not be used as an unbiased accuracy estimate. Its significance is behavioral: Catalyst's target-native resting-floor rule changes lower-level state on all selected images, changes final spike counts in some images, but did not change the winner in this 30-image set.

Accepted evidence:

```text
applications/mnist/evidence/mnist-11-12/matched-corpus-v1/
```

See `docs/MNIST_11_12_CORPUS_RESULTS.md`.

## Pinned K26 feasibility boundary

The M13.5 Catalyst K26 wrapper remains:

```text
configured cores:          2
neurons/core:              256
total configured neurons: 512
pool depth/core:           4096
clock target:              100 MHz
upstream target part:      xczu5ev-sfvc784-2-i
```

The matched graph requires `794` explicit neuron slots, so it does not fit the pinned wrapper. The pinned source also provides no board XDC, no PS/block-design integration, and no `write_bitstream` path. Routed implementation is therefore the strongest source-supported hardware boundary from M13.5.

Current physical decision:

```text
generic Catalyst CPU graph-preserving experiment: SUPPORTED and accepted
Catalyst CPU delivered-drive experiment:          SUPPORTED and accepted
pinned K26 graph-preserving MNIST:                 BLOCKED (794 > 512 neurons)
pinned K26 physical delivered-drive MNIST:         BLOCKED by board integration and not graph matched
```

A thesis-owned expanded/board-integrated Catalyst implementation would be a new hardware experiment and must be labeled separately from the pinned upstream artifact.

## Sub-milestone state

### MNIST-12.1 — Upstream/K26 feasibility audit

**Status:** Complete.

Generic CPU graph fit and the pinned K26 capacity/programming blockers are frozen and machine-readable.

### MNIST-12.2 — Semantic mapping audit

**Status:** Complete.

Threshold, refractory, current-delivery, voltage semantics, state width, and the sub-rest negative-voltage difference are explicitly classified.

### MNIST-12.3 — Catalyst CPU/reference matched experiment

**Status:** Complete.

The two-image anchor and frozen 30-image corpus executed successfully. The graph-preserving and delivered-drive paths agree exactly with each other on all 30 cases, all 30 predictions match FPGA-v1, and the observed lower-level divergence is localized to the predeclared Catalyst resting-floor rule.

### MNIST-12.4 — Physical Catalyst N1 K26 run

**Status:** Blocked at the pinned upstream source boundary.

The exact matched graph does not fit the 512-neuron wrapper, and the release lacks a source-supported programmable KV260 integration. No physical matched-Catalyst result is claimed.

### MNIST-12.5 — Same-K26 characterization

**Status:** Not directly admissible for the matched MNIST graph under the pinned artifact.

M13.5 routed resources/timing remain architecture/context evidence only; they are not an application latency comparison.

### MNIST-12.6 — Final matched matrix

**Status:** In progress.

The 30-image matrix is now populated. A full 10,000-image Catalyst software pass is the next useful sensitivity experiment because it can quantify how often the known resting-floor semantic changes spike vectors or decoded predictions across the unbiased official test set.

## Scaling to full-test execution

Large-scope tooling now uses deterministic request shards, resumable external runners, sparse progress output, and compact full-test archiving. This avoids one giant request JSON and permits an interrupted external run to continue from validated per-image result files.

The full-test analysis will report at minimum:

- transport-consistent case count;
- prediction agreement against FPGA-v1;
- spike-vector agreement against FPGA-v1;
- Catalyst accuracy on the official test split;
- counts/indices classified as `CATALYST_SUB_REST_CLAMP`;
- any other first-divergence class; and
- prediction-disagreement indices, if any.

## Interpretation rules

- Catalyst disagreement with FPGA-v1 is an architecture result unless the two Catalyst controls disagree.
- The first divergent tick/state is more informative than final accuracy alone.
- CPU wall time is not compared to FPGA PL latency.
- M13.5 resource totals do not establish application efficiency ranking.
- No power/energy claim is made from Vivado estimates or board TDP.
- No target-specific retraining is allowed in the primary matched experiment.
