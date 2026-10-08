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
