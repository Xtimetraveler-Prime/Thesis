# Loihi Digital Twin v2 Development Roadmap

## Purpose

This document is the **active development tracker for FPGA-v2**. It records:

- which development phase is currently active;
- which deliverables have been completed in each phase;
- which deliverables remain;
- the completion gate for advancing to the next phase; and
- the architectural and verification rules that apply across the whole v2 program.

The detailed Loihi-1 architectural requirements are defined separately in:

```text
Loihi_Digital_Twin/v2/docs/LOIHI1_TARGET_SPEC.md
```

That specification is the normative architecture contract. This roadmap tracks
**development progress against that contract**.

The preserved FPGA-v1 development history remains in:

```text
Loihi_Digital_Twin/v1/MILESTONES.md
```

---

## Status legend

- **Complete** — all required deliverables and completion criteria are satisfied.
- **In progress** — active work has started, but one or more required deliverables remain.
- **Planned** — agreed work that has not yet started.
- **Blocked** — progress is waiting on an unresolved dependency or decision.
- **Deferred** — intentionally outside the current critical path.

---

## Current phase

> **P08 in progress — P07 deeper mapped multicore SNN validation is complete and physically accepted.**
>
> P07 completed on 2026-09-29 after a compiler-generated six-layer feed-forward
> SNN executed through the complete specification → P06 compiler → Python → FPGA
> path and matched at the normalized architectural boundary on the physical K26.
> The accepted source fingerprint is
> `4d11e473a427b153a23226bd3294d6a243292f14931d6d85f6705c9e85146b76`
> and the accepted compiled-deployment fingerprint is
> `5e5a16062faa8d92d0077de56fcbd07ff74c602f96e52f98e25ccf49a4af34f9`.
>
> The accepted workload contains six neuron layers and 12 neurons mapped across
> three logical contexts serviced by one physical engine. It exercises both
> local and remote inter-layer traffic, records 28 expanded synaptic connections
> represented by six stored shared parameters (`4.666666666666667` expanded per
> stored parameter), and includes an expected mapper rejection when the same
> workload is artificially limited to two logical cores (`required=3`, `limit=2`).
>
> Three physical input scenarios were executed for seven algorithmic timesteps
> under both forward and reverse legal logical-context service orders. All 42
> directed physical ticks passed with nonzero PL cycle counts and Python/FPGA
> agreement. The result record reported `schema=p07-deep-mapped-snn-v1`,
> `logical_contexts=3`, `physical_engines=1`, `logical_capacity_changed=0`, and
> `result=PASS`.
>
> The accepted evidence is archived under:
>
> ```text
> hardware/evidence/p07_physical_20260930T022814Z/
> ```
>
> The P07 workload/validation contract is documented in
> `docs/P07_DEEP_SNN_VALIDATION.md`; the design decisions and closure lessons are
> recorded in `docs/P07_DEEP_SNN_CHALLENGES.md`. P08 is now active to build and
> quantitatively characterize the final deeper MNIST workload and make an
> explicitly bounded comparison with the NxTF-oriented reference workload.

---

## Phase summary

| ID | Phase | Status | Started | Completed |
|---|---|---|---|---|
| P00 | Preserve and freeze FPGA-v1 baseline | Complete | 2026-09 | 2026-09-25 |
| P01 | Define Loihi-1 target and establish v2 project structure | Complete | 2026-09-28 | 2026-09-28 |
| P02 | Build separate Python manycore golden model | Complete | 2026-09-28 | 2026-09-28 |
| P03 | Implement and validate one FPGA-v2 logical core | Complete | 2026-09-28 | 2026-09-28 |
| P04 | Add multicore packet routing and timestep/barrier semantics | Complete | 2026-09-28 | 2026-09-29 |
| P05 | Add logical-core virtualization | Complete | 2026-09-29 | 2026-09-29 |
| P06 | Build deterministic mapper/compiler and deployment format | Complete | 2026-09-29 | 2026-09-29 |
| P07 | Validate deeper mapped multicore SNNs | Complete | 2026-09-29 | 2026-09-29 |
| P08 | Build and compare NxTF-oriented deep MNIST workload | In progress | 2026-09-29 | — |

---

# P00 — Preserve and freeze FPGA-v1 baseline

**Status:** Complete  
**Completed:** 2026-09-25

## Goal

Freeze the validated first-generation architecture and MNIST application before
beginning substantial Loihi-like architectural changes.

## Achieved deliverables

- Preserved the first MNIST application as `applications/mnist_baseline/`.
- Preserved the first architecture under `Loihi_Digital_Twin/v1/`.
- Archived accepted historical FPGA artifacts.
- Rebuilt HLS/Vivado hardware from a fresh checkout.
- Re-ran rebuilt images on the physical K26.
- Confirmed preserved application behavior after repository reorganization.
- Created the immutable source tag `fpga-v1-mnist-v1-final`.
- Retained the compatibility symlink `Neuromorphic Digital Twin -> Loihi_Digital_Twin/v1`.

## Completion gate

Complete. FPGA-v1 behavior and accepted evidence are historical controls.

---

# P01 — Loihi-1 target definition and v2 project foundation

**Status:** Complete  
**Started:** 2026-09-28  
**Completed:** 2026-09-28

## Goal

Define exactly what this thesis means by a Loihi-1 architectural digital twin
before implementing a new model or new FPGA datapath.

## Achieved deliverables

- Created `Loihi_Digital_Twin/v2/docs/LOIHI1_TARGET_SPEC.md`.
- Added requirement-level citations to primary/reference literature.
- Defined the project as a source-backed architectural digital twin, not a
  transistor-level or timing-exact clone.
- Defined logical Loihi-like resource limits independently from physical FPGA
  instantiation.
- Defined destination-core / destination-axon packet semantics.
- Defined axon-to-synapse expansion and explicit source fanout.
- Defined algorithmic timestep/quiescence/barrier semantics separately from
  physical FPGA clock cycles.
