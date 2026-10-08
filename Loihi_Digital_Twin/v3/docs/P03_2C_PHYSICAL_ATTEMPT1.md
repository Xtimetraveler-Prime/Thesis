# P03.2c Physical Attempt 1 — VERSION Read Failure

**Date:** 2026-10-08  
**Phase:** P03.2c — Physical Cortex-A53 MMIO smoke  
**Result:** Physical provisioning/program/launch succeeded; A53 reached the MMIO block and failed at the VERSION register before issuing any page/debug/dispatch command.

## Physical evidence

The run passed:

```text
PASS: P03.2c backing record provisioned and mailbox cleared by physical readback
PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released
PASS: P03.2c standalone ELF downloaded to Cortex-A53 #0
PASS: P03.2c A53 smoke executed and 64-byte mailbox dumped
```

The mailbox then reported:

```text
result=0xDEAD0002
fail_code=2
mmio_version=0x00000000
```

The smoke source defines fail code 2 as `FAIL_MMIO_VERSION`.

The ID check precedes the VERSION check. Because the application reached
`FAIL_MMIO_VERSION`, the preceding ID read returned the expected:

```text
0x4C543302
```

Thus Cortex-A53 -> HPM0 -> MMIO is physically reachable.

No page, resident-memory, or dispatch command was issued in this attempt,
because the application fails closed immediately on the VERSION mismatch.

## Cache/MMU consideration

The ZynqMP 64-bit standalone translation table maps the lower PL range
`0x80000000..0xBFFFFFFF` as Device/strongly ordered memory. The P03 MMIO
window `0xA4000000..0xA4000FFF` lies inside that range.

Therefore ordinary DDR-style cacheability is not the expected explanation for
the VERSION failure.

## Coverage gap found

The P03.2 AXI-Lite simulation previously checked:

- ID at `0x000`;
- capabilities at `0x008`;

but skipped VERSION at `0x004`.

The testbench now explicitly requires:

```text
0x004 -> 0x00010000
```

## Next diagnostic

A read-only XSDB diagnostic was added:

```text
scripts/run_p03_2c_mmio_diag.sh
```

It reads only:

```text
0xA4000000 ID
0xA4000004 VERSION
0xA4000008 CAPABILITIES
0xA400000C GLOBAL_STATUS
```

twice as a four-word sequence and again as individual reads.

It performs no page, resident-memory, or dispatch writes and is diagnostic
evidence only, not acceptance evidence.


## Diagnostic attempt 1

The first read-only XSDB diagnostic selected Cortex-A53 #0 and attempted a
normal `mrd` at `0xA4000000`.

XSDB refused the request before issuing a hardware transaction:

```text
Memory read error at 0xA4000000.
Blocked address 0xA4000000.
PL AXI slave ports access is not allowed.
This address has not been added to the memory map.
```

This is a debugger memory-map policy failure, not evidence that the PL slave
itself is inaccessible.

AMD's XSDB reference documents `mrd -force` for overriding reserved/invalid
address-map protection. The diagnostic now uses forced 32-bit word reads for
the MMIO aperture.


## Diagnostic attempt 2

The forced XSDB diagnostic executed without an access-policy error but printed
only marker lines.

Cause: inside an XSDB Tcl script, `mrd` returns the formatted read result;
the script did not explicitly print that returned string.

The diagnostic now wraps each read as:

```tcl
puts [mrd -force -size w <address> <count>]
```

No hardware, MMIO, or standalone application logic changed.


## Realized block-design inspection

The accepted routed project reports:

```text
M_AXI_HPM0_FPD  AXI4      ADDR_WIDTH=40 DATA_WIDTH=32
SmartConnect SI AXI4      ADDR_WIDTH=40 DATA_WIDTH=32
SmartConnect MI AXI4LITE  ADDR_WIDTH=12 DATA_WIDTH=32
MMIO S_AXI      AXI4LITE  ADDR_WIDTH=12 DATA_WIDTH=32
```

The realized address assignment remains:

```text
offset=0x00A4000000
range =0x0000001000
```

so the requested 4 KiB HPM0 window was not collapsed by the Address Editor.

Physical forced reads with the accepted bitstream returned:

```text
0xA4000000 -> 0x4C543302
0xA4000004 -> 0x00000000
0xA4000008 -> 0x00000000
0xA400000C -> 0x00000000
```

for both repeated multiword and individual transactions.

This proves the failure exists in the realized PS-to-PL hardware path and is
not specific to the standalone A53 application.

## Corrective implementation under test

The only address-width conversion remaining between HPM0 and the MMIO slave
was SmartConnect's 40-bit AXI4 input to 12-bit AXI4-Lite output.

