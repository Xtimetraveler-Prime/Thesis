# P02.2 — DDR Backing-Store and Page-Transfer Reference Model

**Status:** Verification candidate  
**Phase:** P02 — DDR-backed logical-core virtualization  
**Date drafted:** 2026-10-05

## 1. Purpose

P02.1 froze the DDR byte layout. P02.2 now freezes the behavior of moving that
state between the authoritative DDR backing store and the three accepted
resident context slots.

This is still a software reference. It does **not** claim physical AXI transfer
latency or bandwidth. Its purpose is to give P02.3 one exact behavioral oracle.

## 2. DDR record versus resident slot

The 512 KiB DDR stride is not the amount of data physically resident in URAM.

One DDR record contains:

- 4 KiB header;
- 428 KiB of the ten P05 resident-memory banks;
- 80 KiB reserved tail.

Therefore:

    DDR stride                 512 KiB
    resident payload           428 KiB
    header + reserved overhead  84 KiB

P02.2 models page-in as transfer of the ten payload banks plus separate
application of header metadata.

The header and reserved tail do not pretend to be resident URAM.

## 3. Authoritative state rule

DDR is authoritative for a non-resident logical core.

A resident slot is a temporary physical cache entry identified separately by:

- logical core ID;
- resident slot;
- physical engine.

Page replacement must therefore perform:

    if selected resident slot contains a context:
        PAGE_OUT victim
    PAGE_IN requested logical core

A requested logical core may be loaded into any resident slot without rewriting
logical route identities.

## 4. Page-in contract

P02.2 page-in transfers all ten payload banks:

- config;
- state;
- axon;
- synapse;
- route descriptor;
- route;
- event bank 0;
- event bank 1;
- trace;
- packet.

Exact payload size:

    0x6B000 bytes = 438,272 bytes = 428 KiB

Before materialization the DDR record must pass ABI/header/payload-hash
validation.

Runtime metadata loaded alongside the banks includes:

- logical core ID;
- current event-bank selector;
- compartment count;
- synapse count;
- route count;
- event-bank counts;
- packet count.

## 5. Runtime mutability

The accepted software model treats these banks as static during execution:

- config;
- axon;
- synapse;
- route descriptor;
- route.

These banks are mutable:

- state;
- event bank 0;
- event bank 1;
- trace;
- packet.

A runtime attempt to write a static bank is rejected by the reference model.

This is an implementation invariant for P02/P03, not a native-Loihi claim.

## 6. Page-out policies

P02.2 intentionally defines two legal writeback plans so P02.3 can compare
implementation cost without changing the DDR ABI.

### 6.1 Full payload

Write back all ten banks.

    bytes = 0x6B000 = 428 KiB

This is the simplest hardware-correctness target.

### 6.2 Mutable only

Write back:

- state;
- event bank 0;
- event bank 1;
- trace;
- packet.

Exact size:

    state   0x02000
    event0  0x04000
    event1  0x04000
    trace   0x08000
    packet  0x08000
    ----------------
    total   0x1A000 = 106,496 bytes = 104 KiB

Because static banks are invariant while resident, mutable-only writeback must
produce the exact same DDR record as a full writeback for the same runtime
state.

P02.2 tests this equality directly.

## 7. Header refresh after writeback

After resident banks are copied back, the backing record refreshes:

- current event-bank selector;
- event-bank counts;
- packet count;
- payload SHA-256.

Static identity/resource metadata stays unchanged.

A reloaded record must therefore validate normally through the P02.1 parser.

## 8. Transfer accounting

Every software page operation records:

- operation type;
- logical core ID;
- resident slot;
- transferred bank set;
- exact byte count;
- evicted logical core ID when replacement occurs.

No cycle estimate is attached in P02.2.

P02.3 hardware will add measured PL cycle counts and real DDR bandwidth.

## 9. Replacement semantics

The reference replacement operation is deliberately ordered:

    PAGE_OUT victim
    then
    PAGE_IN requested core

The model does not allow silently overwriting an occupied resident slot.

This will later map directly to the physical slot-ownership rule: page movement
cannot target a slot while the HLS engine owns it.

## 10. P02.2 acceptance boundary

Independent verification should confirm:

1. page-in moves exactly 428 KiB of accepted resident-bank state;
2. mutable-only page-out moves exactly 104 KiB;
3. state, events, event-bank selector, counts, traces, and packets survive
   eviction/reload;
4. full and mutable-only writeback produce identical DDR records when static
   banks are unchanged;
5. static runtime bank writes are rejected;
6. a victim is written back before a replacement core is loaded;
7. fixed logical-core DDR addresses remain unchanged by residency;
8. refreshed records retain valid ABI fingerprints/hashes;
9. P02.1 focused tests and inherited v3 regressions remain clean.

P02.2 does not select final hardware writeback policy. P02.3 may begin with full
payload writeback for simplicity and later enable mutable-only writeback if the
measured benefit justifies the additional control logic.
