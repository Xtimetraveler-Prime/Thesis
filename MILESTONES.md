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

- A `SpikeRoute(source_neuron,target_axon)` maps each output spike to one or more axon events.
- Spikes emitted on tick `t` are queued after all neurons finish that tick and become inputs only on tick `t + 1`; same-tick feedback is impossible.
- External axon events are ordered before queued recurrent events. Recurrent events are ordered by source-neuron ID, then route declaration order.
- Event multiplicity is preserved. Two simultaneous source neurons routed to the same axon deliver that axon twice and accumulate its synaptic weight twice.
- Duplicate routes for one `(source_neuron,target_axon)` pair are rejected.
- Reset clears both neuron state and the pending recurrent-event queue.

### Trace contract

`TickTrace` now separates `external_input_axons`, `recurrent_input_axons`, and `routed_output_axons`, while `input_axons` remains the exact combined event sequence consumed by the synapse fabric. Backend trace schema v3 preserves the route table and those three per-tick collections. Readers remain compatible with trace schemas v1 and v2.

### Completion evidence

```text
89 passed
cases=12, pass=12, fail=0, error=0, ticks=34, mismatches=0
```

Nine focused tests cover next-tick delivery, external/recurrent ordering, simultaneous-spike ordering, same-axon multiplicity, self-recurrent chains, reset behavior, validation, comparison-scenario integration, and trace-v3 round trips. The original 80 tests remain passing unchanged in scope.

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
**Repository evidence:** `main` through M11.5.5

### Goal

Translate the frozen M10 computational-core contract into real FPGA logic while preserving the same algorithmic tick behavior and keeping state observable for M12 comparison.

### Implementation strategy

Use Vitis HLS for as much of the computational datapath and deterministic control logic as practical, then add or edit RTL where direct HDL gives clearer control over board-level interfaces, memory plumbing, timing, resource use, or debug instrumentation. HLS is a translation path from deliberate C++ to RTL; the Python golden model remains the behavioral reference and is not synthesized directly.

M11 and later FPGA-development work standardize on AMD Vitis 2025.2 and AMD Vivado 2025.2. The work is split into six ordered sub-milestones. Each stage adds a stronger hardware-specific verification boundary before the next layer is introduced.

---

### M11.1 — Create minimal HLS computational core

**Status:** Complete  
**Started:** 2026-08-20  
**Completed:** 2026-08-24  
**Repository evidence:** branch `agent/m11-hls-core`

### Purpose

Establish the smallest HLS synthesis boundary that implements one complete frozen M10 neuron transition without yet mixing in synapse-memory traversal, recurrent routing, or system integration.

### Delivered

- `hls/core_v1/include/neuron_step_v1.hpp` with the frozen 24-bit state, 16-bit refractory, 13-bit decay, and 1-bit spike HLS types.
- A signed 64-bit HLS working domain for the M11.1 synaptic-input boundary and intermediate arithmetic so values are widened before the explicit M10 `SAT24` operation instead of silently wrapping in a 24-bit temporary.
- `hls/core_v1/src/neuron_step_v1.cpp` implementing explicit signed 24-bit saturation, exact round-away-from-zero decay, input-before-current-decay ordering, voltage integration from pre-decay working current, strict threshold behavior, hard reset, exact refractory timing, and current updates during refractory ticks.
- The `4096 = 2^12` decay division is expressed as an exact add-and-shift magnitude operation, preserving the M10 integer result without requiring a general divider.
- `hls/core_v1/tb/test_neuron_step_v1.cpp`, a self-checking C++ testbench with 11 directed cases covering threshold equality, positive and negative saturation, positive and negative decay behavior, input-before-decay, voltage decay/bias, refractory hold/countdown, refractory loading, and full decay.
- `hls/core_v1/hls_config.cfg` and `hls/core_v1/run_csim.sh` implementing the standardized Vitis 2025.2 C-simulation flow with tool-version checks and explicit target-part selection.
- The wrapper stages the HLS component under a no-space `/tmp` path because Vitis HLS 2025.2 rejects project/work paths containing the space in `Neuromorphic Digital Twin`.
- Vitis-2025.2-compatible explicit `ap_int` width conversions were added where unary negation and subtraction widen intermediate expression types; these casts preserve the frozen M10 arithmetic while removing compiler ambiguity.
- All 11 directed expected results were independently checked against the frozen M10 equations before vendor-tool execution.

### Completion criteria

- [x] Define an HLS-friendly top-level neuron transition with explicit fixed-width types.
- [x] Implement the frozen M10 arithmetic and neuron semantics without relying on native C/C++ overflow behavior.
- [x] Add a self-checking directed C++ testbench.
- [x] Add a reproducible Vitis/Vivado 2025.2 C-simulation command path.
- [x] Independently cross-check the directed expected values against the M10 equations.
- [x] Run the testbench through Vitis HLS C simulation from the development checkout.
- [x] Record the vendor-tool result and mark M11.1 complete.

