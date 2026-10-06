# P02.3b1 — 128-bit AXI Burst Coalescer

**Status:** Verification candidate  
**Phase:** P02 — DDR-backed logical-core virtualization  
**Date drafted:** 2026-10-05

## 1. Purpose

P02.3a proved the exact resident-bank / DDR scalar address stream.

P02.3b1 adds a transport layer behind that already-verified interface so the
same scalar semantic stream can use efficient AXI4 bursts without rewriting the
page walker.

The physical target for P02.3b2 is the Zynq UltraScale+ PS
`S_AXI_HP0_FPD` path configured at 128 data bits.

## 2. Why 256-byte coalescing is exact for this ABI

Every P02 payload bank:

- begins on a 4 KiB-aligned DDR offset; and
- has a size that is an integer multiple of 256 bytes.

The accepted scalar word widths are:

- 4 bytes;
- 8 bytes;
- 16 bytes;
- 32 bytes.

Therefore every bank can be partitioned exactly into:

    256 bytes
      = 16 AXI beats
      x 16 bytes/beat
      = one AXI4 burst with LEN=15 and SIZE=4

No accepted payload bank leaves a partial final coalescing block.

A 256-byte-aligned 256-byte burst also cannot cross a 4 KiB AXI boundary.

## 3. Read behavior

The adapter contains a 256-byte read cache.

On a scalar read miss:

1. align the request down to a 256-byte boundary;
2. issue one 16-beat, 128-bit AXI4 INCR read burst;
3. retain the returned 256 bytes;
4. return the requested 4/8/16/32 bytes to the page walker;
5. service subsequent scalar requests from the same 256-byte region as cache
   hits without another AXI address transaction.

The cache is invalidated by writes.

## 4. Write behavior

Sequential scalar writes are appended into one 256-byte coalescing buffer.

Intermediate scalar writes are acknowledged when accepted into the buffer.

The scalar request that completes byte 256 is **not** acknowledged immediately.
Instead the adapter:

1. issues one AXI write address with LEN=15/SIZE=4/INCR;
2. emits sixteen 128-bit data beats with all byte strobes enabled;
3. waits for the AXI B response;
4. only then acknowledges the scalar request that completed the burst.

This keeps AXI write failures visible through the already-accepted P02.3a error
path.

The page-walker layout guarantees that every legal page-out stream reaches a
complete 256-byte block before changing to a non-contiguous bank.

## 5. AXI restrictions

The first adapter intentionally uses a narrow deterministic subset:

- AXI4;
- 128-bit data;
- one outstanding read or write transaction;
- fixed 16-beat INCR bursts;
- 16-byte beats;
- full write strobes;
- ID 0;
- at most one 256-byte transport unit in flight;
- no narrow AXI bursts;
- no exclusive accesses.

Scalar addresses must fit the 49-bit PS slave-interface address space.

## 6. Error behavior

The adapter reports an error to the scalar requester for:

- unsupported scalar sizes;
- size misalignment;
- addresses outside the 49-bit AXI address range;
- non-sequential writes inside an incomplete coalescing buffer;
- malformed AXI read burst termination;
- non-zero AXI RRESP/BRESP;
- unexpected non-zero AXI ID.

Protocol-shape violations also set a sticky `protocol_error` observation.

A failed AXI burst does not increment the successful burst or byte counters.

## 7. Observability

P02.3b1 exposes:

- completed read bursts;
- completed write bursts;
- total successful AXI bytes moved;
- currently pending coalesced write bytes;
- sticky protocol error.

These are transport counters. They are distinct from:

- algorithmic timesteps;
- HLS dispatch cycles;
- page-walker semantic bytes;
- PS runtime timing.

## 8. Directed RTL gate

`rtl/tb/test_p02_axi128_burst_adapter.v` verifies:

- invalid scalar size rejection before AXI traffic;
- thirty-two sequential 8-byte reads collapsing into one 256-byte read burst;
- eight sequential 32-byte reads collapsing into one 256-byte read burst;
- sixty-four sequential 4-byte writes collapsing into one 256-byte write burst;
- eight sequential 32-byte writes collapsing into one 256-byte write burst;
- LEN=15, SIZE=4, INCR burst geometry;
- 256-byte address alignment;
- no 4 KiB boundary crossing;
- byte-exact packing/unpacking;
- all write strobes asserted;
- WLAST position;
- AXI BRESP failure propagation to the final scalar request;
- successful burst/byte accounting.

## 9. P02.3b1 acceptance boundary

P02.3b1 may be accepted when:

1. the AXI burst-adapter XSIM gate reports PASS with no FAIL/ERROR markers;
2. the accepted P02.3a page-walker gate remains clean;
3. focused P02 Python tests remain clean;
4. the full v3 pytest suite remains clean.

P02.3b1 does not claim a routed K26 DDR path yet.

P02.3b2 will instantiate this master in the P08-derived shell, enable
`S_AXI_HP0_FPD` at 128 bits, assign the DDR-low address segment, route the
design, and produce the next physical verification candidate.
