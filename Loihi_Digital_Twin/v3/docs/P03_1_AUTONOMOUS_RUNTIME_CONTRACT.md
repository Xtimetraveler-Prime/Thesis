# P03.1 — Autonomous PS-Resident Runtime Contract

**Status:** Verification candidate  
**Phase:** P03 — Autonomous PS-resident runtime  
**Branch:** `agent/v3-p03-autonomous-runtime`  
**Date drafted:** 2026-10-06

## 1. Purpose

P03.1 freezes the board-local control semantics that the Cortex-A53 runtime must
implement before production PS software or a new MMIO shell is written.

P02 proved DDR-backed virtualization physically:

```text
5 logical cores
3 resident context slots
1 physical HLS engine
K26 DDR authoritative for non-resident contexts
35 physical dispatches
7 barriers
30 routed packets
all final DDR records byte-exact to golden
```

P03 changes **control ownership**, not the logical Loihi-like architecture.

The research question is:

> Can the KV260 execute the accepted virtualized architecture after launch
> without the external PC participating in logical-core scheduling, page
> replacement, packet routing, or timestep/barrier control?

## 2. Accepted starting point

P03 inherits these accepted P02 facts:

- fixed 512 KiB DDR record per logical core;
- 128 reserved logical-core IDs;
- 64 MiB backing window at
  `0x4000_0000..0x43FF_FFFF`;
- 428 KiB full resident payload;
- 104 KiB mutable-only page-out;
- three full resident URAM context slots;
- one physical HLS engine;
- PL page walker + range guard + 128-bit burst adapter + HP0 DDR path;
- CURRENT/NEXT event-bank separation;
- logical destination IDs independent of residency;
- final P02 page/debug response-latching fix.

Accepted P02 final physical bitstream identity:

```text
0d96ae6af0cc313ccbd8f9c802aeb0c8c7946bfeabaca3152ef5c7b9d2b23f26
```

P03 is allowed to replace the VIO/JTAG control plane. It must not silently
change the accepted P02 data-plane semantics.

## 3. Autonomy boundary

The external PC may:

- build the bitstream and PS software;
- program/boot the board;
- provision a compiled deployment and input buffers before a run;
- issue one start/launch action;
- passively poll or retrieve DONE/ERROR/results;
- perform optional stopped-board debug.

After the board-local run is started, the PC must **not** participate in:

- logical-core service order;
- resident-slot selection;
- page-victim selection;
- page command issue;
- dispatch command issue;
- packet interpretation;
- destination event insertion;
- event-count bookkeeping;
- global barrier decisions;
- event-bank swap;
- timestep advancement.

Passive observation must not be required for forward progress.

## 4. First PS software target

The first implementation target is a Vitis-built Cortex-A53 standalone
application.

Standalone is preferred for first bring-up because it gives explicit control of:

- linker memory placement;
- the 64 MiB P02 backing-window reservation;
- cache maintenance;
- MMIO ordering;
- the ARM generic/global timer;
- interrupt or polling behavior;
- ownership of the run loop.

Linux support may be added later without changing this contract.

## 5. Runtime state machine

The normative first runtime sequence is:

```text
RESET
  -> LOAD_DEPLOYMENT
  -> INITIALIZE_BACKING
  -> INITIALIZE_RESIDENT_SET
  -> LOAD_INPUT
  -> TIMESTEP_BEGIN
       -> SELECT_LOGICAL_CORE
       -> ENSURE_RESIDENT
            -> resident hit
                 -> DISPATCH_CORE
            -> resident miss / clean victim
                 -> LOAD_REQUESTED
                 -> DISPATCH_CORE
            -> resident miss / dirty victim
                 -> SAVE_VICTIM
                 -> LOAD_REQUESTED
                 -> DISPATCH_CORE
       -> DRAIN_AND_ROUTE_PACKETS
       -> MARK_LOGICAL_CORE_COMPLETE
       -> SELECT_LOGICAL_CORE ... until all configured cores complete
  -> BARRIER_CHECK
       -> SWAP_EVENT_BANKS
       -> ADVANCE_TIMESTEP
  -> TIMESTEP_BEGIN ... or FINALIZE
  -> WRITE_RESULT
  -> DONE
```

Any fail-closed condition transitions to:

```text
ERROR
```

ERROR does not automatically resume execution.

The executable reference is:

```text
src/loihi_twin_v2/runtime_v3.py
```

This is a contract model, not the production A53 runtime.

## 6. Logical-core service policy

