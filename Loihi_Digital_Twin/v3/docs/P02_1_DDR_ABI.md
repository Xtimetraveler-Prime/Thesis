# P02.1 — DDR Backing-Image ABI and Coherency Contract

**Status:** Complete — accepted 2026-10-05  
**Phase:** P02 — DDR-backed logical-core virtualization  
**Date drafted:** 2026-10-05

## 1. Purpose

P02.1 freezes the byte-level contract used to store non-resident logical-core
contexts in K26 DDR.

The ABI sits below the accepted logical Loihi-like architecture. It does not
change logical core IDs, neuron arithmetic, route semantics, event causality, or
the global barrier.

The immediate design goal is to make a logical core independently recoverable
from one deterministic DDR record that can be moved into any of the three
resident context slots.

## 2. Fixed logical-core record

Each architectural logical core ID owns one fixed 512 KiB record:

    record_bytes = 0x80000 = 512 KiB
    record_offset(core_id) = core_id * 0x80000

The backing-region base must itself be 512 KiB aligned.

For the currently reserved 128 logical IDs:

    128 * 512 KiB = 64 MiB

This makes address generation a shift/add operation and leaves enough space for
every currently modeled logical core.

## 3. Record layout

All multi-byte words use **little-endian byte order**.

| Region | Offset | Size | Organization |
|---|---:|---:|---|
| v3 context header | 0x00000 | 0x01000 | 4 KiB |
| config | 0x01000 | 0x04000 | 1024 x 128-bit |
| state | 0x05000 | 0x02000 | 1024 x 64-bit |
| axon | 0x07000 | 0x08000 | 4096 x 64-bit |
| synapse | 0x0F000 | 0x40000 | 32768 x 64-bit |
| route descriptor | 0x4F000 | 0x01000 | 1024 x 32-bit |
| route | 0x50000 | 0x04000 | 4096 x 32-bit |
| event bank 0 | 0x54000 | 0x04000 | 4096 x 32-bit |
| event bank 1 | 0x58000 | 0x04000 | 4096 x 32-bit |
| trace | 0x5C000 | 0x08000 | 1024 x 256-bit |
| packet | 0x64000 | 0x08000 | 4096 x 64-bit |
| reserved | 0x6C000 | 0x14000 | must initialize to zero in ABI v1 |
| **record end** | **0x80000** | | |

The ten payload banks exactly match the accepted P05 resident-context memory
depths/widths. The 4 KiB header and 80 KiB tail are v3 implementation
overhead/reserve; they are not native Loihi memory.

## 4. Header v1

ABI magic is LTV3CTX1.

Header fields:

| Offset | Type | Meaning |
|---|---|---|
| 0x00 | 8 bytes | magic |
| 0x08 | u32 | ABI version = 1 |
| 0x0C | u32 | header bytes = 0x1000 |
| 0x10 | u32 | record bytes = 0x80000 |
| 0x14 | u32 | logical core ID |
| 0x18 | u32 | flags, zero/reserved in v1 |
| 0x1C | u32 | CURRENT event-bank selector, 0 or 1 |
| 0x20 | u32 | compartment count |
| 0x24 | u32 | synapse count |
| 0x28 | u32 | route count |
| 0x2C | u32 | event-bank-0 count |
| 0x30 | u32 | event-bank-1 count |
| 0x34 | u32 | packet count |
| 0x38 | 8 bytes | reserved zero |
| 0x40 | 32 bytes | SHA-256 of bytes [0x1000, 0x6C000) |
| 0x60..0xFFF | | reserved zero in v1 |

Unknown ABI versions must be rejected rather than interpreted as compatible.

## 5. Dense physical image rule

The P03/P08 Python image stores some banks sparsely because that is convenient
for software. DDR does not.

Every DDR record contains the **full physical depth** of every resident bank.
Unused entries are zero.

Examples:

- a configured axon at logical index 4095 is written at the last 64-bit axon
  entry, not compacted next to lower IDs;
- unused synapse capacity remains zero-filled;
- route descriptors preserve compartment index;
- trace and packet banks are present even when initially empty.

This allows the PL page mover to copy deterministic ranges without understanding
the logical network structure.