- Defined virtualization invariance and normalized trace requirements.
- Defined Priority-A, deferred, and non-claimed features.
- Defined directed validation tests T1-T10.
- Reorganized the architecture as `Loihi_Digital_Twin/v1/` and `v2/`.
- Moved historical M01-M13 tracking to `Loihi_Digital_Twin/v1/MILESTONES.md`.
- Made this file the active v2 roadmap.
- Verified the relocated v1 and preserved MNIST regression suites locally.
- Merged the accepted P01 branch into `main`.

## Completion gate

Complete. The initial target specification is the architecture authority for
P02 and later implementation.

---

# P02 — Separate Python manycore golden model

**Status:** Complete  
**Started:** 2026-09-28  
**Completed:** 2026-09-28

## Goal

Create a new executable golden model for the Loihi-like manycore architecture
without extending the v1 `NeuromorphicCore` in place.

## Achieved implementation deliverables

- [x] Created an independent v2 Python package under `Loihi_Digital_Twin/v2/`.
- [x] Defined Loihi-1 logical chip/core resource constants and hard limits.
- [x] Added explicit per-core resource accounting and named capacity failures.
- [x] Defined a versioned project synapse-storage cost model behind an isolated
      interface rather than claiming native Loihi SRAM packing.
- [x] Defined a v2 compartment/neuron state interface.
- [x] Re-versioned the validated v1 neuron arithmetic into v2 without a runtime
      dependency on the v1 package.
- [x] Added dedicated compatibility tests against the frozen v1 neuron step.
- [x] Defined destination-side input-axon bindings.
- [x] Defined reusable synapse templates and explicit expanded-connection counts.
- [x] Defined source-side output routing/fanout entries.
- [x] Defined normalized spike packets with target timestep, destination core,
      destination axon, and optional source metadata.
- [x] Implemented explicit packet queues and traffic accounting.
- [x] Implemented logical-core ingress, axon expansion, accumulation,
      compartment update, spike decision, egress, and completion behavior.
- [x] Implemented a centralized logical drain/advance barrier.
- [x] Implemented chip-level scheduling independent of packet-delivery order.
- [x] Defined normalized core/chip traces containing packet, axon-expansion,
      synaptic-contribution, state, spike, and barrier information.
- [x] Added deterministic deployment fingerprints and a versioned JSON deployment
      schema with round-trip loading and tamper detection.
- [x] Added JSON-serializable deployment/capacity reports with per-core headroom.
- [x] Added JSON-serializable architecture trace reports and deterministic trace
      fingerprints.
- [x] Added runnable two-core feed-forward and three-core recurrent examples.
- [x] Added `docs/P02_IMPLEMENTATION_NOTES.md` and
      `docs/P02_DEPLOYMENT_SCHEMA.md`.

## Directed tests and verification

- [x] **T1** — v1-compatible single-neuron/compartment arithmetic.
- [x] **T2** — two-core feed-forward packet delivery.
- [x] **T3** — multicast fanout.
- [x] **T4** — within-timestep packet-order invariance.
- [x] **T5** — barrier drain/advance behavior.
- [x] **T6** — cross-core recurrence.
- [x] **T7** — hard rejection of compartment, input-axon, output-route, and
      synapse-memory capacity overflow.
- [x] **T8** — connection-sharing/resource-accounting behavior.
- [x] **T9** — logical service-order / packet-drain-order invariance at the
      normalized architecture boundary.
- [x] **T10** — Python/FPGA normalized trace comparison, completed during P03 on
      the physical K26. T10 was not required to close P02 itself.
- [x] Installed the v2 package in an independent `.venv-v2` environment.
- [x] Full P02 test suite passed locally with **26 tests passing**.
- [x] Two-core example demonstrated Core 0 firing at timestep 0 and Core 1
      consuming the routed event/firing at timestep 1.
- [x] Three-core recurrent replay produced the expected wave
      `core0@t0 -> core1@t1 -> core2@t2 -> core0@t3`.
- [x] Deployment round-trip fingerprint matched exactly.
- [x] Reordered legal service/drain schedules produced the identical normalized
      trace fingerprint `90a8300b7354744d00024cc9602a12b2f3ac432414ed027983b2c2cce28ad6d1`.

## Completion gate

Complete. The Python model executes representative multicore networks
deterministically and all software-side directed architectural tests T1-T9 pass
without requiring FPGA RTL/HLS.

**Next phase:** P03 — one FPGA-v2 logical core.

---

# P03 — One FPGA-v2 logical core

**Status:** Complete  
**Started:** 2026-09-28  
**Completed:** 2026-09-28

## Goal

Implement one logical v2 neuromorphic core on the K26 against the target
specification and the P02 Python golden model.

## Required deliverables

- [x] Define the FPGA-v2 one-core hardware boundary.
- [x] Implement per-core compartment state.
- [x] Implement input-axon lookup.
- [x] Implement synapse traversal/accumulation.
- [x] Implement output spike generation and routing-entry traversal.
- [x] Implement the P03 runtime configuration/state loading and readback
      interface through the transport-neutral banked host/debug bridge.
- [x] Implement normalized trace/state inspection at the same semantic boundary
      as the Python model.
- [x] Add resource/capacity guards for one logical core.
- [x] Add differential Python-vs-HLS/RTL tests.
- [x] Synthesize/implement the complete one-core memory shell on the K26 target.
- [x] Perform physical directed conformance against the Python model.

## P03 implementation findings

The accepted full-capacity XPM one-core shell closes a requested 100 MHz on the
K26 with WNS `+1.148 ns`, WHS `+0.010 ns`, `3,545` LUTs, `5,607` registers,
`96.5 / 144` BRAM tiles, `0` URAM, and `2` DSPs. The standalone external memory
fabric uses 94.5 BRAM-tile equivalents; the additional two tiles belong to the
HLS-local accumulator.

The external-memory integration, VIO/JTAG handshakes, physical reset behavior,
HLS `ap_ctrl_hs` start semantics, and reserved event-word bits required several
iterations. The complete history is retained in
`docs/P03_INTEGRATION_CHALLENGES.md`.

