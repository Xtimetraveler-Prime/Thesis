# Neuromorphic Digital Twin Experiments

This document records the scientific experiment plan for the FPGA-based, Loihi-inspired neuromorphic digital twin. `MILESTONES.md` tracks engineering and validation capabilities; this file tracks the research questions that become possible once those capabilities are trustworthy.

The intended transition is:

```text
M01-M11: build the digital twin
        ↓
M12: prove the physical FPGA matches the frozen Python FPGA-v1 contract
        ↓
M13: audit and cross-validate the architecture against independent Loihi-oriented references
        ↓
EXPERIMENTS.md: use the validated platform as a controlled architectural instrument
```

The experiments are deliberately kept separate from M12 and M13. M12 answers whether the FPGA implements the project's frozen contract correctly. M13 asks how that contract compares with published Loihi behavior, Brian2Loihi, and Catalyst N1. The experiments below ask what happens when selected architectural properties are controlled, perturbed, or ablated.

## Experiment status legend

- **Proposed** — candidate experiment; research question and method are not yet frozen.
- **Designed** — hypothesis, variables, workload, measurements, and analysis plan are frozen.
- **Ready** — required platform milestones and scripts are complete.
- **Running** — experimental data collection is active.
- **Complete** — reproducible results and interpretation are recorded.
- **Deferred** — useful but outside the selected thesis scope.
- **Blocked** — a required platform, reference, or measurement capability is unavailable.

## Experimental claim boundary

The platform is intended to support controlled experiments on the explicitly implemented and validated Loihi-inspired subset. Results must not be generalized to undocumented Intel Loihi microarchitecture or unsupported processor features without independent evidence.

The following rules apply to every thesis experiment:

1. **M12 is the instrument-validation gate.** Experiments that depend on physical FPGA behavior should not be treated as thesis evidence until the relevant M12 conformance boundary is complete.
2. **M13 is an architectural audit, not a replacement ground truth.** Catalyst N1 and Brian2Loihi provide independent comparison evidence. Disagreement among implementations must be investigated rather than resolved by assuming one implementation is authoritative.
3. **Counterfactual variants must be explicit.** A modified update order, width, recurrence rule, or weight representation is an experimental variant and must not silently replace the validated FPGA-v1 baseline.
4. **Baseline and variant must share workloads.** Wherever practical, the same initial state, topology, events, and seeds should be replayed through the validated baseline and the experimental variant.
5. **All divergence must be measurable.** Experiments should report more than a final pass/fail result. Useful outputs include first-divergence tick, state error, spike-train disagreement, firing-rate change, route/event differences, saturation incidence, and FPGA implementation cost.
6. **Hardware changes require regression protection.** Any experimental hardware variant must preserve a source-controlled path back to the validated baseline. If a finding from M13 causes the baseline contract itself to change, the affected M12 evidence must be rerun before new experiments are interpreted.

## Experiment registry

| ID | Candidate question | Primary architectural feature | Status | Main prerequisite |
|---|---|---|---|---|
| E01 | How sensitive are SNN dynamics to neuron state-update ordering? | current/voltage update schedule | Proposed | M12, M13 discrepancy review |
| E02 | How strongly does Loihi-style weight representation affect behavior? | mantissa/exponent/precision/sign mode | Proposed | M12 |
| E03 | What is the behavioral consequence of next-tick recurrent delivery? | recurrent timing | Proposed | M12.3 |
| E04 | When do finite-width arithmetic choices become behaviorally significant? | state width, saturation, rounding | Proposed | M12.2-M12.4 |
| E05 | Which architectural semantics contribute most to observed network behavior? | multi-feature ablation | Proposed | E01-E04 design maturity |
| E06 | What FPGA cost is associated with preserving architectural fidelity? | resource/timing/throughput cost | Proposed | M12.5 |

These are candidate experiments rather than final thesis commitments. M12 and M13 may reveal a stronger experiment, make one of these redundant, or show that a proposed independent variable cannot be changed cleanly without confounding another architectural property.

---

## E01 — State-update ordering sensitivity

**Status:** Proposed

### Research question

How sensitive are spiking-network state and output dynamics to the ordering of synaptic input accumulation, current integration/decay, voltage integration/decay, threshold evaluation, and state commit?

### Motivation

