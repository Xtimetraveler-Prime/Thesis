# M13 — Final Cross-Validation and Catalyst N1 Audit Summary

## Status

**Complete after independent M13.6 source-level reproduction on 2026-09-10.**

M13 is the architectural audit that follows M12 physical validation of the FPGA-v1 digital twin. Its purpose was not to redesign the project until it resembled another implementation. Its purpose was to ask, with pinned evidence and explicit comparison boundaries, which parts of the validated FPGA-v1 contract agree with independent Loihi-oriented references, which parts differ, which questions cannot be compared exactly, and whether any discrepancy is strong enough to invalidate or revise the M10/M12 baseline.

The final answer is:

```text
M13 crosswalk rows:             19
M13.4 directed probes:          12
accepted agreements:             6
adjudicated non-agreements:      6
resolved audit-harness defects:  2
accepted Class-A/B findings:     0
explicit FPGA-v1 scope limits:   8
M12 baseline changed:            no
M12 physical rerun required:     no
```

The validated FPGA-v1 computational contract therefore remains authoritative. M13 adds architectural context, limitations, and controlled experiment directions without superseding M12.

---

## 1. Evidence hierarchy and source pins

M13 deliberately separates four evidence roles:

1. **Published Loihi evidence** establishes only behavior and architecture that can be defended from publications; undocumented microarchitecture is not inferred.
2. **Brian2Loihi 0.5.2** is an independently implemented Loihi-oriented software model used for executable comparison where its interface supports the question.
3. **The project FPGA-v1 baseline** is the M10 contract physically validated by M12. It is not changed merely to imitate an external implementation.
4. **Catalyst N1** supplies a second independently implemented software/RTL architecture with both behavioral and FPGA implementation evidence.

Pinned identities used throughout the audit are:

```text
project M12 baseline: 80a502ec6dfc4c8d61372089b08c9a584ad65f85
M13.3 normalization:  32cc170ced02af834ed48b9533b245db1f65641d
M13.4 main merge:     54c7840dff765d585e7ff236845b085007405c05
M13.5 main merge:     95f83ed5c1b47d5ad37badfaa091ce24dad2efed
Catalyst N1:          1806bb4b4114d7671e5648fa75b7b83b3a8d5543
Brian2Loihi:          d54676cb113e48dc886615a0b589bb0e4bccbca4
```

The exact M13.6 candidate independently reproduced before closure is the branch state:

```text
agent/m13-6-adjudicate-freeze-findings
dedd3adcffd4f6080bfbb17153110539d8d45061
```

---

## 2. Audit process

### M13.1 — Pin Catalyst and freeze methodology

M13.1 fixed the external Catalyst source before comparison and established the evidence hierarchy, comparison discipline, discrepancy taxonomy, and no-post-hoc-normalization rule. Catalyst was pinned at tag `v2.3-paper`, commit `1806bb4b4114d7671e5648fa75b7b83b3a8d5543`.

The pinned Catalyst source was first checked on its own terms: its native RTL regression passed 25/25 and its CPU simulator tests passed 56/56. This established that later discrepancies were not being attributed to an obviously broken external checkout.

### M13.2 — Four-way architectural crosswalk

M13.2 constructed a source-backed crosswalk spanning published Loihi evidence, Brian2Loihi, FPGA-v1, and Catalyst N1. Nineteen rows cover the milestone's fifteen required feature classes. Each row records whether the feature is exactly comparable, comparable only after a documented transform, architecturally different, unsupported, unobservable, ambiguous in available Loihi evidence, or outside project scope.

The crosswalk prevents a later behavioral test from pretending that unlike interfaces are equivalent. It also makes project omissions explicit rather than misclassifying every omitted Loihi/Catalyst feature as a defect.

### M13.3 — Freeze normalization before observing differential results

M13.3 defined the canonical comparison interface and all permitted transformations before the directed differential was interpreted. Important examples include committed-timestep comparison, Catalyst native staging alignment for the RTL CUBA impulse probes, transformed threshold comparison, semantic refractory release comparison instead of raw counter equality, final delivered signed weight comparison, and logical-ID reconstruction after Catalyst compiler placement.

The central discipline was that a transform could not be changed after seeing a mismatch merely to manufacture agreement.

### M13.4 — Directed differential audit