## Accepted physical-conformance evidence

- [x] Added a transport-neutral nine-bank host/debug bridge and compute/host
      arbitration.
- [x] Made host completion/status pollable over VIO/JTAG.
- [x] Added deterministic physical-vector generation from the Python corpus.
- [x] Verified reset release physically with a free-running PL heartbeat.
- [x] Verified physical write/read access to all nine retained XPM banks.
- [x] Programmed `xck26_0` and completed the automated five-tick T10 corpus.
- [x] Every physical tick matched Python state, normalized trace, packet words,
      spike count, packet count, and status.
- [x] All five ticks completed with `status=0`.

Physical observations for the accepted directed corpus:

| Tick | Timestep | PL cycles | Spikes | Packets | Status |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 36 | 1 | 2 | 0 |
| 1 | 1 | 34 | 1 | 1 | 0 |
| 2 | 2 | 36 | 0 | 0 | 0 |
| 3 | 3 | 23 | 0 | 0 | 0 |
| 4 | 4 | 36 | 1 | 2 | 0 |

The physical harness wrote `schema=p03-physical-conformance-v1` and
`result=PASS`. These cycle counts are implementation observations for the
directed corpus, not algorithmic timesteps or native-Loihi latency claims.

## Completion gate

**Complete.** One hardware core reproduces the normalized golden-model
state/spike/packet behavior for the directed suite on the physical K26, all nine
physical memory banks are host-accessible, and T10 passes through the automated
physical conformance flow.

**Next phase:** P04 — multicore packet routing and barrier semantics.

---

# P04 — Multicore packet routing and timestep/barrier semantics

**Status:** Complete  
**Started:** 2026-09-28  
**Completed:** 2026-09-29

## Goal

Extend FPGA-v2 from an isolated logical core to a true multicore architectural
model with explicit inter-core communication and deterministic algorithmic-time
completion semantics.

## Engineering decision: preserving logical capacity under the K26 memory limit

P03 established a transparent full-capacity one-core physical reference shell,
but that shell uses `96.5 / 144` K26 BRAM tiles. Two literal copies would need
approximately `193` BRAM tiles before the P04 router, barrier, or any extra queue
storage is counted. Therefore a naive two-full-shell implementation is not a
physically valid P04 plan.

The memory problem is treated as a **physical implementation constraint**, not
an architectural permission to shrink the modeled Loihi core. P04 continues to
enforce the source-backed logical limits of 1,024 compartments/core, 4,096 input
axon IDs/core, 4,096 output-route slots/core, and 128 KiB modeled synaptic
fan-in storage/core. A deployment that exceeds those logical limits remains
invalid regardless of how little or how much FPGA memory happens to be present.

The accepted design uses two unchanged P03-compatible compute endpoints with
physical backing memories sized for the directed P04 validation deployment.
This provides genuine simultaneous endpoint/routing behavior while clearly
reporting that the test shell is not capable of retaining two maximally
populated logical cores at once. P05 replaces this fixture limitation with
transparent logical-context storage and scheduling.

The complete architecture contract is recorded in
`docs/P04_MULTICORE_ARCHITECTURE.md`; the integration implementation is recorded
in `docs/P04_INTEGRATION_IMPLEMENTATION.md`; and the bring-up problems and fixes
are recorded in `docs/P04_INTEGRATION_CHALLENGES.md`.

## Sub-milestone progress

### P04.1 — Golden-model multicore contract closure — **Verified**

- [x] Added explicit `external` / `local` / `remote` route-scope accounting.
- [x] Added simultaneous remote producers and fan-in regression coverage.
- [x] Added local+remote multicast regression coverage.
- [x] Preserved feed-forward, recurrence, barrier blocking, and legal
      service-order invariance behavior.
- [x] Targeted multicore pytest and the full v2 pytest suite passed.

### P04.2 — Standalone packet-router/barrier RTL — **Verified**

- [x] Added independent producer capture slots so simultaneous source assertions
      are retained without depending on arbitration priority.
- [x] Added deterministic arbitration with reversible legal service priority.
- [x] Added per-destination FIFOs with explicit ready/valid backpressure.
- [x] Added P03 packet valid/destination/target-timestep integrity checks.
- [x] Added local/remote traffic counters.
- [x] Added per-core completion latching, in-flight accounting, `can_advance`,
      accepted advance, and blocked-advance behavior.
- [x] Added a directed XSim test that stalls destination traffic and proves a
      timestep cannot advance until all traffic drains.
- [x] Vivado 2025.2 XSim passed with
      `PASS: P04 packet router/barrier directed test completed successfully.`

### P04.3 — Two-endpoint P03-core integration shell — **Verified**

- [x] Instantiated two unchanged P03-compatible HLS compute endpoints.
- [x] Added resource-scaled physical backing memories while preserving the full
      logical-capacity contract.
- [x] Converted routed destination-axon packets into each endpoint's next-tick
      event list without adding an algorithmic timestep.
- [x] Added deterministic multicore Python/HLS and physical-vector generation.
- [x] Validated feed-forward, recurrence, simultaneous producers, fan-in, and
      local/remote multicast in the Python↔HLS differential corpus.
- [x] Validated forward and reversed legal packet-service orders.
- [x] Corrected the packet-memory streamer completion handshake after repeated
      timesteps exposed stale sticky `done` state.
- [x] Added a regression for HLS-ready-low startup after physical bring-up showed
      that pre-gating `ap_start` on `ap_ready` could deadlock the first tick.
- [x] Corrected controller XSim and the full P04 source preflight passed.

### P04.4 — K26 implementation/resource gate — **Verified**

- [x] Routed the integrated P04 shell at a requested 100 MHz.
- [x] Demonstrated a two-endpoint physical fixture using 49 BRAM tiles in the
      preconditioned implementation, far below the approximately 193 BRAM tiles
      required for two literal P03 full-memory shells.
