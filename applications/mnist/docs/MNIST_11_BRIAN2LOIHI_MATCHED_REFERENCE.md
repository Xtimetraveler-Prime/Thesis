# MNIST-11 — Brian2Loihi Matched Reference Experiment

**Status:** In progress — MNIST-11.1 through MNIST-11.4 complete; full 10,000-image evaluation remains

## Goal

MNIST-10 used published Loihi MNIST measurements only as cross-system context. MNIST-11 instead executes the **same frozen native-sparse deployment** through Brian2Loihi and asks whether the project reproduces a published Loihi-1-oriented software model under matched graph/input conditions.

The primary question is:

> Given the same 4,086 encoded connections, effective weights, deterministic 16-tick input schedule, zero initial state, and spike-count decoder, how closely do FPGA-v1 semantics and Brian2Loihi agree at the state, spike, and prediction levels?

This is a behavioral/reference-model experiment. Brian2Loihi CPU wall time is not Loihi hardware latency.

## Frozen reference and environment

MNIST-11 reuses the completed M13 external-reference audit rather than creating a second Brian adapter:

```text
Brian2Loihi: 0.5.2
upstream commit: d54676cb113e48dc886615a0b589bb0e4bccbca4
Brian2: 2.9.0
NumPy: 1.26.4
```

The production `Neuromorphic Digital Twin/src/neuromorphic_twin/comparison/brian2loihi_backend.py` adapter preserves Loihi-style encoded-weight fields and reads Brian2Loihi `w_act` back after construction.

Primary source: Michaelis et al., “Brian2Loihi: An emulator for the neuromorphic chip Loihi using the spiking neural network simulator Brian,” *Frontiers in Neuroinformatics* 16:1015624, 2022, DOI `10.3389/fninf.2022.1015624`.

The isolated application environment is created by:

```text
applications/mnist/scripts/setup_mnist_11_brian2loihi_env.sh
```

No Brian2Loihi arithmetic/model source patch is part of the experiment.

## Frozen application contract

The experiment consumes only the accepted `mnist-v1/native-sparse` deployment:

```text
28x28 source image
784 external axons
10 output neurons
4,086 stored encoded synapses
16 deterministic presentation ticks
zero recurrent routes
zero initial state
argmax output spike-count decoder, lowest-ID tie break
no retraining or target-specific tuning
```

Frozen neuron configuration:

```text
current_decay     = 4096
voltage_decay     = 0
threshold         = 8384 = 131 * 64
bias              = 0
reset_voltage     = 0
refractory_ticks  = 0
```

All accepted effective weights retain their encoded metadata and are aligned to 64.

## Application-specific semantic audit

Every relevant field is classified before application-scale results as `EXACT`, `EQUIVALENT`, `TRANSLATED`, `UNREPRESENTABLE`, or `NOT_USED`.

### Refractory 0 -> 1

Brian2Loihi requires refractory in `1..64`, while the frozen application requests `0`. FPGA-v1 stores:

```text
future_blocked_ticks = max(refractory_ticks - 1, 0)
```

so project `R=0` and `R=1` both block zero future ticks under this workload. The matched runner proves exact project `R=0` versus project `R=1` current/voltage/spike equality on every image before using Brian `R=1`.

### SAT24 versus Brian unbounded arithmetic

Brian2Loihi does not model the project's SAT24 policy. The frozen deployment's conservative absolute voltage bound is about `7.55e6`, below SAT24 max `8,388,607`. The Brian comparison therefore uses unbounded comparison arithmetic; exact state agreement verifies saturation remains inactive on every accepted schedule.

## Immutable matched requests

Both Brian2Loihi and Catalyst consume the same backend-neutral request data containing:

- official MNIST test index and label;
- exact 16-tick external-axon schedule;
- frozen project golden spike-count vector and prediction; and
- SHA-256 provenance for the frozen deployment.

Small scopes use one JSON bundle. The full 10,000-image scope uses deterministic bounded-size shards so the external environments do not need to parse one enormous request document.

## Exact case acceptance

For every Brian image, the runner:

1. reconstructs the accepted encoded graph from frozen FPGA storage;
2. proves project `R=0 -> R=1` equivalence;
3. verifies the reconstructed project result against the frozen golden result;
4. instantiates the exact requested Brian mantissa/exponent/precision/sign groups;
5. reads back all 4,086 effective `w_act` values;
6. compares every tick's `current_after`, `voltage_after`, and spike set; and
7. compares final ten-neuron spike counts and prediction.

A case is marked passed only when every compared field is exact.

## Accepted anchor and corpus results

The two-image anchor passed exactly. The subsequent frozen 30-image corpus produced:

```text
case pass:                      30 / 30
prediction agreement:          30 / 30
final spike-vector agreement:  30 / 30
exact current/voltage/spikes:   30 / 30
weight mismatches:              0 on every case
```

The selected corpus happens to contain 17 correct project predictions out of 30; that **56.67% is not an accuracy benchmark** because the corpus was deliberately constructed from both-correct, profile-divergent, and both-wrong examples. Brian2Loihi matches the project prediction on every selected case, including the deliberately incorrect ones.

Full evidence:

```text
applications/mnist/evidence/mnist-11-12/matched-corpus-v1/
```

Interpretation and the cross-target result are summarized in `docs/MNIST_11_12_CORPUS_RESULTS.md`.

## Sub-milestone state

### MNIST-11.1 — Toolchain/provenance freeze

**Status:** Complete.

The isolated pinned environment was created successfully and the existing M13 reference backend remained usable without semantic source patches.

### MNIST-11.2 — Semantic mapping audit

**Status:** Complete.

The application-level mapping is frozen, including explicit treatment of refractory and SAT24 boundaries.

### MNIST-11.3 — Micro-conformance

**Status:** Complete.

Existing M13 directed project/Brian probes plus the MNIST-specific `R=0 -> R=1` and encoded-weight regressions passed.

### MNIST-11.4 — Frozen 30-image corpus

**Status:** Complete.

All 30 selected images matched exactly at effective weights, per-tick current/voltage/spikes, final spike counts, and prediction.

### MNIST-11.5 — Full 10,000-image evaluation

**Status:** Pending execution.

The full-test path is being scaled with sharded immutable requests plus resumable external execution. The intended outputs are:

- exact-trace agreement count;
- spike-vector agreement count;
- prediction agreement count;
- Brian2Loihi accuracy on the official test split; and
- disagreement indices if any.

Brian CPU execution time remains explicitly excluded from FPGA/Loihi hardware-performance comparisons.

## Current interpretation

The strongest accepted claim is now:

> On the frozen 30-image feed-forward native-sparse conformance corpus, FPGA-v1 semantics and pinned Brian2Loihi reproduce the same 4,086 effective weights and agree exactly on every compared current, voltage, spike, final spike-count vector, and decoded prediction.

The planned full-test run will determine whether that exact agreement extends from the selected conformance corpus to all 10,000 official MNIST test images.
