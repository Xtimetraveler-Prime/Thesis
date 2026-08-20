# Thesis Milestones

This file records major research and implementation milestones for the FPGA-based, Loihi-inspired neuromorphic digital twin.

Dates before this tracker was created were reconstructed from the project conversation and repository history. Future milestones should be updated when work begins and when their completion evidence is reproducible.

## Status legend

- **Complete** — completion criteria have been met and evidence is recorded.
- **In progress** — active work has started but completion criteria are not met.
- **Planned** — agreed future work that has not started.
- **Blocked** — progress is waiting on a dependency or unresolved decision.

## Summary

| ID | Milestone | Status | Started | Completed |
|---|---|---|---|---|
| M01 | Define thesis direction: FPGA Loihi digital twin | Complete | 2026-07-18 | 2026-07-18 |
| M02 | Build initial integer Python golden model | Complete | 2026-07-18 | 2026-07-18 |
| M03 | Implement Brian2Loihi comparison harness | Complete | 2026-07-18 | 2026-07-18 |
| M04 | Pass basic integration smoke test | Complete | 2026-07-18 | 2026-07-18 |
| M05 | Correct and validate current-decay update order | Complete | 2026-07-18 | 2026-07-18 |
| M06 | Build directed deterministic conformance suite | Complete | 2026-07-29 | 2026-07-29 |
| M07 | Validate all directed neuron and synapse cases | Complete | 2026-07-29 | 2026-07-29 |
| M08 | Add Loihi-native weight representation | Complete | 2026-07-29 | 2026-08-03 |
| M09 | Add recurrent spike routing | Complete | 2026-08-20 | 2026-08-20 |
| M10 | Freeze computational-core specification | Complete | 2026-08-20 | 2026-08-20 |
| M11 | Implement first FPGA neuron/core datapath | In progress | 2026-08-20 | — |
| M12 | Validate FPGA against Python golden model | Planned | — | — |

---

## M01 — Define thesis direction: FPGA Loihi digital twin

**Status:** Complete  
**Started:** 2026-07-18  
**Completed:** 2026-07-18

### Goal

Define a thesis direction in which an FPGA implements a transparent digital twin of a Loihi-inspired neuromorphic processor rather than only hosting an isolated spiking neural network.

### Outcome

```text
Brian2Loihi reference
        ↓
Python golden model
        ↓
FPGA implementation
```

Brian2Loihi is the external behavioral reference during model validation. After conformance is established, the transparent Python model becomes the golden reference for RTL, HLS, and physical-FPGA comparisons.

### Completion evidence

- The research direction was explicitly defined.
- The project was organized around backend-neutral trace comparison.
- FPGA implementation was deferred until neuron and core semantics were validated.

### Key decisions

- Build the Python model independently rather than modifying Brian2Loihi.
- Keep every state transition explicit and integer-based.
- Treat update ordering as part of the processor architecture.
- Extend beyond Brian2Loihi only after validating the computational core.

---

## M02 — Build initial integer Python golden model

**Status:** Complete  
**Started:** 2026-07-18  
**Completed:** 2026-07-18  
**Repository evidence:** `6f01889b99f6f651a0bae044aaabf108deb6b717`

### Goal

Create a transparent, deterministic model whose state and control flow map naturally to an FPGA implementation.

### Delivered

- Integer current-based leaky integrate-and-fire neuron transition.
- Explicit current and voltage decay.
- Threshold, reset, bias, and refractory state.
- Fixed-weight excitatory and inhibitory synapses.
- Axon fan-in and fan-out.
- Tick-indexed immutable traces.
- Configurable unbounded, saturating, and wrapping arithmetic.
- Unit tests for arithmetic, neuron behavior, and core behavior.

### Key decisions

- Use integer-only state transitions.
- Separate arithmetic policy from neuron behavior.
- Keep the single-neuron transition pure and independently testable.
- Use a structure-of-arrays state layout suitable for FPGA memories.

### Known limitations

- No recurrent output routing.
- No synaptic delays or packet queues.
- No learning rule.
- Exact Loihi state widths and overflow behavior remain unresolved outside the validated subset.

---

## M03 — Implement Brian2Loihi comparison harness

**Status:** Complete  
**Started:** 2026-07-18  
**Completed:** 2026-07-18  
**Repository evidence:** `6f01889b99f6f651a0bae044aaabf108deb6b717`

### Goal

Run identical deterministic scenarios through Brian2Loihi and the Python model, normalize both results, and compare state exactly.

### Delivered

- Backend-neutral `ComparisonScenario` definitions.
- Normalized per-tick `BackendTrace` records.
- Python and Brian2Loihi backend adapters.
- Exact current, voltage, and spike comparison.
- Human-readable mismatch reports.
- Stable JSON trace and report interchange.
- Saved-trace comparison for future RTL and FPGA backends.

### Adapter scope

- One common neuron configuration per Brian2Loihi group.
- Zero bias and zero reset voltage.
- Representable thresholds and weights.
- Separate excitatory and inhibitory synapse groups.
- No duplicate spike from one axon in one tick.
- No saturation or wrapping during reference comparison.

---

## M04 — Pass basic integration smoke test

**Status:** Complete  
**Started:** 2026-07-18  
**Completed:** 2026-07-18

### Goal

Verify that the simplest end-to-end Brian2Loihi comparison executes correctly and that basic mappings agree.

### Validated behavior

- Input axon mapping.
- Synaptic weight scaling.
- Threshold scaling.
- Current accumulation.
- Voltage integration.
- Spike timing and reset.