### Completion evidence

The vendor C simulation was independently run on 2026-08-24 with:

```text
Vitis/Vivado: 2025.2
FPGA part:    xck26-sfvc784-2LV-c
```

Command:

```bash
bash run_csim.sh | tee m11_1_csim_2025_2.log
```

The self-checking testbench completed successfully with:

```text
M11.1 HLS neuron-step tests passed: 11 cases
```

This proves the HLS C++ implementation compiles and produces the expected directed neuron transitions under the selected Vitis 2025.2 toolchain. C simulation does not synthesize RTL or package a Vivado IP; those hardware-generation steps remain M11.3 and M11.4.

### Scope boundary

M11.1 accepts one already-accumulated synaptic-input scalar and produces one neuron transition. It does not yet define the final physical synaptic accumulator capacity, walk the M08 CSR synapse memory, schedule multiple neurons, route recurrent events, synthesize RTL, or create the Vivado system project.

---

### M11.2 — Verify HLS behavior against the Python golden model

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-24  
**Repository evidence:** branch `agent/m11-hls-core`

### Goal

Move beyond the small directed M11.1 testbench and establish an automated differential path in which Python generates broader state/configuration vectors and the HLS C++ implementation must match exactly.

### Deliverables

- [x] Shared/generated Python/HLS test vectors.
- [x] Boundary and randomized deterministic cases across the supported FPGA-v1 state/configuration domain.
- [x] Exact comparison of current, voltage, refractory state, and spike output.
- [x] Regression evidence that the HLS C++ implementation remains synchronized with M10.

### How each deliverable was met

1. **Shared/generated Python/HLS test vectors** — Added `src/neuromorphic_twin/hls_conformance.py` as the vector-generation library and `examples/generate_m11_hls_vectors.py` as its CLI. Every expected output is produced by the existing golden transition `step_neuron(..., arithmetic=FPGA_CORE_ARITHMETIC_V1)` after validating the input state/configuration against the M10 FPGA-v1 profile. The generator writes an ephemeral `generated_m11_2_vectors.inc` into the no-space HLS staging directory, and the C++ testbench includes that initializer. Expected outputs are therefore generated from the Python golden model rather than manually duplicated in C++.
2. **Boundary and randomized deterministic cases** — The standard corpus contains 24 directed FPGA-v1 boundary vectors plus 2,048 seeded pseudo-random vectors, for 2,072 differential cases total. Directed coverage includes strict threshold equality/just-over behavior; signed 24-bit positive and negative saturation; decay values `0`, `1`, `2048`, `4095`, and `4096`; positive and negative round-away-from-zero behavior; refractory state/configuration values including `0`, `1`, and `65535`; positive/negative bias saturation; reset boundaries; and large positive/negative accumulated synaptic inputs. The randomized set spans legal state/configuration domains while deliberately keeping many cases non-refractory so spike/threshold behavior remains exercised. The corpus uses explicit SplitMix64 generation with seed `0x4D313132`, so vector reproduction is tied to a specified integer algorithm rather than Python's library RNG implementation.
3. **Exact comparison of all neuron outputs** — `tb/test_neuron_step_v1.cpp` runs every Python-generated vector through `neuron_step_v1` and compares all four observable outputs exactly: `current_after`, `voltage_after`, `refractory_after`, and `spiked`. A mismatch prints the vector name and expected/actual tuple and returns nonzero. The original 11 M11.1 directed cases remain in the same testbench and run first as a regression gate.
4. **Regression evidence synchronized with M10** — `tests/test_m11_hls_conformance.py` verifies deterministic corpus generation, required boundary presence, exact replay of generated expectations through the frozen Python golden model, and byte-for-byte reproducible C++ initializer output. `run_csim.sh` regenerates the vector file on every vendor run before invoking Vitis 2025.2, so the C++/HLS comparison cannot silently retain stale expected values after Python-golden changes.

### Completion evidence

The M11.2 branch state was independently pulled and tested on 2026-08-24. Both requested gates passed:

```bash
python3 -m pytest -q tests/test_m11_hls_conformance.py
python3 -m pytest -q
```

The independent report confirmed both Python commands completed successfully. No exact pytest count is recorded because only pass status was reported.

The same checkout was then run through Vitis/Vivado 2025.2 for target part:

```text
xck26-sfvc784-2LV-c
```

with:

```bash
bash run_csim.sh | tee m11_2_csim_2025_2.log
```

The vendor testbench retained the M11.1 gate and passed the new differential corpus:

```text
M11.1 HLS neuron-step tests passed: 11 cases
M11.2 Python/HLS differential tests passed: 2072 cases (directed=24, random=2048, seed=0x4d313132)
```

### What completion means

M11.2 establishes an automated behavioral bridge from the frozen Python FPGA-v1 model to the HLS C++ implementation. The result is substantially stronger than the original hand-authored cases: thousands of deterministic states/configurations are checked exactly, while expected values continue to come from the Python golden model. This is still C simulation, so it proves the C++ behavior but not yet the behavior, latency, timing, or resource use of generated RTL.

---

### M11.3 — Synthesize HLS and run C/RTL co-simulation

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-24  
**Repository evidence:** branch `agent/m11-hls-core`

### Goal

Prove that the behaviorally verified C++ description is accepted by Vitis HLS for the selected FPGA target, inspect the resulting hardware implementation estimates, and prove that the generated RTL reproduces the verified C++/Python behavior.

### Frozen synthesis baseline

- FPGA part: `xck26-sfvc784-2LV-c`.
- Toolchain: AMD Vitis 2025.2 and AMD Vivado 2025.2.
- HLS target clock: `10ns` (100 MHz).
- HLS clock uncertainty: `12%` = `1.20ns`.
- Flow target: `vivado`.
- Synthesis output format: `rtl`.

The 100 MHz target is a baseline for measurement and later system integration, not a claim about final maximum frequency.

### Delivered

- `hls_config.cfg` freezes the 10ns/12% HLS timing baseline with `flow_target=vivado` and `package.output.format=rtl`.
- `run_m11_3.sh` stages the component under a no-space `/tmp` path, regenerates the 2,072-vector M11.2 corpus, runs `v++ -c --mode hls`, preserves the complete `csynth` report and vendor log, then runs `vitis-run --mode hls --cosim` using the same verified testbench.
- Vitis generates both Verilog and VHDL RTL for `neuron_step_v1`.
- The HLS top remains `ap_ctrl_hs`; scalar inputs are `ap_none`; all four output pointers use `ap_vld` so result validity is explicit for automatic co-simulation and later integration.
- The HLS synthesis boundary is a global `neuron_step_v1(...)` wrapper while fixed-width types and arithmetic helpers remain in `neuromorphic_hls`. This Vitis-2025.2 tooling boundary avoids the co-simulation hardware-stub linker failure seen when the top itself was namespaced without changing any M10 arithmetic or neuron semantics.
- The initial deprecated `syn.output.format` spelling was replaced with the 2025.2 `package.output.format` key.

### Synthesis result

The independently reproduced `csynth` report records:

```text
Target clock:        10.000 ns
Estimated clock:      8.785 ns
Clock uncertainty:    1.200 ns
Estimated Fmax:     ~113.83 MHz

Latency:              1 cycle
Absolute latency:    10.000 ns
Transaction interval: 2 cycles
Pipeline type:        no

BRAM_18K:             0
DSP:                  2
FF:                  51
LUT:               1418
URAM:                 0
```

The two DSP instances are the two signed 24-bit-by-13-bit decay multipliers (`mul_24s_13ns_37_1_1`). The remaining datapath is primarily LUT-based add/subtract, compare, saturation/select, and control logic. The report also contains one small sparse multiplexer instance and no inferred memories or FIFOs.

The estimated 8.785ns datapath is only slightly below the effective 8.8ns target after the 1.2ns uncertainty allowance, so the 100 MHz setting should be treated as a useful first baseline rather than large timing headroom. Physical post-place-and-route timing remains later M11 evidence.

### Warning resolution

- The first synthesis warned that `ap_none` output pointers might not be automatically verifiable. The outputs were changed to `ap_vld`; the final interface table confirms dedicated validity signals for current, voltage, refractory state, and spike.
- The deprecated output-format config name was replaced with `package.output.format`.
- The first co-simulation attempts failed while generating the C-side hardware stub with `undefined symbol: neuron_step_v1_hw_stub`; XSIM had not started and there was no RTL behavioral mismatch. Moving only the HLS top wrapper to the global namespace resolved that Vitis 2025.2 instrumentation issue.
- Repeated parenthesis warnings came from AMD-supplied Vitis headers (`gmp.h`, `hls_half_fpo.h`, `ap_int_base.h`, and `ap_fixed_base.h`), not project source, and were nonfatal.

### Completion criteria