The initial P03 implementation uses a deterministic service order derived from
the compiled deployment.

For the first implementation:

- configured logical cores are serviced in compiled logical-core order;
- a logical core is dispatched at most once per algorithmic timestep unless a
  later accepted execution model explicitly requires multiple phases;
- the initial resident set is the first up-to-three logical cores in that order;
- replacement uses deterministic round-robin victim selection.

These are implementation policies, not source-backed Loihi scheduling claims.

Later policies are permitted only if normalized architecture results remain
identical.

## 7. Page ownership and replacement ordering

On a resident miss:

### Clean victim

```text
ENSURE_RESIDENT
  -> LOAD_REQUESTED
  -> DISPATCH_CORE
```

### Dirty victim

```text
ENSURE_RESIDENT
  -> SAVE_VICTIM
  -> LOAD_REQUESTED
  -> DISPATCH_CORE
```

A dirty victim must be fully written back before the requested record is loaded
into that resident slot.

A page operation must not overlap compute ownership of the selected resident
slot.

The PS commands page movement. PL remains the bulk data mover.

## 8. Packet-routing contract

After every completed logical-core dispatch:

1. PS reads the latched packet count.
2. PS drains exactly that many packet words.
3. Every packet must validate before delivery.
4. The packet logical destination core is resolved independently of residency.
5. Every generated packet from timestep `t` must target `t + 1`.
6. Delivery is always to the destination core's **NEXT** event bank.
7. Event capacity is checked before insertion.
8. The source core is not marked complete until all emitted packets are
   committed.

### Resident destination

If the destination logical core is resident, PS writes the destination axon
through the resident-memory control path.

### Non-resident destination

If the destination is non-resident, PS writes the destination axon into that
logical core's DDR-backed NEXT event-bank image and updates the PS runtime
event-count table.

The PS must not page a destination solely to deliver a packet unless later
measurements justify that policy.

## 9. Event-count and event-bank authority

During an active run, the PS runtime owns the authoritative event-count table.

The global CURRENT bank is derived from the global algorithmic timestep:

```text
current_bank = timestep & 1
next_bank    = 1 - current_bank
```

The event-bank selector changes only after a successful global barrier.

Raw event words may remain stale beyond the active event count, matching the
accepted P02 physical model.

## 10. Global barrier contract

The PS may complete timestep `t` only when all of these are true:

- every configured logical core has completed its required dispatch;
- every packet produced by those dispatches has been drained;
- every valid packet has been committed to its destination NEXT bank;
- no routing work remains pending;
- no page command remains active;
- no dispatch command remains active;
- all NEXT event counts for the upcoming timestep are finalized.

Only then may the runtime:

1. increment the barrier counter;
2. swap CURRENT/NEXT ownership globally;
3. advance the algorithmic timestep;
4. begin servicing the next timestep.

An idle HLS engine alone is not barrier completion.

## 11. DDR and cache ownership

P03 retains the accepted non-coherent P02 ownership model.

### Reserved backing window

The standalone BSP/linker/runtime memory layout must reserve:

```text
0x4000_0000 .. 0x43FF_FFFF
```

for P02/P03 logical-core backing records.

The standalone program, heap, stack, input/output buffers, and other runtime
storage must not overlap this region.

### PS -> PL

Before PL reads a DDR range that PS has modified:

1. PS completes writes;
2. PS flushes/cleans the affected cache range;
3. PS executes the required memory/order barrier;
4. PS issues the PL operation;
5. PS does not modify the range until PL completion.

### PL -> PS

Before PS reads a DDR range that PL has modified:

1. PS waits for PL completion;
2. PS invalidates the affected cache range;
3. PS then reads or modifies the range.

Concurrent PS and PL writers to the same range are forbidden.

## 12. Active-run header and digest rule

The 512 KiB DDR record remains the storage ABI.

However, the P02 physical page mover transfers payload banks and does not refresh
the 4 KiB record header or SHA-256 digest.

Therefore P03 freezes this rule:

- initial records must pass ABI/static integrity validation before the run;
- during an active run, PS runtime metadata is authoritative for event counts,
  residency, dirty state, and global event-bank parity;
- the payload SHA-256 in a record header may become stale after mutable PL
  writeback;
- the runtime must not reject a valid active record merely because that digest
  is stale;
- before a complete record is declared an externally reusable checkpoint or
  exported canonical context image, its runtime header/digest must be refreshed.

This is an implementation rule for the P02 ABI during active execution; it does
not change logical Loihi semantics.

## 13. PS-to-PL command semantics

