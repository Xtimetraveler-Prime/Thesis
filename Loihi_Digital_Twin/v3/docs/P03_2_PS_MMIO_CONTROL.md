# P03.2 — PS-Visible AXI-Lite Control/Status Shell

**Status:** Implementation candidate  
**Phase:** P03 — Autonomous PS-resident runtime  
**Branch:** `agent/v3-p03-autonomous-runtime`  
**Date drafted:** 2026-10-06

## Purpose

P03.2 replaces the P02 VIO-owned algorithmic command path with a PS-visible
memory-mapped control/status interface.

The accepted P02 bulk DDR path is retained unchanged:

```text
PL page walker
  -> range guard
  -> 128-bit / 256-byte burst adapter
  -> SmartConnect
  -> PS S_AXI_HP0_FPD
  -> K26 DDR
```

P03.2 adds the opposite control direction:

```text
Cortex-A53
  -> PS M_AXI_HPM0_FPD
  -> SmartConnect
  -> p03_ps_control_regs / AXI4-Lite
  -> page / dispatch / resident-memory command signals
```

The register block is not the autonomous scheduler. P03.3 software will drive
this interface according to the accepted P03.1 runtime contract.

## Fixed PS address

The initial standalone software contract reserves:

```text
MMIO base:   0xA4000000
MMIO range:  0x00001000  (4 KiB)
data width:  32 bits
protocol:    AXI4-Lite
```

This address is an FPGA-v3 implementation choice, not a Loihi architectural
property.

Python/software constants are frozen in:

```text
src/loihi_twin_v2/p03_mmio.py
```

## Register map

All offsets are relative to `0xA4000000`.

### Identity/global

| Offset | Name | Access | Meaning |
|---:|---|---|---|
| 0x000 | ID | RO | `0x4C543302` |
| 0x004 | VERSION | RO | `0x00010000` |
| 0x008 | CAPABILITIES | RO | page/dispatch/resident-memory, 64-bit DDR addr, 256-bit resident data, 3 slots, 1 engine |
| 0x00C | GLOBAL_STATUS | RO | page/dispatch/debug busy + aggregate error flags |

### Page command

| Offset | Name | Access | Meaning |
|---:|---|---|---|
| 0x020 | PAGE_CONFIG | RW | bit0 page-out, bit1 mutable-only, bits9:8 resident slot |
| 0x024 | PAGE_BASE_LO | RW | DDR record address [31:0] |
| 0x028 | PAGE_BASE_HI | RW | DDR record address [63:32] |
| 0x02C | PAGE_COMMAND | WO | bit0 START, bit1 CLEAR_DONE |
| 0x030 | PAGE_STATUS | RO | busy, sticky done/start-blocked, page/AXI/range errors |
| 0x034 | PAGE_BYTES | RO | semantic bytes transferred |
| 0x038 | PAGE_COMPLETED | RO | completed page transfers |
| 0x03C | PAGE_CYCLES_LO | RO | last transfer PL cycles [31:0] |
| 0x040 | PAGE_CYCLES_HI | RO | last transfer PL cycles [63:32] |
| 0x044 | PAGE_READ_BURSTS | RO | completed AXI read bursts |
| 0x048 | PAGE_WRITE_BURSTS | RO | completed AXI write bursts |
| 0x04C | PAGE_AXI_BYTES_LO | RO | aggregate AXI bytes [31:0] |
| 0x050 | PAGE_AXI_BYTES_HI | RO | aggregate AXI bytes [63:32] |
| 0x054 | PAGE_PENDING_BYTES | RO | burst-adapter pending write bytes |

### Dispatch command