- [x] Freeze the target FPGA part and initial HLS clock/uncertainty baseline.
- [x] Add a reproducible Vitis 2025.2 synthesis and co-simulation command path.
- [x] Run HLS C synthesis successfully on the development checkout.
- [x] Inspect and record top-level latency, transaction interval, estimated clock/timing, operator mapping, and BRAM/DSP/FF/LUT estimates.
- [x] Resolve or explicitly document synthesis/co-simulation warnings that affect interfaces or tool compatibility.
- [x] Run C/RTL co-simulation using the verified M11.2 vector corpus.
- [x] Record the vendor-tool evidence and mark M11.3 complete before packaging the block.

### Completion evidence

The final M11.3 run on 2026-08-24 completed XSIM and C post-checking successfully. The post-check retained both prior gates:

```text
M11.1 HLS neuron-step tests passed: 11 cases
M11.2 Python/HLS differential tests passed: 2072 cases (directed=24, random=2048, seed=0x4d313132)
```

Vitis then reported:

```text
INFO: [COSIM 212-1000] *** C/RTL co-simulation finished: PASS ***
M11.3 synthesis and C/RTL co-simulation completed successfully.
```

This proves that the generated RTL, not only the C++ model, reproduces every observable neuron result in the M11.2 differential corpus under the selected Vitis/Vivado 2025.2 configuration.

---

### M11.4 — Export Vivado IP and create the Vivado project

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-24  
**Repository evidence:** branch `agent/m11-hls-core`

### Goal

Package the verified HLS core as Vivado IP and establish the real FPGA system project that will host the digital twin.

### Frozen packaging boundary

- FPGA part: `xck26-sfvc784-2LV-c`.
- Toolchain: Vitis/Vivado 2025.2.
- Packaged IP VLNV: `neuromorphic-twin.org:hls:neuron_step_v1:1.0`.
- HLS baseline clock: 10ns / 100 MHz.
- Verified HLS interface: `ap_ctrl_hs`, scalar `ap_none` inputs, and `ap_vld` outputs.

### Delivered

- `hls_package.cfg` selects `package.output.format=ip_catalog`, disables package generation during the synthesis step with `package.output.syn=false`, and freezes the project-specific IP vendor/library/name/version metadata.
- `run_m11_4.sh` provides one reproducible Vitis/Vivado 2025.2 command path that checks the exact K26 target part, stages the HLS component under `/tmp`, regenerates the deterministic M11.2 vector include, runs fresh HLS synthesis, executes `vitis-run --mode hls --package`, preserves the packaged ZIP/unpacked IP under ignored `build/m11_4/`, and invokes Vivado in batch mode.
- `vivado/create_m11_4_project.tcl` creates project `neuromorphic_twin_m11_4`, registers `build/m11_4/ip_repo` with `IP_REPO_PATHS` plus `update_ip_catalog`, verifies the exact expected VLNV, creates block design `neuromorphic_twin_core`, and instantiates the HLS IP as `neuron_step_v1_0`.
- The final Tcl flow externalizes the complete HLS `ap_ctrl_hs` interface so `ap_start`, `ap_done`, `ap_idle`, and `ap_ready` remain one transaction-control interface, then externalizes the remaining unconnected clock/reset/data/result pins.
- The block design is validated and saved, interface/scalar ports are reported while the BD is still current/open, output products are generated, the HDL wrapper is created and added, and compile order is updated.
- The checked-in Tcl is the normative Vivado reconstruction source. Generated `write_bd_tcl`/`write_project_tcl` snapshots were deliberately removed from the final flow because they embedded build-local custom-IP paths and produced avoidable repository warnings.
- `vivado/README.md` documents the packaged-IP boundary, the batch reconstruction path, completion evidence, and the Vivado-specific fixes made while closing the milestone.

### Vivado integration issues resolved

1. The first project-generation run reached successful BD/wrapper generation but failed on an invalid zero-argument `save_project` call. The call was removed because `create_project` already creates and maintains the requested project in place.
2. A manual `ap_start` connection produced an IP-Integrator interface-override warning because `ap_start` belongs to the HLS `ap_ctrl` interface. The final flow externalizes the complete `ap_ctrl_hs` interface instead.
3. Port-reporting originally called `get_bd_ports` after export helpers had changed the current IP-Integrator design context. The final flow reports ports immediately after BD validation while the design is open.
4. Generated project/BD Tcl snapshots produced custom-IP repository warnings and local path coupling. They were removed in favor of the source-controlled generator that already reproduces the project from the packaged IP repository.

These are project/integration changes only; the verified M10/M11.3 arithmetic and generated HLS datapath are unchanged.

### Completion criteria

