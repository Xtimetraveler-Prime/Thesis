# M13.4 Directed Differential Architectural Probes

## Status

**Candidate pass boundary achieved in automated clean-room reconstruction; awaiting independent local validation before M13.4 is marked Complete or merged.**

Development branch:

```text
agent/m13-4-directed-differential-probes
```

M13.4 executes the directed architectural questions frozen before comparison, under the M13.3 normalization specification. It does not redefine the M10/M12 computational baseline and it does not treat Catalyst N1 or Brian2Loihi as Loihi ground truth.

## Authority and pinned inputs

The comparison uses:

```text
project M12 baseline: 80a502ec6dfc4c8d61372089b08c9a584ad65f85
M13.3 normalization:  32cc170ced02af834ed48b9533b245db1f65641d
Catalyst N1:           1806bb4b4114d7671e5648fa75b7b83b3a8d5543
Brian2Loihi:           d54676cb113e48dc886615a0b589bb0e4bccbca4
```

Normative comparison transforms remain those in `references/m13_3_normalization_spec.json`. M13.4 is not allowed to change a transform after seeing a result merely to create agreement.

The candidate findings snapshot is `references/m13_4_candidate_findings.json`. Generated native and normalized traces remain build artifacts so they can be regenerated from the pinned sources rather than treated as hand-authored evidence.

## Executable comparison boundaries

M13.4 uses several boundaries because no single external implementation exposes every state in a defensibly identical form.

### Project and Brian2Loihi point-neuron scenarios

The existing project comparison infrastructure is reused for threshold, refractory, delivered-drive, encoded-weight, and simultaneous-spike questions where the established `ComparisonScenario` representation applies. Project expectations continue to come from the independent integer golden model. Brian2Loihi runs through the pinned Loihi-oriented classes and preserves its native state before normalization.

### Catalyst synchronous CPU boundary

Catalyst's pinned SDK synchronous simulator is used for simple-LIF threshold, refractory, signed-drive, graph, and recurrent questions. External axon events are collapsed into the exact per-neuron delivered current only for the M13.3 `cpu_direct_drive` scenario class. For graph probes, connections are compiled through Catalyst's actual `Network`/`Compiler` path.

Catalyst compiler placement is explicitly translated back to logical neuron IDs before comparison. The native artifact preserves `logical_to_catalyst_gid` so this transform remains auditable.

### Catalyst RTL CUBA boundary

`rtl/m13_4/tb_m13_4_catalyst_cuba.sv` is thesis-side audit infrastructure. It instantiates the untouched pinned `rtl/scalable_core_v2.v`, programs only the M13.3 CUBA parameters, drives an isolated impulse, and reads Catalyst's probe interface.

`scripts/run_m13_4_catalyst_cuba_probes.sh` verifies the exact Catalyst pin and runs this testbench under Icarus Verilog 12+. It emits and validates machine-readable native trace lines before any normalization.

For this restricted scenario class, the frozen M13.3 alignment is:

```text
canonical tick k <- Catalyst native tick k+1
```

Catalyst native tick 0 is preserved as the input-staging/warmup tick and is never silently discarded from the evidence bundle.

### Recurrent Brian2Loihi boundary

The generic Brian2Loihi adapter intentionally continues to reject project `spike_routes`; M13.4 does not weaken that guard. Instead a dedicated native probe instantiates a neuron-to-neuron `LoihiSynapses` edge after the logical recurrent graph has been flattened.

A separate diagnostic confirmed that the observed null recurrent target is reproducible under the pinned package's own `LoihiNetwork` scheduling: the source neuron spikes, but the target receives no observable current/voltage/spike for native recurrent delays 0, 1, or 2 over six ticks. This is therefore retained as a Brian2Loihi modeling/scheduling difference rather than repaired with a post-hoc timing shift.

## Candidate directed result set

The corrected clean execution produced:

```text
probes:                     12
agreement:                   6
architectural_difference:    3
partial_scope:                1
non_comparable:               2
Class A/B candidates:         0
M12 revalidation required:   no
```