M13.4 executed twelve frozen architectural probes. Native evidence was preserved before normalization, and each non-agreement was assigned an A-H class. During development two Class-H harness defects were found and corrected before the accepted snapshot: stale Catalyst neuron SRAM state was accidentally reused across CUBA probes, and Catalyst physical compiler GIDs were initially mistaken for logical neuron IDs.

After those harness fixes, the accepted result was:

```text
agreement:                   6
architectural difference:    3
partial scope:                1
non-comparable:               2
Class A/B candidates:         0
```

### M13.5 — Catalyst K26-class hardware reproduction

M13.5 moved the Catalyst comparison beyond documentation and software simulation. The exact pinned Catalyst K26-class RTL was reproduced through Vivado 2025.2 synthesis, placement, physical optimization, and routing at a 100 MHz constraint.

The upstream source supplied enough information for routed implementation but not a complete attributable KV260 physical-execution image. In particular, the pinned K26 flow does not provide the complete board-level constraints, PS integration, clock/reset plumbing, and bitstream/programming path required to claim physical Catalyst execution. M13.5 therefore froze routed implementation as the strongest source-supported Catalyst hardware boundary.

### M13.6 — Adjudication, change control, and closure

M13.6 consumes the frozen M13.2 crosswalk, M13.4 directed findings, and M13.5 hardware closure. It deterministically regenerates the candidate final findings and fails closed if source pins, classifications, scope exclusions, hardware limits, or baseline disposition drift.

The candidate was validated twice before closure: once in a clean GitHub Actions environment and once independently from the user's local Linux VS Code terminal. The independently tested candidate itself is preserved unchanged; `references/m13_6_closure.json` binds its exact bytes to the accepted validation evidence.

---

## 3. Accepted directed findings

| ID | Probe | Outcome | Class | Final interpretation |
| --- | --- | --- | --- | --- |
| P01 | current impulse/decay | agreement | — | Positive isolated CUBA current evolution agrees after the frozen Catalyst staging transform. |
| P02 | voltage decay | agreement | — | Positive isolated voltage evolution agrees at the normalized boundary. |
| P03 | negative decay rounding | architectural difference | C | Catalyst RTL CUBA rounds the tested negative `/4096` decay differently from project/Brian2Loihi. |
| P04 | threshold boundary | agreement | — | Strict project/Brian threshold behavior agrees with Catalyst after the predeclared threshold transform. |
| P05 | refractory release | agreement | — | All compared software participants release at the same semantic next-eligible tick for the directed case. |
| P06 | signed negative drive | architectural difference | C | Catalyst synchronous simple-LIF clamps sufficiently negative sub-rest state to rest while project/Brian2Loihi retain negative voltage. |
| P07 | weight encoding boundary | partial scope | C, G | All 13 common signed-int16 effective weights agree; native encoding formats are not field-equivalent and two cases lie outside Catalyst's common envelope. |
| P08 | fan-in/fan-out | agreement | — | Logical graph behavior agrees after Catalyst physical-GID to logical-ID normalization. |
| P09 | repeated same-source events | non-comparable | G | No defensible identical three-way event-list interface exists for this case. |
| P10 | recurrent timing | architectural difference | D | FPGA-v1 and Catalyst synchronous execution produce one-tick recurrence; pinned Brian2Loihi's native recurrent probe produced no target effect. |
| P11 | finite-width saturation | non-comparable | E, G | Available interfaces and published Loihi evidence do not establish one shared overflow/saturation contract. |
| P12 | simultaneous spikes | agreement | — | Per-tick spike sets agree; a universal global event ordering is not claimed. |

---

## 4. Meaning of the six non-agreement findings

### D01 / P03 — negative CUBA decay rounding

For the frozen negative impulse case, project and Brian2Loihi produce first normalized current `-47`, while Catalyst RTL CUBA produces `-46`. This is a concrete arithmetic difference, but the audit does not establish Catalyst's implementation as stronger evidence for undocumented Loihi negative fixed-point behavior. The result is therefore Class C and becomes a controlled finite-precision experiment candidate rather than a reason to rewrite FPGA-v1.

### D02 / P06 — sub-rest negative membrane handling

A one-tick isolated `-128` drive leaves project and Brian2Loihi at `V=-128`; Catalyst's synchronous simple-LIF path returns the state to rest `0`. The net-positive mixed excitation/inhibition case agrees. This is a Catalyst model/architecture choice at the tested boundary, Class C.

### D03 / P07 — weight representation