- [x] Freeze packaged-IP identity, target part, toolchain, and HLS interface boundary.
- [x] Add a reproducible Vitis 2025.2 `ip_catalog` packaging flow.
- [x] Add a reproducible Vivado 2025.2 project/block-design creation flow.
- [x] Run HLS packaging successfully and preserve the packaged IP repository/ZIP artifacts.
- [x] Confirm Vivado discovers `neuromorphic-twin.org:hls:neuron_step_v1:1.0` in the custom IP catalog.
- [x] Create and validate the K26-targeted Vivado project and `neuromorphic_twin_core` block design from the source-controlled Tcl flow.
- [x] Generate the block-design output products and HDL wrapper without fatal errors.
- [x] Independently verify that the `.xpr` project and `.bd` block-design artifacts exist.
- [x] Record the vendor-tool evidence and mark M11.4 complete before starting memory/tick-controller integration.

### Completion evidence

The final vendor flow on 2026-08-24 successfully packaged the HLS core and loaded the resulting custom IP repository in Vivado. Vivado found the expected VLNV, instantiated `neuron_step_v1_0`, validated `neuromorphic_twin_core`, generated Verilog/VHDL output products, generated the HDL wrapper and hardware handoff files, and created the target project.

After the final Tcl fixes, the following independent verification commands were run and passed:

```bash
test -f build/m11_4/vivado_project/neuromorphic_twin_m11_4.xpr \
  && echo "XPR: PASS"

find build/m11_4/vivado_project \
  -type f -name 'neuromorphic_twin_core.bd' -print
```

This establishes the M11.4 boundary: the M11.3-verified RTL is now a custom Vivado IP that is discoverable in the IP catalog, instantiated in a validated K26-targeted IP-Integrator design, wrapped as HDL, and reproducible from the repository scripts.

### Reproduction command

```bash
export HLS_PART='xck26-sfvc784-2LV-c'
cd "Neuromorphic Digital Twin/hls/core_v1"
bash run_m11_4.sh | tee m11_4_2025_2.log
```

### Scope boundary

M11.4 proves the verified HLS datapath can become a reusable Vivado IP and live inside a deterministic Vivado/IP-Integrator project. It intentionally does not add board pin constraints, neuron/synapse memories, a multi-neuron tick controller, recurrent routing, host registers, physical implementation, or a bitstream; those belong to M11.5 and M11.6.

---

### M11.5 — Integrate memories, tick control, routing, and observability

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-25  
**Repository evidence:** `main` through M11.5.5

### Goal

Turn the isolated neuron transition into the first complete FPGA computational core capable of processing configured state and events over deterministic algorithmic ticks.

### Integration strategy

M11.5 keeps the M11.4 packaged `neuron_step_v1` HLS block as the verified neuron-transition boundary and surrounds it with source-controlled RTL for finite memories, deterministic phase scheduling, packed M08 synapse traversal, recurrent routing, queue banking, faults, and debug visibility. The first implementation is intentionally serialized: correctness and exact observability are prioritized over throughput.

The work is split into five smaller closure gates:

1. M11.5.1 — finite capacity profile and packed neuron-memory contract.
2. M11.5.2 — multi-neuron state/config memories plus the real-HLS transaction sequencer.
3. M11.5.3 — packed M08 synapse traversal and exact signed-64 Phase-B accumulation.
4. M11.5.4 — recurrent route CSR plus double-buffered next-tick event queues.
5. M11.5.5 — integrated observability, resource cleanup, and final Vivado system validation before M11.6.

---

#### M11.5.1 — Freeze finite core capacity and neuron-memory words

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-24

##### How it was met

- Froze the first K26 physical profile at 256 neurons, 1,024 axons, 4,096 synapses, 16 weight formats, 4,096 recurrent routes, 4,096 external events/tick, and 4,096 recurrent events/tick while retaining the wider M10 architectural ID widths.
- Froze a 64-bit neuron-state word containing signed-24 current, signed-24 voltage, and unsigned-16 refractory state.
- Froze a 128-bit neuron-configuration word containing both 13-bit decays, signed-24 threshold/bias/reset, unsigned-16 refractory ticks, and required-zero reserved bits.
- Proved that the existing signed-64 HLS synaptic-input boundary is sufficient for every legal physical workload: the worst-case absolute sum under the frozen event/synapse capacities is below `2^46`.
- Added machine-readable pack/unpack APIs and a capacity/storage estimator. The capacity-only logical total is 500,288 bits, or a 14-BRAM36 lower bound before legal width/depth/banking effects.

##### Completion evidence

The capacity-report example was independently run and produced the expected frozen profile, including:

```text
schema=neuromorphic-twin-fpga-core-capacity-v1
max_neurons=256
max_axons=1024
max_synapses=4096
max_weight_formats=16
max_routes=4096
max_external_events_per_tick=4096
max_recurrent_events_per_tick=4096
storage_total_bits=500288
bram36_capacity_lower_bound=14
```

The later independently reported full Python regressions include the M11.5.1 pack/unpack/capacity tests and completed with zero failures.

