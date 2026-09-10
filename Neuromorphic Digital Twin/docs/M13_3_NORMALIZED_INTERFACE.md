# M13.3 — Common Behavioral Subset and Normalized Comparison Interface

**Status:** In progress — implementation is complete and frozen; independent local validation is required before milestone closure and merge.

## Purpose

M13.3 freezes the normalization rules that later M13 differential probes must use. Its purpose is not to make this project's FPGA, Brian2Loihi, and Catalyst N1 produce identical outputs. Its purpose is to define, before broad comparison, which architectural quantities have a defensible common meaning, how native parameters are translated, which timestep boundaries correspond, and which fields must remain qualitative or non-comparable.

The machine-readable authority is:

```text
references/m13_3_normalization_spec.json
schema = neuromorphic-twin-m13-normalization-v1
status = frozen
version = 1
```

The executable implementation is `src/neuromorphic_twin/comparison/m13_normalization.py`.

The specification is based on the M12-closed project baseline and the M13.1/M13.2 source pins. It does not change the project computational core, HLS, RTL, or physical-FPGA evidence.

## Evidence boundary

M13.3 is a **mapping specification**, not a discrepancy result. Published Loihi material remains the authority for claims about Loihi itself. Brian2Loihi 0.5.2 and Catalyst N1 are independent implementations or interpretations. Agreement among them is useful evidence but does not establish undocumented Intel behavior.

M13.3 therefore obeys four rules:

1. transforms are selected before M13.4 Catalyst differential outputs are inspected;
2. native configuration and traces are retained beside normalized artifacts;
3. unlike native states are never renamed into artificial equality;
4. a later disagreement cannot cause these transforms to be changed merely to obtain a pass.

A mapping defect discovered later is a Class-F finding and must be corrected transparently rather than retrofitted to one output.

## Comparison categories

Every normalized observable is assigned one of four categories.

| Category | Meaning |
|---|---|
| `exact` | The same architectural quantity is already represented in the same normalized integer units. |
| `transformed` | The same intended quantity is comparable only after an explicitly frozen parameter, state-unit, identifier, or tick transform. |
| `qualitative` | The implementations expose related behavior, but the available interfaces do not justify integer equality. |
| `non_comparable` | No defensible shared observable exists at the selected boundary; native evidence is preserved only. |

This vocabulary is normative for the M13.4 comparison layer.

## Canonical comparison boundary

### Algorithmic time

One canonical tick means one **committed target-neuron update**. Internal HLS/RTL clock cycles, Catalyst FSM states, Brian scheduler phases, and host/JTAG transactions are not canonical time.

### State units

The canonical integer state unit is the project's effective current/voltage integer unit. There is no hidden scale factor applied to Catalyst potential/current values. The common state-observation envelope is restricted to signed 16-bit values (`-32768..32767`) because Catalyst exposes 16-bit probe/parameter interfaces even where the pinned RTL stores wider internal state.

### Logical identifiers

Comparisons use zero-based logical neuron identity, not raw CSR addresses, route slots, physical FIFO positions, or project axon-memory addresses. Common scenarios are restricted to one logical core and at most 256 logical neurons so the same corpus remains portable to the pinned Catalyst K26 configuration used later in M13.5.

### Spike observable

The common spike quantity is binary spike presence for a logical neuron on a canonical tick. Native payloads are retained but are not treated as an exact cross-implementation quantity.

## Frozen common constraints

The shared behavioral subset disables features that are not represented across the current project baseline:

```text
one logical core
<= 256 logical neurons
reset voltage = 0
bias = 0
learning = disabled
graded spikes = disabled
dendritic compartments = disabled
noise = disabled
programmable synaptic delay = disabled for the common baseline
multicore NoC = excluded
```

Thresholds in the shared exact/transformed subset are multiples of 64 in `64..32704`. Legacy effective weights are multiples of 64 in `-16384..16320`. Shared refractory durations are `1..64` canonical ticks.

These are comparison-domain restrictions, not newly imposed limits on the project's FPGA-v1 implementation.

## Catalyst is represented by two explicit profiles

M13.2 showed that treating Catalyst as one undifferentiated neuron model would be misleading. M13.3 therefore freezes two Catalyst participation profiles.

### `catalyst_cpu_sync`

