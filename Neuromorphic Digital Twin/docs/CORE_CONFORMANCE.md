# M10.3 — Computational-Core Requirement Conformance

This document records how the normative requirements in
[`CORE_SPECIFICATION.md`](CORE_SPECIFICATION.md) are tied to executable tests
before M11 begins translating the core into FPGA logic.

## Objective

Every normative requirement with a `CORE-*` identifier must be covered by at
least one executable test. The mapping itself is also tested so adding a new
requirement to the specification without adding coverage causes the M10.3 gate
to fail.

The primary requirement-linked implementation lives in:

```text
tests/test_core_specification.py
```

That file contains `REQUIREMENT_TESTS`, a requirement-ID to pytest-function
mapping, plus a coverage-gate test that extracts all IDs matching
`CORE-[A-Z]+-NNN` from the specification and requires exact set equality with
the mapping.

Final profile-boundary and cross-contract guards live in:

```text
tests/test_core_specification_boundaries.py
```

These tests protect hardware-facing assumptions that span M08 and M10 or sit at
the boundary between the configurable Python model and the frozen FPGA-v1
profile.

## Coverage groups

The current specification contains requirements in these groups:

| Group | Covered behavior |
|---|---|
| `CORE-TICK-*` | atomic tick schedule, event ordering, pre-state isolation, next-tick recurrence |
| `CORE-STATE-*` | current/voltage/refractory/tick/ID widths and reset state |
| `CORE-ARITH-*` | 24-bit saturation and round-away-from-zero decay |
| `CORE-SYN-*` | effective-weight use, fan-out, multiplicity, exact accumulation |
| `CORE-NEURON-*` | current update, voltage integration, threshold, reset, refractory timing |
| `CORE-ROUTE-*` | fan-out, duplicate rejection, simultaneous ordering, next-tick queueing |
| `CORE-CFG-*` | representability and static configuration validation |
| `CORE-TRACE-*` | state and routing observability for M12 comparison |

## Directed cases

The M10.3 suite now includes checks for:

1. frozen architectural widths and the named `neuromorphic-twin-core-spec-v1` profile;
2. signed 24-bit saturation at positive and negative limits;
3. atomic tick behavior and next-tick-only recurrent delivery;
4. external-before-recurrent event ordering and event multiplicity;
5. exact synaptic accumulation before the state-width operation;
6. consumption of the M08 effective encoded weight without re-quantization;
7. decay endpoints and round-away-from-zero behavior;
8. input-before-current-decay and voltage use of pre-decay working current;
9. strict-greater-than threshold behavior, hard reset, and refractory release timing;
10. deterministic simultaneous routing and same-axon multiplicity across sources;
11. reset disposal of a genuinely pending recurrent event plus deterministic replay;
12. rejection of unrepresentable profile configuration and duplicate routes;
13. trace visibility for state and routing boundaries;
14. exact requirement-ID coverage of the normative specification;
15. equality of M10's 16-bit ID profile with M08 axon and target-neuron storage widths;
16. 16-bit validation of runtime external axon IDs while preserving order and multiplicity;
17. representability validation for injected/replayed current, voltage, and refractory state;
18. an explicit regression that threshold must remain strictly greater than reset voltage.

## Profile isolation

The generic golden model remains configurable and retains its previous default
unbounded arithmetic. M10.3 instead exposes the frozen hardware profile through:

```python
FPGA_CORE_ARITHMETIC_V1
validate_core_configuration_v1(...)
validate_input_axons_v1(...)
validate_neuron_state_v1(...)
```

This keeps the earlier Brian2Loihi conformance path unchanged while giving M11
and M12 a single explicit FPGA contract. Runtime axon-event validation and
injected-state validation are deliberately profile helpers rather than changes
to `NeuromorphicCore`, because changing the generic core would alter behavior
already used by earlier validation milestones.

## Verification history

A focused local reconstruction of the original M10 profile and core transition
path was executed after the recurrent-reset test was strengthened:

```text
11 passed
```

The repository-level M10.3 test file, complete Python suite, and original
Brian2Loihi directed conformance suite were then independently run by the user
on 2026-08-20 and reported successful.

A final specification audit after that verification identified two additional
profile-boundary risks:

- runtime external axon IDs needed an explicit 16-bit FPGA-v1 validator;
- replay/injected neuron state needed explicit profile-width validation.

The same audit added direct guards tying the M10 identifier widths to M08's
frozen FPGA storage fields and explicitly testing the threshold/reset relation.
Because these changes were made after the successful repository-level run, the
final branch state requires one more independent verification before M10.3 is
marked complete.

## Final completion commands

From `Neuromorphic Digital Twin/` run:

```bash
pytest -q tests/test_core_specification.py tests/test_core_specification_boundaries.py
pytest -q
python examples/run_directed_conformance.py
```

M10.3 is complete when all three commands pass on this final branch state. M10
will remain in progress and the branch will remain unmerged until that final
independent verification is confirmed.