---

#### M11.5.2 — Integrate neuron memories and real HLS transactions

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-24

##### How it was met

- Added a serialized RTL controller owning 64-bit state, 128-bit configuration, signed-64 accumulator, and spike memories for up to 256 neurons.
- Added explicit architectural reset that initializes current to zero, voltage to configured reset voltage, refractory state to zero, accumulators/spikes to zero, and tick to zero without requiring asynchronous memory reset.
- Preserved M10 atomic observability by blocking architectural debug reads while the controller is busy, so in-place per-neuron Phase-C writeback cannot expose a partial tick.
- Sequenced neurons in ascending ID through the packaged `neuron_step_v1` block and handled the actual `ap_ctrl_hs` ready/done behavior, including coincident `ap_ready`/`ap_done`.
- Worked around Vivado 2025.2 integration constraints with a thin Verilog Module-Reference top over the SystemVerilog controller, no-space `/tmp` source staging, and explicit scalar wiring for all four HLS handshake members.
- Compared complete packed state words and spike flags against Python-generated expectations rather than only checking transaction completion.

##### Completion evidence

The standalone controller XSIM gate passed, and the final real packaged-IP Vivado/XSIM gate passed a 64-neuron corpus containing 24 directed M11.2 boundary vectors plus 40 deterministic random vectors:

```text
M11.5.2 real packaged-IP integration passed: neurons=64, directed=24, random=40, seed=0x4d313132
M11.5.2 controller + real packaged HLS IP simulation completed successfully.
```

This established the real HLS memory/transaction/writeback boundary before adding synapse traversal.

---

#### M11.5.3 — Implement M08 synapse traversal and exact accumulation

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-24

##### Goal

Replace M11.5.2 testbench-preloaded accumulator values with real Phase-B hardware that consumes the frozen M08 packed weight image and produces the exact signed-64 per-neuron accumulator image before Phase C begins.

##### How it was met

1. **Packed-memory software oracle** — Added `fpga_synapse_reference.py`, which consumes `FrozenWeightStorage` directly rather than high-level `Synapse` objects. It preserves external-before-recurrent event order, event and synapse multiplicity, CSR row order, legal unconfigured-axon no-op behavior, and reconstructs every effective weight from the packed requested mantissa plus referenced shared M08 format. It returns both the complete accumulator tuple and a contribution-level trace.
2. **RTL M08 decoder and CSR walker** — Added `m08_weight_decoder_v1.sv` plus `phase_b_synapse_accumulator_v1.sv`. The decoder implements M08 sign-mode validation, precision truncation toward zero, signed exponent handling, fixed six-bit alignment, and effective-weight clipping. The walker clears configured accumulators, consumes external events first and recurrent events second, traverses each CSR row, and performs exact signed-64 read-modify-write accumulation with deterministic fault paths.
3. **Python/RTL differential closure** — Added a 12-case deterministic packed-image corpus using seed `0x4D313533`. Each XSIM case reloads full format/synapse/row/event memories and compares every configured neuron's complete signed-64 accumulator word with the Python oracle. Coverage includes positive/negative exponents, all three sign modes, precision settings, empty rows, repeated events, recurrent events, and physically valid unconfigured axons.
4. **Real-HLS end-to-end integration** — Added `integrated_core_controller_v1.sv`, which latches the complete command/count boundary, runs Phase B to completion, transfers the produced accumulator image internally, and only then launches the already-verified M11.5.2 Phase-C controller. The integration boundary intentionally has no host/testbench accumulator preload port, so the HLS `synaptic_input` values in the final test can only originate from packed M08 memories and event buffers. Python composes the Phase-B oracle with `step_packed_neuron_array_v1()` to produce the final expected packed state/spike image.

##### Completion evidence

The focused M11.5.3 Python tests and the complete Python suite were independently reported passing with zero failures. The directed standalone RTL gate also passed.

The stronger Python/RTL differential gate then passed:

```text
M11.5.3 Python/RTL accumulator differential passed: cases=12, seed=0x4d313533
M11.5.3 Python-to-RTL differential simulation completed successfully.
```

Finally, the K26-targeted Vivado design using the actual M11.4 packaged HLS IP validated and the integrated tick matched Python exactly:

```text
M11.5.3 packed-M08 real-HLS block design validated successfully.
M11.5.3 packed-M08 + real-HLS integrated tick passed: neurons=16, axons=8, synapses=16, tag=0x4d353349
M11.5.3 packed-M08 + real packaged HLS IP simulation completed successfully.
```

This proves the simulated path `packed M08 image + external/recurrent events -> exact signed-64 Phase B -> real packaged HLS Phase C -> packed next state/spikes` without precomputed accumulator injection.