### Completion evidence

```bash
python examples/compare_brian2loihi.py --scenario smoke
```

Result: `PASS`.

### Environment decision

Brian2 code generation is explicitly set to NumPy to avoid dependence on a local Cython compiler and Python development headers.

---

## M05 — Correct and validate current-decay update order

**Status:** Complete  
**Started:** 2026-07-18  
**Completed:** 2026-07-18  
**Repository evidence:** `6f01889b99f6f651a0bae044aaabf108deb6b717`

### Goal

Determine the exact relationship among delivered synaptic input, current decay, voltage integration, and stored next-current state.

### Discovery and correction

The original model decayed old current before adding new input. Brian2Loihi showed that new synaptic input must be visible before the neuron update.

The corrected contract is:

```text
current_for_voltage = previous_current + delivered_input
voltage_next uses current_for_voltage
current_next = decay(current_for_voltage)
```

### Delivered

- Corrected `step_neuron()` ordering.
- Regression test proving new input is visible to voltage before decay.
- Regression sequence proving stored current follows `64, 32, 16` after a half-decay impulse of `128`.

### Completion evidence

```bash
python examples/compare_brian2loihi.py --scenario decay-order
```

Result: `PASS`.

### Architectural implication

The FPGA datapath should expose newly accumulated working current to the voltage path and separately write the decayed value into the current-state register.

---

## M06 — Build directed deterministic conformance suite

**Status:** Complete  
**Started:** 2026-07-29  
**Completed:** 2026-07-29  
**Repository evidence:** `47be971cf47b609d3f108647656887e7a26a1b77`

### Goal

Replace isolated probes with a repeatable suite in which each scenario asks one targeted architectural question.

### Delivered

- Twelve deterministic conformance scenarios.
- Case listing and selection.
- Full-suite execution and stop-on-first-failure mode.
- Per-case traces and comparison reports.
- Top-level machine-readable suite report.
- Unit tests and dedicated documentation.

### Directed cases

1. `smoke-no-decay`
2. `current-decay-order`
3. `voltage-decay`
4. `negative-current-rounding`
5. `inhibitory-synapse`
6. `threshold-boundary`
7. `refractory-one-tick`
8. `refractory-three-ticks`
9. `simultaneous-fan-in`
10. `fan-out`
11. `mixed-excitation-inhibition`
12. `multiple-simultaneous-spikes`

### Important distinction

This milestone establishes the suite. External agreement for every case is recorded in M07.

---

## M07 — Validate all directed neuron and synapse cases

**Status:** Complete  
**Started:** 2026-07-29  
**Completed:** 2026-07-29  
**Repository evidence:** PR #2, `6591a17e96b99d665428adf51b5c04fbd10180a6`

### Goal

Execute all directed scenarios against Brian2Loihi, diagnose each first divergence, and revise the Python computational contract until the supported subset conforms exactly.

### Initial result

The first complete run passed 10 of 12 cases. Both failures were isolated to refractory release timing:

```text
refractory-one-tick: 1 spike mismatch
refractory-three-ticks: 2 spike mismatches
```

The Python model released a neuron one tick later than Brian2Loihi because it loaded the full configured refractory duration after the spike tick had already occurred.

### Correction

The spike tick now counts as part of `refractory_ticks`. After a spike at tick `t`, the neuron is next eligible at:

```text
t + refractory_ticks
```

The model therefore loads `max(refractory_ticks - 1, 0)` future blocked ticks. Focused neuron and core regression tests preserve release timing, current updates during blocked ticks, reset-voltage holding, and release without forced spiking.

### Completion criteria

- [x] Run the complete suite in the Brian2Loihi environment.
- [x] Record the initial pass/fail/error summary.
- [x] Diagnose the earliest mismatch in every failing category.
- [x] Add a regression test for each corrected behavior.
- [x] Re-run the suite after the correction.
- [x] Achieve exact agreement for all supported cases.
- [x] Record final evidence and mark this milestone complete.

### Completion evidence

Python regression suite:

```text
28 passed
```

Final Brian2Loihi directed conformance result:

```text
cases=12, pass=12, fail=0, error=0, ticks=34, mismatches=0
```

All twelve supported deterministic scenarios agree exactly on compared current, voltage, and spike traces.

---

## M08 — Add Loihi-native weight representation

**Status:** Complete  
**Started:** 2026-07-29  
**Completed:** 2026-08-03  
**Repository evidence:** PR #3 and PR #4

### Goal

Represent static synaptic weights using explicit Loihi-style mantissa, exponent, precision, and sign-mode concepts while preserving a deterministic, integer-only path from reference behavior to an FPGA-loadable storage image.

### Scope decisions

- Implement published static-weight initialization behavior independently rather than copying Brian2Loihi source code.
- Keep weight-format configuration separate from each synapse's mantissa so exponent, precision, and sign mode can be shared in FPGA memory.
- Preserve requested, quantized, unclipped, and final effective values for traceability.
- Defer plastic weights and stochastic rounding to a later milestone.
- Keep the effective integer as the sole core-datapath interface while retaining immutable source encoding metadata.
- Freeze a project-specific Loihi-inspired memory profile without claiming it reproduces Intel Loihi's undocumented physical SRAM layout.

### Final outcome

```text
requested mantissa + shared WeightFormat
                  ↓
validated integer encoder
                  ↓
production Synapse.encoded(...)
                  ↓
Python core and generic Brian2Loihi backend
                  ↓
frozen JSON + hexadecimal FPGA memory image
```

