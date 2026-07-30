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
- Do not replace the existing integer `Synapse.weight` representation until the encoder itself conforms to Brian2Loihi.

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

**Status:** Planned

Add directed comparisons for negative and positive exponents, reduced precision, mixed-sign quantization, sign-mode limits, minimum and maximum values, and clipping behavior.

Completion criteria:

- [ ] Python effective weights agree with Brian2Loihi for every supported directed case.
- [ ] Any ambiguity between published equations and emulator behavior is isolated and documented.
- [ ] Stable comparison artifacts are produced for the weight suite.

#### M08.4 — Integrate encoded weights into synapses and traces

**Status:** Planned

Introduce encoded weights without breaking the twelve Phase-1 conformance scenarios. Synaptic accumulation should consume only the derived effective integer weight, while traces retain the original format and mantissa.

Completion criteria:

- [ ] Existing integer-weight scenarios remain reproducible.
- [ ] Encoded synapses drive the same core through a single effective-weight interface.
- [ ] Scenario and trace schemas preserve weight-format metadata.

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