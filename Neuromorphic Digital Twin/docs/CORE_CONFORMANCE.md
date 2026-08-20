# M10.3 — Computational-Core Requirement Conformance

This document records how the normative requirements in
[`CORE_SPECIFICATION.md`](CORE_SPECIFICATION.md) are tied to executable tests
before M11 begins translating the core into FPGA logic.

## Objective

Every normative requirement with a `CORE-*` identifier must be covered by at
least one executable test. The mapping itself is also tested so adding a new
requirement to the specification without adding coverage causes the M10.3 gate
to fail.

The implementation lives in:

```text
tests/test_core_specification.py
```

That file contains `REQUIREMENT_TESTS`, a requirement-ID to pytest-function
mapping, plus a coverage-gate test that extracts all IDs matching
`CORE-[A-Z]+-NNN` from the specification and requires exact set equality with
the mapping.

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

## Focused cases added

The M10.3 suite includes directed checks for:

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
14. exact requirement-ID coverage of the normative specification.

## Profile isolation

The generic golden model remains configurable and retains its previous default
unbounded arithmetic. M10.3 instead exposes the frozen hardware profile through:

```python
FPGA_CORE_ARITHMETIC_V1
validate_core_configuration_v1(...)
```

This keeps the earlier Brian2Loihi conformance path unchanged while giving M11
and M12 a single explicit FPGA contract.

## Verification status

A focused local reconstruction of the M10 profile and core transition path was
executed after the reset-queue test was strengthened:

```text
11 passed
```

Those checks exercised the new width, saturation, decay, encoded-weight,
recurrent-routing, reset, and configuration-validation behavior. The exact
repository-level M10.3 pytest file and the complete pre-existing regression
suite still need to be executed from a full checkout before M10.3 and M10 are
marked complete in `MILESTONES.md`.

Recommended completion commands from `Neuromorphic Digital Twin/`:

```bash
pytest -q tests/test_core_specification.py
pytest -q
```

The original Brian2Loihi directed regression should also remain unchanged:

```bash
python examples/run_directed_conformance.py
```

M10.3 is complete only when the requirement-link gate passes and the full Python
regression suite remains green.