All five M08 sub-milestones are complete. The software representation, external conformance path, trace schema, and FPGA-oriented storage contract now share one tested interpretation of each static weight.

### Overall completion evidence

- Pure and exhaustive encoder validation: `147,456` valid combinations.
- Complete current Python regression suite: `80 passed`.
- Legacy Brian2Loihi conformance: `12/12`, zero mismatches.
- Production encoded-weight conformance: `15/15`, zero mismatches.
- Reproducible versioned JSON and fixed-width `.mem` storage artifacts.
- Frozen field widths, signed encodings, reserved values, format capacity, and CSR routing organization.

---

### M08.1 — Implement pure static weight encoder

**Status:** Complete  
**Started:** 2026-07-29  
**Completed:** 2026-07-29  
**Repository evidence:** PR #3, branch `agent/m08-weight-encoder`

### Delivered

- `WeightSignMode` for mixed, excitatory, and inhibitory formats.
- `WeightFormat` containing exponent, number of weight bits, and sign mode.
- Sign-mode-specific mantissa validation.
- Mantissa quantization toward zero at configured precision.
- Exponent scaling and final alignment to multiples of 64.
- Signed 21-bit-aligned clipping.
- A traceable `StaticWeightEncoding` containing requested and quantized mantissas, pre-clip value, final value, and clipping status.

### Completion criteria

- [x] Pure encoder is implemented without Brian2Loihi as a runtime dependency.
- [x] Public types are exported from the package.
- [x] Integer-only behavior is documented for later RTL translation.
- [x] Focused unit tests pass.

### Completion evidence

```text
50 passed
```

The result was independently reproduced from the development branch on 2026-07-29.

---

### M08.2 — Exhaustively validate encoder arithmetic

**Status:** Complete  
**Started:** 2026-07-29  
**Completed:** 2026-07-29  
**Repository evidence:** PR #3, branch `agent/m08-weight-encoder`

### Delivered

- Directed tests for all documented configuration boundaries.
- An equation-oriented reference calculation that does not call encoder helpers.
- A full sweep of all `147,456` valid static-weight input combinations.
- Exact comparisons of requested mantissa, quantized mantissa, pre-clip value, final value, clipping flag, alignment, and output bounds.

The sweep covers:

- Exponents `-8..7`.
- Weight-bit settings `0..8`.
- Excitatory, inhibitory, and mixed sign modes.
- Positive and negative quantization toward zero.
- Negative fractional alignment.
- Minimum and maximum mantissas.
- Extreme negative clipping.

### Completion criteria

- [x] Every configuration boundary has a directed test.
- [x] Cross-product tests preserve quantization, alignment, and clipping invariants.
- [x] A complete valid-input sweep is practical and reproducible.
- [x] The complete branch test suite was independently rerun.

### Completion evidence

```text
55 passed
```

The complete branch suite, including the exhaustive `147,456`-case sweep, was independently reproduced on 2026-07-29.

---

### M08.3 — Validate encoded weights against Brian2Loihi

**Status:** Complete  
**Started:** 2026-08-03  
**Completed:** 2026-08-03  
**Repository evidence:** PR #4, branch `agent/m08-weight-conformance`

### Validation boundary

- Give the Python candidate the encoder's derived effective integer.
- Give Brian2Loihi the original requested mantissa, exponent, precision, and sign mode.
- Compare Brian2Loihi's directly observable `w_act` and the resulting current, voltage, and spike traces.

### Tests added

- Fifteen directed encoded-weight cases covering positive and negative exponents, negative-exponent alignment, reduced precision, mixed-sign quantization, sign-mode extrema, zero configured weight bits, and clipping.
- Five harness tests covering case scope, Python mapping, passing behavior, direct effective-weight mismatch detection, and suite JSON evidence.
- Per-case traces and exact comparison reports plus a suite-level result.

### Completion criteria

- [x] Directed cases cover all agreed static-weight boundaries.
- [x] Python effective weights are compared directly with Brian2Loihi `w_act`.
- [x] Current, voltage, and spike traces are compared exactly.
- [x] Stable per-case and suite-level artifacts are produced.
- [x] All supported cases agree exactly.

### Completion evidence

```text
cases=15, pass=15, fail=0, error=0, ticks=15, mismatches=0
```

Passing all fifteen cases means the Python encoder's final effective integer equals Brian2Loihi `w_act` for each tested format boundary, and the resulting one-synapse current, voltage, and spike traces also agree exactly.

---

### M08.4 — Integrate encoded weights into synapses and traces

**Status:** Complete  
**Started:** 2026-08-03  
**Completed:** 2026-08-03  
**Repository evidence:** PR #4, branch `agent/m08-weight-conformance`

### Architecture selected

- `Synapse.weight` remains the only integer consumed by `NeuromorphicCore`.
- `Synapse.encoding` optionally retains the immutable `StaticWeightEncoding` that produced it.
- `Synapse.encoded(...)` derives and validates both representations together.
- Backend traces contain structured synapse descriptors.
- Trace schema v2 stores encoded metadata while readers remain compatible with v1.
- The generic Brian2Loihi adapter groups connections by `(exponent, num_weight_bits, sign_mode)` and restores observed `w_act` values to original scenario order.

### Delivered

- Backward-compatible encoded production synapses.
- An invariant rejecting disagreement between the stored effective integer and encoding.
- One unchanged integer accumulation path in the core.
- Generic backend support for legacy-only, encoded-only, and mixed scenarios.
- All fifteen weight cases routed through production `Synapse.encoded(...)` scenarios and the generic backend.
- Eight focused integration tests covering construction, invariants, core equivalence, trace metadata, v2 round-trip, v1 compatibility, mixed grouping, and observed-weight order restoration.