| Probe | Result | Class | Directed finding |
| --- | --- | --- | --- |
| P01 current impulse/decay | agreement | — | Project, Brian2Loihi, and Catalyst RTL CUBA agree after the predeclared one-native-tick staging transform. |
| P02 voltage decay | agreement | — | Positive isolated-impulse voltage evolution agrees at the normalized boundary. |
| P03 negative rounding | architectural difference | C | Project/Brian first normalized current is `-47`; Catalyst RTL CUBA is `-46`. |
| P04 threshold boundary | agreement | — | Catalyst `>=` behavior agrees with strict project/Brian `>` after the frozen `T+1` native-threshold transform. |
| P05 refractory release | agreement | — | With canonical `R=3`, all three executable software participants spike on ticks `0` and `3`; raw counters are not compared. |
| P06 signed drive | architectural difference | C | Project/Brian preserve isolated `-128` membrane state; Catalyst CPU simple-LIF returns the sub-rest state to `0`. Mixed net-positive drive agrees. |
| P07 weight boundaries | partial scope | C, G | All 13 final effective weights inside Catalyst's signed-int16 compiler envelope agree exactly. Two cases are outside the common envelope; Catalyst source encoding fields are not equivalent to the Loihi-style mantissa/exponent/precision/sign-mode boundary. |
| P08 fan-in/fan-out | agreement | — | Real Catalyst compiled graph produces fan-in `192` and fan-out `[64,128,192]` after logical-ID normalization. |
| P09 repeated-event multiplicity | non-comparable | G | No common same-source/same-tick event-list boundary exists across all participants. |
| P10 recurrent timing | architectural difference | D | Project and Catalyst produce one-tick recurrence; pinned Brian2Loihi produces no target effect in the directed neuron-to-neuron recurrence probe. |
| P11 finite-width saturation | non-comparable | E, G | M13.3 intentionally does not invent one shared overflow contract across different state/probe widths and incomplete Loihi evidence. |
| P12 simultaneous spikes | agreement | — | Per-tick spike sets agree; global event order remains non-comparable. |

## Detail: P03 negative rounding

The isolated negative CUBA probe programs:

```text
initial delivered current: -64
current decay coefficient: 1025 / 4096
voltage decay coefficient: 0
```

The corrected Catalyst native trace begins from an isolated state slot:

```text
native 0: I=-64  V=0
native 1: I=-46  V=-64
native 2: I=-33  V=-110
native 3: I=-23  V=-143
```

After the frozen native-to-canonical staging transform, the first current comparison is project/Brian `-47` versus Catalyst `-46`.

Inspection of the pinned Catalyst RTL shows that `raz_div4096` slices the high bits of the signed product and then, whenever fractional low bits are nonzero, adjusts one more unit away from zero according to sign. For this negative product, that produces a different result than the project's/Brian2Loihi's signed round-away-from-zero decay rule. This is evidence about Catalyst's implementation choice and is classified C; it does not invalidate the M12 project baseline.

## Detail: P06 negative membrane behavior

At the CPU simple-LIF boundary, a one-tick isolated `-128` delivered drive produces:

```text
project:       V=-128
Brian2Loihi:   V=-128
Catalyst CPU:  V=0
```

Catalyst's synchronous simulator returns the membrane state to its configured resting value when `potential + total_input <= leak`; with the frozen comparison settings `resting=0` and `leak=0`, sufficiently negative input therefore clamps back to zero. This is a Catalyst architectural/model choice, Class C. The mixed excitation/inhibition probe whose net drive is positive agrees across the three implementations.

## Detail: P10 recurrence

The logical directed motif is a source neuron that spikes on canonical tick 0 and drives a target neuron strongly enough to spike once the recurrent edge is delivered.

Observed source-to-target spike lag:

```text
project FPGA-v1 semantics: 1 tick
Catalyst CPU sync:         1 tick
Brian2Loihi 0.5.2:        no target effect observed
```

The project result uses the frozen next-tick recurrent route-bank contract. Catalyst's synchronous SDK delivers its previous-timestep pending spikes before the next UPDATE and therefore matches the one-tick semantic lag.

