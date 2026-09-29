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

> **P04 in progress — P04.4 verified; physical P04.5 conformance is active.**
>
> P04 started on 2026-09-28 from the accepted P03 baseline. P04.1 golden-model
> contract closure, P04.2 standalone router/barrier RTL, P04.3 two-endpoint
> P03-core integration, and P04.4 routed K26 implementation are now verified.
> The corrected repeated-timestep controller test and consolidated source
> preflight pass under Vivado/Vitis 2025.2, including feed-forward and
> recurrent/multicast Python↔HLS differential cases under forward and reversed
> legal service orders.
>
> The final integrated two-endpoint shell routes on the K26 at a requested
> 100 MHz with WNS `+0.987 ns` and WHS `+0.010 ns`, using `7,065` CLB LUTs,
> `9,999` CLB registers, `49 / 144` BRAM tiles, `0` URAM, and `4` DSPs. All
> reported bus-skew constraints meet timing; the smallest reported bus-skew
> slack is `+9.517 ns`. The final routed build has no reported `ERROR:` or
> `CRITICAL WARNING:` diagnostics. The KV260 board preset resolves
> `proc_sys_reset/C_EXT_RESET_HIGH=1`; the build now verifies that read-only
> board-resolved active-high polarity explicitly, and the physical harness uses
> the matching VIO reset sequence. The emitted metrics explicitly record
> `logical_capacity_changed=0`.
>
> The accepted P03 shell occupies 96.5 of 144 K26 BRAM tiles, so blindly
> duplicating two full-capacity P03 physical memory shells would require about
> 193 BRAM tiles before adding any router/barrier storage. P04 therefore keeps
> all logical Loihi capacities unchanged while using a **resource-scaled physical
> validation allocation** for the directed two-endpoint corpus. This is a
> physical test-shell choice only; it is not a smaller logical core and it is
> not transparent core virtualization. P05 remains responsible for retaining
> and scheduling multiple independent full logical-core contexts on fewer
> physical resources.

---

## Phase summary

| ID | Phase | Status | Started | Completed |
|---|---|---|---|---|
| P00 | Preserve and freeze FPGA-v1 baseline | Complete | 2026-09 | 2026-09-25 |
| P01 | Define Loihi-1 target and establish v2 project structure | Complete | 2026-09-28 | 2026-09-28 |
| P02 | Build separate Python manycore golden model | Complete | 2026-09-28 | 2026-09-28 |
| P03 | Implement and validate one FPGA-v2 logical core | Complete | 2026-09-28 | 2026-09-28 |
| P04 | Add multicore packet routing and timestep/barrier semantics | In progress | 2026-09-28 | — |
| P05 | Add logical-core virtualization | Planned | — | — |
| P06 | Build deterministic mapper/compiler and deployment format | Planned | — | — |
| P07 | Validate deeper mapped multicore SNNs | Planned | — | — |
| P08 | Build and compare NxTF-oriented deep MNIST workload | Planned | — | — |

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
- [x] Working tree remained clean after validation.

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

## P03 HLS implementation findings

The first HLS gate passed the five-timestep Python/HLS C and C/RTL differential
corpus plus runtime integrity checks. At a 10 ns target the HLS estimate was
8.785 ns with 1.20 ns uncertainty, so the estimate left essentially no
uncertainty-adjusted margin. The later full-capacity routed Vivado shell closed
100 MHz with WNS `+1.148 ns`, showing that the HLS estimate was conservative for
the integrated physical design. HLS reported a pathological maximum of
272,664,582 cycles per tick because the maximum-capacity event-by-synapse
traversal is fully serialized; this remains an upper capacity bound rather than
a representative workload latency.

The external-memory integration required several iterations. Native BMG
instances silently resolved all requested depths to 2,048 words, so the physical
shell was moved to source-controlled fixed-depth `xpm_memory_tdpram` banks. The
standalone nine-bank fabric synthesized to `94.5` BRAM-tile equivalents, and the
complete HLS + memory shell routed using `96.5 / 144` BRAM tiles. The 32,768 x 64
synapse bank alone occupies 57 RAMB36E2 primitives. This challenge and its
resolution are documented in `docs/P03_INTEGRATION_CHALLENGES.md`.