- [x] Recorded the physical validation allocation separately from logical Loihi
      occupancy; implementation metrics report `logical_capacity_changed=0`.
- [x] Generated `.bit`, `.ltx`, checkpoint, timing, utilization, bus-skew, DRC,
      and methodology artifacts.
- [x] Diagnosed the board reset path with a reset-independent PL0 counter and
      direct observation of `peripheral_aresetn`.
- [x] Replaced the functional `proc_sys_reset` dependency with the
      source-controlled `p04_reset_conditioner` using active-high VIO reset
      request and a 16-PL-cycle synchronous release interval.
- [x] Promoted the conditioned project into the canonical `run_p04_impl.sh`
      output so `p04_two_core.bit/.ltx` are the same artifact class used by the
      normal physical harness.
- [x] Rebuilt the canonical conditioned implementation before final board
      acceptance.

### P04.5 — Physical multicore conformance — **Verified**

- [x] Programmed the K26 with the canonical P04 `.bit/.ltx` artifacts.
- [x] Verified reset release using the free-running heartbeat.
- [x] Passed physical write/read preflight for both endpoint memory fabrics.
- [x] Executed the two-timestep feed-forward corpus under both legal packet
      service priorities.
- [x] Executed the three-timestep recurrent local+remote multicast corpus under
      both legal packet service priorities.
- [x] Compared physical core state, trace data, packets, next-timestep events,
      spike counts, packet counts, local/remote traffic, barrier completion, and
      status/error observations against Python-generated expectations.
- [x] Verified nonzero physical cycle counts on every directed tick.
- [x] Archived the final accepted evidence under
      `hardware/evidence/p04_physical_20260929T211309Z/`.
- [x] Final result: `schema=p04-physical-conformance-v1`, `result=PASS`.

Accepted physical observations:

| Scenario | Reverse priority | Timestep | PL cycles | Local packets | Remote packets |
|---|---:|---:|---:|---:|---:|
| feed_forward | 0 | 0 | 28 | 0 | 1 |
| feed_forward | 0 | 1 | 21 | 0 | 0 |
| feed_forward | 1 | 0 | 28 | 0 | 1 |
| feed_forward | 1 | 1 | 21 | 0 | 0 |
| recurrent_multicast | 0 | 0 | 33 | 2 | 2 |
| recurrent_multicast | 0 | 1 | 39 | 2 | 2 |
| recurrent_multicast | 0 | 2 | 39 | 2 | 2 |
| recurrent_multicast | 1 | 0 | 33 | 2 | 2 |
| recurrent_multicast | 1 | 1 | 39 | 2 | 2 |
| recurrent_multicast | 1 | 2 | 39 | 2 | 2 |

The final heartbeat check observed `4,710,844 -> 7,448,013` across the reset
release interval before the harness proceeded into memory and compute testing.
These physical cycle counts are implementation observations for the directed
corpus, not native-Loihi timing claims.

## Required deliverables

- [x] Instantiate at least two logical compute endpoints in the integrated FPGA path.
- [x] Implement destination-core / destination-axon packet delivery.
- [x] Implement explicit local versus remote routing accounting.
- [x] Support simultaneous packet sources at the routing boundary.
- [x] Demonstrate fan-in and fanout through integrated compute endpoints.
- [x] Define and implement packet queue/backpressure behavior.
- [x] Implement quiescence/completion detection and timestep advancement.
- [x] Demonstrate cross-core recurrence without execution-order dependence.
- [x] Expose packet/core/timestep/barrier state in normalized software and
      physical differential validation.

## Required validation

- [x] Two-core feed-forward network through integrated compute endpoints.
- [x] Bidirectional/recurrent two-core network through integrated compute endpoints.
- [x] Multiple simultaneous packet producers.
- [x] Multicast to local and remote destinations through integrated compute endpoints.
- [x] Different legal packet-service orders produce identical normalized results.
- [x] A timestep cannot advance while current-timestep traffic remains pending.
- [x] Physical K26 execution matches the Python-directed corpus under both legal
      service priorities.

## Completion gate

**Complete.** Multicore hardware execution is deterministic at the normalized
architectural boundary and independent of the tested legal FPGA packet-service
ordering. P04.1-P04.5 are verified, including canonical physical K26
conformance and archived evidence.

**Next phase:** P05 — logical-core virtualization.

---

# P05 — Logical-core virtualization

**Status:** Complete  
**Started:** 2026-09-29  
**Completed:** 2026-09-29

## Goal

Support more logical Loihi-like cores than physically instantiated FPGA compute
engines while preserving visible architecture and logical limits.

P05 begins from the accepted P04 boundary: two physical compute endpoints,
destination-core/destination-axon packet routing, quiescence/barrier semantics,
normalized state/packet visibility, a physically verified reset/control path,
and a clear distinction between logical Loihi capacity and physical FPGA
allocation. P05 removes the P04 validation fixture's context-retention limitation
without changing those externally visible semantics.

The architecture contract is documented in
`docs/P05_VIRTUALIZATION_ARCHITECTURE.md`; the implementation decisions,
constraints, failures, and physical closure are recorded in
`docs/P05_INTEGRATION_CHALLENGES.md`.

## Sub-milestone progress

### P05.1 — Virtualization contract and software invariance — **Verified**

- [x] Added explicit separation between logical-core identity and physical-engine
      assignment.
- [x] Added deterministic logical-core scheduling and explicit dispatch records.
- [x] Added reporting for logical core count, physical engine count,
      virtualization ratio, and scheduling waves.
- [x] Kept physical-engine assignment out of normalized logical traces.
- [x] Ran the same three-core recurrent network with one, two, and three abstract
      physical engines and confirmed identical normalized traces.
- [x] Ran different legal logical-core service orders and packet-drain orders and
      confirmed identical normalized traces.
- [x] Confirmed logical capacity errors are raised before and independently of
      physical sharing.

### P05.2 — Full-context K26 virtualization shell — **Verified**