Thirteen of fifteen effective project/Brian2Loihi weights fit Catalyst's signed-int16 compiler boundary and reproduce exactly. That is strong evidence that the common delivered integer contribution can be compared. It does not make Catalyst's native source encoding field-for-field equivalent to the project's Loihi-style mantissa/exponent/precision/sign-mode representation. Two project/Brian2Loihi cases also lie outside the common Catalyst int16 envelope. The final classification is C/G.

### D04 / P09 — repeated event multiplicity

FPGA-v1 preserves repeated events from a source in one tick, but the pinned Brian stimulus interface cannot express the identical same-source/same-time event list and Catalyst's external stimulus path is not the same interface. Rather than coerce these into a synthetic equality test, M13 records the question as non-comparable at the available common boundary, Class G.

### D05 / P10 — recurrence

FPGA-v1 and Catalyst synchronous execution both show a one-tick source-to-target spike effect. Under the pinned Brian2Loihi package's own `LoihiNetwork` scheduling, the directed recurrent connection produced no target effect; the diagnostic remained null for native delays 0, 1, and 2 over six ticks. The project does not reinterpret that null as a Loihi hardware rule. It is retained as a Brian2Loihi modeling/scheduling result, Class D.

### D06 / P11 — overflow and saturation

FPGA-v1 deliberately specifies signed 24-bit state with explicit SAT24 application points. Published Loihi evidence used by the thesis does not establish the exact same overflow/saturation contract, Brian2Loihi is not a hardware-width-accurate state-register model at this interface, and Catalyst's widths/assignment behavior are not the same project policy. The result is E/G: useful for counterfactual finite-precision experiments but not a universal Loihi claim.

---

## 5. Resolved Class-H audit defects

Two errors were found in the comparison infrastructure itself and corrected before the accepted M13.4 result:

- **H01 — stale Catalyst CUBA state:** resetting the control path did not clear the reused neuron SRAM state. Positive and negative CUBA probes were separated into independent state slots.
- **H02 — compiler GID observation mismatch:** Catalyst physical compiler placement was initially treated as logical neuron order. The final harness preserves the logical-to-physical mapping and remaps observations back to logical IDs.

These defects matter methodologically because they demonstrate why native evidence and first-divergence analysis were retained. Neither H issue changed FPGA-v1, Brian2Loihi, Catalyst source, or the frozen M13.3 normalization. H02 specifically removed an apparent fan-in/fan-out mismatch; the accepted P08 result is agreement.

---

## 6. Explicit FPGA-v1 scope boundary

M13 confirms that the thesis platform is a **Loihi-inspired digital twin of a validated architectural subset**, not a complete clone of Intel Loihi. Eight crosswalk rows are explicitly outside FPGA-v1's validated scope:

```text
dendritic compartments
programmable synaptic delays beyond the baseline recurrent delivery rule
native Loihi/Catalyst synapse-memory layout equivalence
inter-core routing / packet NoC
online learning / plasticity
Loihi-like embedded management processors
multicore scaling
asynchronous / quiescence execution
```

This scope statement is part of the final result, not a future-defect list. Extending one of these features would constitute new architecture work with its own specification and validation requirements.

---

## 7. Catalyst routed hardware evidence

At the frozen 100 MHz target, the pinned Catalyst K26-class route closed with:

```text
WNS:              +0.001 ns
WHS:              +0.013 ns
CLB LUTs:         19,891 / 117,120
CLB registers:    30,850 / 234,240
Block RAM tiles:  52.5 / 144
DSPs:             14 / 1,248
URAM:             0 / 64
```

The project M12.5 validation-capable image and Catalyst configuration are not identical systems. They differ in target-part strings, configured neuron/core capacity, architectural feature set, host/debug instrumentation, and strength of execution evidence. Therefore these numbers are retained as implementation context only.

M13 explicitly withholds:

```text
maximum-Fmax inference from WNS
raw winner/loser efficiency claims
latency/throughput comparison
power/energy comparison
physical Catalyst KV260 execution claim
```

A routed DCP demonstrates successful source-supported implementation, not physical board execution.

---

## 8. Change-control result

The M13 discrepancy taxonomy reserves baseline-changing action for findings strong enough to be Class A or B:

```text
A = project implementation defect
B = project interpretation/specification inconsistent or incomplete relative to stronger Loihi evidence
```

The accepted M13 result contains **zero A findings and zero B findings**. Consequently:

```text
M10/M12 computational baseline changed: no
normative specification update required: no
HLS/RTL regeneration required: no
M12 evidence superseded: no
M12 physical revalidation required: no
```