## 6. Static versus mutable banks

The first implementation classifies:

**Static after deployment load**

- config;
- axon;
- synapse;
- route descriptor;
- route.

**Mutable during execution**

- state;
- event bank 0;
- event bank 1;
- trace;
- packet;
- header runtime counts/event-bank selector.

P02.3 may optimize which sections are written back on eviction, but the complete
512 KiB record remains the authoritative ABI. Any partial-transfer optimization
must be observationally equivalent to a full save/load.

## 7. Integrity

The header stores SHA-256 over the complete payload-bank area [0x1000, 0x6C000).

This detects corruption or a mismatched backing image before it is treated as a
valid context.

The project may later add a cheaper hardware CRC for runtime transfers. Such a
CRC would be an additional transport check and would not replace the canonical
ABI fingerprint unless a new ABI version explicitly says so.

## 8. PS/PL ownership and cache contract

The initial implementation uses explicit ownership and does **not** depend on
hardware cache coherency.

AMD documents S_AXI_HP{0:3}_FPD as PL-master high-performance paths into the
FPD/DDR system. v3 uses that class of interface for the first page mover.

The first standalone A53 software contract is:

### PS -> PL ownership handoff

When the PS creates or modifies a context record that PL will read:

1. PS completes all writes to the record.
2. PS calls Xil_DCacheFlushRange(record_address, record_length) for the
   affected DDR range.
3. PS performs the command/register ordering barrier required by the control
   driver.
4. PS issues the PL page/load command.
5. PS must not modify that owned range until PL completion is observed.

AMD UG643 documents Xil_DCacheFlushRange in the standalone BSP.

### PL -> PS ownership handoff

When PL writes DDR state that the PS will inspect:

1. PS waits until the PL command reports complete.
2. PS calls Xil_DCacheInvalidateRange(record_address, record_length) before
   reading the affected range.
3. PS may then inspect/update the range.

For Cortex-A53, AMD's standalone documentation notes that invalidate-range
operations are promoted to clean-and-invalidate behavior. The design therefore
must never rely on concurrently dirty PS cache lines while PL owns the same
range.

### No concurrent writers

PS and PL must never write the same context range concurrently.

This explicit rule is part of the acceptance contract even if a future
implementation maps the region non-cacheable or moves to a coherent interface.

## 9. Page-transfer command boundary

P02.1 does not freeze final AXI-Lite register addresses, but it freezes the
minimum semantic command needed by P02.3:

    operation          PAGE_IN | PAGE_OUT
    logical_core_id    0..127
    resident_slot      0..2
    ddr_record_address 512-KiB-aligned record address
    section_mask       full-record initially; partial sections optional later
    start

Completion status must include:

    busy
    done
    error
    error_code
    bytes_transferred
    pl_cycles

The page mover must reject:

- invalid logical core IDs;
- invalid resident slots;
- unaligned/out-of-range DDR addresses;
- unsupported section masks;
- command overlap with an HLS engine owning the selected resident slot.

## 10. Deterministic software reference

src/loihi_twin_v2/ddr_abi.py is the executable P02.1 reference.

It provides:

- fixed layout constants;
- core-ID-to-DDR offset/address calculation;
- densification of sparse P03 banks;
- deterministic initial-record serialization;
- header parsing and validation;
- payload SHA-256 verification;
- complete-record fingerprinting.

This serializer is the source of truth for P02.2/P02.3 test vectors. RTL is not
allowed to invent a second layout.

## 11. P02.1 acceptance boundary

P02.1 is complete when independent verification confirms:

1. the record is exactly 512 KiB;
2. all ten accepted resident banks have exact non-overlapping offsets/depths;
3. all unused entries and reserved bytes serialize deterministically to zero;
4. logical core address arithmetic covers all 128 reserved IDs in 64 MiB;
5. sparse P03 axon/route-descriptor indices survive densification exactly;
6. event-bank selector/count metadata round-trips;
7. payload corruption is detected;
8. invalid core IDs, alignment, and event capacity are rejected;
9. inherited v3 tests still pass.

P02.1 does **not** claim physical DDR transfers yet. That begins in P02.3 after
the P02.2 software reference/transfer model is accepted.