- [x] Reused one unchanged P03-compatible HLS compute engine.
- [x] Added three independently retained full logical-core context slots.
- [x] Moved full context retention to UltraRAM-backed shared memories while
      preserving the accepted P03 local address widths/depths.
- [x] Preserved logical core IDs in packets and added logical-ID-to-context-slot
      resolution in the controller.
- [x] Added double-buffered 4,096-entry event memories per context so early
      `t+1` traffic cannot overwrite unconsumed `t` events for later-serviced
      logical contexts.
- [x] Preserved the P04 lesson that HLS `ap_ready` is diagnostic only and must
      not gate the initial `ap_start` transaction.
- [x] Added directed RTL/controller regression coverage for forward and reverse
      three-context service order and event-bank rollover.
- [x] Fixed the P05 hardware-image test fixture to use the accepted P03 required
      saturating arithmetic profile rather than generic software defaults.
- [x] Vivado synthesis used exactly 47 URAM288 primitives, matching the first-pass
      packing estimate, plus 2 BRAM tiles and 2 DSPs.
- [x] Routed the canonical P05 shell at the requested 100 MHz with WNS
      `+0.588 ns` and WHS `+0.011 ns`.
- [x] Post-route utilization: 47/64 URAM288, 2/144 BRAM tiles, 5,062 LUTs,
      7,686 registers, and 2 DSPs.
- [x] Implementation metrics report `logical_contexts=3`,
      `physical_engines=1`, `double_buffered_events=1`, and
      `logical_capacity_changed=0`.

### P05.3 — Physical virtualization conformance — **Verified**

- [x] Programmed the K26 with the canonical P05 `.bit/.ltx` artifacts.
- [x] Verified reset release using the source-controlled synchronous reset path
      and free-running heartbeat.
- [x] Passed host read/write preflight at the final legal address of every full
      retained bank in all three context slots, including both event banks.
- [x] Verified nonexistent physical context slot 3 is rejected rather than
      aliased.
- [x] Executed a three-core ring using noncontiguous logical IDs 7, 42, and 99,
      proving logical identity is independent of physical context slot.
- [x] Executed recurrent local+remote fanout/fan-in traffic.
- [x] Ran both directed scenarios under forward and reverse legal logical-context
      service orders.
- [x] Verified event-bank selection flips only after the logical barrier advances.
- [x] Compared physical state, trace words, packet words, routed next-timestep
      events, event counts, logical/context identity, traffic counters, barrier
      state, HLS status, and memory/controller error flags against Python-generated
      expectations.
- [x] Verified nonzero physical cycle counts on every directed tick.
- [x] Archived the accepted evidence under
      `hardware/evidence/p05_physical_20260930T011850Z/`.
- [x] Final result: `schema=p05-physical-conformance-v1`, `result=PASS`.

Accepted physical observations:

| Scenario | Reverse service | Timestep | PL cycles | Local packets | Remote packets |
|---|---:|---:|---:|---:|---:|
| logical_id_ring | 0 | 0 | 56 | 0 | 1 |
| logical_id_ring | 0 | 1 | 56 | 0 | 1 |
| logical_id_ring | 0 | 2 | 56 | 0 | 1 |
| logical_id_ring | 0 | 3 | 56 | 0 | 1 |
| logical_id_ring | 1 | 0 | 56 | 0 | 1 |
| logical_id_ring | 1 | 1 | 56 | 0 | 1 |
| logical_id_ring | 1 | 2 | 56 | 0 | 1 |
| logical_id_ring | 1 | 3 | 56 | 0 | 1 |
| local_remote_fanin | 0 | 0 | 77 | 2 | 2 |
| local_remote_fanin | 0 | 1 | 100 | 3 | 3 |
| local_remote_fanin | 0 | 2 | 112 | 3 | 3 |
| local_remote_fanin | 1 | 0 | 77 | 2 | 2 |
| local_remote_fanin | 1 | 1 | 100 | 3 | 3 |
| local_remote_fanin | 1 | 2 | 112 | 3 | 3 |

The accepted heartbeat check observed `2,410,690 -> 5,146,953` before the
harness proceeded into full-depth memory and compute testing. These cycle counts
are synchronous FPGA implementation observations for the directed corpus, not
native-Loihi physical timing claims.

## Required deliverables

- [x] Separate logical-core state from physical execution-engine identity.
- [x] Store independent compartment/axon/synapse/routing state per logical core.
- [x] Add a deterministic scheduler for logical-core service.
- [x] Preserve logical per-core resource limits when memories are physically shared.
- [x] Report both logical core count and physical engine count.
- [x] Report physical FPGA occupancy separately from logical Loihi occupancy.
- [x] Maintain transparent logical-core-to-engine mapping.
- [x] Preserve the accepted P04 packet format, barrier contract, reset strategy,
      and host/debug observability unless a change is explicitly justified and
      regression-tested.

## Required validation

- [x] Run the same network with different physical-engine counts.
- [x] Run the same network with different legal logical-core service orders.
- [x] Confirm identical normalized logical state/spike/packet traces.
- [x] Confirm logical capacity errors cannot be bypassed by physical sharing.
- [x] Demonstrate more logical cores/contexts than simultaneously resident
      physical compute endpoints on the K26.

## Completion gate

**Complete.** Virtualization invariance is demonstrated at the normalized
architectural boundary. The software model produces identical logical results
across one-, two-, and three-engine schedules and different legal service/drain
orders; the physical K26 retains three full logical contexts and services them
with one compute engine while matching the Python-directed corpus under both
forward and reverse context-service orders.

**Next phase:** P06 — deterministic mapper/compiler.

---

# P06 — Deterministic mapper/compiler and deployment format

**Status:** Complete  
**Started:** 2026-09-29  
**Completed:** 2026-09-29

## Goal

Map trained networks onto modeled Loihi-like resources and emit one
deterministic deployment consumed by both Python and FPGA execution.

P06 takes the manually configured architecture accepted through P05 and adds a
single deterministic compiler boundary above it. High-level population and
projection specifications are compiled into the same `Deployment` logical-core
configuration consumed by Python and the accepted P05 FPGA image packer. No
second FPGA-specific mapping format is maintained.

