# MNIST-11/12 — Accepted Two-Image Anchor Gate

**Status:** Accepted; 30-image matched corpus is the next execution gate.

## Scope

The anchor bundle contains the same two official MNIST test images previously used for FPGA-v1 runtime/timing acceptance:

```text
index 3, label 0
index 1, label 2
```

Both external-reference paths consume the same immutable native-sparse request bundle generated from `mnist-v1`, including the exact 16-tick event schedules, frozen golden spike counts/predictions, and deployment provenance.

The application regression passed after the Catalyst wide-fan-in correction:

```text
79 passed
```

## MNIST-11 — Brian2Loihi anchor

The pinned Brian2Loihi environment and two-image anchor completed successfully before the Catalyst rerun. The application adapter requires, per case:

- exact project `R=0` versus reference `R=1` equivalence before external execution;
- all 4,086 observed Brian2Loihi effective weights to equal the frozen deployment;
- exact compared current/voltage/spike traces;
- exact final spike-count vector; and
- exact decoded prediction.

The exact generated JSON remains local under the ignored `applications/mnist/build/` tree until the matched evidence archive step. The accepted result is sufficient to advance MNIST-11 to the 30-image corpus gate; the archive will preserve the exact counts before milestone closure.

## MNIST-12 — Catalyst N1 anchor

The pinned generic Catalyst CPU reference reports:

```text
generic_cpu_graph_fit=True
k26_graph_fit=False
physical_source_supported=False
```

Thus the graph-preserving CPU experiment is feasible, while the already-pinned M13.5 K26 wrapper cannot hold the 794 materialized neurons and still lacks a source-supported programmable KV260 integration.

Two independent Catalyst CPU constructions were executed for each image:

1. **graph-preserving** — 784 explicit source neurons, ten outputs, exact 4,086 effective-weight matrix, and the declared one-native-tick source-to-target pipeline;
2. **delivered-drive control** — the same external events collapsed to exact per-output fan-in currents and injected directly into the ten output neurons using Catalyst's signed-32-bit CPU current boundary.

The two Catalyst constructions matched each other exactly at every normalized output-voltage/spike tick:

```text
index 3: catalyst_internal_trace_mismatches=0, transport_consistent=True
index 1: catalyst_internal_trace_mismatches=0, transport_consistent=True
```

Both also preserved the FPGA-v1 decoded class on the anchor:

```text
index 3: project=0, graph=0, direct=0
index 1: project=2, graph=2, direct=2
```

### Confirmed semantic divergence

Catalyst does **not** reproduce FPGA-v1 membrane state exactly. The first mismatch on both images is the predeclared Catalyst simple-LIF resting-floor behavior: negative FPGA-v1 membrane values are replaced by Catalyst resting value `0` while non-negative components remain unchanged.

Index 3, canonical tick 0:

```text
FPGA-v1: [0, -13888, 2176, -2368, -3840, 192, 3328, 2112, 832, 448]
Catalyst: [0,      0, 2176,     0,     0, 192, 3328, 2112, 832, 448]
```

Index 1, canonical tick 0:

```text
FPGA-v1: [3136, -3072, 8128, 320, -22016, 1088, 3584, -31744, 3776, -25344]
Catalyst: [3136,     0, 8128, 320,      0, 1088, 3584,      0, 3776,      0]
```

Because the graph-preserving and delivered-drive Catalyst paths are trace-identical, this divergence is classified as a **target-native neuron semantic difference**, not a graph translation or host-transport defect.

The FPGA-v1/Catalyst trace mismatch counts on the anchor were:

```text
index 3: 17 mismatched tick/field records in both Catalyst views
index 1: 16 mismatched tick/field records in both Catalyst views
```

Those counts must not be interpreted as 17 or 16 independent root causes: later state differences may be downstream consequences of the first sub-rest clamp.

### Wide fan-in correction

The first Catalyst anchor attempt exposed an adapter-scope issue when one exact per-output fan-in sum reached `-55,680`, outside signed int16. Individual frozen synaptic weights are signed-int16-compatible, but their same-tick sum need not be. The pinned Catalyst CPU simulator uses signed-32-bit external-current and soma-accumulator arrays, so the accepted CPU-only delivered-drive control now preserves the exact sum with no clipping or scaling. The stricter signed-int16 guard remains part of the older M13 hardware-common direct-stimulus subset and is not reused for this CPU-only MNIST control.

The accepted rerun observed maximum absolute delivered currents of:

```text
index 3: 27,328
index 1: 61,440
```

## Sub-milestone status after the anchor

The evidence is sufficient to treat these gates as complete:

- **MNIST-11.1 — Toolchain/provenance freeze:** complete.
- **MNIST-11.2 — Semantic mapping audit:** complete for the frozen native-sparse workload.
- **MNIST-11.3 — Directed/application anchor conformance:** complete; advance to the 30-image corpus.
- **MNIST-12.1 — Upstream/K26 feasibility audit:** complete; generic CPU graph is supported and the pinned K26 physical graph is explicitly blocked.
- **MNIST-12.2 — Catalyst semantic mapping audit:** complete; sub-rest negative-voltage retention is confirmed `UNREPRESENTABLE` in the pinned simple-LIF path.
- **MNIST-12.3 — Catalyst CPU/reference experiment:** in progress; two-image anchor accepted, 30-image corpus next.
- **MNIST-12.4 — Physical matched Catalyst K26 execution:** blocked under the pinned upstream wrapper by capacity and missing board integration. This is a documented platform boundary, not a failed behavioral experiment.

The next gate is the exact same frozen 30-image corpus for Brian2Loihi and Catalyst.