| Offset | Name | Access | Meaning |
|---:|---|---|---|
| 0x080 | DISPATCH_CONFIG | RW | bits1:0 resident slot, bit8 event-read bank |
| 0x084 | DISPATCH_META_LO | RW | accepted packed metadata [31:0] |
| 0x088 | DISPATCH_META_HI | RW | accepted packed metadata [63:32] |
| 0x08C | DISPATCH_TIMESTEP | RW | algorithmic timestep |
| 0x090 | DISPATCH_COMMAND | WO | bit0 START, bit1 CLEAR_DONE |
| 0x094 | DISPATCH_STATUS | RO | busy, sticky done/start-blocked, dispatch errors |
| 0x098 | DISPATCH_PACKET_COUNT | RO | latched packet count |
| 0x09C | DISPATCH_CORE_STATUS | RO | HLS/core status |
| 0x0A0 | DISPATCH_COMPLETED | RO | completed dispatch counter |
| 0x0A4 | DISPATCH_CYCLES_LO | RO | last dispatch PL cycles [31:0] |
| 0x0A8 | DISPATCH_CYCLES_HI | RO | last dispatch PL cycles [63:32] |
| 0x0AC | DISPATCH_ACTIVE | RO | slot, event bank, logical core ID |

The 64-bit dispatch metadata layout is inherited unchanged:

```text
[6:0]   logical_core_id
[17:7]  compartment_count
[33:18] synapse_count
[46:34] route_count
[59:47] current event count
[63:60] reserved zero
```

### Resident-memory command

| Offset | Name | Access | Meaning |
|---:|---|---|---|
| 0x100 | DEBUG_CONFIG | RW | bit0 write, bits9:8 resident slot, bits15:12 bank |
| 0x104 | DEBUG_ADDR | RW | resident-bank word address |
| 0x108 | DEBUG_COMMAND | WO | bit0 START, bit1 CLEAR_DONE |
| 0x10C | DEBUG_STATUS | RO | busy, sticky done/rvalid/error/start-blocked |
| 0x110..0x12C | DEBUG_WDATA[0..7] | RW | 256-bit request payload, little word order |
| 0x130..0x14C | DEBUG_RDATA[0..7] | RO | 256-bit captured response, little word order |

## Command completion rule

P02 used one-cycle `transfer_done` / `dispatch_done` pulses because VIO
scripts watched them directly.

A Cortex-A53 polling loop must not depend on seeing a one-PL-clock pulse.

P03.2 therefore latches page and dispatch completion into sticky MMIO status
bits. Software clears the sticky bit explicitly or implicitly by starting the
next command.

Resident-memory commands use the final accepted P02 slow-request protocol:

1. MMIO START asserts `debug_req`;
2. `debug_req` stays high until the arbiter exposes its latched ACK;
3. the MMIO block captures ACK/RVALID/ERROR/RDATA;
4. the MMIO block deasserts `debug_req`;
5. the result remains sticky/software-readable until clear or the next request.

This removes JTAG/VIO polling speed from the command-response boundary.

## Command ownership

P03.2 makes PS MMIO the command owner for:

- page command fields/start;
- dispatch metadata/start;
- resident-memory reads/writes.

VIO may remain as **read-only physical observability** and as a pre-run reset /
bring-up mechanism during P03.2/P03.3 development.

VIO must not remain connected as a competing page/dispatch/resident-memory
command source in the P03.2 integrated shell.

## Acceptance checks

P03.2a register-level simulation must prove:

- AXI-Lite identity/capability registers;
- page command field packing and one-cycle START;
- sticky page completion;
- dispatch field packing and sticky completion;
- resident read request held until ACK;
- captured 256-bit resident read response;
- resident write payload;
- blocked resident request reporting.

P03.2b Vivado integration must prove:

- `M_AXI_HPM0_FPD` is enabled;
- PS master reaches the MMIO block through SmartConnect;
- fixed `0xA4000000/4KiB` address assignment;
- P02 HP0 DDR path remains enabled and unchanged in direction;
- MMIO drives page/dispatch/debug command inputs;
- no VIO output drives those command inputs;
- synthesis/route close timing on K26;
- three resident contexts / one physical engine remain unchanged.

## Claim boundary

P03.2 proves a PS-accessible hardware control plane.

It does not yet prove:

- standalone A53 scheduling/routing/barrier software;
- the PC is absent from the active algorithmic loop;
- end-to-end autonomous inference.

Those are P03.3–P03.5.