The compiler contract is documented in `docs/P06_MAPPING_COMPILER.md`; the
implementation decisions and closure lessons are recorded in
`docs/P06_MAPPING_COMPILER_CHALLENGES.md`.

## Sub-milestone progress

### P06.1 — Network/deployment compiler contract — **Verified**

- [x] Added versioned `p06-network-v1` high-level network specifications.
- [x] Added versioned `v2.1-p06` compiled deployments around the validated P02
      logical `Deployment` boundary.
- [x] Added deterministic source and compiled-deployment SHA-256 fingerprints.
- [x] Added explicit population/neuron → logical-core/compartment placement
      records and external ingress-route metadata.
- [x] Added deterministic JSON round-trip and tamper detection.

### P06.2 — Deterministic placement/resource allocation — **Verified**

- [x] Added deterministic population splitting and logical-core allocation.
- [x] Added deterministic destination input-axon allocation and source output
      route construction.
- [x] Added normalized fanout-pattern sharing using reusable synapse templates
      plus destination `target_offset`, without claiming native Loihi SRAM
      compression.
- [x] Added hard compartment, input-axon, output-route, and synapse-memory
      capacity enforcement during mapping.
- [x] Added explicit mapping diagnostics naming core/resource/used/limit.
- [x] Added per-core occupancy/headroom, static local/remote traffic, placement,
      and sharing reports.
- [x] Added compiler regressions for reordered-equivalent inputs, population
      splitting, template sharing, external ingress, capacity rejection, and
      compiled Python execution.

### P06.3 — Shared Python/FPGA deployment and physical conformance — **Verified**

- [x] Added `CompiledDeployment.build_chip()` so Python executes the contained
      logical deployment directly.
- [x] Added `export_compiled_fpga_image()` so the same compiled deployment is
      exported through the accepted P05 full-context hardware packer.
- [x] Added CLI flow `network.json -> deployment.json + mapping report + FPGA
      report + load vectors` with fingerprint continuity checks.
- [x] Added a compiler-driven physical corpus and K26 conformance harness without
      changing or resynthesizing the accepted P05 compute architecture.
- [x] Loaded and read back the generated compiled context image before execution.
- [x] Executed mapped `pixel0`, `pixel1`, and `both_pixels` scenarios under both
      forward and reverse legal context-service orders.
- [x] Compared mapped physical state, trace words, packet words, next-timestep
      events, traffic counters, barrier state, HLS status, and error flags against
      expectations generated from the exact compiled deployment.
- [x] Verified the physical result records the same deployment fingerprint as the
      compiled JSON artifact.
- [x] Verified nonzero physical cycle counts on all 24 directed ticks.
- [x] Archived the accepted evidence under
      `hardware/evidence/p06_physical_20260930T014904Z/`.
- [x] Final result: `schema=p06-physical-mapped-deployment-v1`, `result=PASS`.

Accepted physical identity:

```text
source_fingerprint=8e5fb969a806aac8bdc82d1129fc8ee50b53aef8e053ee10b6e11bd9748a1383
deployment_fingerprint=32937f2fd8f861ac28f516509a054b03e6098c2c8a051512ad289fc3be49ea4b
logical_contexts=3
physical_engines=1
logical_capacity_changed=0
```

Accepted physical observations:

| Scenario | Reverse service | Timestep | PL cycles | Local packets | Remote packets |
|---|---:|---:|---:|---:|---:|
| pixel0 | 0 | 0 | 74 | 0 | 1 |
| pixel0 | 0 | 1 | 76 | 0 | 1 |
| pixel0 | 0 | 2 | 68 | 0 | 0 |
| pixel0 | 0 | 3 | 61 | 0 | 0 |
| pixel0 | 1 | 0 | 74 | 0 | 1 |
| pixel0 | 1 | 1 | 76 | 0 | 1 |
| pixel0 | 1 | 2 | 68 | 0 | 0 |
| pixel0 | 1 | 3 | 61 | 0 | 0 |
| pixel1 | 0 | 0 | 74 | 0 | 1 |
| pixel1 | 0 | 1 | 76 | 0 | 1 |
| pixel1 | 0 | 2 | 68 | 0 | 0 |
| pixel1 | 0 | 3 | 61 | 0 | 0 |
| pixel1 | 1 | 0 | 74 | 0 | 1 |
| pixel1 | 1 | 1 | 76 | 0 | 1 |
| pixel1 | 1 | 2 | 68 | 0 | 0 |
| pixel1 | 1 | 3 | 61 | 0 | 0 |
| both_pixels | 0 | 0 | 87 | 0 | 2 |
| both_pixels | 0 | 1 | 91 | 0 | 2 |
| both_pixels | 0 | 2 | 75 | 0 | 0 |
| both_pixels | 0 | 3 | 61 | 0 | 0 |
| both_pixels | 1 | 0 | 87 | 0 | 2 |
| both_pixels | 1 | 1 | 91 | 0 | 2 |
| both_pixels | 1 | 2 | 75 | 0 | 0 |
| both_pixels | 1 | 3 | 61 | 0 | 0 |

## Required deliverables

- [x] Finalize the machine-readable deployment schema.
- [x] Partition populations/compartments across logical cores.
- [x] Allocate input axons, synapse groups/lists, and output routes.
- [x] Implement supported connection sharing/compression or the explicit
      project-defined equivalent.
- [x] Enforce hard per-core limits during mapping.
- [x] Reject invalid mappings with explicit diagnostics.
- [x] Make mapping deterministic for a fixed network/configuration.
- [x] Report per-core use/headroom and expected traffic where meaningful.
- [x] Hash/version deployment artifacts.
- [x] Load the same deployment artifact into Python and FPGA paths.

## Completion gate

**Complete.** Networks can be mapped deterministically into inspectable,
resource-valid deployments without hand-editing FPGA-specific configuration.
The accepted physical test demonstrates the same versioned compiled deployment
feeding both Python expectations and FPGA context loading/execution while
preserving its fingerprint through the physical result.

