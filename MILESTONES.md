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
| M08 | Add Loihi-native weight representation | In progress | 2026-07-29 | — |
| M09 | Add recurrent spike routing | Planned | — | — |
| M10 | Freeze computational-core specification | Planned | — | — |
| M11 | Implement first FPGA neuron/core datapath | Planned | — | — |
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
- The project was organized around a backend-neutral trace comparison.
- FPGA implementation was deferred until neuron and core semantics are validated.

### Key decisions

- Build the Python model from scratch rather than modifying Brian2Loihi.
- Keep each state transition explicit and integer-based.
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
- Exact Loihi state widths and overflow behavior remain unresolved.

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

### Discovery

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

This milestone establishes the suite. It does not claim that all external Brian2Loihi cases pass; that is M07.

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

The model therefore loads `max(refractory_ticks - 1, 0)` future blocked ticks. Focused neuron and core regression tests preserve one-tick and three-tick release behavior, current updates during blocked ticks, reset-voltage holding, and release without forced spiking.

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

All twelve supported deterministic scenarios agree exactly on compared current, voltage, and spike traces. Generated artifacts were written beneath `comparison_output/directed/` and remain reproducible rather than version-controlled.

---

## M08 — Add Loihi-native weight representation

**Status:** In progress  
**Started:** 2026-07-29

### Goal

Represent static synaptic weights using explicit Loihi-style mantissa, exponent, precision, and sign-mode concepts while preserving a deterministic, integer-only path to FPGA implementation.

### Scope decisions

- Implement the published static-weight initialization behavior independently rather than copying Brian2Loihi source code.
- Keep weight-format configuration separate from each synapse's mantissa so exponent, precision, and sign mode can later be shared in FPGA memory.
- Preserve requested, quantized, unclipped, and final effective values for traceability.
- Defer plastic weights and stochastic rounding to a later milestone.
- Keep the effective integer as the sole core-datapath interface while attaching optional immutable encoding metadata to production synapses.

### Sub-milestones

#### M08.1 — Implement pure static weight encoder

**Status:** Complete  
**Started:** 2026-07-29  
**Completed:** 2026-07-29  
**Repository evidence:** PR #3, branch `agent/m08-weight-encoder`

Deliver an isolated integer-only encoder with:

- `WeightSignMode` for mixed, excitatory, and inhibitory formats.
- `WeightFormat` containing exponent, number of weight bits, and sign mode.
- Sign-mode-specific mantissa validation.
- Mantissa quantization toward zero at the configured precision.
- Exponent scaling and final alignment to multiples of 64.
- Signed 21-bit-aligned clipping.
- A traceable result containing requested mantissa, quantized mantissa, pre-clip effective weight, final effective weight, and clipping status.

Completion criteria:

- [x] Pure encoder is implemented without Brian2Loihi as a runtime dependency.
- [x] Public types are exported from the package.
- [x] Integer-only behavior is documented for later RTL translation.
- [x] Focused unit tests pass.

Completion evidence:

```text
50 passed
```

The result was independently reproduced from the development branch on 2026-07-29.

#### M08.2 — Exhaustively validate encoder arithmetic

**Status:** Complete  
**Started:** 2026-07-29  
**Completed:** 2026-07-29  
**Repository evidence:** PR #3, branch `agent/m08-weight-encoder`

Test all important boundaries and representative combinations of:

- Exponents from `-8` through `7`.
- Weight-bit settings from `0` through `8`.
- Excitatory, inhibitory, and mixed sign modes.
- Positive and negative quantization toward zero.
- Final alignment behavior for negative fractional scaling.
- Minimum and maximum mantissas.
- The extreme negative clipping case.
- Invalid configuration and mantissa inputs.

Delivered:

- Directed tests for all documented configuration boundaries.
- An equation-oriented reference calculation that does not call encoder helpers.
- A full sweep of all `147,456` valid static-weight input combinations.
- Exact comparisons of requested mantissa, quantized mantissa, pre-clip value, final value, clipping flag, alignment, and output bounds.

Completion criteria:

- [x] Every configuration boundary has a directed test.
- [x] Representative cross-product tests preserve quantization, alignment, and clipping invariants.
- [x] A full valid-input sweep is available and practical.
- [x] Independently rerun the branch test suite and record the result.

Completion evidence:

```text
55 passed
```

The complete branch suite, including the exhaustive `147,456`-case sweep, was independently reproduced on 2026-07-29.

#### M08.3 — Validate encoded weights against Brian2Loihi

**Status:** Complete  
**Started:** 2026-08-03  
**Completed:** 2026-08-03  
**Repository evidence:** PR #4, branch `agent/m08-weight-conformance`