This is not a statement that every implementation agrees. It is the narrower and more defensible conclusion that none of the observed differences justifies invalidating the already physically validated FPGA-v1 contract under the evidence hierarchy established before the audit.

---

## 9. Independent M13.6 validation

The final candidate preflight in GitHub Actions regenerated `references/m13_6_findings.json`, verified byte identity, passed the focused M13.6 suite, passed the complete historical regression, and verified that the M13.6 branch did not modify a frozen computational/HLS/RTL path.

The user then independently pulled branch head:

```text
dedd3adcffd4f6080bfbb17153110539d8d45061
```

and reported:

```text
M13.6 findings candidate PASS:
crosswalk=19 directed=12 agreements=6 adjudications=6 A/B=0 scope=8
m12_revalidation=False

cmp candidate vs regenerated candidate: success, no output
focused M13.6 tests: 9 passed in 0.12 s
complete regression:    367 passed in 5.63 s
```

The local `git status --short` also showed two untracked paths, `Neuromorphic` and `Neuromorphic Digital Twin/rtl/core_v1/xvlog.pb`. They were not part of the source-controlled branch diff and are not treated as M13 evidence. The accepted validation is tied to the tracked branch state and candidate bytes, not to those local generated/untracked artifacts.

---

## 10. Final thesis claim boundary

After M13, the thesis may state that:

- the FPGA-v1 implementation physically conforms to the frozen project model over the M12 validation boundary;
- the M13 audit compared that baseline against source-backed published Loihi information, Brian2Loihi, and pinned Catalyst N1 using declared normalization boundaries;
- six directed normalized behaviors agree at their declared common interfaces;
- six other directed questions expose concrete architecture/model/scope differences rather than project baseline defects;
- the pinned Catalyst K26-class RTL is reproducible through routed Vivado implementation at 100 MHz;
- no accepted M13 finding requires changing or physically revalidating FPGA-v1.

The thesis should not claim that:

- FPGA-v1 is a full Loihi clone;
- Brian2Loihi or Catalyst N1 is Intel Loihi ground truth;
- FPGA-v1 SAT24 behavior is proven Intel overflow behavior;
- all coincident-event order/multiplicity semantics are common across implementations;
- the Brian2Loihi recurrent null observation is a Loihi hardware rule;
- routed Catalyst evidence proves physical KV260 execution;
- raw M13.5 resource/timing totals establish a fair architecture-efficiency ranking.

---

## 11. Experiment handoff

M13 closes the validation/audit phase and sharpens the experiment plan without automatically promoting any experiment to Designed or Ready.

- **E01 — update ordering:** retain FPGA-v1 as baseline; alternative schedules are explicit counterfactuals.
- **E02 — weight representation:** separate effective delivered-weight effects from native encoding-layout differences.
- **E03 — recurrent timing:** use validated next-tick FPGA-v1 recurrence as baseline; keep the Catalyst one-tick agreement and Brian2Loihi null as comparison context.
- **E04 — finite precision:** prioritize negative rounding, sub-rest clamping, and overflow/saturation as controlled variants, while preserving uncertainty about undocumented Loihi overflow behavior.
- **E05 — multi-feature ablation:** defer combined variants until the relevant single-factor changes are independently validated.
- **E06 — fidelity cost:** compare controlled project variants under the same target/tool/constraint/workload boundary; use M13.5 Catalyst totals as context, not as the efficiency baseline.

---

## 12. Final reproducibility chain

The M13 closure is represented by the following source-controlled authorities:

```text
references/m13_2_feature_crosswalk.json
references/m13_3_normalization_spec.json
references/m13_4_candidate_findings.json
references/m13_5_closure.json
references/m13_6_findings.json
references/m13_6_closure.json
```

The final M13.6 candidate can be regenerated and checked from `Neuromorphic Digital Twin/` with:

```bash
python3 examples/validate_m13_6_findings.py
rm -rf build/m13_6
python3 examples/generate_m13_6_findings.py
cmp references/m13_6_findings.json build/m13_6/m13_6_findings.json
python3 -m pytest --override-ini addopts='' -q tests/test_m13_6_findings.py
```

The final closure can then be regenerated and validated with:

```bash
python3 examples/generate_m13_6_closure.py
python3 examples/validate_m13_6_closure.py
```

The candidate remains preserved as the exact pre-closure object that was independently tested. The separate closure record establishes that the candidate passed the required independent gate and that M13 is complete.