Board bring-up additionally exposed two control/safety issues before closure.
The VIO-driven reset path initially used the wrong external-reset polarity, and
the first run monitor incorrectly pre-gated `ap_start` on `ap_ready`, creating a
circular `ap_ctrl_hs` condition. Both were corrected and captured in the P03
challenge log. The widened 32-bit event path was also hardened so reserved bits
`[31:12]` are rejected before any axon-table lookup.

## Accepted routed implementation evidence

- [x] Full fixed-depth XPM one-core shell routed on `xck26-sfvc784-2LV-c`.
- [x] 100 MHz setup timing closed: WNS `+1.148 ns`, zero failing endpoints.
- [x] 100 MHz hold timing closed: WHS `+0.010 ns`, zero failing endpoints.
- [x] Bus-skew reporting passed for the routed design.
- [x] Complete utilization recorded: `3,545` LUTs, `5,607` registers,
      `96.5` Block RAM tiles, `0` URAM, and `2` DSPs.
- [x] Primitive-level evidence reconciles the standalone 94.5-tile external
      fabric with the full 96.5-tile shell; the extra two BRAM tiles are the HLS
      local accumulator memory.
- [x] Keep the all-BRAM XPM shell as the transparent P03 reference baseline.
      Moving the synapse bank to UltraRAM is deferred as a P04/P05 scaling
      optimization rather than required for P03 correctness.

## Accepted physical-conformance evidence

- [x] Added a transport-neutral nine-bank host/debug bridge and compute/host
      arbitration.
- [x] Hardened host completion for VIO/JTAG by making `ack`, `rvalid`, and error
      state pollable rather than one-PL-cycle-only observations.
- [x] Added a completed-run counter and a proper `ap_ctrl_hs` start handshake for
      deterministic physical tick control.
- [x] Added deterministic physical-vector generation from the same Python
      configuration used by the HLS differential corpus.
- [x] Added a Vivado Hardware Manager/VIO harness that programs the K26,
      preflights read/write access to all nine banks, executes all five directed
      timesteps, and compares physical state/trace/packet results against Python.
- [x] Extended the implementation flow to emit `.bit` and `.ltx` artifacts.
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

**Status:** In progress  
**Started:** 2026-09-28

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

Five approaches were considered:

1. **Duplicate two full P03 memory shells.** Rejected because the measured BRAM
   requirement exceeds the K26 before multicore transport is added.
2. **Reduce the logical core capacities.** Rejected because FPGA fit must not
   redefine the architecture being modeled.
3. **Immediately move the large memories into URAM or external DDR.** Kept as a
   later scaling option, but rejected as the first P04 step because it would
   make routing/barrier validation depend on a new memory subsystem.
4. **Immediately time-multiplex several full logical contexts through one
   physical engine.** Rejected for P04 because that is the explicit P05
   virtualization problem and would collapse the roadmap boundary.
5. **Use two unchanged P03-compatible compute endpoints with physical backing
   memories sized only for the directed P04 validation deployment.** Accepted.
   This provides genuine simultaneous endpoint/routing behavior while clearly
   reporting that the test shell is not capable of retaining two maximally
   populated logical cores at once.

The accepted option is therefore a **resource-scaled physical validation
allocation**. It is intentionally analogous to using a smaller test fixture
around the same processor interface: the logical architecture and its capacity
checks remain full-sized in the specification/Python model, while the P04 FPGA
fixture only retains addresses exercised by its directed corpus. P05 will later
replace this fixture limitation with transparent logical-context storage and
scheduling; the P04 packet format, router, barrier invariant, and normalized
trace boundary are designed to remain reusable when that happens.

The complete rationale and interface contract are recorded in
`docs/P04_MULTICORE_ARCHITECTURE.md`.

## Sub-milestone progress

### P04.1 — Golden-model multicore contract closure — **Verified**

- [x] Added explicit `external` / `local` / `remote` route-scope accounting.
- [x] Added simultaneous remote producers and fan-in regression coverage.
- [x] Added local+remote multicast regression coverage.
- [x] Preserved feed-forward, recurrence, barrier blocking, and legal
      service-order invariance behavior.
- [x] Targeted multicore pytest passed locally on 2026-09-28.
- [x] Full v2 pytest suite passed locally after the P04.1 changes.

### P04.2 — Standalone packet-router/barrier RTL — **Verified**

- [x] Added independent producer capture slots so simultaneous source assertions
      are retained without depending on arbitration priority.
