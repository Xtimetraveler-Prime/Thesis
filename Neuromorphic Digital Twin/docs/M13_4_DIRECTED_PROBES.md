# M13.4 Pre-Normalization Directed-Probe Checkpoint

## Historical status

This document records the **pre-normalization M13.4 checkpoint** created before M13.3 was complete. It is retained for provenance, but it is no longer the current M13.4 status document.

Current M13.4 methods, results, classifications, and validation boundary are documented in:

```text
docs/M13_4_DIRECTED_DIFFERENTIAL.md
references/m13_4_candidate_findings.json
```

The probe catalog remains at `references/m13_4_probe_catalog.json`; it has since been advanced to record that the M13.3 normalization authority is frozen and executable comparison is permitted only under those predeclared transforms.

## Purpose of the checkpoint

M13.4 was intentionally started before M13.3 so the architectural questions could be frozen independently of later Catalyst outputs. This prevented comparison mappings from being invented after observing an interesting difference.

The branch began from the merged M13.2 crosswalk at:

```text
49ab7be6dfce427979622b585165b59bbbfbc2da
```

At that checkpoint, no M12 computational behavior, HLS, or RTL was modified.

## Frozen directed-probe catalog

The pre-normalization catalog established 12 probe questions covering the 11 required M13.4 probe classes:

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

The catalog deliberately contained no result verdict or A-H discrepancy class. It recorded only the question, crosswalk provenance, intended observables, reusable earlier evidence, and then-current participation boundary.

## Reused project/Brian2Loihi evidence

Before normalized Catalyst execution was authorized, M13.4 could still rerun scenarios whose project/Brian2Loihi mapping had already been established. That reuse boundary contained:

- all 12 M06/M07 directed conformance cases;
- all 15 M08 encoded-weight conformance cases.

The pre-normalization evidence runner preserved, per case:

```text
scenario.json
project.native.json
brian2loihi.native.json
project-vs-brian2loihi.report.json
```

Encoded-weight cases additionally preserved `effective-weight.json`; the aggregate manifest recorded SHA-256 hashes and explicitly marked that Catalyst execution and normalized comparison had not yet occurred.

## Comparison-runtime Class-H correction

The pre-normalization preflight exposed a dependency-only incompatibility before any Catalyst architectural result was produced. An unrestricted NumPy resolver selected NumPy 2.x, while the selected Brian2 2.9.0 path still depended on an ndarray API removed by NumPy 2.

The comparison-only environment was therefore frozen to:

```text
numpy==1.26.4
brian2==2.9.0
brian2-loihi==0.5.2
```

This was classified as tooling/reproducibility evidence, not a neuron-model change. The project computational core was unchanged.

## Fail-closed guards established here

The generic Brian2Loihi adapter was changed to reject project `spike_routes` rather than silently drop recurrence. Repeated identical-source/same-tick events and explicit finite-width overflow were also kept outside that adapter's comparison boundary when no defensible transform existed.

Those guards remain intentional after M13.3. The final M13.4 implementation uses a dedicated Brian2Loihi native recurrent probe rather than weakening the generic route guard, and it keeps repeated-event multiplicity and cross-implementation overflow non-comparable where the frozen M13.3 specification says no shared exact observable exists.

## Handoff to completed M13.4 candidate

M13.3 subsequently froze `references/m13_3_normalization_spec.json`, after which M13.4 implemented the Catalyst CPU and RTL CUBA boundaries, native/normalized artifact preservation, first-divergence reporting, logical compiler-placement normalization, and directed discrepancy classification.

The resulting candidate pass-boundary evidence is now in `docs/M13_4_DIRECTED_DIFFERENTIAL.md`. This historical checkpoint should therefore be cited only when explaining how the directed questions and pre-normalization guards were established before Catalyst outputs were interpreted.

## Closure handoff

M13.3 subsequently froze `neuromorphic-twin-m13-normalization-v1`, enabling the predeclared Catalyst and Brian2Loihi transforms without redesigning the probe questions. M13.4 then executed all 12 frozen questions and closed with 6 agreements, 3 architectural/model differences, 1 partial-scope result, 2 non-comparable results, and no Class-A/B candidate. Independent local validation on 2026-09-10 reproduced the full requested gate. The authoritative result narrative is `M13_4_DIRECTED_DIFFERENTIAL.md`; this file remains useful as provenance for how the questions and reuse boundary were frozen before those outputs were known.