The project already found that state-update ordering is architecturally observable: newly delivered synaptic input must be visible to voltage integration before the stored current is decayed. That discovery was necessary for Brian2Loihi agreement and later became part of the frozen M10 contract. A validated digital twin makes it possible to move from conformance testing to a controlled counterfactual experiment.

### Baseline

Use the validated FPGA-v1 update schedule and its Python golden equivalent.

### Candidate variants

Change one scheduling relationship at a time, for example:

- decay previous current before adding new input;
- integrate voltage from post-decay rather than pre-decay working current;
- change threshold evaluation relative to state decay/integration;
- expose serialized partial state rather than atomic tick commit only as a deliberately invalid control if useful.

Each variant must be named and versioned. Multiple ordering changes should not be combined until single-change effects are understood.

### Candidate workloads

- isolated impulse responses;
- threshold-near-boundary neurons;
- repeated input trains;
- feed-forward chains;
- recurrent chains and loops;
- networks with simultaneous excitation and inhibition.

### Candidate measurements

- first state-divergence tick;
- first spike-divergence tick;
- number/fraction of differing spikes over time;
- current and voltage error trajectories;
- persistence or convergence of divergence after input stops;
- network-level firing-rate or oscillation changes where meaningful.

### Hypothesis to refine

Small update-order changes that appear numerically minor at one neuron/tick can create persistent or amplified spike-timing divergence in recurrent networks.

### Threats to validity

- A variant may accidentally change more than scheduling order.
- Some workloads may never approach a boundary where ordering matters.
- Network-level divergence alone does not establish that one ordering is biologically or algorithmically superior.

---

## E02 — Loihi-style weight-representation sensitivity

**Status:** Proposed

### Research question

How do Loihi-style static-weight mantissa, exponent, precision, sign mode, quantization, alignment, and clipping constraints alter neuron and network behavior relative to higher-precision or idealized weight representations?

### Motivation

M08 provides a validated, traceable path from requested mantissa plus shared format to the effective integer consumed by the core. This creates a natural experimental control surface that can be varied without changing the rest of the computational schedule.

### Baseline

Use a network represented through the validated M08 encoded-weight path.

### Candidate variants

- vary `num_weight_bits` while preserving the intended unquantized weight as closely as possible;
- vary exponent within representable equivalent or near-equivalent ranges;
- compare mixed, excitatory, and inhibitory sign-mode constraints where semantically appropriate;
- compare encoded weights with a wider/unquantized software reference;
- deliberately exercise clipping boundaries.

### Candidate workloads

- single-synapse transfer cases;
- balanced excitation/inhibition;
- fan-in networks with accumulated quantization error;
- recurrent networks where small weight changes affect threshold crossing;
- selected trained or hand-designed SNNs if a reproducible mapping is available.

### Candidate measurements

- effective-weight error distribution;
- first spike/state divergence;
- spike-train similarity;
- change in firing rate or output classification/control metric if an application-level workload is selected;
- frequency of clipping and quantization-induced zero weights;
- sensitivity versus network depth/recurrent duration.

### Hypothesis to refine

The behavioral effect of weight precision is topology- and state-dependent: many local quantization errors will be benign, while errors near threshold and in recurrent paths can produce disproportionate spike divergence.

### Threats to validity

- Comparing different formats can unintentionally change the intended weight scale.
- Application-level accuracy may hide substantial internal spike divergence.
- Results from one topology should not be generalized to all SNN workloads.

---

## E03 — Recurrent timing semantics

**Status:** Proposed

### Research question

What behavioral effect is caused by Loihi-inspired next-tick recurrent delivery compared with a counterfactual same-tick or otherwise altered recurrent-delivery rule?

### Motivation

M09/M10 explicitly define that spikes produced on tick `t` can first re-enter the computational core as recurrent events on tick `t+1`. M11 implements this using double-buffered recurrent queues. This timing rule is therefore both validated and experimentally alterable.

### Baseline

Use the validated next-tick recurrent-delivery contract.

### Candidate variants

- same-tick recurrent delivery, if an unambiguous counterfactual reference model can be built;
- an additional fixed one-tick delay;
- altered ordering between external and recurrent events while preserving event multiplicity.