**Next phase:** P07 — deeper mapped SNN validation.

---

# P07 — Deeper mapped multicore SNN validation

**Status:** Complete  
**Started:** 2026-09-29  
**Completed:** 2026-09-29

## Goal

Demonstrate that FPGA-v2 supports networks that genuinely exercise multicore
mapping, routing, sharing, and capacity constraints before final MNIST work.

The workload and validation contract are documented in
`docs/P07_DEEP_SNN_VALIDATION.md`; design decisions and closure lessons are
recorded in `docs/P07_DEEP_SNN_CHALLENGES.md`.

## Achieved deliverables

- [x] Built a deterministic six-layer feed-forward SNN with 12 neurons and four
      external input channels.
- [x] Defined the workload once in `src/loihi_twin_v2/workload_p07.py` and reused
      that source for tests, JSON generation, compiler analysis, physical-vector
      generation, and board execution.
- [x] Mapped the network entirely through the P06 compiler with four compartments
      per logical core, producing three logical cores with two layers per core.
- [x] Exercised both local and remote inter-layer routing in one mapped graph.
- [x] Exercised supported normalized fanout/template sharing on every feed-forward
      stage.
- [x] Recorded 28 expanded synaptic connections represented by six stored shared
      parameters (`4.666666666666667` expanded per stored parameter).
- [x] Added deterministic mapping/occupancy analysis and forward/reverse logical
      service-order invariance regressions.
- [x] Added an explicit mapping-capacity probe that rejects the same workload
      when mapper policy is limited to two logical cores.
- [x] Recorded the expected capacity diagnostic as
      `logical_core_capacity`, `required=3`, `limit=2`.
- [x] Reused the accepted P05 physical shell and P06 Hardware Manager checker so
      the P07 validation delta remained the deeper compiled workload rather than
      another FPGA-control implementation.
- [x] Compared Python and physical FPGA state, normalized trace words, packets,
      routed next-timestep events, local/remote traffic, barrier state, identity,
      status, and error observations.
- [x] Validated physical K26 execution under both forward and reverse legal
      logical-context service orders.
- [x] Preserved the accepted routed physical occupancy from the unchanged P05
      shell: 47/64 URAM288, 2/144 BRAM, 5,062 LUTs, 7,686 registers, and 2 DSPs.

## Accepted physical evidence

The accepted physical identity is:

```text
schema=p07-deep-mapped-snn-v1
source_fingerprint=4d11e473a427b153a23226bd3294d6a243292f14931d6d85f6705c9e85146b76
deployment_fingerprint=5e5a16062faa8d92d0077de56fcbd07ff74c602f96e52f98e25ccf49a4af34f9
layers=6
neurons=12
input_channels=4
logical_contexts=3
physical_engines=1
logical_capacity_changed=0
expanded_connections=28
stored_shared_parameters=6
capacity_probe_result=EXPECTED_REJECTION
capacity_probe_code=logical_core_capacity
capacity_probe_required=3
capacity_probe_limit=2
scenarios=3
physical_ticks=42
result=PASS
```

The three directed scenarios (`pixel0`, `pixel0_pixel2`, and `all_pixels`) each
executed seven algorithmic timesteps under both forward and reverse context
service order. All 42 directed physical ticks passed. The observed workload
traffic alternated local and remote transfers across the six-layer chain and
then reached quiescence as expected.

The reset-release heartbeat changed from `5,903,621` to `8,486,799` before the
physical workload proceeded. Tick costs ranged from 97 to 143 synchronous PL
cycles for the accepted corpus; these are FPGA implementation observations, not
native-Loihi timing claims.

The accepted evidence is archived under:

```text
hardware/evidence/p07_physical_20260930T022814Z/
```

## Required deliverables

- [x] Select/build a deeper feed-forward SNN with multiple mapped layers.
- [x] Map through the P06 compiler rather than manual placement.
- [x] Exercise multiple logical cores and inter-core traffic.
- [x] Exercise supported connection sharing/resource optimization.
- [x] Compare Python and FPGA normalized traces on representative cases.
- [x] Validate physical K26 execution.
- [x] Record logical occupancy, physical FPGA utilization, and capacity failures.

## Completion gate

**Complete.** A nontrivial six-layer SNN executes reproducibly through the
specification → mapper → Python → FPGA flow, exercises both local and remote
multicore traffic plus connection sharing and capacity rejection, and agrees at
the normalized architectural boundary across all 42 accepted physical ticks.

**Next phase:** P08 — NxTF-oriented deep MNIST comparison.

---

# P08 — NxTF-oriented deep MNIST comparison

**Status:** In progress  
**Started:** 2026-09-29

## Goal

Build a substantially deeper MNIST workload that exercises the new multicore
architecture and supports a defensible comparison with Rueckauer et al. NxTF.

## Required deliverables

- [ ] Select a deeper MNIST topology comparable in purpose/mapping pressure to
      the NxTF workload.
- [ ] Freeze data/preprocessing, training/conversion, neuron, weight, timestep,
      and decoder contracts.
- [ ] Map the network with the P06 compiler.
- [ ] Record logical placement/core count and per-resource occupancy.
- [ ] Record sharing/compression effectiveness and packet traffic.
- [ ] Validate Python-vs-FPGA inference behavior.
- [ ] Run the physical K26 workload.
- [ ] Measure/report accuracy, architectural cycles/latency, and FPGA resources.
- [ ] Record mapping failures/headroom where relevant.
- [ ] Build an explicit NxTF comparison table separating comparable from
      contextual/non-comparable quantities.

Energy claims remain out of scope unless a defensible workload-specific physical
measurement method is established.

## Completion gate

P08 is complete when the deep MNIST workload has been mapped, executed on the
K26, quantitatively characterized, and compared to NxTF under an explicitly
bounded comparison contract.

---

# Cross-phase architectural requirements