The pinned `sdk/neurocore/simulator.py` synchronous path executes `DELIVER -> UPDATE -> LEARN`. In the disabled-learning common subset it is useful for simple threshold, reset, refractory, delivered-drive, and logical recurrent questions. It exposes membrane potential and refractory state but does not expose the same independent dual current state as the project/Brian2Loihi model.

For this profile:

```text
async = false
learning = false
graded = false
dendritic = false
noise = false
leak = 0
resting = 0
```

Current state is therefore marked non-comparable rather than fabricated from the injected drive.

### `catalyst_rtl_cuba`

The pinned `rtl/scalable_core_v2.v` contains separate current and potential memories and 12-bit `decay_u`/`decay_v` fields. It is the Catalyst boundary used for dual-state CUBA probes.

For the common CUBA profile:

```text
scale_u_enable = false
learning = false
graded = false
dendritic = false
noise = false
resting = 0
bias_cfg = 0
```

Catalyst CPU simple-LIF output must never be substituted for this RTL CUBA boundary in a dual-current comparison.

## Threshold normalization

The project and Brian2Loihi use a strict threshold test:

```text
V > T
```

The pinned Catalyst CPU and RTL paths use:

```text
V >= T_native
```

Because compared states are integers, the two predicates are exactly equivalent when:

```text
T_native = T + 1
```

Proof:

```text
V > T    iff    V >= T + 1       for integer V and T
```

Therefore M13.3 freezes:

```text
project threshold       = T
Brian threshold mantissa = T / 64
Catalyst threshold      = T + 1
```

This transform intentionally removes only the comparator-notation difference when a probe asks a shared strict-threshold question. M13.4 may still run a native-threshold-equality probe to document that Catalyst's unnormalized native comparator is `>=`; normalization must not erase that architectural fact from the native evidence.

## Refractory normalization

The canonical refractory duration `R` is semantic rather than register-level:

> If a neuron spikes on tick `t`, `t + R` is the first canonical tick on which it is eligible to spike again.

The project already uses that definition. Brian2Loihi's configured refractory duration is also mapped as `R` for the supported `1..64` domain.

Catalyst loads its raw refractory counter **after** the spike update and then blocks while that counter is greater than zero. To produce the same first-eligible tick, M13.3 programs:

```text
Catalyst raw refractory parameter = R - 1
```

For example, canonical `R=3` becomes Catalyst raw value `2`:

```text
t       spike, load 2
t+1     blocked, 2 -> 1
t+2     blocked, 1 -> 0
t+3     eligible
```

Consequently the preferred common observable is `next_eligible_tick`, not equality of native refractory registers.

## Static-weight normalization

The common semantic quantity is the **final signed effective current contribution** `W`.

For legacy exponent-zero project/Brian cases:

```text
project effective weight = W
Brian mantissa            = W / 64
Brian exponent            = 0
Brian precision           = 8
Catalyst weight/current   = W
```

The shared legacy domain is restricted so the Brian mantissa and Catalyst signed-16-bit value are both representable.

For M08 Loihi-style encoded weights, project and Brian2Loihi retain requested mantissa, exponent, precision, sign mode, quantized mantissa, and observed/final effective value. Catalyst does not expose that same Loihi-style source encoding contract. Therefore:

- final effective weight is transformed-comparable when representable;
- mantissa/exponent/precision/sign-mode fields are non-comparable for Catalyst;
- M13.4 must retain the native project/Brian source encoding instead of pretending Catalyst used it.

## Direct-drive scenario class

Catalyst CPU lacks the project's explicit input-axon-to-current-state boundary. M13.3 therefore defines a restricted `cpu_direct_drive` class for neuron-semantics probes.

The canonical axon-event rows are collapsed exactly into the mathematical per-target effective current delivered during each tick. This is allowed only when:

```text
current_decay = 4096
voltage_decay = 0
bias = 0
reset = 0
no recurrence
```

Full current decay is required so the project's hidden current register cannot persist into a later tick while Catalyst CPU has no corresponding current state. Under this class, the comparison asks whether the **same delivered target drive** produces the same membrane/spike/refractory behavior. It does **not** claim that Catalyst traversed the same external axon CSR structure.

The translator fails if these preconditions are violated.