Brian2Loihi's `LoihiNetwork` explicitly orders its schedule as `start -> synapses -> groups -> thresholds -> resets -> end`. In the pinned package, the dedicated neuron-to-neuron `LoihiSynapses` probe produced no target effect despite an observed recurrent `w_act=320`. A diagnostic repeated the experiment for recurrent delays 0, 1, and 2; all remained null over six ticks while the source spike was observed. The result is classified D: a Brian2Loihi modeling/scheduling difference. M13.4 does not invent a post-hoc shift or replace the native LoihiNetwork schedule to force agreement.

## Resolved Class-H harness defects

Two comparison-harness errors were found during development and fixed before the candidate result set was frozen.

First, an early CUBA test attempted to reuse the same Catalyst neuron after toggling `rst_n`. The pinned RTL's state SRAM was not cleared by that control reset, so the negative probe inherited the preceding positive state. The final harness uses separate neuron state slots for the positive and negative cases and requires the negative native staging state to begin at `I=-64, V=0`.

Second, an early Catalyst SDK graph observer assumed compiler physical GID order was identical to logical population order. Catalyst is free to place singleton populations differently. The final graph runner records the placement and remaps native potential, refractory, and spike observations to logical IDs. After this correction, the apparent P08 discrepancy disappeared and fan-in/fan-out agreed.

Neither H issue changed project model behavior, Catalyst source, Brian2Loihi source, or the frozen M13.3 normalization.

## Change-control outcome

No M13.4 probe produced a supported Class-A project implementation defect or Class-B project-specification defect. Therefore:

```text
M10/M12 computational baseline changed: no
HLS/RTL regeneration required:          no
M12 physical evidence superseded:       no
M12 physical rerun required:            no
```

The C/D/E/G findings are audit results and scope boundaries, not reasons to make the project imitate another implementation.

## Reproducible execution

From `Neuromorphic Digital Twin`, with the comparison dependencies installed:

```bash
bash scripts/fetch_m13_1_catalyst.sh
python3 -m pip install -e build/m13_1/catalyst-n1/sdk
bash scripts/run_m13_4_catalyst_cuba_probes.sh
python3 examples/run_m13_4_differential.py \
  --output build/m13_4/differential \
  --catalyst-cuba-log build/m13_4/catalyst-rtl/native.log
python3 examples/validate_m13_4_candidate_findings.py \
  --report build/m13_4/differential/directed-report.json
```

The generated bundle preserves native/normalized artifacts and writes `build/m13_4/differential/manifest.json` plus `directed-report.json`.

Focused source-contract tests:

```bash
python3 -m pytest -q \
  tests/test_m13_3_normalization.py \
  tests/test_m13_4_directed_probes.py \
  tests/test_m13_4_differential.py
```

Full regression:

```bash
python3 -m pytest -q
```

The final automated clean candidate-closure reconstruction used Ubuntu 24.04, Icarus Verilog 12, NumPy 1.26.4, Brian2 2.9.0, Brian2Loihi 0.5.2, and the exact pinned Catalyst SDK. It reproduced the 12-probe findings snapshot, passed **30/30 focused M13.3/M13.4 tests**, and passed the complete **331/331 project regression**. A branch-diff guard also verified that M13.4 introduced no computational-core, HLS-core, or FPGA-v1 behavioral changes.

## M13.4 pass boundary

M13.4 is ready for independent validation when all of the following are true:

- the exact Catalyst and Brian2Loihi source pins are unchanged;
- all 12 frozen directed probe questions have an explicit agreement/difference/scope outcome;
- every meaningful difference has an A-H classification and first divergence where an exact field is comparable;
- native evidence is preserved before normalization;
- P03, P06, and P10 reproduce with the recorded classifications;
- P08 remains agreement after logical compiler-placement normalization;
- non-comparable P09/P11 fields are not coerced into equality tests;
- no unresolved Class-H harness defect remains;
- no A/B candidate exists, or any A/B candidate has completed the required M12 change-control loop;
- focused M13.4 tests and the complete historical regression pass;
- no computational-core/HLS/FPGA-v1 behavior changed as part of the audit.

The automated candidate satisfies these criteria with zero A/B candidates. M13.4 remains **In progress** only until the development branch is independently pulled and the validation commands are reproduced.