Add directed comparisons for negative and positive exponents, reduced precision, mixed-sign quantization, sign-mode limits, minimum and maximum values, zero configured weight bits, and clipping behavior.

Design boundary:

- Keep encoded-weight configuration outside the production `Synapse` and trace schemas during arithmetic validation.
- Give the Python candidate the encoder's derived effective integer weight.
- Give Brian2Loihi the original requested mantissa, exponent, number of weight bits, and sign mode.
- Compare both Brian2Loihi's directly observable `w_act` value and the resulting current, voltage, and spike traces.

Tests added:

- Fifteen directed encoded-weight cases spanning exponent scaling, negative-exponent alignment, reduced precision, mixed-sign quantization, sign-mode extrema, zero configured weight bits, and 21-bit-aligned clipping.
- Five isolated harness tests covering case uniqueness and scope, Python effective-weight mapping, passing behavior when runners agree, direct `effective_weight` mismatch detection, and suite JSON evidence.
- Per-case Brian2Loihi and Python traces, exact comparison reports, and a suite-level machine-readable result.

Completion criteria:

- [x] Define directed cases covering all agreed static-weight boundaries.
- [x] Compare Python effective weights directly with Brian2Loihi `w_act`.
- [x] Compare observable current, voltage, and spike traces.
- [x] Produce stable per-case and suite-level artifacts.
- [x] Pass isolated harness tests in the development environment.
- [x] Independently run the baseline case in the Brian2Loihi environment.
- [x] Run all directed weight cases and diagnose every mismatch.
- [x] Achieve exact agreement for all supported cases.
- [x] Record final evidence and mark M08.3 complete.

Completion evidence:

```text
cases=15, pass=15, fail=0, error=0, ticks=15, mismatches=0
```

Passing all fifteen cases means that the Python encoder's final effective integer exactly equals Brian2Loihi `w_act` for every tested format boundary, and that the resulting one-synapse current, voltage, and spike traces also agree exactly. This validates the tested static-weight arithmetic and delivery behavior; it does not by itself validate production synapse or portable trace-schema integration, which is M08.4.

#### M08.4 — Integrate encoded weights into synapses and traces

**Status:** In progress  
**Started:** 2026-08-03  
**Repository evidence:** PR #4, branch `agent/m08-weight-conformance`

Introduce encoded weights without breaking the twelve Phase-1 conformance scenarios. Synaptic accumulation consumes only the derived effective integer weight, while scenarios and traces retain the original format and mantissa.

Architecture selected:

- `Synapse.weight` remains an integer and is the only value consumed by `NeuromorphicCore`.
- `Synapse.encoding` optionally stores the immutable `StaticWeightEncoding` that produced that integer.
- `Synapse.encoded(...)` derives and validates both values together.
- Backend traces use structured synapse descriptors rather than flattening encoding fields into string metadata.
- Trace schema v2 stores structured synapse metadata; the reader remains compatible with v1 traces.
- The generic Brian2Loihi adapter groups connections by `(exponent, num_weight_bits, sign_mode)` and restores observed `w_act` values to original scenario order.

Delivered so far:

- Backward-compatible encoded production synapses.
- An invariant that rejects disagreement between `Synapse.weight` and `encoding.effective_weight`.
- A single unchanged integer accumulation path in the core.
- Structured backend synapse descriptors containing routing, effective weight, requested and quantized mantissas, format fields, pre-clip value, and clipping status.
- Trace schema v2 serialization plus v1 read compatibility.
- A testable `Brian2LoihiSynapseGroup` representation preserving format, routing, requested mantissas, and original scenario indices.
- Generic backend support for legacy-only, encoded-only, and mixed legacy/encoded format groups.
- `Brian2LoihiBackendRun`, which retains the normalized trace and directly observed effective weights in scenario order while preserving the old trace-only API.
- All fifteen weight-conformance scenarios now construct `Synapse.encoded(...)` and call the generic production Brian2Loihi backend; the dedicated construction path has been removed.
- Eight focused integration tests covering construction, invariant enforcement, core equivalence, trace metadata, v2 JSON round-trip, v1 compatibility, mixed grouping, and observed-weight order restoration through a fake backend.

Completion plan and reasoning:

1. Introduce one internal generic-backend run result containing the normalized trace and Brian2Loihi's actual effective weight for each scenario synapse. Keep `run_brian2loihi_backend()` backward compatible by returning only the trace.
2. Convert every scenario synapse into a group entry containing its original scenario index, routing fields, requested Brian2Loihi mantissa, and a format key `(exponent, num_weight_bits, sign_mode)`.
3. Preserve legacy integer scenarios by translating their effective weights through the existing exponent-zero mapping and assigning excitatory or inhibitory sign mode exactly as before.
4. Preserve encoded scenarios by using the requested mantissa stored in `Synapse.encoding`, never reverse-engineering it from the effective integer. Group encoded connections only when all three format fields match.
5. Instantiate one `LoihiSynapses` object per format group, read each group's `w_act`, and restore those values to original scenario order for direct comparison evidence.
6. Refactor all fifteen weight-conformance cases to construct production `Synapse.encoded(...)` objects and call the same generic Brian2Loihi backend used by ordinary scenarios. Remove the dedicated one-synapse Brian2Loihi construction path.
7. Add focused tests for deterministic grouping, mixed encoded and legacy scenarios, preservation of original ordering, production-case construction, and complete v2 metadata.
8. Validate in increasing scope: focused Python tests, complete `pytest`, the original 12-case Brian2Loihi suite, the 15-case encoded suite through the production path, and inspection of generated v2 artifacts.

Reasoning and invariants:

- The core must continue to consume only `Synapse.weight`; format selection belongs to configuration and backend translation, not the neuron datapath.
- Legacy integer scenarios must retain their previously validated exponent-zero behavior without requiring encoding metadata.
- Encoded scenarios must pass their requested mantissas directly to Brian2Loihi. Reconstructing a mantissa from the effective weight would discard quantization intent and can be ambiguous after clipping or negative-exponent alignment.
- Group identity requires exponent, precision, and sign mode because Brian2Loihi stores those fields on `LoihiSynapses`, not independently per connection.
- Direct `w_act` values must be restored to scenario order so grouping remains an implementation detail and comparison artifacts stay deterministic.
- M08.4 is complete only when the dedicated M08.3 adapter path has been eliminated and the production scenario path proves both behavior and metadata preservation.

Completion criteria:

- [ ] Reproduce the complete Python test suite at the current generic-adapter head.
- [ ] Re-run all twelve original Brian2Loihi directed cases at the current head.
- [x] Refactor the generic Brian2Loihi adapter to group encoded synapses by exponent, precision, and sign mode.
- [x] Refactor the weight-conformance scenarios to use `Synapse.encoded(...)` directly.
- [ ] Re-run all fifteen encoded-weight cases through the production scenario path.
- [ ] Confirm generated trace-v2 artifacts preserve every encoded-weight field.
- [ ] Record final evidence and mark M08.4 complete.

Implementation evidence:

- Generic grouping and scenario-order restoration: `b7ddca2dab786c3b388df99e3dd7dc18f82486a6`.
- Production weight-conformance scenarios: `219efff11f992b4fabb52ef383b6e28c8674cf62`.
- Mixed-format and fake-backend order tests: `b0f6c1a6d6c5b21960fcf9dbaec2d18dc499ce11`.
- No repository CI workflow is configured, so the current branch head requires independent local execution.

Pre-refactor regression baseline:

```text
67 passed
cases=12, pass=12, fail=0, error=0, ticks=34, mismatches=0
cases=15, pass=15, fail=0, error=0, ticks=15, mismatches=0
```

The expected current Python count is `68 passed` because the generic backend now has one additional direct order-restoration test. The external 15-case result must be reproduced again because it now exercises the production scenario path rather than the dedicated M08.3 construction path.

#### M08.5 — Freeze FPGA-oriented weight storage

**Status:** Planned

Define the hardware representation after software conformance, favoring a shared weight-format table and per-synapse mantissa plus format index.

Completion criteria:

- [ ] Field widths and signed encodings are documented.
- [ ] BRAM cost is estimated for repeated per-synapse fields versus shared formats.
- [ ] The packed representation reconstructs every validated effective weight exactly.

---

## M09 — Add recurrent spike routing

**Status:** Planned

### Goal

Allow output spikes to become input axon events on later ticks, enabling deterministic recurrent networks.

### Planned deliverables

- Neuron-output to axon mapping.
- Explicit tick-boundary routing contract.
- Deterministic simultaneous-spike handling.
- Recurrent-network scenarios and routing traces.

---

## M10 — Freeze computational-core specification

**Status:** Planned

### Goal

Convert validated software behavior into an implementation-neutral specification suitable for direct FPGA translation.

### Planned deliverables

- Formal per-tick update schedule.
- State-register definitions and widths.
- Arithmetic, rounding, and overflow rules.
- Threshold, reset, refractory, accumulation, and routing semantics.
- Conformance tests linked to every requirement.

---

## M11 — Implement first FPGA neuron/core datapath

**Status:** Planned

### Goal

Implement the frozen computational core on the FPGA while preserving deterministic tick behavior and observable state.

### Planned deliverables

- Current accumulation and decay datapath.
- Voltage decay and integration datapath.
- Threshold, reset, and refractory logic.
- Neuron and synapse memories.
- Tick controller and host-visible trace interface.
- RTL or HLS trace exporter using the backend-neutral schema.

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