## Dual-state CUBA isolated-impulse alignment

The pinned Catalyst CUBA RTL has an important update-order difference. New external input is written into current during a native timestep, while voltage uses the previously stored current. The project's FPGA-v1 path instead makes same-tick delivered input visible to the voltage update.

For a canonical isolated impulse `S` from zero state, followed only by zero-input ticks, the two traces can be aligned without hiding arbitrary future input timing.

Ignoring threshold/refractory effects and writing `D_I`/`D_V` for the common decay operators, the project starts:

```text
canonical tick 0:
I_p[0] = D_I(S)
V_p[0] = S
```

Catalyst CUBA native timestep 0 stages the new current:

```text
native tick 0:
I_c[0] = S
V_c[0] = 0
```

On the following zero-input native timestep:

```text
native tick 1:
I_c[1] = D_I(S)
V_c[1] uses previous current S
```

Therefore M13.3 freezes the observation mapping for **this restricted scenario class only**:

```text
canonical tick k  <-  Catalyst native tick k+1
```

Catalyst native tick 0 is retained in the native trace as a staging/warmup tick and is never deleted from the evidence; it is merely excluded from the normalized comparison view.

This does **not** authorize a global one-tick shift for arbitrary input schedules. If later input occurs, the project's input-before-decay/same-tick-voltage behavior and Catalyst's staged-current behavior are themselves the architectural quantity being tested. The translator therefore rejects any `rtl_cuba_isolated_impulse` scenario with nonzero external input after canonical tick 0.

The shared Catalyst RTL decay domain is `0..4095` because its pinned decay memories are 12 bits. The project's/Brian2Loihi `4096` full-decay endpoint remains valid natively but is outside the Catalyst CUBA exact/transformed common subset.

## Logical recurrence normalization

Raw project recurrence is represented as:

```text
source neuron -> target axon -> target synapse row
```

Brian2Loihi and Catalyst naturally represent logical neuron-to-neuron synapses. M13.3 therefore defines recurrence comparison on a flattened logical edge multiset:

```text
(source_neuron, target_neuron, effective_weight)
```

The project route plus target-axon row is expanded into those logical edges. Brian2Loihi uses recurrent `LoihiSynapses`; Catalyst uses same-core sparse connections in synchronous mode. Raw route-table addresses, CSR pool addresses, route slots, and FIFO order are not compared.

The normalized recurrent observable is the lag from source spike tick to first target effect/spike plus target state/spike outcomes and representable multiplicity. Importantly, M13.3 does **not** predeclare a Brian2Loihi output shift to force next-tick agreement: its native delay-0 lag is measured in M13.4 and preserved as evidence.

## Event ordering and multiplicity

The project exposes a strong ordered-event trace. Brian2Loihi does not expose an equivalent hardware-style global event FIFO trace, and Catalyst uses its own FIFO/mesh organization. M13.3 therefore distinguishes:

- delivered target accumulation and logical edge multiplicity, which can often be compared;
- global total order of coincident events, which is non-comparable unless every participating interface exposes a defensible order;
- repeated copies of one source event in one tick, which remain project-native evidence when an external source interface cannot represent the same event multiplicity.

No deduplication or invented ordering is allowed in normalization.

## Finite-width behavior

The project has a frozen SAT24 policy. Earlier Brian2Loihi comparisons deliberately avoided overflow, and Catalyst contains its own width/assignment behavior. M13.3 therefore excludes universal overflow/saturation equality from the common exact subset.

Finite-width probes remain valuable M13.4 architecture-specific evidence, but they must be classified as native/qualitative unless a later source establishes a genuinely shared operation.

## Field policy summary

| Field | Project | Brian2Loihi | Catalyst CPU sync | Catalyst RTL CUBA |
|---|---|---|---|---|
| current after tick | exact | exact | non-comparable | transformed |
| voltage after tick | exact | exact | transformed | transformed |
| spike presence | exact | exact | transformed | transformed |
| spike payload | non-comparable | non-comparable | non-comparable | non-comparable |
| threshold configuration | exact | transformed | transformed | transformed |
| raw refractory register | exact | non-comparable | transformed | transformed |
| next eligible tick | exact | transformed | transformed | transformed |
| final effective weight | exact | transformed | transformed | transformed |
| Loihi-style source weight fields | exact | transformed | non-comparable | non-comparable |
| logical edge multiset | transformed | transformed | transformed | transformed |
| raw coincident-event total order | exact | non-comparable | non-comparable | qualitative |
| same-source/same-tick duplicate event | exact | non-comparable | non-comparable | qualitative |
| overflow/saturation contract | exact | non-comparable | non-comparable | qualitative |
| hardware cycle count | non-comparable | non-comparable | non-comparable | non-comparable |