The same-tick variant must be implemented carefully because it can create causality/iteration questions not present in the baseline. The experimental specification must define whether newly generated same-tick spikes can recursively trigger further same-tick updates or whether only one feedback layer is permitted.

### Candidate workloads

- self-recurrent neurons;
- short feed-forward/recurrent chains;
- two-neuron loops;
- fan-in/fan-out recurrent motifs;
- simultaneous source spikes targeting one recurrent axon;
- periodic or oscillatory networks.

### Candidate measurements

- first spike-divergence tick;
- phase shift and period changes in oscillatory motifs;
- recurrent queue/event-count differences;
- spike multiplicity and ordering differences;
- persistence of divergence after identical external stimulation.

### Hypothesis to refine

Changing recurrent delivery by a single architectural tick can change phase, threshold crossings, and long-term recurrent activity even when neuron equations and weights are unchanged.

### Threats to validity

- A same-tick implementation may not be a meaningful model of any real processor.
- Recursive same-tick semantics can confound latency with a fundamentally different computation model.
- Small networks may exaggerate or understate effects seen in larger networks.

---

## E04 — Finite-precision state effects

**Status:** Proposed

### Research question

At what state widths and arithmetic policies do finite-precision implementation choices begin to alter spike behavior relative to the validated FPGA-v1 profile or a wider arithmetic reference?

### Motivation

M10 freezes signed 24-bit current and voltage state plus explicit saturating state operations and round-away-from-zero decay. The independent Python model can also represent broader arithmetic policies. This provides a controlled way to distinguish mathematically ideal behavior from finite hardware behavior.

### Baseline

Use the validated FPGA-v1 state widths, saturation points, and decay rounding semantics.

### Candidate variants

- wider current and voltage state;
- narrower state widths where useful for a stress study;
- wrapping versus saturation as an intentionally non-Loihi-v1 project counterfactual;
- alternative decay rounding rules in software;
- altered intermediate precision while holding architectural state width fixed.

### Candidate workloads

- saturation-boundary directed cases;
- long decay sequences;
- high fan-in accumulation;
- alternating excitation/inhibition;
- recurrent accumulation near state limits;
- deterministic generated networks from the M12.4 corpus.

### Candidate measurements

- saturation/wrap event counts;
- numerical state error before spike divergence;
- first spike-divergence tick;
- percentage of networks with any divergence over a fixed horizon;
- relationship between fan-in/load and divergence probability;
- implementation resource/timing effects for selected hardware variants.

### Hypothesis to refine

Finite precision remains behaviorally invisible over a substantial interior region of the state space but produces abrupt spike divergence near threshold, saturation, and long recurrent accumulation boundaries.

### Threats to validity

- A wider software reference is not automatically closer to physical Loihi behavior.
- Hardware cost comparisons can be confounded by synthesis mapping changes unrelated to bit width alone.
- Saturation incidence depends strongly on workload scaling.

---

## E05 — Architectural ablation study

**Status:** Proposed

### Research question

Which validated architectural semantics contribute most strongly to divergence in representative spiking workloads when changed individually from the baseline?

### Motivation

E01-E04 each isolate one class of architectural choice. A later ablation study can place those effects on a common scale and identify which implementation details are behaviorally consequential versus largely invisible for selected workloads.

### Candidate factors

Only factors with independently validated single-variable variants should be included. Candidates include:

- update ordering;
- weight precision/quantization;
- state width/saturation;
- refractory timing;
- recurrent delivery latency;
- external/recurrent event ordering;
- event multiplicity treatment.

### Experimental design direction

Prefer one-factor-at-a-time comparisons first. A factorial or interaction study should be attempted only if the number of factors and workloads remains statistically and computationally manageable.

### Candidate response metrics

- normalized first-divergence time;
- spike edit/Hamming distance over a fixed trace horizon;
- state error before and after first spike divergence;
- output-task metric if a suitable application workload is selected;
- effect-size ranking across architectural factors.

### Hypothesis to refine

A small subset of timing and finite-precision rules may dominate behavioral divergence, while other implementation details contribute little over normal operating regions.

### Threats to validity

- Rankings can depend strongly on workload selection.
- Factors may interact, making one-factor effects non-additive.
- A behavioral effect-size ranking is not the same as a ranking of importance in Intel Loihi's full architecture.

---

## E06 — Cost of architectural fidelity on FPGA

