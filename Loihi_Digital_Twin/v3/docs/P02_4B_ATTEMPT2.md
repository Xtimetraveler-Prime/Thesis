# P02.4b Physical Attempt 2 — Diagnostic Read Sampling Race

**Date:** 2026-10-05  
**Result:** Harness diagnostic failed before resident-image comparison; P02 remains open.

## Evidence before failure

The retry again passed:

- frozen 35-dispatch / 30-packet fixture generation;
- XSDB provisioning and verification of all five K26 DDR backing records.

The new resident-image diagnostic then attempted to read slot 0, bank 0,
address 0 immediately after the first page-in.

Observed failure:

```text
P02.4b host read failed slot=0 bank=0 addr=0 valid=0 error=0
```

## Root cause

The debug host response passes through `p02_page_host_arbiter`.

The fabric produces:

- `fabric_ack`;
- `fabric_rvalid`;
- `fabric_error`;
- `fabric_rdata`.

The arbiter exposes these to the debug side only while the transaction owner is
still latched as debug.

The initial Tcl helper waited for ACK with one `refresh_hw_vio`, then performed
separate refreshes for RVALID, ERROR, and RDATA. Those refreshes can observe
different PL cycles / arbiter ownership phases of the same completed
transaction.

The reported `valid=0,error=0` therefore does not establish a resident-memory
data failure.

## Correction

P02.4b now samples the complete debug response tuple from **one VIO refresh**:

```text
ACK
RVALID
ERROR
RDATA
```

Both debug reads and writes use this atomic response snapshot. This also avoids
missing a transient debug write error.

The preflight explicitly requires this response-sampling contract.

## Acceptance state

This attempt does not change the P02.4b neural or paging acceptance result. The
original timestep-0 core-1 state mismatch remains unresolved until a retry gets
through the corrected resident-image diagnostics.