### Completion criteria

- [x] Complete Python suite passes after schema changes.
- [x] Twelve original Brian2Loihi cases remain exact.
- [x] Generic adapter groups encoded synapses by exponent, precision, and sign mode.
- [x] Weight-conformance scenarios use `Synapse.encoded(...)` directly.
- [x] Fifteen encoded cases pass through the production path.
- [x] Trace-v2 artifacts preserve every encoded-weight field.

### Completion evidence

```text
68 passed
8 focused integration tests passed
cases=12, pass=12, fail=0, error=0, ticks=34, mismatches=0
cases=15, pass=15, fail=0, error=0, ticks=15, mismatches=0
```

Representative trace-v2 encoding payload:

```text
{
  'requested_mantissa': 124,
  'quantized_mantissa': 124,
  'exponent': 0,
  'num_weight_bits': 8,
  'sign_mode': 'excitatory',
  'effective_weight_before_clip': 7936,
  'clipped': False
}
```

For that case, `124 × 64 = 7936`; no precision truncation or clipping occurred.

---

### M08.5 — Freeze FPGA-oriented weight storage

**Status:** Complete  
**Started:** 2026-08-03  
**Completed:** 2026-08-03  
**Repository evidence:** PR #4, branch `agent/m08-weight-conformance`

### Goal

Convert the validated software representation into a fixed binary contract that host tools, HDL testbenches, RTL, and physical FPGA memories can consume without reinterpretation.

### Why this sub-milestone was required

- Python objects such as `WeightFormat`, `StaticWeightEncoding`, and enum values are not BRAM layouts.
- Vivado and RTL need exact word widths, bit positions, signed encodings, reserved-bit behavior, table capacities, and routing-memory organization.
- Freezing these choices before neuron/core RTL prevents hardware convenience changes from silently altering validated weight semantics.
- A stable memory image allows software configuration, simulation, and the physical FPGA to consume identical words.
- Sharing formats reduces repeated metadata but adds a table and index, so the memory tradeoff needed an explicit estimate.

### Frozen storage profile v1

#### Shared format word — 16 bits

| Bits | Field | Encoding |
|---|---|---|
| `[3:0]` | exponent | signed four-bit two's complement, `-8..7` |
| `[7:4]` | `num_weight_bits` | unsigned four-bit value, valid `0..8` |
| `[9:8]` | sign mode | `00=mixed`, `01=excitatory`, `10=inhibitory`, `11=reserved` |
| `[15:10]` | reserved | must be zero |

#### Per-synapse word — 32 bits

| Bits | Field | Encoding |
|---|---|---|
| `[8:0]` | requested mantissa | signed nine-bit two's complement, `-256..255` |
| `[12:9]` | format index | unsigned four-bit index, up to 16 formats |
| `[28:13]` | target neuron | unsigned sixteen-bit neuron ID |
| `[31:29]` | reserved | must be zero |

#### CSR axon routing

- Axon IDs are sixteen-bit row-table addresses and are not repeated in every synapse word.
- Thirty-two-bit row pointers store each row's start and terminal offsets.
- Synapse records are ordered by ascending axon ID while preserving source order inside each row.

The record stores the requested mantissa rather than a quantized mantissa or final effective integer. Requested mantissa plus shared format is the validated source representation from which the existing encoder reconstructs quantization, exponent alignment, clipping, and the effective weight.

Legacy integer-only synapses are rejected by the freezer because their source mantissa and format can be ambiguous after quantization, negative-exponent alignment, or clipping.

### Delivered

- Public strict pack/unpack APIs for format and synapse words.
- Two's-complement conversion and reserved-value rejection.
- `FrozenWeightStorage` with deterministic format deduplication and CSR rows.
- Decode back into production `Synapse.encoded(...)` objects.
- Versioned JSON manifest schema:

```text
neuromorphic-twin-fpga-weight-storage-v1
```

- Fixed-width hexadecimal memory files:

```text
weight_formats.mem
weight_synapses.mem
weight_axon_rows.mem
```

- Shared-versus-inline logical-bit and capacity-only BRAM36 estimator.
- Hardware-facing `docs/FPGA_WEIGHT_STORAGE.md`.
- `examples/build_fpga_weight_image.py` for generating directly inspectable memory images from the validated cases.

### Storage-cost decision

Repeating all format fields requires 35 used bits per synapse and naturally maps to a 36-bit physical word. The shared profile uses a 32-bit synapse word and a 16-bit entry per unique format.

Excluding the common row-pointer table:

```text
shared format: 32N + 16F bits
inline format: 36N bits
savings:        4N - 16F bits
```

`N` is synapse count and `F` is unique format count. Shared storage breaks even at `N = 4F` and saves logical capacity for `N > 4F`.

BRAM36 figures are documented as capacity-only lower bounds. Legal width/depth configurations, banking, parity use, placement, and timing may increase actual synthesized utilization.

### Tests added

Twelve focused storage tests cover:

- Public API availability.
- All 432 possible weight-format configurations.
- Signed field and routing boundaries.
- Reserved and corrupt-image rejection.
- Deterministic format deduplication and CSR reconstruction.
- Legacy-synapse and format-capacity rejection.
- Empty storage behavior.
- Shared-versus-inline estimates.
- JSON and fixed-width hexadecimal artifact reproducibility.
- Every one of the `147,456` valid static-weight combinations.