P03.1 freezes semantic command classes, not final MMIO addresses.

P03.2 will assign an AXI-Lite register map.

### Page command

Minimum request:

```text
operation        PAGE_IN | PAGE_OUT
mutable_only     bool
resident_slot    0..2
record_base      512-KiB-aligned DDR address
start
```

Minimum completion/status:

```text
busy
done
start_blocked
bytes_transferred
last_transfer_cycles
error_command
error_host
error_ddr
range_error
protocol_error
AXI read/write burst counters
AXI bytes moved
pending_write_bytes
```

### Dispatch command

Minimum request:

```text
resident_slot
logical_core_id
compartment_count
synapse_count
route_count
event_count
timestep
event_read_bank
start
```

Minimum completion/status:

```text
busy
done
start_blocked
packet_count
core_status
last_dispatch_cycles
completed_dispatches
metadata_error
packet_overflow_error
core_status_error
memory_address_error
```

### Resident-memory access

PS requires a low-rate resident-memory command path for:

- packet reads;
- state/trace debug when enabled;
- destination event insertion;
- directed regression inspection.

The P02 slow-request response-latching rule remains normative for this path.

## 14. Timing and counter boundaries

P03 separates two PS timer intervals.

### Autonomous-control interval

Starts when the board-local runtime accepts RUN/START and locks out external
algorithmic control.

Ends when DONE or ERROR is committed.

This includes deployment validation, backing initialization, resident
initialization, input load, inference, and final result commit.

### Inference interval

Starts at the transition into `LOAD_INPUT`, after deployment/backing/resident
initialization is complete.

Ends after `WRITE_RESULT` commits final result/evidence.

This is the preferred per-sample board-local latency boundary.

### Required counters

The runtime must expose at least:

- algorithmic timesteps completed;
- barriers completed;
- logical dispatches;
- routed packets;
- page-ins;
- page-outs;
- evictions;
- page hits;
- PL dispatch cycles;
- PL page-transfer cycles;
- PS routing ticks;
- PS barrier ticks;
- PS complete-timestep ticks;
- PS complete-inference ticks;
- first fault code and fault state.

External-PC wall time is not a final inference-latency metric.

## 15. Fail-closed error contract

The first detected fault is sticky until reset.

Initial error classes are:

```text
0  NONE
1  INVALID_RUN_CONFIG
2  DEPLOYMENT_INVALID
3  BACKING_ABI
4  BACKING_RANGE
5  CACHE_OWNERSHIP
6  PAGE_ERROR
7  DISPATCH_ERROR
8  PACKET_FORMAT
9  EVENT_OVERFLOW
10 RESOURCE_OVERFLOW
11 BARRIER_INCOMPLETE
12 CONTROL_PROTOCOL
13 TIMEOUT
```

On ERROR:

- no new dispatch is issued;
- no new page command is issued;
- no barrier/event-bank swap occurs;
- first fault code/state are preserved;
- partial counters remain readable;
- recovery requires explicit reset/reinitialization.

A later error must not overwrite the first fault.

## 16. Result/evidence record

DONE must leave board-local result metadata sufficient to reconstruct the run
without PC-owned bookkeeping.

At minimum:

```text
schema/version
deployment identity/fingerprint
run identity
logical_core_count
resident_context_count
physical_engine_count
requested_timesteps
completed_timesteps
barriers
dispatches
routed_packets
page_ins/page_outs
evictions/page_hits
current/final event bank
PL cycle counters
PS timer counters
first_fault=NONE
result=PASS
```

ERROR must write the same available metadata with the sticky fault code/state.

## 17. P03.1 executable checks

The focused contract model must prove:

- external algorithmic control locks out after begin-run;
- a dirty victim is saved before replacement page-in;
- packet drain is required before logical-core completion;
- barrier cannot complete while work remains;
- event-bank swap cannot occur before a completed barrier;
- first error is sticky and fail-closed;
- reset is the explicit recovery boundary;
- a legal multi-timestep run reaches DONE with exact counters.

Primary test:

```text
tests/test_p03_1_runtime_contract.py
```

## 18. P03.1 acceptance boundary

P03.1 is complete when independent verification confirms:

1. this runtime contract and v3 target-spec addendum are reviewed;
2. focused executable contract tests pass;
3. the inherited v3 Python regression remains clean;
4. no accepted P02 semantic/data-plane rule is silently changed.

P03.1 does **not** claim that the PS runtime or AXI-Lite control interface is
implemented yet.

Those begin in P03.2/P03.3.