- [x] Added deterministic arbitration with a reversible legal service priority.
- [x] Added per-destination FIFOs with explicit ready/valid backpressure.
- [x] Added P03 packet valid/destination/target-timestep integrity checks.
- [x] Added local/remote traffic counters.
- [x] Added per-core completion latching, in-flight accounting, `can_advance`,
      accepted advance, and blocked-advance behavior.
- [x] Added a directed XSim test that stalls destination traffic and proves a
      timestep cannot advance until all traffic drains.
- [x] Vivado 2025.2 XSim gate passed locally on 2026-09-28 with
      `PASS: P04 packet router/barrier directed test completed successfully.`

### P04.3 — Two-endpoint P03-core integration shell — **Verified**

- [x] Instantiated two unchanged P03-compatible HLS compute endpoints in the
      integrated Vivado shell.
- [x] Added explicitly resource-scaled physical backing memories for the
      directed corpus while preserving the full logical-capacity contract.
- [x] Converted delivered destination-axon packets into each endpoint's next-tick
      input-event list without introducing an extra algorithmic timestep.
- [x] Added deterministic multicore Python/HLS and physical-vector generation.
- [x] Validated feed-forward, recurrence, simultaneous producers, fan-in, and
      local/remote multicast in the two-core Python↔HLS differential corpus.
- [x] Validated both forward and reversed legal packet-service orders.
- [x] Corrected the packet-memory streamer completion handshake after the first
      repeated-timestep controller run exposed a stale sticky `done` condition.
- [x] Corrected controller XSim passed on 2026-09-29 with no `FAIL:` diagnostics.
- [x] Full P04 source preflight passed after the correction.
- [x] Integrated two-endpoint synthesis completed successfully on the K26 target.

### P04.4 — K26 implementation/resource gate — **Verified**

- [x] Routed the integrated P04 shell at a requested 100 MHz.
- [x] Closed routed setup timing with WNS `+0.987 ns`.
- [x] Closed routed hold timing with WHS `+0.010 ns`.
- [x] Recorded routed utilization: `7,065` CLB LUTs, `9,999` CLB registers,
      `49 / 144` BRAM tiles, `0` URAM, and `4` DSPs.
- [x] Recorded the physical validation allocation separately from logical Loihi
      occupancy; routed metrics report `logical_capacity_changed=0`.
- [x] Generated routed `.bit`, `.ltx`, checkpoint, timing, utilization, bus-skew,
      DRC, and methodology artifacts.
- [x] Replaced the invalid write to read-only `proc_sys_reset/C_EXT_RESET_HIGH`
      with explicit board-preset readback; the accepted KV260 build reports
      `C_EXT_RESET_HIGH=1` and the physical harness now uses active-high reset.
- [x] Final routed build completed with no reported errors/critical warnings and
      all reported bus-skew constraints met; minimum reported bus-skew slack was
      `+9.517 ns`.

The resource result confirms the P04 memory decision: two genuine compute
engines plus routing/control fit using 49 BRAM tiles rather than the roughly 193
BRAM tiles that two literal full-capacity P03 memory shells would require. This
is a physical validation-shell result, not a claim that two maximally populated
logical cores are simultaneously resident; P05 remains responsible for that
transparent context-storage problem.

### P04.5 — Physical multicore conformance — **In progress**

- [ ] Execute the directed multicore corpus on the K26.
- [ ] Compare core state, packets, barrier state, and status to Python.
- [ ] Re-run with an alternate legal packet-service priority where supported.
- [ ] Archive the physical result, generated vectors, run log, routed reports,
      and bitstream/debug-probe SHA-256 identities under `hardware/evidence/`.

## Required deliverables

- [x] Instantiate or schedule at least two logical cores in the integrated FPGA path.
- [x] Implement destination-core / destination-axon packet delivery in the standalone RTL fabric.
- [x] Implement explicit local versus remote routing accounting.
- [x] Support simultaneous packet sources at the routing boundary.
- [x] Demonstrate fan-in and fanout through integrated compute endpoints in the
      source-level Python↔HLS differential corpus.
- [x] Define and implement explicit packet queue/backpressure behavior.
- [x] Implement quiescence/completion detection and timestep advancement.
- [x] Demonstrate cross-core recurrence without execution-order dependence in
      the integrated source-level differential corpus.
- [x] Expose packet/core/timestep/barrier state in normalized software traces;
      physical FPGA trace comparison remains the P04.5 gate.

## Required validation