The exhaustive storage test packs and unpacks each requested mantissa and format, re-runs the validated encoder, and requires the complete `StaticWeightEncoding` to match, including quantized mantissa, pre-clip value, final effective weight, and clipping flag.

### Completion criteria

- [x] Field widths, positions, signed encodings, capacities, and reserved values are documented.
- [x] Public pack/unpack and freeze/decode APIs implement the frozen v1 contract.
- [x] Versioned JSON and fixed-width hexadecimal memory images are reproducible.
- [x] Shared-format versus repeated-format storage and BRAM36 lower bounds are estimated.
- [x] All `147,456` valid combinations reconstruct their exact validated encoding and effective weight.
- [x] The complete Python suite passes after storage implementation.
- [x] The twelve legacy and fifteen encoded Brian2Loihi suites remain exact.
- [x] Final evidence is recorded and M08.5 and M08 are marked complete.

### Completion evidence independently reproduced on 2026-08-03

Complete Python suite:

```text
80 passed
```

Focused FPGA storage suite:

```text
12 passed
```

Generated sample image:

```text
Frozen FPGA weight storage v1
formats=14
synapses=120
axons=8
shared_total_bits=4352
inline_total_bits=4608
saved_bits=256
```

The generated directory contains the versioned manifest and all three fixed-width memory files.

Legacy conformance regression:

```text
cases=12, pass=12, fail=0, error=0, ticks=34, mismatches=0
```

Production encoded-weight regression:

```text
cases=15, pass=15, fail=0, error=0, ticks=15, mismatches=0
```

### What completion means

M08.5 proves that the frozen binary representation is lossless for every supported static-weight encoding and does not change previously validated neuron or synapse behavior. Host software, an HDL testbench, and future RTL can now use the same format words, synapse words, and axon-row pointers without redefining weight semantics.

### Scope boundary

This milestone freezes a project-specific storage profile and capacity model. It does not yet prove post-synthesis BRAM mapping, timing closure, or physical-FPGA execution; those are addressed by M11 and M12.

---

## M09 — Add recurrent spike routing

**Status:** Complete

**Started:** 2026-08-20

**Completed:** 2026-08-20

**Repository evidence:** branch `agent/m09-recurrent-spike-routing`

### Goal

Allow output spikes to become input axon events on later ticks, enabling deterministic recurrent networks.

### Deliverables

- [x] Neuron-output to axon mapping.
- [x] Explicit tick-boundary routing contract.
- [x] Deterministic simultaneous-spike handling.
- [x] Recurrent-network scenarios and routing traces.

### How each deliverable was met

1. **Neuron-output to axon mapping** — Added the immutable `SpikeRoute(source_neuron, target_axon)` model and a `spike_routes` input to `NeuromorphicCore`. The core validates that source neurons exist, rejects negative IDs and duplicate `(source_neuron, target_axon)` pairs, and stores each source neuron's target axons in declaration order. One output spike can therefore fan out to multiple input axons with an explicit, FPGA-translatable route table.
2. **Explicit tick-boundary routing contract** — `NeuromorphicCore.step()` consumes only the recurrent axons queued by the previous tick, processes the complete synapse and neuron update, then converts the current tick's output spikes into `_pending_recurrent_axons` for the next call. A spike emitted on tick `t` can first affect neurons on tick `t + 1`, so same-tick recurrent feedback is impossible. `reset()` also clears the pending recurrent queue. Focused tests verify both next-tick delivery and a deterministic self-recurrent spike chain.
3. **Deterministic simultaneous-spike handling** — Neurons are stepped in ascending neuron ID, so simultaneous spikes have a stable source order. Routed axons are flattened in that spike order and then in route declaration order for each source. External events are concatenated before recurrent events, and event multiplicity is never deduplicated. Tests prove the exact simultaneous route order `(8, 7, 9)` and prove that two source neurons routed to the same axon produce `(6, 6)` and accumulate that synaptic weight twice.
4. **Recurrent-network scenarios and routing traces** — `ComparisonScenario` and the Python backend now carry `spike_routes`, allowing recurrent networks to run through the same backend-neutral comparison path as the earlier feed-forward cases. `TickTrace` and `BackendTick` separately record `external_input_axons`, `recurrent_input_axons`, and `routed_output_axons`; backend trace schema v3 stores those per-tick collections plus the route table while retaining v1/v2 read compatibility. Tests cover comparison-scenario execution and exact trace-v3 JSON round trips.

### Routing contract

- A `SpikeRoute(source_neuron, target_axon)` maps each output spike to one or
  more axon events.
- Spikes emitted on tick `t` are queued after all neurons finish that tick and
  become inputs only on tick `t + 1`; same-tick feedback is impossible.
- External axon events are ordered before queued recurrent events. Recurrent
  events are ordered by source-neuron ID, then route declaration order.
- Event multiplicity is preserved. Two simultaneous source neurons routed to
  the same axon deliver that axon twice and accumulate its synaptic weight
  twice.
- Duplicate routes for one `(source_neuron, target_axon)` pair are rejected.
- Reset clears both neuron state and the pending recurrent-event queue.

### Trace contract

`TickTrace` now separates `external_input_axons`, `recurrent_input_axons`, and
`routed_output_axons`, while `input_axons` remains the exact combined event
sequence consumed by the synapse fabric. Backend trace schema v3 preserves the
route table and those three per-tick collections. Readers remain compatible
with trace schemas v1 and v2.

### Completion evidence

```text
89 passed
cases=12, pass=12, fail=0, error=0, ticks=34, mismatches=0
```

