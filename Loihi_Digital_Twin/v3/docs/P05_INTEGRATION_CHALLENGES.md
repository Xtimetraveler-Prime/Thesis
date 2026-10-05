# P05 Integration Challenges and Closure

## Purpose

This document records the main implementation decisions, failures, constraints,
and verification results encountered while adding logical-core virtualization to
FPGA-v2. It complements `P05_VIRTUALIZATION_ARCHITECTURE.md` by focusing on the
engineering path from the accepted P04 boundary to the physically validated P05
K26 implementation.

P05 completed the transition from P04's two resource-scaled physical endpoint
fixtures to independently retained full logical-core contexts serviced by fewer
physical compute engines.

## 1. Why P04 could not simply be scaled by replication

P03 established that one literal full-capacity logical-core shell consumed about
96.5 of the K26's 144 BRAM tiles. P04 therefore used two genuine compute
endpoints with reduced physical validation memories while preserving the full
logical-capacity contract in software/specification.

That approach was correct for validating multicore routing, but it did not solve
the later requirement that multiple full logical contexts be retained while the
number of physical compute engines is smaller than the logical core count.

P05 therefore changed the implementation strategy rather than shrinking logical
resources further:

- keep the accepted P03 HLS compute engine unchanged;
- retain full local address spaces for every logical context;
- store logical-core state independently from physical execution-engine state;
- time-multiplex one physical compute engine across multiple retained contexts;
- keep logical core IDs in architectural packets and traces;
- use physical context slots only as local storage/scheduling identifiers.

## 2. Choosing three retained contexts and one physical engine

The first P05 hardware target uses three full retained logical contexts serviced
by one physical P03-compatible HLS engine. Three contexts were chosen because
this is the smallest hardware configuration that clearly demonstrates
`logical_core_count > physical_engine_count` while still leaving useful K26
resource margin.

The initial packing estimate predicted 47 UltraRAM288 primitives for three
contexts when the full P03 memory image is retained and input events are double
buffered. Vivado 2025.2 synthesis matched that estimate exactly:

- URAM288: 47 / 64 (73.44%)
- BRAM tiles: 2 / 144 (1.39%)
- CLB LUTs: 4,993 (4.26%)
- CLB registers: 6,945 (2.96%)
- DSPs: 2

Post-route utilization remained 47 URAM and 2 BRAM tiles. Routed logic used
5,062 LUTs and 7,686 registers.

This result was important because it showed that full retained contexts could be
moved out of the BRAM-heavy P03/P04 replication model and into a physically
viable K26 UltraRAM organization.

## 3. Context identity must remain separate from logical core identity

P05 uses context slots 0, 1, and 2 as physical storage locations. They are not
architectural core IDs.

The hardware-image contract therefore stores an explicit logical core ID in each
context's metadata. Packets continue to carry logical destination-core IDs, and
the controller resolves those IDs to retained context slots when routing next-
timestep events.

The physical validation corpus deliberately uses noncontiguous logical IDs 7,
42, and 99 in the `logical_id_ring` scenario. This prevents a hidden assumption
that logical ID equals physical slot from passing accidentally.

## 4. Sequential service requires double-buffered input events

P04's two compute endpoints could retain their own current-timestep input event
lists while both endpoints were being evaluated. P05 instead services logical
contexts sequentially with one engine.

That introduces a specific hazard: an early-serviced logical context can emit a
packet targeting timestep `t+1` for a context that has not yet consumed its
`t` input events. If routed output were written into the same event memory, the
next-timestep event could overwrite current-timestep input before that later
context executes.

P05 therefore uses two full input-event banks per retained logical context:

- one bank is read by HLS for the current algorithmic timestep;
- routed packets are appended to the opposite bank;
- the controller flips the selected read bank only after all retained logical
  contexts complete and the timestep barrier advances.

The physical conformance harness verifies the bank flip after every directed
algorithmic timestep and reads the newly selected bank back through the host
interface.

## 5. Preserve the P04 HLS transaction-start lesson

P04 physical bring-up proved that `ap_ready` from the non-pipelined
`ap_ctrl_hs` HLS block must not be treated as an idle-before-start indication.
Doing so creates a circular dependency in which the controller waits for
`ap_ready` while the HLS core waits for `ap_start`.

P05 keeps `ap_ready` as an observation only. Initial transaction admission is
based on controller idle state, epoch validity, host ownership, and metadata
validity. The directed P05 controller regression intentionally holds HLS ready
low before start so the P04 failure mode cannot silently reappear.

