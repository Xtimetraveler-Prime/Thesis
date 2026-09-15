# MNIST-11 — Brian2Loihi Matched Reference Experiment

**Status:** Planned

## Goal

MNIST-10 compared the accepted FPGA-v1 MNIST application against published Loihi MNIST results only as cross-system context. MNIST-11 creates a stronger experiment by porting the **same frozen native-sparse MNIST workload** into Brian2Loihi, an open-source Brian2-based emulator of Intel Loihi-1 neuron/synapse semantics.

The primary research question is:

> Given the same frozen graph, effective weights, deterministic input events, presentation length, and decoder, how closely do FPGA-v1 and Brian2Loihi agree at the neuron-state, spike, and classification levels?

This is a **behavioral/reference-model comparison**, not a hardware-performance benchmark. Brian2Loihi CPU wall time must never be compared to FPGA PL architectural latency.

## Why Brian2Loihi

Brian2Loihi was published by Michaelis, Lehr, Oed, and Tetzlaff as a Loihi emulator built on Brian2. The authors report exact Loihi agreement for neuron/network dynamics without plasticity, while learning introduces stochastic-rounding differences. This MNIST application uses fixed inference weights and no on-chip learning, making it a useful reference target.

Primary sources:

- Michaelis et al., “Brian2Loihi: An emulator for the neuromorphic chip Loihi using the spiking neural network simulator Brian,” *Frontiers in Neuroinformatics* 16:1015624, 2022. DOI: `10.3389/fninf.2022.1015624`.
- PyPI package `brian2-loihi`, latest published release currently `0.5.2` (2021): https://pypi.org/project/brian2-loihi/
- Source repository: https://github.com/sagacitysite/brian2_loihi

The package is old relative to current Brian2/Python releases, so environment compatibility is itself a milestone deliverable rather than an assumption.

---

## Frozen comparison contract

The primary comparison profile is **native-sparse** because it preserves the original 28x28 MNIST input and is the accepted Loihi-facing FPGA profile.

The comparison must reuse, without retraining:

```text
source package:          applications/mnist/frozen/mnist-v1
input representation:   original 28x28 MNIST
input axons:             784
output neurons:          10
stored connections:      4,086
presentation:            16 algorithmic ticks
external events:         exact deterministic FPGA-v1 encoder schedule
recurrent routes:        none
initial state:           zero
readout:                 output spike counts, lowest-ID tie break
weights:                 accepted effective quantized deployment weights
```

The floating checkpoint is not the reference for this experiment. The reference is the **already frozen hardware deployment** and its exact deterministic event schedule.

No Brian2Loihi-specific retraining, weight tuning, threshold tuning, or input re-encoding is allowed in the primary matched experiment. If an exact parameter mapping is impossible, that limitation must be measured and documented rather than hidden by retuning the network.

Cropped-dense may be added later as a secondary sensitivity check, but it is not required to close MNIST-11.

---

## MNIST-11.1 — Toolchain and provenance freeze

**Goal:** establish a reproducible Brian2Loihi environment without contaminating the existing MNIST virtual environment.

Deliverables:

1. Create an isolated environment/container for Brian2Loihi.
2. Pin Python, Brian2, Brian2Loihi, NumPy, and supporting package versions.
3. Record package versions and hashes in a source-controlled environment manifest.
4. Run the upstream single-neuron/basic-network examples before adding any project adapter.
5. Record the exact upstream repository/package revision used.
6. Keep any compatibility shim separate from Brian2Loihi's model equations.

Important constraint: Brian2Loihi `0.5.2` dates from 2021 and specifies Brian2 `>=2.4.2`; current Brian2 has moved substantially since then. If the current Python environment is incompatible, use a dedicated older interpreter rather than modifying Brian2Loihi arithmetic merely to make it run.

**Acceptance gate:** a pinned environment reproduces an upstream Brian2Loihi inference example with no project-specific semantic patches.

---

## MNIST-11.2 — Semantic mapping audit

Before running MNIST, build a machine-readable mapping between the two neuron/synapse models.

Audit at minimum:

