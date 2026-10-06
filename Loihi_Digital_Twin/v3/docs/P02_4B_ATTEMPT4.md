# P02.4b Physical Attempt 4 — PSU `verify -data` Invalid Context

**Date:** 2026-10-05  
**Result:** Provisioning harness failure before PL execution; P02 remains open.

## Evidence before failure

The retry successfully:

- generated the frozen 35-dispatch / 30-packet workload;
- halted the visible Cortex-A53 cores;
- selected the non-processor `PSU` target for physical DDR access;
- issued `dow -data` to physical address `0x40000000` without the prior A53
  MMU translation fault.

Observed:

```text
P02.4b physical DDR access target: PSU
P02.4b provisioning logical_core=0 address=0x40000000
```

The following `verify -data` command then failed with:

```text
Code 16 ... {Invalid context}
```

No PL page or dispatch command executed.

## Root cause

AMD documents non-processor APU/RPU/PSU targets as physical-memory targets for
memory read/write commands through the Arm DAP/AXI-AP path.

The installed XSDB accepts the physical `dow -data` write on PSU, but the
higher-level `verify -data` command rejects that active target as an invalid
context.

Therefore `verify -data` is not a portable verification mechanism for this
physical-target workflow.

## Correction

Provisioning verification now uses only physical-memory operations:

1. `dow -data <record> <physical_addr>`;
2. `mrd -bin -file <readback> <physical_addr> 131072`;
3. require the readback file to be exactly 512 KiB;
4. compare the readback file byte-for-byte with the source record.

The temporary readback is deleted after a successful comparison.

This keeps the entire provisioning/verification path on the non-processor
physical-memory target and removes dependence on an A53 execution/MMU context.

The same hardening was applied to the P02.4a reproduction script.

## Claim boundary

This attempt provides no new PL paging evidence because it failed during
debugger-side provisioning verification.