The MMIO slave has therefore been changed to accept the full 40-bit system
address and decode only `addr[11:0]` internally. This preserves:

- base `0xA4000000`;
- 4 KiB aperture;
- every existing register offset;
- 32-bit AXI4-Lite data width;
- page/dispatch/resident command semantics.

The RTL regression now drives full `0xA4000000 + offset` addresses and
explicitly checks VERSION at `+0x004`.

This correction is not accepted until a new routed shell passes timing and
physical forced reads demonstrate the nonzero offsets.


## Diagnostic attempt 3

After programming the full-width candidate shell from a normal Linux boot,
the read-only diagnostic failed before reaching PL:

```text
MMU fault at VA 0xA4000000
Translation fault, level 0
```

Cause: the diagnostic selected `Cortex-A53 #0`, so XSDB attempted the read in
the processor's current virtual-address/MMU context.

Correction: the diagnostic now follows the same proven physical-memory access
pattern as the P03.2c provisioning/mailbox scripts:

1. halt visible Cortex-A53 cores;
2. select the `PSU` physical target, falling back to `APU`;
3. issue `mrd -force -size w` physical reads of the PL MMIO aperture.

This bypasses the A53 MMU while retaining the debugger address-map override.


## Full-width candidate physical result

After routing the 40-bit end-to-end HPM0/MMIO candidate, the realized path was:

```text
HPM0 master        AXI4      ADDR_WIDTH=40
SmartConnect input AXI4      ADDR_WIDTH=40
SmartConnect output AXI4LITE ADDR_WIDTH=40
MMIO slave         AXI4LITE  ADDR_WIDTH=40
```

with the PS mapping still limited to:

```text
0xA4000000 + 0x1000
```

The candidate routed at:

```text
WNS=+0.604 ns
WHS=+0.010 ns
URAM=47
```

Its physical PSU-target reads nevertheless remained:

```text
0xA4000000 -> 0x4C543302
0xA4000004 -> 0x00000000
0xA4000008 -> 0x00000000
0xA400000C -> 0x00000000
```

Thus removing SmartConnect's 40-to-12 address-width conversion did not by
itself fix the physical nonzero-offset failure.

## Next discriminating build

A temporary read-only diagnostic behavior is added for otherwise unmapped
register reads:

```text
value = 0xD1A60000 | received_addr[11:0]
```

The physical diagnostic additionally reads `0xA4000018`, which is
intentionally unassigned by the MMIO ABI.

Expected interpretation:

- `0xA4000018 -> 0xD1A60018`: nonzero address accesses reach the custom
  slave, so investigation moves into synthesized register-decode behavior.
- `0xA4000018 -> 0x00000000`: the transaction/response is being lost or
  rejected upstream of the RTL default decode.

This signature is temporary diagnostic logic and is not part of the final
P03 MMIO ABI.


## Diagnostic-signature preflight correction

The first preflight after adding the unmapped-read signature reported:

```text
FAIL: resident-slot capability mismatch
FAIL: physical-engine capability mismatch
```

This was a testbench ordering bug, not an RTL failure.

The testbench read the capabilities register at `0x008`, checked only the
low capability flags, then overwrote `read_value` by reading the diagnostic
offset `0x018` before checking the resident-slot and physical-engine fields.

The assertions are now ordered correctly:

1. read `0x008`;
2. check flags, resident slots, and engine count;
3. then read/check `0x018`.


## Diagnostic-signature physical result

The diagnostic-signature candidate routed successfully:

```text
WNS=+0.412 ns
WHS=+0.014 ns
URAM=47
```

Physical PSU-target reads were:

```text
0xA4000000 -> 0x4C543302
0xA4000004 -> 0x00000000
0xA4000008 -> 0x00000000
0xA400000C -> 0x00000000
0xA4000018 -> 0x00000000
```

The intentionally unmapped `0x018` offset therefore did not return the RTL
diagnostic signature `0xD1A60018`.

This is evidence that nonzero-offset reads are being answered or rejected
upstream of the custom register block rather than reaching its default decode.

## HPM0 topology correction under test

The one-slave HPM0 control path no longer uses SmartConnect.

New path:

```text
PS M_AXI_HPM0_FPD (AXI4)
    -> AXI Protocol Converter
    -> p03_ps_control_regs (AXI4-Lite)
```

The accepted HP0/DDR SmartConnect path is unchanged.

The AXI Protocol Converter is a dedicated protocol bridge; with only one HPM0
control slave, no address-routing fabric is required on this path. The
temporary unmapped-read signature remains enabled until physical nonzero-offset
access is proven.