These requirements apply throughout P02-P08. Normative definitions and source
citations live in `docs/LOIHI1_TARGET_SPEC.md`.

## Priority-A requirements

The first complete v2 architecture must support:

- multiple logical neuromorphic cores;
- explicit per-core compartment, input-axon, synapse, and output-routing resources;
- Loihi-like hard capacity accounting;
- destination-core / destination-axon spike packets;
- explicit inter-core fanout and packet routing;
- deterministic placement and mapping;
- algorithmic timestep/quiescence barriers independent of FPGA clock cycles;
- convolution-oriented axon/synapse sharing or a clearly modeled equivalent;
- transparent configuration, state, packet, spike, and resource traces;
- deeper feed-forward SNN graphs; and
- one deterministic mapping/compiler layer used by both Python and FPGA.

## Digital-twin boundary

The project targets a **source-backed architectural digital twin**, not a
transistor-level clone.

Logical resources may be virtualized or time-multiplexed on the K26 only when:

- virtualization is explicit;
- architectural state remains inspectable;
- logical resource limits are enforced;
- packet/timestep ordering rules remain deterministic and documented;
- physical FPGA cycles are distinguished from algorithmic timesteps; and
- Python and FPGA implementations compare at the same normalized boundary.

Physical asynchronous-circuit equivalence is not required. FPGA-v2 is a
synchronous FPGA realization of source-backed event-driven architectural
semantics.

---

# Cross-phase verification policy

Every architectural addition should be validated at three levels whenever the
relevant implementation layer exists:

1. **Directed unit behavior** — minimal tests isolate one semantic rule.
2. **Mapped-network differential behavior** — Python and FPGA normalized traces
   agree across representative multicore networks.
3. **Physical application behavior** — a K26 deployment reproduces the golden
   workload result.

Hardware-only control assumptions must not be inferred solely from source-level
simulation. P04 specifically demonstrated that reset release and HLS transaction
startup can fail on the physical board despite passing software/HLS/RTL tests.
When practical, regressions should therefore preserve the hardware condition
that exposed the failure (for example, ready-low startup), and physical gates
should retain direct observability such as reset-independent clocks/heartbeats,
pollable completion counters, and archived artifact identities.

The normalized v2 trace boundary should expose, when practical:

```text
algorithmic timestep
logical core
architectural phase
packets in / packets out
axon expansion
synaptic contributions
compartment state before / after
spikes
local completion
barrier state
physical FPGA cycle
```

---

# Deferred fidelity extensions

## Priority B — later architectural fidelity

- richer dendritic/multi-compartment structures;
- programmable synaptic delays;
- broader native weight/compression formats;
- more detailed event scheduling/queue/congestion behavior when source-backed;
- richer configuration/state behavior; and
- more detailed asynchronous/quiescence modeling at the architectural level.

## Priority C — non-critical-path fidelity

- on-chip plasticity/learning engines;
- management-processor emulation;
- chip-to-chip routing;
- exact physical asynchronous circuit behavior; and
- undocumented implementation details unsupported by public evidence.

A feature with insufficient public evidence remains **unknown/not claimed**.

---

# Documentation and evidence structure

```text
Loihi_Digital_Twin/
├── v1/
│   ├── MILESTONES.md              historical M01-M13 development record
│   └── ...                        preserved implementation/evidence
│
└── v2/
    ├── LOIHI_TWIN_ROADMAP.md      active phase/status tracker
    ├── docs/
    │   ├── LOIHI1_TARGET_SPEC.md
    │   ├── P02_IMPLEMENTATION_NOTES.md
    │   ├── P02_DEPLOYMENT_SCHEMA.md
    │   ├── P03_INTEGRATION_CHALLENGES.md
    │   ├── P03_ONE_CORE_HARDWARE_BOUNDARY.md
    │   ├── P03_VIVADO_IMPLEMENTATION.md
    │   ├── P04_MULTICORE_ARCHITECTURE.md
    │   ├── P04_INTEGRATION_IMPLEMENTATION.md
    │   ├── P04_INTEGRATION_CHALLENGES.md
    │   ├── P05_VIRTUALIZATION_ARCHITECTURE.md
    │   ├── P05_INTEGRATION_CHALLENGES.md
    │   ├── P06_MAPPING_COMPILER.md
    │   ├── P06_MAPPING_COMPILER_CHALLENGES.md
    │   ├── P07_DEEP_SNN_VALIDATION.md
    │   └── P07_DEEP_SNN_CHALLENGES.md
    ├── src/loihi_twin_v2/         Python golden model + FPGA image tooling
    ├── hls/core_v2/               accepted P03-P07-compatible HLS compute core
    ├── rtl/                       v2 RTL integration/observability logic
    ├── vivado/                    source-controlled K26 build flows
    ├── hardware/                  physical programming/conformance flows
    │   └── evidence/              archived accepted physical evidence
    ├── tests/                     directed architecture/packing tests
    ├── scripts/                   phase validation tools
    └── examples/                  corpus generators and architecture examples

applications/
├── mnist_baseline/                preserved FPGA-v1 application
└── <future deep MNIST app>/       FPGA-v2 / NxTF-oriented workload
```

New FPGA-v2 implementation evidence belongs with v2 and should be referenced
from the corresponding roadmap phase. It must not be appended to preserved v1
milestone history.

`EXPERIMENTS.md` remains a repository-level collection of deferred/follow-on
studies and is not the active implementation tracker while this roadmap is in
progress.

---

# Advancement rule

Only one phase should normally be marked **In progress** at a time.

Before moving to the next phase:

1. mark completed deliverables in the active phase;
2. record the validation evidence needed by that phase;
3. verify its completion gate;
4. change that phase to **Complete** with its completion date; and
5. change the next phase from **Planned** to **In progress** with its start date.

P07 satisfied this rule on 2026-09-29 when the compiler-generated six-layer K26
physical evidence reported `result=PASS`, preserved the compiled-deployment
identity, and passed all 42 directed physical ticks; P08 is therefore the active
phase.
