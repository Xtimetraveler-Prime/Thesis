# P02.3a — Resident-Bank Page Walker and Port-B Ownership

**Status:** Verification candidate  
**Phase:** P02 — DDR-backed logical-core virtualization  
**Date drafted:** 2026-10-05

## 1. Purpose

P02.3a is the first RTL implementation step for board-local paging.

P02.1 defined the 512 KiB DDR record. P02.2 proved the software page-transfer
semantics. P02.3a now implements the programmable-logic sequencer that walks the
ten accepted P05 resident-memory banks in the same order and with the same
transfer sizes.

This sub-step deliberately stops at an abstract DDR request/response boundary.
It does **not** yet claim AXI bursts or physical DDR bandwidth. P02.3b will place
the burst-capable AXI adapter behind this verified walker.

## 2. Why the existing P05 host port is reused first

The accepted P05 memory fabric already exposes every retained memory bank through
Port B when compute is idle.

That interface supports:

- resident context slot;
- bank ID;
- word address;
- read/write direction;
- up to 256 bits of data;
- acknowledgement/error/read-valid response.

Using this accepted boundary for P02.3a avoids modifying the HLS-facing Port A or
the internal UltraRAM bank construction while transfer sequencing is still being
verified.

The limitation is that this interface is scalar. Therefore P02.3a is a
**correctness sequencer**, not the final high-bandwidth DDR engine.

## 3. New RTL blocks

### 3.1 p02_context_page_bank_walker.v

The page walker accepts:

    cmd_start
    cmd_page_out
    cmd_mutable_only
    cmd_context_slot
    cmd_record_base

It emits one resident-memory transaction and one abstract DDR transaction for
each physical bank word.

It exposes:

    busy
    transfer_done
    start_blocked
    bytes_transferred
    completed_transfers
    active_cycles
    last_transfer_cycles
    error_command
    error_host
    error_ddr

### 3.2 p02_page_host_arbiter.v

The arbiter multiplexes the existing P05 Port-B transaction boundary between:

- external host/debug access when no page transfer owns the port; and
- the page walker while a transfer is active.

The owner of each in-flight transaction is latched until acknowledgement.

That response-owner latch is required because the final page transaction may
retire in the same clock cycle that the walker drops page_active. Routing the
acknowledgement only from the current live page_active signal could otherwise
make the last page response appear spuriously on the debug side.

## 4. Bank traversal

Full transfers follow DDR offset order:

| Sequence | DDR offset | P05 host bank | Bank | Depth | Word bytes |
|---:|---:|---:|---|---:|---:|
| 0 | 0x01000 | 0 | config | 1024 | 16 |
| 1 | 0x05000 | 1 | state | 1024 | 8 |
| 2 | 0x07000 | 2 | axon | 4096 | 8 |
| 3 | 0x0F000 | 3 | synapse | 32768 | 8 |
| 4 | 0x4F000 | 4 | route descriptor | 1024 | 4 |
| 5 | 0x50000 | 5 | route | 4096 | 4 |
| 6 | 0x54000 | 6 | event bank 0 | 4096 | 4 |
| 7 | 0x58000 | 9 | event bank 1 | 4096 | 4 |
| 8 | 0x5C000 | 7 | trace | 1024 | 32 |
| 9 | 0x64000 | 8 | packet | 4096 | 8 |

The host-bank numbering is inherited from P05 and is not numerically identical
to DDR layout order, so the walker uses an explicit sequence map.

A complete transfer therefore performs 57,344 resident-memory word
transactions and moves exactly:

    0x6B000 bytes = 428 KiB

## 5. Page-in behavior

For every bank word:

    DDR_READ(record_base + bank_offset + word_index * word_bytes)
        ->
    RESIDENT_WRITE(context_slot, bank_id, word_index)

Page-in always transfers the complete 428 KiB payload.

Mutable-only page-in is rejected because static deployment state must be present
before a context can be treated as resident.

## 6. Page-out behavior

Full page-out performs:

    RESIDENT_READ(context_slot, bank_id, word_index)
        ->
    DDR_WRITE(record_base + bank_offset + word_index * word_bytes)

for all ten banks.

Mutable-only page-out walks:

1. state;
2. event bank 0;
3. event bank 1;
4. trace;
5. packet.

That is 14,336 resident word transactions and exactly:

    0x1A000 bytes = 104 KiB

P02.3a does not update the 4 KiB DDR header itself. Header/runtime metadata
refresh remains a separate control-plane operation frozen by P02.1/P02.2.

## 7. Command validation

The walker rejects a command before any memory transaction when:

- resident slot is not 0..2;
- DDR record base is not 512 KiB aligned;
- mutable-only is requested for page-in.

P02.3b will additionally validate the address against the reserved DDR backing
region before issuing AXI traffic.

## 8. Compute ownership

P02.3a does not weaken the existing P05 compute-versus-Port-B rule.

The page walker uses the same Port-B transaction path that the P05 memory fabric
already blocks while compute_busy is asserted.

At the v3 system-control level, a page command must therefore be issued only
when the selected resident slot is not owned by the HLS engine.

P03 will make that ownership transition explicit in the board-local scheduler.

## 9. DDR adapter boundary

The walker exposes an abstract scalar transaction interface:

    ddr_req
    ddr_write
    ddr_addr
    ddr_size_bytes
    ddr_wdata
    ddr_busy
    ddr_ack
    ddr_rvalid
    ddr_error
    ddr_rdata

This is intentionally not described as the final DDR performance path.

P02.3b will convert these semantically verified accesses into buffered AXI
bursts. The adapter may combine adjacent scalar words into wider/burst
transactions, but it must preserve exactly the addresses/data implied by this
walker.

## 10. Directed RTL gate

rtl/tb/test_p02_context_page_bank_walker.v verifies:

- rejection of a misaligned DDR record base;
- complete page-in of all 57,344 words;
- exact 428 KiB full-transfer byte count;
- exact DDR address calculation at every word;
- resident slot and bank/address preservation;
- debug blocking while page ownership is active;
- mutable-only page-out of all 14,336 runtime words;
- exact 104 KiB mutable transfer count;
- full page-out of all 57,344 words;
- resident-read to DDR-write data preservation;
- rejection of mutable-only page-in;
- nonzero physical cycle accounting;
- successful-transfer counting.

The test uses behavioral responders for the accepted P05 host transaction
boundary and for the future DDR adapter boundary. It does not claim physical DDR
timing.

## 11. P02.3a acceptance boundary

P02.3a may be accepted when:

1. the directed XSIM gate passes without FAIL markers;
2. full page-in reports 0x6B000 bytes;
3. mutable-only page-out reports 0x1A000 bytes;
4. full page-out reports 0x6B000 bytes;
5. all bank/address/data checks pass across the complete bank depths;
6. debug access is blocked for page ownership;
7. invalid alignment/mode commands are rejected;
8. focused P02 Python tests remain clean;
9. the full v3 pytest regression remains clean.

P02.3a acceptance does **not** close P02.3. Physical burst DDR integration
remains P02.3b.