##### Remaining implementation note

The M11.5.3 composition deliberately preserves the separately verified Phase-B and Phase-C blocks and copies accumulator words between them. This temporarily duplicates accumulator storage. M11.5.5 must collapse that storage into a shared physical organization or explicitly account for the extra memories before the final synthesis/resource baseline is accepted.

---

#### M11.5.4 — Add recurrent route CSR and double-buffered event queues

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-24  
**Repository evidence:** branch `agent/m11-5-4-recurrent-routing`

##### Goal

Implement the M09/M10 next-tick recurrent-routing contract in hardware while preserving ascending source-neuron order, declaration order inside each source, event multiplicity, and strict separation between the queue consumed on tick `t` and the queue generated for tick `t+1`.

##### How it was met

1. **Frozen Python route/queue oracle** — Added `fpga_recurrent_routing.py` with a strict source-neuron CSR image and an immutable two-bank recurrent queue model. Route freezing canonicalizes ascending source-neuron order while preserving declaration order inside each source, rejects exact duplicate source/target pairs, preserves cross-source same-target multiplicity, validates finite route/event capacities, and models reset plus next-tick-only bank commit.
2. **Standalone RTL route engine** — Added `recurrent_route_queue_v1.sv` with a 257-entry 32-bit route-row table, 4096-entry 16-bit route-target table, 256 spike flags, and two 4096-entry 16-bit recurrent banks. The FSM scans spike sources in ascending neuron order, enforces canonical CSR continuity, writes only the inactive bank, clears that bank logically by count rather than mass-erasing BRAM words, and toggles the selector only in the commit state. Directed XSIM proved ordering `(6, 8, 7, 9, 6)`, multiplicity, next-tick consumption, stale-bank suppression, reset, and route-target faulting.
3. **Stateful Python/RTL differential closure** — Added a deterministic 16-case corpus using SplitMix64 seed `0x4D313534`, with four consecutive routing ticks per case for 64 stateful transitions. The XSIM test compares the complete valid current-bank prefix before each tick and, after commit, compares routed contents, selector, current count, and both physical bank counts. This tests queue history across swaps rather than isolated one-shot route examples.
4. **Packed-M08 + real-HLS multi-tick integration** — Added `recurrent_integrated_core_controller_v1.sv` to compose the verified M11.5.3 core and route engine. Each tick latches and copies only the old current recurrent-bank prefix into Phase B, runs packed M08 accumulation and the real packaged `neuron_step_v1`, scans committed spike flags into the route CSR engine, waits for Phase-F bank swap, and only then commits the externally visible algorithmic tick. The final integration boundary has no host recurrent-event preload, so recurrence consumed by Phase B must originate from the physical double-buffered router.

##### Completion evidence

The focused M11.5.4 Python/source gates and complete Python suite were independently reported passing with zero failures. The directed standalone XSIM gate passed:

```text
M11.5.4 recurrent-route RTL tests passed: order + multiplicity + next-tick banks + reset + target fault
M11.5.4 standalone recurrent-route RTL simulation completed successfully.
```

The stronger stateful differential gate then passed:

```text
M11.5.4 Python/RTL routing differential passed: cases=16, ticks=64, seed=0x4d313534
M11.5.4 Python-to-RTL routing differential simulation completed successfully.
```

Finally, the K26-targeted Vivado design using the actual M11.4 packaged HLS IP validated and passed the four-tick recurrent chain:

```text
M11.5.4 recurrent packed-M08 real-HLS block design validated successfully.
M11.5.4 packed-M08 + real-HLS recurrent multi-tick passed: ticks=4, neurons=3, routes=2, tag=0x4d353449
M11.5.4 recurrent packed-M08 + real packaged HLS IP simulation completed successfully.
```

The directed chain required spike vectors `(1,0,0) -> (0,1,0) -> (0,0,1) -> (0,0,0)`, consumed recurrent sequences `() -> (1,) -> (2,) -> ()`, and routed sequences `(1,) -> (2,) -> () -> ()`. A same-tick recurrence error would therefore have moved neuron 1 or neuron 2 one tick early and failed exact state/spike comparison. The top-level tick was also held at its pre-tick value while Phase E/F was active and advanced only after the route-bank commit, preserving the M10 atomic tick boundary.

##### What completion means

M11.5.4 establishes the complete simulated recurrent path `old recurrent bank + external events -> packed M08 Phase B -> real packaged HLS Phase C -> committed spikes -> route CSR -> inactive bank -> Phase-F swap`. Ordering, multiplicity, finite capacity, reset/stale-event behavior, strict next-tick recurrence, and atomic state/queue/tick visibility are now all backed by independently reproduced RTL/XSIM evidence.

---