Nine focused tests cover next-tick delivery, external/recurrent ordering,
simultaneous-spike ordering, same-axon multiplicity, self-recurrent chains,
reset behavior, validation, comparison-scenario integration, and trace-v3
round trips. The original 80 tests remain passing unchanged in scope.

---

## M10 — Freeze computational-core specification

**Status:** Complete  
**Started:** 2026-08-20  
**Completed:** 2026-08-20  
**Repository evidence:** branch `agent/m10-core-specification`

### Goal

Convert validated software behavior into an implementation-neutral specification suitable for direct FPGA translation.

### Deliverables

- [x] Formal per-tick update schedule.
- [x] State-register definitions and widths.
- [x] Arithmetic, rounding, and overflow rules.
- [x] Threshold, reset, refractory, accumulation, and routing semantics.
- [x] Conformance tests linked to every normative requirement.

### How the deliverables were met

1. **Formal per-tick update schedule** — `docs/CORE_SPECIFICATION.md` freezes six behaviorally ordered phases: latch external and recurrent events, accumulate synapses, update every neuron from the same pre-tick state snapshot, collect spikes, generate recurrent routes, and atomically commit state. This prevents an FPGA implementation from changing observable behavior merely because it pipelines or time-multiplexes the work.
2. **State-register definitions and widths** — The FPGA-v1 profile freezes signed 24-bit current and voltage state, 16-bit refractory state and neuron/axon identifiers, a 32-bit tick counter, 13-bit decay configuration with domain `0..4096`, and signed 24-bit threshold/bias/reset configuration. Final boundary tests also prove those ID widths remain consistent with the previously frozen M08 FPGA weight-storage contract.
3. **Arithmetic, rounding, and overflow rules** — The profile names signed 24-bit saturation as the FPGA state policy, preserves integer round-away-from-zero decay with denominator `4096`, and specifies the exact points where saturation occurs. The generic Python/Brian2Loihi path remains configurable and unchanged so this project-defined hardware overflow policy does not rewrite earlier external-conformance evidence.
4. **Threshold, reset, refractory, accumulation, and routing semantics** — The specification freezes input-before-current-decay ordering, voltage integration from pre-decay working current, exact mathematical synaptic accumulation before state-width application, strict `>` threshold behavior, hard reset, refractory release timing, deterministic route order and multiplicity, next-tick-only recurrence, and reset disposal of queued recurrent events.
5. **Conformance tests linked to every requirement** — `tests/test_core_specification.py` maps every normative `CORE-*` identifier to an executable pytest function and contains a coverage gate that fails if the specification and test map diverge. `tests/test_core_specification_boundaries.py` adds hardware-profile boundary checks for runtime axon IDs, replayed state width, threshold/reset validity, and M08/M10 identifier consistency. `src/neuromorphic_twin/specification.py` provides the machine-readable `neuromorphic-twin-core-spec-v1` constants and validators that M11/M12 can consume directly.

The work was completed as three ordered sub-milestones so the implementation contract was defined before the executable completion gate was closed.

### Overall completion evidence

The final branch state was independently reproduced from a complete checkout on 2026-08-20. The following gates all passed:

```bash
pytest -q tests/test_core_specification.py tests/test_core_specification_boundaries.py
pytest -q
python examples/run_directed_conformance.py
```

The independently reproduced Python test runs completed with zero failures. The established Brian2Loihi directed regression remained:

```text
cases=12, pass=12, fail=0, error=0, ticks=34, mismatches=0
```

No exact final pytest test count is recorded here because only the successful pass status was reported for the final independent rerun.

---

### M10.1 — Freeze execution schedule and architectural state

**Status:** Complete  
**Started:** 2026-08-20  
**Completed:** 2026-08-20  
**Repository evidence:** `b6d90fdbb967a81da74285b9e6a6b8a474c19e85`

### Deliverables grouped here

- Formal per-tick update schedule.
- State-register definitions and widths.

These are grouped because register boundaries only make sense relative to the exact algorithmic-tick boundary at which state is read and committed.

### Delivered

- `docs/CORE_SPECIFICATION.md` as the normative implementation-neutral contract.
- Six behavioral tick phases: latch events, accumulate synapses, update neurons, collect spikes, generate recurrent routes, and atomically commit.
- Explicit pre-state/next-state isolation so partially updated neuron state cannot affect another neuron during the same tick.
- Stable external-before-recurrent input ordering and ascending source-neuron spike ordering.
- Next-tick-only recurrent delivery.
- Frozen architectural widths for the FPGA v1 profile:
  - current: signed 24 bits;
  - voltage: signed 24 bits;
  - refractory state: unsigned 16 bits;
  - tick: unsigned 32 bits;
  - neuron/axon/route IDs: unsigned 16 bits;
  - decay configuration: unsigned 13 bits with valid values `0..4096`;
  - threshold, bias, and reset voltage: signed 24 bits.
- Deterministic reset state including disposal of pending recurrent events.

### Completion evidence

The first normative specification revision was committed independently of the later arithmetic and test layers. Requirement IDs `CORE-TICK-*` and `CORE-STATE-*` make the schedule and state contract addressable by later conformance tests.

---

### M10.2 — Freeze arithmetic and behavioral semantics

**Status:** Complete  
**Started:** 2026-08-20  
**Completed:** 2026-08-20  
**Repository evidence:** `740fb6d471aa9c4a613f1da7a6bfba6783537e95`

### Deliverables grouped here

- Arithmetic, rounding, and overflow rules.
- Threshold, reset, refractory, accumulation, and routing semantics.

### Delivered