- current decay representation and rounding;
- voltage decay representation and rounding;
- threshold representation and `>` versus `>=` firing semantics;
- bias handling;
- reset rule and reset timing;
- refractory semantics;
- signed weight representation and effective weight scaling;
- same-tick event accumulation order;
- state-update ordering;
- integer width, clipping, and saturation behavior;
- input-spike timing convention;
- spike visibility/readout timing.

Every field receives one of these labels:

```text
EXACT                same mathematical/integer operation
EQUIVALENT           same observable behavior under the frozen MNIST domain
TRANSLATED           deterministic parameter conversion required
UNREPRESENTABLE      no exact mapping in the target model
NOT_USED             feature absent from the frozen workload
```

The adapter must never silently replace an `UNREPRESENTABLE` feature with a nearby value.

**Acceptance gate:** all frozen MNIST semantics are classified and the project can state whether exact state-level equivalence is theoretically possible before looking at classification accuracy.

---

## MNIST-11.3 — Micro-conformance suite

Do not begin with 10,000 images. First isolate the arithmetic.

Directed tests should include:

1. one neuron, no input;
2. one positive input event;
3. one negative input event;
4. repeated same-axon events within one tick;
5. multiple axons converging on one neuron;
6. threshold-minus-one, threshold-equal, and threshold-plus-one cases;
7. reset after spike;
8. current/voltage decay across silent ticks;
9. maximum/minimum relevant frozen weight values;
10. sequences that exercise any discovered rounding boundary.

For each tick compare all mutually observable quantities:

```text
current
voltage
spike flag
spike time/tick
```

Where both systems expose equivalent pre/post state timing, compare both before and after state words/values.

**Acceptance gate:** either exact agreement on the common semantic subset, or a deterministic, localized mismatch report that explains every divergence before application-scale testing.

---

## MNIST-11.4 — Frozen corpus comparison

Once the micro-suite is understood, replay the existing 30-image frozen conformance corpus through Brian2Loihi using the **same source indices and same 16-tick event schedules**.

Required outputs per image:

- label;
- FPGA-v1 golden prediction;
- Brian2Loihi prediction;
- ten final spike counts;
- per-tick spike flags;
- per-tick current/voltage where representable;
- first divergent tick/neuron/state field, if any;
- prediction-agreement flag.

Report separately:

```text
state-exact cases
spike-exact cases
prediction-agreement cases
classification accuracy on the selected corpus
semantic-mismatch categories
```

The 30-image set remains a conformance corpus, not an unbiased accuracy benchmark.

**Acceptance gate:** the complete 30-image result is reproducible and every mismatch is attributable either to a known semantic difference or an implementation defect.

---

## MNIST-11.5 — Full-test matched software evaluation

If the adapter/mapping is stable, run the official 10,000-image MNIST test split through Brian2Loihi using exactly the same native-sparse deployment and input encoder.

Record:

- Brian2Loihi accuracy;
- prediction agreement against FPGA-v1 golden;
- spike-count-vector agreement;
- disagreement indices;
- confusion matrix;
- agreement grouped by any semantic edge condition discovered in 11.2/11.3.

Do **not** interpret Python/Brian execution time as Loihi hardware latency.

### MNIST-11 completion criterion

MNIST-11 is complete when the thesis can make one of two defensible statements:

1. **Exact/near-exact matched behavior:** the frozen FPGA-v1 application maps to Brian2Loihi with quantified state/spike/prediction agreement; or
2. **Quantified semantic divergence:** exact mapping is impossible, the precise incompatible semantics are identified, and the resulting application-level effect is measured without retuning the network.

Either outcome is scientifically useful. A forced match obtained by retraining or silently changing the workload is not acceptable.

---

## Evidence boundary

MNIST-11 may support claims about:

- agreement with a published Loihi-1 emulator;
- sensitivity of the MNIST workload to differences in Loihi-like arithmetic/update semantics;
- application-level prediction/state agreement under matched graph/input conditions.

It may **not** support claims about:

- actual Loihi hardware latency or energy;
- Loihi-2 behavior;
- FPGA-vs-Loihi hardware speedup;
- an exact Loihi comparison if the semantic audit finds unrepresentable differences.