- [x] Two-core feed-forward network through integrated compute endpoints.
- [x] Bidirectional/recurrent two-core network through integrated compute endpoints.
- [x] Multiple simultaneous packet producers.
- [x] Multicast to local and remote destinations through integrated compute endpoints.
- [x] Different legal packet-service orders produce identical source-level
      normalized results.
- [x] A timestep cannot advance while current-timestep traffic remains pending.

## Completion gate

P04 is complete when multicore hardware execution is deterministic at the
normalized architectural boundary and independent of incidental FPGA service
ordering. P04.1-P04.4 are verified. The remaining gate is P04.5: physical K26
conformance against the Python-generated directed corpus under both legal packet
service priorities.

**Next phase:** P05 — logical-core virtualization.

---

# P05 — Logical-core virtualization

**Status:** Planned

## Goal

Support more logical Loihi-like cores than physically instantiated FPGA compute
engines while preserving visible architecture and logical limits.

## Required deliverables

- [ ] Separate logical-core state from physical execution-engine identity.
- [ ] Store independent compartment/axon/synapse/routing state per logical core.
- [ ] Add a deterministic scheduler for logical-core service.
- [ ] Preserve logical per-core resource limits when memories are physically shared.
- [ ] Report both logical core count and physical engine count.
- [ ] Report physical FPGA occupancy separately from logical Loihi occupancy.
- [ ] Maintain transparent logical-core-to-engine mapping.

## Required validation

- [ ] Run the same network with different physical-engine counts.
- [ ] Run the same network with different legal logical-core service orders.
- [ ] Confirm identical normalized logical state/spike/packet traces.
- [ ] Confirm logical capacity errors cannot be bypassed by physical sharing.

## Completion gate

P05 is complete when **virtualization invariance** is demonstrated.

**Next phase:** P06 — deterministic mapper/compiler.

---

# P06 — Deterministic mapper/compiler and deployment format

**Status:** Planned

## Goal

Map trained networks onto modeled Loihi-like resources and emit one
deterministic deployment consumed by both Python and FPGA execution.

## Required deliverables

- [ ] Finalize the machine-readable deployment schema.
- [ ] Partition populations/compartments across logical cores.
- [ ] Allocate input axons, synapse groups/lists, and output routes.
- [ ] Implement supported connection sharing/compression or the explicit
      project-defined equivalent.
- [ ] Enforce hard per-core limits during mapping.
- [ ] Reject invalid mappings with explicit diagnostics.
- [ ] Make mapping deterministic for a fixed network/configuration.
- [ ] Report per-core use/headroom and expected traffic where meaningful.
- [ ] Hash/version deployment artifacts.
- [ ] Load the same deployment artifact into Python and FPGA paths.

## Completion gate

P06 is complete when networks can be mapped deterministically into inspectable,
resource-valid deployments without hand-editing FPGA-specific configuration.

**Next phase:** P07 — deeper mapped SNN validation.

---

# P07 — Deeper mapped multicore SNN validation

**Status:** Planned

## Goal

Demonstrate that FPGA-v2 supports networks that genuinely exercise multicore
mapping, routing, sharing, and capacity constraints before final MNIST work.

## Required deliverables

- [ ] Select/build a deeper feed-forward SNN with multiple mapped layers.
- [ ] Map through the P06 compiler rather than manual placement.
- [ ] Exercise multiple logical cores and inter-core traffic.
- [ ] Exercise supported connection sharing/resource optimization.
- [ ] Compare Python and FPGA normalized traces on representative cases.
- [ ] Validate physical K26 execution.
- [ ] Record logical occupancy, physical FPGA utilization, and capacity failures.

## Completion gate

P07 is complete when a nontrivial deeper SNN executes reproducibly through the
specification → mapper → Python → FPGA flow and agrees at the normalized
architectural boundary.

**Next phase:** P08 — NxTF-oriented deep MNIST comparison.

---

# P08 — NxTF-oriented deep MNIST comparison

**Status:** Planned

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
    │   └── P04_MULTICORE_ARCHITECTURE.md
    ├── src/loihi_twin_v2/         Python golden model + FPGA image tooling
    ├── hls/core_v2/               P03 one-core HLS source and packaging flow
    ├── rtl/                       v2 RTL integration/observability logic
    ├── vivado/                    source-controlled K26 build flows
    ├── hardware/                  physical programming/conformance flows
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

This keeps v2 driven by an explicit source-backed contract and makes project
status recoverable directly from this file without reconstructing intent from
commit history or conversation context.
