# MNIST-11 — Brian2Loihi Matched Reference Experiment

**Status:** In progress — frozen application adapter, semantic audit, request-bundle boundary, exact comparison runner, regression coverage, and pinned environment bootstrap implemented; local/external execution pending

## Goal

MNIST-10 used published Loihi MNIST measurements only as cross-system context. MNIST-11 instead executes the **same frozen native-sparse deployment** through Brian2Loihi and asks whether the project reproduces a published Loihi-1-oriented software model under matched graph/input conditions.

The primary question is:

> Given the same 4,086 encoded connections, effective weights, deterministic 16-tick input schedule, zero initial state, and spike-count decoder, how closely do FPGA-v1 semantics and Brian2Loihi agree at the state, spike, and prediction levels?

This is a behavioral/reference-model experiment. Brian2Loihi CPU wall time is not Loihi hardware latency.

## Reuse of the completed M13 reference audit

MNIST-11 does **not** restart the external-reference methodology from scratch. Core milestone M13 already froze and independently validated:

- Brian2Loihi `0.5.2`, upstream commit `d54676cb113e48dc886615a0b589bb0e4bccbca4`;
- Brian2 `2.9.0` and NumPy `1.26.4` in the project compare extra;
- a production `brian2loihi_backend.py` adapter;
- exact Loihi-style static-weight field mapping and observed `w_act` checks;
- threshold/current/voltage mapping rules;
- directed project/Brian2Loihi conformance probes; and
- the frozen M13.3 normalization/change-control policy.

M13 found no Class-A/B project defect. For the present feed-forward MNIST workload, the M13 Brian recurrence finding is irrelevant because the deployment has zero recurrent routes.

Primary Brian2Loihi source remains Michaelis et al., “Brian2Loihi: An emulator for the neuromorphic chip Loihi using the spiking neural network simulator Brian,” *Frontiers in Neuroinformatics* 16:1015624, 2022, DOI `10.3389/fninf.2022.1015624`.

## Frozen application contract

The experiment consumes only:

```text
applications/mnist/frozen/mnist-v1/deployments/native-sparse/
```

and preserves:

```text
28x28 source image
784 external axons
10 output neurons
4,086 stored encoded synapses
16 deterministic presentation ticks
zero recurrent routes
zero initial state
argmax output spike-count decoder, lowest ID tie break
no retraining or target-specific tuning
```

The frozen neuron config is:

```text
current_decay     = 4096
voltage_decay     = 0
threshold         = 8384 = 131 * 64
bias              = 0
reset_voltage     = 0
refractory_ticks  = 0
```

The deployment has two sign-specific exponent-zero, 8-bit Loihi-style weight formats; all accepted effective weights are aligned to 64.

## Application-specific semantic audit

`mnist_app/matched_reference.py` freezes the application-level mapping before Brian outputs are observed. Every field is labeled `EXACT`, `EQUIVALENT`, `TRANSLATED`, `UNREPRESENTABLE`, or `NOT_USED`.

Two points require explicit treatment:

### Refractory 0 -> 1

Brian2Loihi requires `refractory` in `1..64`, while the frozen application requests `0`. This is **not** silently clamped. FPGA-v1 loads:

```text
future_blocked_ticks = max(refractory_ticks - 1, 0)
```

on a spike, so project `R=0` and `R=1` both store zero future blocked ticks under the one-update-per-neuron-per-tick contract. The matched runner therefore:

1. executes the exact image in FPGA-v1 semantics with `R=0`;
2. executes the same image in FPGA-v1 semantics with `R=1`;
3. requires exact current/voltage/spike trace equality; and only then
4. permits Brian2Loihi to use `R=1`.

Any failed equivalence aborts the case.

### SAT24 versus Brian unbounded arithmetic

Brian2Loihi does not expose the project's SAT24 state policy. The frozen deployment, however, records a conservative absolute voltage bound of about `7.55e6`, below SAT24 max `8,388,607`. The Brian scenario is therefore run with unbounded comparison arithmetic while the project retains FPGA-v1 SAT24 arithmetic. Exact state comparison itself verifies that saturation did not create a hidden discrepancy on each executed schedule.

## Immutable matched request bundle

TensorFlow/MNIST loading is separated from both external environments. In the normal MNIST environment:

```text
scripts/prepare_matched_reference_bundle.py
```

writes one JSON bundle containing, per selected image:

- official MNIST test index and label;
- exact 16-tick external axon schedule;
- total event count;
- frozen project golden spike-count vector and prediction; and
- SHA-256 provenance for the freeze manifest, deployment, and weight image.

Brian2Loihi and Catalyst consume the same bundle. This prevents either external environment from reloading/re-encoding MNIST differently.

Scopes are:

```text
anchor  -> indices 3 and 1
corpus  -> exact frozen 30-image conformance corpus
full    -> official 10,000-image test set
```

## Exact Brian case runner

`mnist_app/brian2loihi_matched.py` and `scripts/run_mnist_11_brian2loihi.py` perform each case as follows:

1. rebuild the accepted encoded graph from frozen FPGA storage;
2. prove project `R=0` and reference `R=1` exact equivalence for that image;
3. verify the reconstructed project scenario still matches the frozen golden spike vector/prediction;
4. instantiate Brian2Loihi with the exact requested mantissa/exponent/precision/sign-mode groups;
5. read Brian2Loihi `w_act` and require all **4,086** effective weights to equal the frozen project weights;
6. compare every tick's `current_after`, `voltage_after`, and spike set exactly; and
7. compare final ten-neuron spike counts and prediction.

A case passes only when all of those checks pass.

## Environment

The application bootstrap script is:

```text
applications/mnist/scripts/setup_mnist_11_brian2loihi_env.sh
```

It creates an isolated `.venv-mnist-brian2loihi` by default and installs the already-frozen core compare extra:

```text
numpy==1.26.4
brian2==2.9.0
brian2-loihi==0.5.2
```

No Brian arithmetic/model source patch is part of MNIST-11.

## Sub-milestone state

### MNIST-11.1 — Toolchain/provenance freeze

**Implementation status:** substantially inherited from completed M13; application bootstrap added. Local bootstrap/import confirmation remains.

### MNIST-11.2 — Semantic mapping audit

**Implementation status:** complete in source. Local pytest/audit generation remains as the validation gate.

### MNIST-11.3 — Micro-conformance

**Implementation status:** core directed project/Brian probes already accepted under M13. MNIST-11 adds the application-specific `R=0 -> R=1` equivalence regression and full frozen-weight contract checks. Local pytest remains.

### MNIST-11.4 — Frozen 30-image corpus

**Implementation status:** runner complete; external execution pending. Start with the two-image anchor before spending time on all 30 cases.

### MNIST-11.5 — Full 10,000-image evaluation

**Implementation status:** bundle/runner path supports it, but it remains intentionally gated on the 30-image result. Full-test CPU runtime may be substantial and is not a hardware-performance metric.

## Acceptance / interpretation

Possible scientifically valid outcomes are:

1. exact state/spike agreement on the matched feed-forward workload;
2. prediction agreement with lower-level deterministic state differences; or
3. a reproducible semantic divergence trace.

Retuning to force agreement is forbidden. Brian CPU execution time is never compared to FPGA PL latency or published Loihi hardware latency.