- Signed 24-bit FPGA state range and explicit saturating state operator.
- Project-specific saturation decision separated from claims about undocumented Intel Loihi overflow behavior.
- Integer round-away-from-zero decay with denominator `4096`.
- Exact current equation in which new synaptic input is visible before current decay and voltage uses the pre-decay working current.
- Exact voltage-decay, bias, strict-greater-than threshold, hard-reset, and refractory equations.
- Exact mathematical synaptic accumulation before the single current-state width operation.
- M08 effective encoded weights consumed without re-quantization in the tick datapath.
- Deterministic recurrent fan-out, duplicate-route rejection, cross-source multiplicity, simultaneous-spike ordering, and next-tick queueing.
- Required state and routing trace observability for future M12 comparison.

### Architectural decision

The generic Python golden model remains configurable and keeps its prior default arithmetic so the established Brian2Loihi comparison path is not silently changed. The 24-bit saturating behavior is instead named as the FPGA-v1 profile that M11 and M12 must explicitly select.

---

### M10.3 — Link every specification requirement to executable conformance

**Status:** Complete  
**Started:** 2026-08-20  
**Completed:** 2026-08-20  
**Repository evidence:** branch `agent/m10-core-specification`

### Delivered

- `src/neuromorphic_twin/specification.py` containing the machine-readable `neuromorphic-twin-core-spec-v1` profile, frozen widths, saturating arithmetic configuration, and representability validators.
- Public exports for the FPGA-v1 profile without changing generic model defaults.
- `tests/test_core_specification.py` with directed conformance cases for schedule, widths, saturation, decay, encoded weights, accumulation, threshold, reset, refractory timing, simultaneous routing, configuration validation, and trace boundaries.
- `REQUIREMENT_TESTS`, an explicit map from every normative `CORE-*` requirement ID to an executable pytest function.
- A coverage-gate test that extracts all normative requirement IDs from `CORE_SPECIFICATION.md` and requires exact equality with `REQUIREMENT_TESTS`, so specification growth without a test causes failure.
- `docs/CORE_CONFORMANCE.md` documenting the coverage strategy and completion gate.
- A strengthened reset test that queues a real recurrent event before reset and proves both queue disposal and deterministic replay.
- FPGA-v1 runtime input validation so external axon events must fit the frozen unsigned 16-bit ID space without tightening the generic golden-model core.
- FPGA-v1 replay/state validation so injected current, voltage, and refractory values must fit the frozen architectural registers.
- Boundary regressions proving the threshold remains strictly above reset voltage and M10 neuron/axon ID widths remain identical to M08's frozen storage widths.

### Completion criteria

- [x] Every normative requirement has a stable `CORE-*` identifier.
- [x] Every current requirement is linked to an executable test in `REQUIREMENT_TESTS`.
- [x] A machine-readable FPGA-v1 profile exists for M11/M12.
- [x] Focused M10 behavior was exercised during development.
- [x] `tests/test_core_specification.py` and `tests/test_core_specification_boundaries.py` pass from a complete repository checkout.
- [x] The complete Python regression suite passes from that checkout.
- [x] The original Brian2Loihi directed conformance suite remains exact.
- [x] Final independent verification was reported and M10.3 and M10 are marked complete.

### Final independent verification

On 2026-08-20 the final branch state was pulled and the requested completion commands were run independently. Both Python test commands completed successfully with zero failures. The Brian2Loihi suite retained all twelve passing cases and zero mismatches.

### What completion means

M10 now provides one frozen, test-addressable computational contract for M11. Hardware may pipeline or serialize the implementation, but current/voltage arithmetic, tick boundaries, reset/refractory behavior, synaptic accumulation, event ordering, routing, widths, and trace observability may not change without changing the specification and its linked conformance tests together.

---

## M11 — Implement first FPGA neuron/core datapath

**Status:** In progress  
**Started:** 2026-08-20  
**Repository evidence:** branch `agent/m11-hls-core`

### Goal

Translate the frozen M10 computational-core contract into real FPGA logic while preserving the same algorithmic tick behavior and keeping state observable for M12 comparison.

### Implementation strategy

Use Vitis HLS for as much of the computational datapath and deterministic control logic as practical, then add or edit RTL where direct HDL gives clearer control over board-level interfaces, memory plumbing, timing, resource use, or debug instrumentation. HLS is a translation path from deliberate C++ to RTL; the Python golden model remains the behavioral reference and is not synthesized directly.

The work is split into six ordered sub-milestones. Each stage adds a stronger hardware-specific verification boundary before the next layer is introduced.

---

### M11.1 — Create minimal HLS computational core

**Status:** In progress  
**Started:** 2026-08-20  
**Repository evidence:** branch `agent/m11-hls-core`

### Purpose

Establish the smallest HLS synthesis boundary that implements one complete frozen M10 neuron transition without yet mixing in synapse-memory traversal, recurrent routing, or system integration.

### Delivered so far

- `hls/core_v1/include/neuron_step_v1.hpp` with the frozen 24-bit state, 16-bit refractory, 13-bit decay, and 1-bit spike HLS types.
- A signed 64-bit HLS working domain for the M11.1 synaptic-input boundary and intermediate arithmetic so values are widened before the explicit M10 `SAT24` operation instead of silently wrapping in a 24-bit temporary.
- `hls/core_v1/src/neuron_step_v1.cpp` implementing:
  - explicit signed 24-bit saturation;
  - exact round-away-from-zero decay with denominator `4096`;
  - input-before-current-decay ordering;
  - voltage integration from the pre-decay working current;
  - strict `>` threshold behavior;
  - hard reset;
  - exact refractory countdown/load timing;
  - current updates during refractory ticks.
