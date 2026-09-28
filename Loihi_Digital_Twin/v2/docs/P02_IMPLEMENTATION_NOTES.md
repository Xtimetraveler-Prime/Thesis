# P02 Python Manycore Golden Model — Implementation Notes

## Purpose

This note records implementation choices made while translating `LOIHI1_TARGET_SPEC.md` into the first executable v2 Python architecture. It is subordinate to the target specification; conflicts must be resolved in favor of the specification.

## Implemented architectural boundary

The P02 model is independent from FPGA-v1 at runtime. The validated v1 neuron-step behavior was re-versioned into `loihi_twin_v2.compartment` and is checked against the frozen v1 implementation by a dedicated compatibility test.

The model currently separates:

1. logical resource capacities (`resources.py`);
2. single-compartment arithmetic (`arithmetic.py`, `compartment.py`);
3. destination-side input axon bindings and reusable synapse templates (`axon.py`, `synapse.py`);
4. source-side explicit fanout routes (`axon.py`);
5. normalized destination-core/destination-axon packets (`packet.py`);
6. per-core ingress, accumulation, compartment update, spike decision, egress, and completion (`core.py`);
7. explicit packet queues and traffic accounting (`router.py`);
8. logical drain/advance synchronization (`barrier.py`);
9. chip-level scheduling (`chip.py`);
10. deterministic deployment fingerprints and JSON round-trip loading (`mapping.py`);
11. deterministic multi-timestep execution/replay (`runtime.py`); and
12. JSON-serializable capacity and trace reports (`reporting.py`).

## Timestep interpretation

`SpikePacket.target_timestep` names the architectural update at which the destination consumes the packet's expanded contribution. A spike emitted while evaluating timestep `t` creates a packet targeting `t + 1`. Packet draining may occur immediately in emulator wall-clock time, but the contribution is retained in the destination's pending state until its target algorithmic timestep.

This keeps physical/emulator scheduling separate from algorithmic time and prevents service order from creating same-timestep causality.

## Barrier interpretation

The current P02 barrier is centralized and intentionally simple. A timestep may advance only after:

- every configured logical core has completed its compartment evaluation; and
- every packet emitted during that timestep has been removed from the router queue and delivered into destination pending state.

This is a PROJECT CHOICE implementing the logical drain/advance invariant in the target specification. It is not a claim that Loihi uses this software data structure.

## Deployment and replay boundary

`Deployment` is the first machine-readable architecture configuration consumed by the v2 model. It serializes the complete logical-core configuration, including compartments, destination-side axons, shared synapse templates, output routes, arithmetic profile, logical capacity, and synapse-cost model.

The deployment schema is versioned as `v2.0-p02`. Its SHA-256 fingerprint is computed from a canonical logical payload with core configurations sorted by logical core ID. Serialized documents that carry a fingerprint are rejected if their contents no longer match that identity.

This format is a PROJECT CHOICE and not a claim about native Loihi configuration storage. P06 should emit this boundary, or a strictly versioned successor, so Python and later FPGA execution do not acquire separate incompatible configuration formats.

`run_deployment()` executes a deployment for a fixed number of algorithmic timesteps with explicit external-event, core-service-order, and packet-drain-order schedules. `RunResult.trace_fingerprint` hashes the JSON-normalized architectural trace. These controls exist specifically to validate that legal scheduling differences do not change logical behavior.

See `P02_DEPLOYMENT_SCHEMA.md` for the field-level document contract.

## Synaptic storage accounting

The first cost model is named `v2-simple-32bit-entry`:

- 4 bytes per unique synapse-template header;
- 4 bytes per stored template entry; and
- 4 bytes per input-axon binding.

This is deliberately conservative and simple. It is **not** claimed to reproduce native Loihi SRAM packing. The cost model is versioned and isolated behind `SynapseCostModel`; P06 or later fidelity work may replace it with sparse/dense/run-length models while preserving the same logical connectivity interface.

Reusable templates are counted once even when multiple axons bind to them, allowing the golden model to represent and measure the resource effect of connection sharing without claiming native compression bitfields.

## P02 directed-test mapping

- T1: exact v1-compatible single-compartment arithmetic.
- T2: two-core feed-forward packet causality.
- T3: explicit multicast fanout.
- T4: same-timestep arrival-order invariance.
- T5: barrier blocks advancement until traffic drains.
- T6: cross-core recurrence.
- T7: explicit rejection of compartment, input-axon, output-route, and synapse-memory overflow.
- T8: shared-template accounting with equivalent expanded synaptic effects.
- T9: normalized invariance to logical core service order and packet drain order.

Additional P02 regression coverage checks deployment JSON round-trip behavior, fingerprint tamper detection, schema-version rejection, deterministic three-core recurrent replay, stable core-order-independent deployment identity, and multi-timestep trace-fingerprint invariance.

T10 is intentionally reserved for the later Python/FPGA differential phase.

## Integrated P02 validator

`scripts/validate_p02.py` builds a three-core recurrent ring, serializes and reloads its deployment, executes four timesteps under forward and reversed legal scheduling policies, and requires:

- the deployment fingerprint to survive round-trip serialization;
- three logical cores to remain configured;
- the spike wave `core0@t0 -> core1@t1 -> core2@t2 -> core0@t3`;
- identical normalized traces across service-order changes;
- identical trace fingerprints across those schedules; and
- non-negative reported resource headroom.

This script is intended as the final software-only behavioral smoke test before closing P02.

## Not implemented in P02 v2.0 profile

The data structures reserve delay and future metadata fields, but executable programmable delays remain disabled. Dendritic trees, native 1–9-bit mixed synapse formats, exact native compression packing, plasticity, management processors, multi-chip routing, and physical asynchronous timing remain outside this phase per the target specification.
