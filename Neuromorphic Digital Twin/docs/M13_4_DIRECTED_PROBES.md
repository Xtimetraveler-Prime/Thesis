# M13.4 — Directed Differential Architectural Probes

**Status:** In progress — native/pre-normalization evidence boundary implemented; normalized four-way comparison remains blocked on M13.3.

## Purpose

M13.4 uses small deterministic probes to expose architectural agreements and differences among the M12-validated project baseline, Brian2Loihi 0.5.2, pinned Catalyst N1, and published Loihi evidence. This work must not tailor parameter transforms after observing a discrepancy. For that reason, the M13.4 implementation is deliberately split into a native-evidence layer that can be developed now and a normalized-comparison layer that is fail-closed until M13.3 freezes the common behavioral subset and mapping rules.

The branch is based on the merged M13.2 crosswalk at `49ab7be6dfce427979622b585165b59bbbfbc2da`. No M12 computational behavior, HLS, or RTL is modified by this work.

## Why M13.3 is a hard dependency

M13.2 identified several cases where superficially identical integer fields do not yet have a defensible shared meaning: current/update indexing, strict `>` versus Catalyst `>=` threshold behavior, refractory register conventions, weight formats, recurrence timing, and event-order observability. M13.4 therefore may collect native evidence before M13.3, but it must not call unlike native states equal or different until a frozen mapping says what is comparable.

The machine gate expects a future normalization authority at:

```text
references/m13_3_normalization_spec.json
schema = neuromorphic-twin-m13-normalization-v1
status = frozen
```

Until that file exists, `require_frozen_m13_3()` raises `M13NormalizationNotFrozen`, and the M13.4 catalog keeps every Catalyst normalized participation state at `blocked_by_m13_3`.

## Frozen directed-probe catalog

The authority is `references/m13_4_probe_catalog.json`. It contains 12 probes covering all 11 M13.4 probe classes:

1. current impulse / current-decay ordering;
2. voltage decay;
3. negative-current rounding;
4. threshold equality and just-over-threshold behavior;
5. refractory entry/hold/countdown/release;
6. positive, negative, and mixed synaptic drive;
7. weight precision/exponent/sign-mode/clipping boundaries;
8. simultaneous fan-in and fan-out;
9. repeated event multiplicity;
10. recurrent delivery timing and recurrent chains;
11. finite-width saturation/overflow boundaries;
12. simultaneous independent spikes and observable ordering.

The catalog records the M13.2 crosswalk rows that motivate each question, intended observables, reusable earlier cases, and participation status for published Loihi, Brian2Loihi, this project, and Catalyst N1. It intentionally contains no A-H discrepancy class and no verdict.

## Reused evidence before normalization

M13.4 can already re-execute cases whose project/Brian2Loihi mapping was established before Catalyst entered the audit. The current reuse boundary is:

- all 12 M06/M07 directed conformance cases;
- all 15 M08 encoded-weight conformance cases.

This is not a substitute for the eventual four-way corpus. It is a provenance-preserving re-execution of already shared project/Brian2Loihi scenarios so later M13.4 evidence can reuse exact inputs rather than reconstructing them informally.

Run:

```bash
PYTHONPATH=src python3 examples/run_m13_4_directed_probes.py \
  --run-pre-normalization-reuse build/m13_4/pre_normalization
```

For each directed case the evidence tree contains:

```text
directed/<case>/
  scenario.json
  project.native.json
  brian2loihi.native.json
  project-vs-brian2loihi.report.json
```

Encoded-weight cases additionally contain `effective-weight.json`. The top-level `manifest.json` records summary counts and SHA-256 hashes for every preserved artifact. It also explicitly records:

```text
normalized_comparison_performed = false
catalyst_execution_performed = false
```

Those flags prevent this evidence from being misrepresented later as a completed Catalyst comparison.

## Probe provenance and reuse

The catalog links earlier evidence rather than discarding it. Examples include:

- M05/M07 `current-decay-order`, `voltage-decay`, negative rounding, threshold, refractory, fan-in/fan-out, mixed excitation/inhibition, and simultaneous spike scenarios;
- all 15 M08 encoded-weight cases;
- M12.2 physical boundary cases for threshold, refractory, rounding, repeated multiplicity, encoded weights, and state saturation;
- M12.3 recurrent chain/fan-in/fan-out/multiplicity/order/history cases.

The M12 references are catalog provenance only at this stage; the pre-normalization runner does not rerun physical FPGA evidence.

## New work still required after M13.3

Once M13.3 freezes the common subset, M13.4 must still:

- implement the exact Catalyst adapter(s) named by the normalization specification;
- add new native scenarios for repeated multiplicity, recurrence, and saturation where an existing backend-neutral M06/M08 case is insufficient;
- preserve Catalyst native configuration and trace artifacts alongside project/Brian2Loihi native traces;
- generate normalized traces using only the frozen M13.3 transforms;
- compare only fields categorized as exact or transformed-comparable;
- preserve qualitative/non-comparable fields without forcing equality;
- report the first divergent architectural quantity;
- carry every meaningful difference forward for A-H adjudication rather than changing the project baseline inside the probe runner.

## Current pass boundary

M13.4 is **not complete** at this checkpoint. The pre-normalization scaffold is complete enough to freeze the questions and preserve existing shared evidence, but the milestone pass boundary requires the agreed directed corpus to run across every applicable implementation. That cannot be done defensibly while M13.3 remains Planned.

The correct next dependency is therefore M13.3: freeze the common behavioral subset and normalization interface. After that merge, this branch/work can continue without redesigning the probe questions in response to observed Catalyst outputs.
