# MNIST-11 — Brian2Loihi Matched Reference Experiment

**Status:** Complete

## Goal

MNIST-11 replaces the loose published-Loihi comparison from MNIST-10 with a matched **software/reference-model** experiment. The accepted `native-sparse` deployment is executed through the pinned Brian2Loihi reference without retraining or target-specific tuning.

The frozen comparison contract is:

```text
28x28 source image
784 external axons
10 output neurons
4,086 stored encoded synapses
16 deterministic presentation ticks
zero recurrent routes
zero initial state
same spike-count decoder
same official MNIST test indices
```

The primary question is:

> Given the same effective graph, effective weights, input schedule, initial state, and decoding rule, does FPGA-v1 reproduce the pinned Brian2Loihi model at the internal state and output-spike levels?

This is a behavioral/reference-model comparison. Brian2Loihi CPU wall time is **not** Loihi hardware latency and is never compared with FPGA PL latency.

## Frozen reference and provenance

MNIST-11 reuses the Brian2Loihi reference already audited during core milestone M13:

```text
Brian2Loihi: 0.5.2
Brian2:      2.9.0
NumPy:       1.26.4
upstream commit: d54676cb113e48dc886615a0b589bb0e4bccbca4
```

The project adapter remains:

```text
Neuromorphic Digital Twin/src/neuromorphic_twin/comparison/brian2loihi_backend.py
```

Primary external source: Michaelis et al., “Brian2Loihi: An emulator for the neuromorphic chip Loihi using the spiking neural network simulator Brian,” *Frontiers in Neuroinformatics* 16:1015624, 2022, DOI `10.3389/fninf.2022.1015624`.

Brian2Loihi is a software emulator/reference model. MNIST-11 does **not** constitute execution on Intel Loihi silicon.

## Application semantic mapping

The frozen neuron configuration is:

```text
current_decay     = 4096
voltage_decay     = 0
threshold         = 8384 = 131 * 64
bias              = 0
reset_voltage     = 0
refractory_ticks  = 0
```

The application-level semantic audit was frozen before external outputs were inspected. Fields are classified as `EXACT`, `EQUIVALENT`, `TRANSLATED`, `UNREPRESENTABLE`, or `NOT_USED`.

### Refractory 0 -> 1

Brian2Loihi requires refractory in `1..64`, while the project deployment requests `0`. FPGA-v1 stores:

```text
future_blocked_ticks = max(refractory_ticks - 1, 0)
```

on a spike. Therefore project `R=0` and `R=1` both store zero future blocked ticks for this one-update-per-neuron-per-tick application. The matched runner proves exact project-side `R=0`/`R=1` current, voltage, and spike equality for each image before allowing Brian2Loihi to use `R=1`.

### SAT24 versus Brian arithmetic

Brian2Loihi does not expose the FPGA-v1 SAT24 state policy. The accepted frozen deployment has conservative headroom below SAT24 max, and every matched run compares the resulting current/voltage state exactly. Exact full-test agreement therefore directly checks that this representational difference does not alter the accepted workload.

## Exact matched runner

For every image, the runner:

1. reconstructs the accepted 4,086-edge graph from frozen storage;
2. proves project `R=0 -> R=1` trace equivalence;
3. confirms the reconstructed project result still equals the frozen golden spike vector and prediction;
4. instantiates Brian2Loihi using the frozen Loihi-style weight fields;
5. reads Brian2Loihi `w_act` and checks all **4,086 effective weights**;
6. compares every tick's current, voltage, and spike set exactly; and
7. compares the final ten-neuron spike-count vector and decoded prediction.

No retraining, threshold fitting, weight fitting, output correction, or post-result parameter tuning is permitted.

## Accepted validation sequence

### Two-image anchor

Official test indices `3` and `1` passed exact matched comparison and established the application/environment path.

### Frozen 30-image corpus

The exact corpus previously used for FPGA application conformance produced:

```text
cases:                         30
Brian2Loihi prediction match:  30 / 30
spike-count-vector match:      30 / 30
exact state/spike trace match: 30 / 30
effective-weight mismatches:   0
```

The corpus is intentionally selected for conformance coverage and is not an unbiased accuracy sample.

### Full official 10,000-image test set

The final matched experiment executed all official MNIST test images through the unchanged frozen deployment and pinned Brian2Loihi environment:

```text
cases:                          10,000
project accuracy:               91.71%
Brian2Loihi accuracy:           91.71%
prediction agreement:           10,000 / 10,000
spike-count-vector agreement:   10,000 / 10,000
exact current/voltage/spike:    10,000 / 10,000
all cases passed:               true
```

The request set was generated deterministically in 100 shards of 100 images. The compact accepted evidence is source-controlled under:

```text
applications/mnist/evidence/mnist-11-12/matched-full-v1/
```

The archive retains the complete Brian suite, semantic audit, request-manifest provenance/hashes, and matched comparison summary while leaving large transient per-image request files under `build/`.

## Interpretation

For the frozen feed-forward native-sparse MNIST application, **FPGA-v1 golden semantics reproduce the pinned Brian2Loihi reference exactly across the full official 10,000-image test set at the observed effective-weight, current, voltage, spike-set, spike-count, and decoded-prediction boundary.**

This is substantially stronger than saying the two systems have similar classification accuracy. The matched experiment demonstrates state-level behavioral equivalence for this particular application and semantic subset.

The result remains bounded by the experiment:

- Brian2Loihi is an emulator, not Intel Loihi hardware;
- the application has no recurrence or on-chip learning;
- the result does not establish equivalence for every Loihi feature;
- Brian CPU execution time is not a hardware-performance measurement; and
- published Intel Loihi MNIST timing/energy numbers remain unmatched literature context only.

## Sub-milestone closure

- **MNIST-11.1 — Toolchain/provenance freeze:** Complete.
- **MNIST-11.2 — Semantic mapping audit:** Complete.
- **MNIST-11.3 — Micro-conformance/application anchor:** Complete.
- **MNIST-11.4 — Frozen 30-image corpus:** Complete, 30/30 exact.
- **MNIST-11.5 — Full 10,000-image evaluation:** Complete, 10,000/10,000 exact.

See also:

```text
docs/MNIST_11_12_ANCHOR_RESULTS.md
docs/MNIST_11_12_CORPUS_RESULTS.md
docs/MNIST_11_12_FULL_TEST_RESULTS.md
```