- The `4096 = 2^12` decay division is expressed as an exact add-and-shift magnitude operation, preserving the M10 integer result without requiring a general divider.
- `hls/core_v1/tb/test_neuron_step_v1.cpp`, a self-checking C++ testbench with 11 directed cases covering threshold equality, positive and negative saturation, positive and negative decay behavior, input-before-decay, voltage decay/bias, refractory hold/countdown, refractory loading, and full decay.
- `hls/core_v1/run_csim.tcl`, a Vitis HLS 2023.2-compatible C-simulation entry point.
- `hls/core_v1/README.md` documenting the HLS boundary and why physical accumulator/event capacity is deferred until the wider core is integrated.
- All 11 directed expected results were independently checked against the frozen M10 equations before vendor-tool execution.

### Completion criteria

- [x] Define an HLS-friendly top-level neuron transition with explicit fixed-width types.
- [x] Implement the frozen M10 arithmetic and neuron semantics without relying on native C/C++ overflow behavior.
- [x] Add a self-checking directed C++ testbench.
- [x] Add a reproducible Vitis HLS 2023.2 C-simulation command path.
- [x] Independently cross-check the directed expected values against the M10 equations.
- [ ] Run the testbench through Vitis HLS C simulation from the development checkout.
- [ ] Record the vendor-tool result and mark M11.1 complete.

### Scope boundary

M11.1 accepts one already-accumulated synaptic-input scalar and produces one neuron transition. It does not yet define the final physical synaptic accumulator capacity, walk the M08 CSR synapse memory, schedule multiple neurons, route recurrent events, or create the Vivado system project.

---

### M11.2 — Verify HLS behavior against the Python golden model

**Status:** Planned

### Goal

Move beyond the small directed M11.1 testbench and establish an automated differential path in which Python generates or evaluates broader state/configuration vectors and the HLS C++ implementation must match exactly.

### Planned deliverables

- Shared or generated Python/HLS test vectors.
- Boundary and randomized deterministic cases across the supported FPGA-v1 state/configuration domain.
- Exact comparison of current, voltage, refractory state, and spike output.
- Regression evidence that the HLS C++ implementation remains synchronized with M10.

---

### M11.3 — Synthesize HLS and run C/RTL co-simulation

**Status:** Planned

### Goal

Prove that the C++ description is accepted by Vitis HLS for the selected FPGA target and that generated RTL reproduces the C++ results.

### Planned deliverables

- Freeze the target FPGA part and initial clock constraint for the HLS solution.
- Run C synthesis and inspect latency, initiation interval, operator mapping, and resource estimates.
- Resolve synthesis warnings that could affect bit accuracy or interfaces.
- Run C/RTL co-simulation with the verified M11.2 vectors.
- Record synthesis and co-simulation evidence before packaging the block.

---

### M11.4 — Export Vivado IP and create the Vivado project

**Status:** Planned

### Goal

Package the verified HLS core as Vivado IP and establish the real FPGA system project that will host the digital twin.

### Planned deliverables

- Package the HLS RTL for the Vivado IP flow.
- Create the M11 Vivado project for the target board/device.
- Add the HLS core to the IP catalog/block design.
- Connect clock, reset, and initial control/data interfaces.
- Preserve a reproducible project-generation or source-management flow rather than relying only on GUI state.

---

### M11.5 — Integrate memories, tick control, routing, and observability

**Status:** Planned

### Goal

Turn the isolated neuron transition into the first complete FPGA computational core capable of processing configured state and events over deterministic algorithmic ticks.

### Planned deliverables

- Neuron state/configuration memories.
- M08-compatible weight-format, synapse, and axon-row storage path.
- Synaptic accumulation scheduling and a frozen finite hardware capacity profile.
- Multi-neuron tick controller preserving the six M10 behavioral phases.
- Next-tick recurrent event queue/routing semantics from M09/M10.
- Host-visible or simulation-visible state/spike/route observability suitable for later trace export.
- Use targeted handwritten RTL where HLS is not the clearest or most controllable implementation choice.

---

### M11.6 — Generate first integrated bitstream and perform hardware smoke checks

**Status:** Planned

### Goal

Produce the first loadable FPGA image containing the integrated M11 core and prove that its control/debug interfaces operate on the physical board.

### Planned deliverables

- Successful Vivado synthesis, implementation, timing review, and bitstream generation.
- Program the target board with the M11 design.
- Confirm reset/start/control access and basic state/spike observability on hardware.
- Record initial utilization and timing information.
- Keep full tick-by-tick Python-versus-RTL and Python-versus-physical-FPGA conformance in M12 rather than treating a smoke test as behavioral validation.

---

## M12 — Validate FPGA against Python golden model

**Status:** Planned

### Goal

Use the same scenarios and trace format to establish that RTL simulation and physical FPGA execution match the Python model.

### Planned deliverables

- RTL-simulation traces.
- Physical-FPGA trace capture.
- Automated Python-versus-RTL and Python-versus-FPGA comparison.
- Resource, timing, and throughput results.
- Final validation summary for the thesis results chapter.

---

## Maintenance rules

For each future milestone:

1. Set **Started** when active work begins.
2. Keep completion criteria as checkboxes while work is active.
3. Link relevant issues, branches, pull requests, and commits.
4. Record the command or artifact that proves completion.
5. Document architectural decisions and known limitations.
6. Set **Completed** only after evidence is reproducible.
7. Update the summary table in the same change.