## Small translation-smoke corpus

M13.3 freezes four minimal cases before broad M13.4 execution:

1. `m13-3-threshold-boundary` — Catalyst `T+1` threshold translation;
2. `m13-3-refractory-release` — canonical `R=3` to Catalyst raw `2`;
3. `m13-3-signed-drive` — positive and negative effective current collapse;
4. `m13-3-isolated-cuba-decay` — Catalyst CUBA native warmup/tick alignment.

The purpose of these four cases is to prove that the frozen common schema can generate native plans and normalized artifacts. **M13.3 does not issue a cross-backend PASS/FAIL verdict for them.** Differential interpretation remains M13.4.

Run the mapping-only gate with:

```bash
PYTHONPATH=src python3 examples/run_m13_3_normalization.py
```

Generate project/Brian native and normalized evidence plus Catalyst native plans with:

```bash
PYTHONPATH=src python3 examples/run_m13_3_normalization.py \
  --output build/m13_3/translation_smoke
```

When the pinned Catalyst SDK is available on `PYTHONPATH`, the first three CPU-profile plans can also be executed:

```bash
PYTHONPATH="src:/path/to/catalyst-n1/sdk" \
python3 examples/run_m13_3_normalization.py \
  --output build/m13_3/translation_smoke \
  --execute-catalyst-cpu
```

The bundle preserves native plans, native traces, normalized views, and a SHA-256 manifest. The manifest explicitly records that no differential comparison and no A-H discrepancy classification were performed.

## Comparison-runtime reproducibility

A fresh M13.4 pre-normalization run exposed a Class-H environment incompatibility: an unconstrained modern NumPy installation could select NumPy 2.x while the installed Brian2 path still referenced an API removed from `ndarray`. The project comparison extra is therefore pinned to the exact validated software stack:

```text
numpy==1.26.4
brian2==2.9.0
brian2-loihi==0.5.2
```

This pin changes no neuron behavior. It makes the external-reference environment reconstructable and prevents dependency resolution from changing the comparison executable underneath M13.

## Explicit exclusions

M13.3 does not normalize dendritic trees, online plasticity, trace learning, stochastic noise, graded payload equivalence, general programmable delays, multicore NoC behavior, management processors, raw routing-memory organization, production host control, power, resource utilization, or hardware-cycle performance.

Those features remain architectural scope differences or belong to M13.5/M13.6. Their absence from the common behavioral subset must not be interpreted as evidence that they are unimportant to Loihi or Catalyst.

## M13.4 handoff

M13.4 must consume the frozen schema/version above. It may add native adapters and evidence capture required to execute the already-frozen probe catalog, but it must not silently choose a new threshold offset, refractory convention, decay coefficient, state scale, logical-edge mapping, or tick shift after seeing outputs.

For every M13.4 probe:

```text
canonical scenario
      -> frozen M13.3 transform
      -> native configuration/input
      -> native trace (preserved)
      -> normalized trace
      -> compare only fields authorized by field_policy
```

A disagreement in a transformed field is evidence to investigate. It is not permission to retune the transform.

## Completion boundary

The implementation reaches the M13.3 pass boundary when:

- the frozen machine-readable specification validates;
- each transform is covered by executable tests;
- the four-case common corpus generates native plans for every applicable implementation;
- project and Brian2Loihi native/normalized traces can be materialized;
- the pinned Catalyst synchronous CPU profile executes the applicable plans in the pinned SDK environment;
- the Catalyst RTL CUBA plan is generated with its exact source-level parameter/tick contract for M13.4 RTL execution;
- non-comparable fields are explicitly represented rather than coerced;
- the complete historical project regression remains green;
- an independent local checkout reproduces the requested validation commands.

Milestone status remains **In progress** until that final independent local validation is reported.