## 6. Hardware-image test fixture arithmetic mismatch

The first P05 source preflight failed three hardware-image tests before any RTL
or Vivado work was implicated. The new tests created `LogicalCoreConfig` objects
with the generic software arithmetic default, but the P05 hardware exporter
correctly reuses the accepted P03 hardware packing contract, which requires
signed 24-bit saturating arithmetic.

The tests were corrected to use `P03_REQUIRED_ARITHMETIC` explicitly. No
architecture or hardware behavior changed. This preserved the rule that P05
virtualizes the accepted compute engine rather than silently changing neuron
arithmetic.

## 7. Full-depth memory validation is part of the physical gate

P05 must prove more than a small directed workload fitting into the low addresses
of each memory. The physical harness therefore performs host write/read checks at
the final legal address of every retained full-depth context bank for all three
physical context slots, including both event buffers.

The gate checks full retained depth for:

- compartment configuration/state/trace memories;
- 4,096 input axons;
- 32,768 HLS synapse entries;
- 4,096 route entries;
- 4,096 input events in each event bank;
- 4,096 output packet entries.

It also verifies that physical context slot 3 is rejected rather than aliased to
a retained context.

The accepted board run printed:

`P05 full-context memory preflight passed for all three retained contexts`

This is the physical evidence that distinguishes P05 from the smaller P04
validation fixture.

## 8. Routed implementation closure

The canonical P05 implementation closes the requested 100 MHz PL clock with:

- WNS: +0.588 ns
- WHS: +0.011 ns
- URAM288: 47 / 64 (73.44%)
- BRAM tiles: 2 / 144 (1.39%)
- CLB LUTs: 5,062 (4.32%)
- CLB registers: 7,686 (3.28%)
- DSPs: 2

The route wrapper rejects negative WNS or WHS, so successful artifact generation
alone is not enough to pass the P05 implementation gate.

The reset/control path reuses the P04-proven source-controlled synchronous reset
conditioner instead of reintroducing the earlier `proc_sys_reset` dependency.

## 9. Accepted physical virtualization conformance

The accepted physical run is archived locally under:

`hardware/evidence/p05_physical_20260930T011850Z/`

The result record reports:

- schema: `p05-physical-conformance-v1`
- device: `xck26_0`
- logical contexts: 3
- physical engines: 1
- virtualization ratio: 3.0
- full logical context depths: enabled
- double-buffered events: enabled
- logical capacity changed: 0
- scenarios: 2
- result: `PASS`

The reset-release heartbeat advanced from 2,410,690 to 5,146,953 before memory
or compute testing began.

### `logical_id_ring`

This scenario uses logical core IDs 7, 42, and 99 and validates logical identity
independently of context slots. Four timesteps were run under each legal context
service direction. Every tick completed in 56 PL cycles and produced one remote
packet.

### `local_remote_fanin`

This scenario exercises local recurrence together with remote fanout/fan-in.
Three timesteps were run under each legal context service direction.

Observed cycles and traffic were:

| Reverse service | Timestep | PL cycles | Local packets | Remote packets |
|---:|---:|---:|---:|---:|
| 0 | 0 | 77 | 2 | 2 |
| 0 | 1 | 100 | 3 | 3 |
| 0 | 2 | 112 | 3 | 3 |
| 1 | 0 | 77 | 2 | 2 |
| 1 | 1 | 100 | 3 | 3 |
| 1 | 2 | 112 | 3 | 3 |

Across both scenarios the harness compared Python expectations against physical
state, trace words, packet words, routed next-timestep events, event counts,
logical/context identity, traffic counts, barrier completion, error/status
signals, and event-bank selection.

All 14 directed physical ticks passed.

## 10. What P05 proves and does not prove

P05 proves that the K26 implementation can retain more full logical-core
contexts than it has physical compute engines and can time-multiplex the accepted
compute engine without changing the tested normalized architecture behavior.

The software validation also runs the same logical network under one, two, and
three abstract physical-engine schedules and under different legal logical-core
service and packet-drain orders. The normalized logical traces are invariant,
and logical capacity validation occurs independently of physical sharing.

P05 does not claim native Loihi physical timing, native asynchronous circuitry,
or an unlimited number of simultaneously retained full contexts. The first
physical profile retains three full contexts because of K26 UltraRAM capacity.
Later mapping/compiler work can build on this explicit logical/physical boundary
without redefining logical Loihi capacities.