**Status:** Proposed

### Research question

What FPGA resource, timing, and throughput costs are associated with preserving selected architectural semantics of the validated Loihi-inspired model?

### Motivation

M12.5 will establish the baseline implementation's routed timing, utilization, latency, throughput, and scaling characteristics. Experimental variants from E01-E04 can then be evaluated not only for behavioral effects but also for implementation cost.

### Baseline measurements

Use the final M12 validation-capable image and its source-controlled reports.

### Candidate comparisons

- state width versus LUT/register/BRAM use;
- weight representation/storage choices versus BRAM and decode logic;
- recurrent queue/routing support versus resource and cycle cost;
- trace observability overhead versus resource/timing cost, where separable;
- serialized exact implementation versus selected safe parallelization if a comparable variant is later built.

### Candidate metrics

- CLB LUTs and registers;
- BRAM/URAM/DSP utilization;
- routed WNS/WHS and achievable clock target where reproducibly measured;
- cycles per architectural tick;
- event/synapse and neuron-update throughput;
- latency versus configured neuron/synapse/event counts;
- incremental resource cost relative to the validated baseline.

### Hypothesis to refine

Some semantics that are behaviorally important may have modest FPGA cost, while others may impose disproportionate memory/control overhead. The useful result is a measured fidelity/cost tradeoff rather than a claim that one architecture is universally more efficient.

### Threats to validity

- Vivado mapping can change discontinuously between variants.
- Comparisons require equivalent timing constraints and target device/tool versions.
- Resource counts alone are not a fair proxy for system-level efficiency.
- Power/energy should remain outside the claim set unless a trustworthy measurement method is established.

---

## Required experiment record

When an experiment moves from **Proposed** to **Designed**, add a frozen record containing at least:

- research question;
- hypothesis;
- baseline architecture/version;
- experimental variant/version;
- independent variable(s);
- controlled variables;
- workload/scenario definitions;
- deterministic seeds where applicable;
- measured outputs and derived metrics;
- number of cases/trials;
- pass/failure or interpretation criteria;
- statistical analysis, if any;
- required software/FPGA tool versions;
- source-controlled reproduction command;
- raw-artifact location and naming convention;
- threats to validity;
- result summary and thesis claim supported.

## Reproducibility requirements

Every completed experiment should be reproducible without manual transcription. At minimum, preserve:

```text
experiment ID
experiment schema/version
repository commit
baseline/variant identifiers
Vivado/Vitis version where hardware is involved
FPGA part/board where hardware is involved
scenario generator version
seed(s)
configuration hash
input/load artifacts
raw traces/reports
analysis output
summary result
```

Generated cases should carry stable IDs so a single failure or interesting outlier can be replayed directly. Raw traces should remain separate from derived plots/tables so analysis can be rerun without recollecting hardware data.

## Relationship to M13 findings

M13 may identify architectural differences among published Loihi descriptions, Brian2Loihi, this project's twin, and Catalyst N1. Those findings can affect the experiment plan in three ways:

1. **Confirmed baseline defect or incomplete interpretation** — correct the project model, add a directed regression, and rerun the affected M12 validation before using the revised baseline experimentally.
2. **Legitimate architectural difference** — retain the FPGA-v1 baseline and consider the difference as a candidate controlled experimental variant.
3. **Ambiguous or unsupported behavior** — record the uncertainty and avoid presenting an experiment as a test of Loihi itself unless independent evidence resolves the ambiguity.

This separation is important: M13 establishes what can defensibly be said about architectural correspondence, while `EXPERIMENTS.md` establishes what scientific questions can be asked with the resulting validated platform.

## Selection criteria for final thesis experiments

Before promoting any proposed experiment into the final thesis campaign, prefer experiments that satisfy most of the following:

- isolate a clearly defined architectural property;
- use the validated platform rather than merely benchmarking generic FPGA performance;
- produce a measurable effect beyond a trivial unit-test result;
- are reproducible across deterministic workloads;
- have a defensible relationship to documented Loihi-inspired behavior;
- can distinguish baseline behavior from a meaningful counterfactual;
- add insight not already provided by M12 or M13;
- fit the remaining thesis schedule and hardware/tool access.

A future execution milestone may be created once the final experiment set is selected. No later milestone number is frozen by this document.