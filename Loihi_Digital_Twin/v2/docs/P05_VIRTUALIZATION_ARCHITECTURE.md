# P05 Logical-Core Virtualization Architecture

## Purpose

P05 removes the P04 physical validation fixture's context-retention limitation
without changing the logical Loihi-like architecture. P04 proved two genuine
compute endpoints, routed packet delivery, recurrence, multicast, and the
algorithmic barrier on the K26, but used reduced physical memories because two
literal full P03 BRAM shells do not fit simultaneously.

P05 instead separates **logical core context** from **physical execution-engine
identity**. The first closure target retains three full logical-core contexts and
services them with one unchanged P03 HLS compute engine. Logical packets,
capacity checks, barrier participation, and normalized traces continue to use
logical core IDs.

This implements the project choice in `LOIHI1_TARGET_SPEC.md` section 14:
physical engines may be fewer than logical cores only when state remains
independent, logical capacities remain enforced, packet identities remain
logical, barriers are logical-core barriers, service order cannot alter
normalized results, and physical/logical resource counts are reported
separately.

## P05 sub-milestones

P05 is intentionally kept to three sub-milestones:

1. **P05.1 — Virtualization contract and invariance model.** Add a deterministic
   logical-core scheduler to the Python golden model and prove that normalized
   results do not depend on physical-engine count or legal service order.
2. **P05.2 — Full-context FPGA virtualization path.** Retain multiple independent
   full contexts in shared physical memory, schedule them through an unchanged
   P03 compute engine, preserve logical packet identity, and validate the RTL/HLS
   integration at source/simulation level.
3. **P05.3 — Routed K26 implementation and physical invariance.** Route the
   one-engine/three-context shell, demonstrate more logical contexts than
   physical engines on the board, and compare the overlapping two-core corpus
   against the accepted P04 two-engine result.

## Why one engine and three resident contexts

The accepted P03 retained image is 3,375,104 bits per core before P05 event
buffering. P04 demonstrated why duplicating that image in BRAM is not scalable:
the full P03 shell consumes 96.5 of 144 K26 BRAM tiles.

P05 moves retained logical context storage to UltraRAM and reuses one compute
engine. Three contexts are the first closure target because they are sufficient
to demonstrate `logical_core_count > physical_engine_count` while leaving useful
UltraRAM headroom for implementation uncertainty and routing.

The P05 context image adds a second full input-event buffer per logical core:

```text
P03 retained image                    3,375,104 bits/context
second 4096 x 32 event buffer           131,072 bits/context
P05 retained context                  3,506,176 bits/context
three-context raw storage            10,518,528 bits
```

Using the existing P03 bank widths/depths and UltraRAM288's 4096 x 72 geometry,
the first-pass three-context primitive estimate is:

| Bank | Logical organization across 3 contexts | Estimated URAM288 |
|---|---:|---:|
| config | 3072 x 128 | 2 |
| state | 3072 x 64 | 1 |
| axon | 12288 x 64 | 3 |
| synapse | 98304 x 64 | 24 |
| route descriptor | 3072 x 32 | 1 |
| routes | 12288 x 32 | 3 |
| input events A | 12288 x 32 | 3 |
| input events B | 12288 x 32 | 3 |
| trace | 3072 x 256 | 4 |
| packets | 12288 x 64 | 3 |
| **Total** | | **47 / 64** |

This is an implementation planning estimate, not an accepted routed utilization
claim. P05.3 must replace it with measured post-route evidence.

A four-context version would consume materially more UltraRAM and leave much
less routing headroom. It is therefore deferred until/unless the three-context
closure target shows enough physical margin.

## Logical context versus physical context slot

P05 introduces an explicit distinction:

```text
logical_core_id     architectural identity carried by packets/traces
context_slot        physical retained-memory location
physical_engine_id  compute engine currently servicing a context
```

These identities must never be conflated. A deployment may, for example, retain
logical cores `(7, 42, 99)` in physical context slots `(0, 1, 2)`. A packet from
logical core 7 to logical core 42 still carries destination core ID 42; the
controller resolves 42 to context slot 1 only at the physical storage boundary.

The first P05 metadata record is 64 bits per resident context:

```text
[6:0]    logical_core_id
[17:7]   compartment_count
[33:18]  synapse_count
[46:34]  route_count
[59:47]  initial_event_count
[63:60]  reserved = 0
```

Three records fit in one 192-bit control vector. The counts remain the full
logical P03 widths and are checked against the same P03/Loihi limits before a
tick may start.

## Shared full-context memory fabric

`rtl/p05_context_memory_fabric.v` retains the existing HLS local address widths:

- 1024 configuration words;
- 1024 state words;
- 4096 input axons;
- 32768 synapse entries;
- 1024 route descriptors;
- 4096 output routes;
- 4096 current input events;
- 4096 next input events;
- 1024 trace records; and
- 4096 output packets.

Every bank adds a physical `context_slot` dimension. The active HLS engine sees
exactly the same local address space as P03. Context selection is added outside
the HLS engine, so no logical address is truncated or aliased.

Host/debug access also carries a context slot. Host accesses are rejected while
the compute scheduler owns the memory, preserving the P03/P04 ownership rule.

## Why input events must be double buffered

P04 launched two HLS cores together, so both endpoints consumed their
current-timestep inputs before the routed next-timestep event lists became
architecturally visible.

A sequential virtualized engine changes that physical timing. Suppose logical
core 0 runs first and produces a packet for logical core 2 at `t+1`. If the
packet were immediately written over core 2's single input-event image, core 2
could incorrectly consume a next-timestep event when it later receives its turn
for timestep `t`.

P05 therefore retains two event buffers per context:

```text
current event bank  -> read by HLS for every logical core at timestep t
next event bank     -> receives every routed packet generated during timestep t
barrier advance     -> swap bank roles atomically for timestep t+1
```

The event-bank selector is global to the configured logical chip and may flip
only after all logical contexts are complete and all packet traffic has been
retained for the next boundary.

This double buffering is a physical implementation mechanism for preserving the
existing P02/P04 algorithmic causality rule; it is not a new logical Loihi
feature.

## Deterministic scheduler

The Python scheduler and first RTL controller use deterministic wave/slot
service. For one engine and three contexts the default order is:

```text
slot 0 -> slot 1 -> slot 2
```

The alternate legal order used for invariance testing is:

```text
slot 2 -> slot 1 -> slot 0
```

`service_reverse` changes only physical/logical service order. It does not alter
logical core IDs, packet fields, state ownership, or algorithmic time.

`ap_ready` is intentionally not a pre-start admission condition. P04 physical
bring-up proved that doing so creates a circular `ap_ctrl_hs` startup condition
on the real HLS block. Scheduler ownership, epoch state, host ownership, and
logical-capacity validity determine whether a transaction may start.

## Packet routing under one physical engine

The unchanged P03 HLS core writes its retained `packet_words` image. After
`ap_done`, the existing packet-memory streamer drains that image through an
explicit ready/valid holding queue. For each packet P05:

1. validates the P03 64-bit packet valid/reserved/timestep fields;
2. compares destination logical core ID against the three context metadata IDs;
3. resolves the destination to a physical context slot;
4. appends the destination axon ID to that context's **next** event buffer;
5. accounts local versus remote traffic using logical source/destination IDs;
6. marks the source logical core complete only after its packet stream drains.

Invalid packets are consumed after a sticky error is raised so malformed traffic
cannot deadlock the logical barrier. Legal traffic is retained exactly once.

## Logical barrier under virtualization

A physical HLS engine becoming idle does not mean an algorithmic timestep is
complete. P05 tracks completion per **logical context**.

The barrier advances only after:

- all three configured logical contexts have executed the current timestep;
- each context's retained packet image has been drained;
- no packet remains in the controller's holding queue; and
- every accepted packet has been written to the appropriate next-event context.

Only then does the controller:

- increment `current_timestep`;
- promote each `next_event_count` to `current_event_count`;
- clear next-event counts;
- atomically flip the event-bank selector; and
- emit `tick_done`.

## Golden-model virtualization invariance

`src/loihi_twin_v2/virtualization.py` wraps the existing `LogicalChip` without
moving architectural state into physical-engine objects. It adds an
implementation-only dispatch schedule and separate virtualization report.

The required P05.1 regression compares the same three-core recurrent ring under:

- one physical engine;
- two physical engines;
- three physical engines;
- multiple logical-core service permutations; and
- forward/reverse packet drain order.

The normalized `ChipTrace` must remain byte-for-byte/equality identical across
those schedules. Physical dispatch metadata is deliberately excluded from that
normalized logical trace.

## P05.3 physical acceptance plan

The first physical closure corpus should include two complementary checks:

1. **Three logical contexts / one physical engine.** A three-core recurrent ring
   proves that more logical contexts are retained and serviced than physical
   engines exist.
2. **P04 overlap invariance.** Re-run the accepted two-core feed-forward and
   recurrent/multicast behavior through the P05 one-engine path and compare the
   normalized results to the accepted P04 two-engine evidence. Physical cycle
   counts are expected to differ and are not part of normalized equality.

P05 is complete only after those board results are archived with the same
artifact/evidence discipline used for P03 and P04.
