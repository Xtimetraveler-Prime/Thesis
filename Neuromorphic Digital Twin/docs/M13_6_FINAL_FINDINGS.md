# M13.6 — Adjudicate Discrepancies and Freeze M13 Findings

## Status

**Candidate findings frozen — pending independent local source-level validation before M13.6 and M13 are marked Complete.**

Development branch:

```text
agent/m13-6-adjudicate-freeze-findings
```

M13.6 is the change-control and interpretation boundary for the complete M13 audit. It does not rerun external implementations merely to seek additional agreement. Instead it consumes the already accepted M13.2 architectural crosswalk, M13.4 directed findings, and M13.5 routed hardware closure, assigns the final A–H interpretation, and freezes which claims may or may not change the validated FPGA-v1 baseline.

The candidate machine-readable authority is:

```text
references/m13_6_findings.json
schema = neuromorphic-twin-m13-final-findings-v1
status = candidate_frozen_pending_independent_validation
```

The record is generated deterministically from the three tracked evidence authorities rather than transcribed by hand.

---

## Evidence authorities

M13.6 consumes:

```text
M13.2 architectural crosswalk: references/m13_2_feature_crosswalk.json
M13.4 directed findings:       references/m13_4_candidate_findings.json
M13.5 hardware closure:        references/m13_5_closure.json
```

Pinned source identities remain:

```text
project M12 baseline: 80a502ec6dfc4c8d61372089b08c9a584ad65f85
M13.3 normalization:  32cc170ced02af834ed48b9533b245db1f65641d
M13.4 main merge:     54c7840dff765d585e7ff236845b085007405c05
M13.5 main merge:     95f83ed5c1b47d5ad37badfaa091ce24dad2efed
Catalyst N1:          1806bb4b4114d7671e5648fa75b7b83b3a8d5543
Brian2Loihi:          d54676cb113e48dc886615a0b589bb0e4bccbca4
```

The M13.6 generator fails closed if those authorities drift in schema, source pins, accepted probe classes, crosswalk scope exclusions, M13.5 comparison limits, or the accepted routed Catalyst boundary.

---

## Final discrepancy taxonomy

M13.6 uses the taxonomy frozen in `MILESTONES.md`:

```text
A. project implementation defect
B. project interpretation/specification incomplete or inconsistent with stronger Loihi evidence
C. Catalyst N1 makes a different architectural choice
D. Brian2Loihi makes or exposes a different modeling choice
E. published Loihi evidence is ambiguous or insufficient
F. comparison mapping/normalization issue
G. feature is unsupported or outside the project's validated subset
H. test/capture/tooling defect
```

Only A or B may trigger a change to the project computational baseline. C–G are retained as differences, ambiguity, normalization limits, or scope boundaries. H findings require correction of the audit machinery and regeneration of affected evidence, but do not alter the computational baseline unless the corrected evidence subsequently produces an A/B result.

---

## Directed findings adjudication

The accepted M13.4 result contains 12 probes: six agreements and six non-agreement/scope outcomes. None is Class A or B.

### Accepted agreement set

The following normalized questions agree at their declared comparison boundaries:

- P01 current impulse/decay;
- P02 voltage decay;
- P04 threshold boundary after the frozen Catalyst threshold transform;
- P05 refractory release using next-eligible-tick semantics;
- P08 fan-in/fan-out after Catalyst physical-GID to logical-ID normalization;
- P12 per-tick simultaneous spike sets.

These agreements support the common subset but do not prove undocumented Intel Loihi microarchitecture.

### D01 — Negative CUBA decay rounding

**Probe:** P03  
**Class:** C — Catalyst architectural choice

Project and Brian2Loihi produce first normalized `current_after=-47`; the pinned Catalyst RTL CUBA path produces `-46`. This remains a Catalyst implementation difference. It does not justify changing the project/Brian2Loihi decay rule and is a useful controlled candidate for E04 finite-precision experiments.

### D02 — Negative sub-rest membrane behavior

**Probe:** P06  
**Class:** C — Catalyst architectural choice

For isolated signed drive, project and Brian2Loihi retain `V=-128`; the Catalyst synchronous simple-LIF path returns the state to resting `0`. The mixed net-positive case agrees. M13.6 retains the FPGA-v1 behavior and treats the Catalyst clamp as a possible counterfactual arithmetic/neuron-state variant, not Loihi ground truth.

### D03 — Weight encoding common envelope

**Probe:** P07  
**Classes:** C, G

Thirteen of fifteen project/Brian2Loihi final effective weights fit Catalyst's signed-int16 compiler boundary and reproduce exactly. Two cases are outside that common envelope, and Catalyst does not expose a field-for-field equivalent of the project/Brian2Loihi Loihi-style source mantissa/exponent/precision/sign-mode representation. E02 should therefore compare final delivered effective weight first and treat native encoding structure as an explicit architecture variable.

### D04 — Same-source same-tick event multiplicity

**Probe:** P09  
**Class:** G — no common exact interface

No defensible three-way exact event-list boundary exists for repeated events from one source in one timestep. FPGA-v1 preserves multiplicity, the pinned Brian2 stimulus interface cannot encode the same case, and Catalyst external stimulus is not the same event-list interface. M13.6 withholds a universal equality claim rather than inventing a transform.

### D05 — Recurrent timing/modeling boundary

**Probe:** P10  
**Class:** D — Brian2Loihi modeling/scheduling difference