#### M11.5.5 — Integrated observability and Vivado system validation

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-25  
**Repository evidence:** branch `agent/m11-5-5-system-validation`, merged to `main`

##### Goal

Complete trace/debug exposure, resolve physical resource-mapping problems, and validate the full scripted Vivado system before physical implementation in M11.6.

##### How it was met

1. **Lossless post-tick trace contract** — Added `FpgaTickTraceSnapshot` and passive hardware readback for every normative M10/M12 field: committed tick, external and recurrent inputs, combined input order, exact signed-64 synaptic sums, pre- and post-neuron state, spikes, and routed output axons. Trace reads are valid only after the outer Phase-F commit and before the next tick/reset/host mutation, so partially committed state is never exposed.
2. **Trace hardware without datapath feedback** — Added a passive 256 x 64 pre-Phase-C state snapshot, Phase-B accumulator/event readback, and propagation of trace ports through the integrated recurrent Module Reference. The trace memories and debug paths never feed HLS inputs or architectural writeback.
3. **Whole-core synthesis exposed a physical blocker** — The first complete K26 synthesis reported `172225 / 117120` CLB LUTs (`147.05%`) despite modest BRAM/DSP use. This proved that synthesis completion alone was not a sufficient milestone gate. Inspection showed several large arrays were using access patterns incompatible with block-RAM inference and were expanding into LUT logic/read muxes.
4. **BRAM-friendly memory remediation** — Phase-B external/recurrent event buffers, the signed-64 Phase-B accumulator, neuron state/accumulator memories, and both recurrent banks were rewritten with explicit synchronous single-clock RAM ports. Implementation-only capture/read states were added where required. These extra cycles do not alter M10 arithmetic, event ordering, next-tick recurrence, or the atomic algorithmic tick boundary.
5. **Behavior preserved after the memory refactor** — The focused/full Python regressions and the affected M11.5.2, M11.5.3, M11.5.4, and final trace-aware real-packaged-HLS hardware gates were independently rerun and reported passing after the synchronous-RAM changes.
6. **Physical resource gate hardened and passed** — `run_m11_5_5_synth.sh` now parses `utilization.rpt` and fails if CLB LUTs, CLB registers, block-RAM tiles, DSPs, or URAM exceed the selected K26 capacity. The final remediated synthesis passed this gate.

##### Final behavioral evidence

The final trace-aware real-HLS regression passed all four scripted markers:

```text
M11.5.5 trace real-HLS block design validated successfully.
M11.5.5 trace snapshot + real-HLS recurrent regression passed: ticks=4, neurons=3, tag=0x4d353554
M11.5.5 trace real-HLS Vivado simulation flow completed.
M11.5.5 trace snapshot + real packaged HLS IP simulation completed successfully.
```

This verifies the complete simulated path after the resource refactor, including post-Phase-F trace reconstruction rather than only final neuron state.

##### Final synthesized K26 resource profile

The accepted final synthesis reported:

```text
M11.5.5 resource capacity check passed: CLB_LUT=1757/117120, CLB_REG=944/234240, BRAM_TILE=27/144, DSP=2/1248, URAM=0/64
M11.5.5 complete-core synthesis and reporting completed successfully.
```

Approximate utilization:

```text
CLB LUTs        1.50%
CLB Registers   0.40%
Block RAM Tile 18.75%
DSPs            0.16%
URAM            0.00%
```

The BRAM increase from the first 16-tile profile to 27 tiles is intentional: memories that previously consumed LUT fabric now map into dedicated block RAM. The decisive improvement is the CLB-LUT reduction from 172,225 (`147.05%`, impossible to implement) to 1,757 (`1.50%`). The verification-first duplicated accumulator organization can therefore remain because the real synthesized design now fits comfortably inside the K26 resource budget.

##### Timing handoff

The earlier complete-core synthesis timing report showed a positive 100 MHz setup estimate (`WNS=+1.337 ns`) but a small pre-route hold estimate (`WHS=-0.149 ns`). No artificial delay or timing exception was added. The final post-remediation synthesis completed successfully, but routed timing closure is intentionally not claimed by M11.5.5. M11.6 must perform placement/routing and require nonnegative routed setup and hold slack before accepting the bitstream timing result.

##### What completion means

M11.5 is now a complete, finite, behaviorally verified, trace-observable, synthesizable computational core for the selected K26. It integrates packed M08 weights, exact signed-64 Phase-B accumulation, the real packaged HLS neuron transition, deterministic recurrent routing with next-tick-only delivery, atomic tick commit, and hardware-visible trace reconstruction. Vivado synthesis confirms the final memory organization fits the device; physical implementation, routed timing closure, bitstream generation, programming, and board smoke checks remain M11.6.

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