Project FPGA-v1 and Catalyst synchronous execution both produce a one-tick source-to-target spike lag. The pinned Brian2Loihi native neuron-to-neuron recurrence probe produces no target effect, including the accepted delay diagnostic. This does not make the Brian2Loihi null result a Loihi rule. E03 may study recurrence timing using FPGA-v1 as its validated baseline, with the M13 result recorded as comparison context.

### D06 — Finite-width overflow/saturation

**Probe:** P11  
**Classes:** E, G

A shared exact overflow/saturation contract is not justified across the available interfaces and published Loihi evidence. FPGA-v1's explicit SAT24 policy remains a deterministic project profile, not a universal Loihi claim. E04 may vary state width, saturation/wrapping, and rounding as controlled counterfactuals while retaining this uncertainty.

---

## Resolved Class-H audit defects

Two harness defects were corrected before the accepted M13.4 snapshot:

1. the initial Catalyst CUBA negative probe reused a neuron state slot whose SRAM state survived control reset;
2. the initial Catalyst graph observer confused compiler physical GIDs with logical neuron IDs.

Both corrections affected audit infrastructure only. The first was eliminated by using independent state slots; the second by preserving and applying the logical-to-Catalyst-GID map. Neither changed the project model, HLS, RTL, or the frozen M13.3 transforms.

---

## Architectural scope findings

M13.2 identified eight explicit project exclusions that remain outside FPGA-v1 rather than becoming defects:

```text
dendritic compartments
programmable synaptic delays beyond the baseline recurrent tick
native synapse-memory equivalence
inter-core routing / NoC
online learning / plasticity
Loihi-like management processors
multicore scaling
asynchronous / quiescence execution
```

These are important limits on the phrase "Loihi-inspired digital twin." The project reproduces a validated point-neuron/static-weight/local-routing subset; it does not claim to reproduce the full Loihi feature set.

---

## M13.5 hardware adjudication

The pinned Catalyst K26-class source reproduced through Vivado 2025.2 routed implementation at 100 MHz with positive setup/hold slack. The accepted routed Catalyst result remains:

```text
WNS:              +0.001 ns
WHS:              +0.013 ns
CLB LUTs:         19,891 / 117,120
CLB registers:    30,850 / 234,240
Block RAM tiles:  52.5 / 144
DSPs:             14 / 1,248
URAM:             0 / 64
```

This evidence is useful implementation context, but the project and Catalyst part strings, capacity, feature scope, host/debug infrastructure, and evidence strength differ. Therefore M13.6 preserves all M13.5 restrictions:

- no maximum-Fmax inference from routed WNS;
- no raw architecture-efficiency winner/loser claim;
- no latency/throughput comparison;
- no power/energy comparison;
- no claim of physical Catalyst KV260 execution.

The strongest attributable Catalyst hardware boundary remains **source-supported routed implementation**.

---

## Change-control decision

The candidate M13.6 decision is:

```text
accepted Class-A findings:             0
accepted Class-B findings:             0
project computational baseline change: no
normative specification update:        no
HLS/RTL regeneration required:         no
M12 evidence superseded:               no
M12 physical revalidation required:    no
```

This is the key M13.6 result. The audit found meaningful architecture/model/scope differences, but none meets the milestone's threshold for rewriting the already physically validated FPGA-v1 contract.

---

## Claim boundary frozen by M13.6

After M13, the thesis may defensibly state that the implemented FPGA-v1 subset has exact physical agreement with its frozen Python model and that selected normalized behaviors also agree with independent Loihi-oriented implementations. It may also report the concrete Catalyst/Brian2Loihi differences above.

The thesis should **not** state that FPGA-v1 is a complete Loihi clone, that Catalyst or Brian2Loihi is Intel Loihi ground truth, that FPGA-v1's SAT24 policy is proven Loihi overflow behavior, that all coincident event ordering is common across implementations, that the Brian2Loihi recurrent null behavior is a Loihi rule, or that the M13.5 resource numbers prove one architecture is more efficient.

---

## Experiment handoff

M13.6 keeps E01–E06 in the experiment registry without silently promoting any experiment to Designed or Ready. The audit changes their interpretation:

- **E01:** retain the validated FPGA-v1 update schedule as baseline; altered ordering remains a named counterfactual.
- **E02:** prioritize common effective-weight behavior; use D03 to separate delivered-value effects from native encoding-layout differences.
- **E03:** retain next-tick FPGA-v1 recurrence as baseline; record the project/Catalyst one-tick agreement and Brian2Loihi null result as context rather than ground truth.
- **E04:** explicitly include negative-decay rounding, sub-rest clamping, and overflow/saturation policy as candidate controlled variants, while preserving the Class-E uncertainty around true Loihi overflow behavior.
- **E05:** do not combine these factors until independently validated single-factor variants exist.
- **E06:** use M13.5 only as implementation context; fair fidelity-cost experiments should compare controlled project variants under the same target/tool boundary.

---

## Reproduction and remaining gate

Candidate generation from `Neuromorphic Digital Twin/` is:

```bash
python3 examples/generate_m13_6_findings.py
```

The committed candidate will additionally be guarded by tests requiring exact deterministic regeneration from the three upstream authorities.

No new Vivado run, board programming, Catalyst runtime execution, or Brian2Loihi experiment is required to adjudicate the currently accepted evidence. The remaining M13.6 gate is independent local source-level reproduction of the candidate record plus the complete project regression. Only after that independent validation should the candidate status be promoted to `validated_complete` and M13.6/M13 be marked Complete.
