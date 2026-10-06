# P02.4b Physical Attempt 3 — A53 MMU Address Translation Fault

**Date:** 2026-10-05  
**Result:** Harness provisioning failure before PL execution; P02 remains open.

## Failure

After rebooting the KV260, the third retry generated the accepted golden fixture
but failed on the very first DDR provisioning write:

```text
P02.4b provisioning logical_core=0 address=0x40000000
Memory write error at 0x40000000.
MMU fault at VA 0x40000000.
Translation fault, level 0
```

No DDR record was provisioned and no PL page/dispatch command executed.

## Root cause

The XSDB prepare script halted Cortex-A53 #0 and then left that **processor
target** selected while issuing:

```text
dow -data <record> 0x40000000
```

AMD's XSDB target model distinguishes processor and non-processor memory
accesses:

- with a Cortex-A53 processor target selected, memory commands are performed
  through that processor and the supplied address is interpreted through its
  MMU/cache context;
- with a non-processor PSU/APU target selected, debugger memory access uses the
  Arm DAP/AXI-AP path and the supplied DDR address is physical.

The rebooted Linux instance left an MMU mapping in which virtual address
`0x40000000` was not translated, producing the observed level-0 fault.

The earlier P02.4a/P02.4b provisioning successes therefore depended on the A53
being in a debugger state where this address happened to be accessible. That is
not a sufficiently reproducible physical-memory contract.

## Correction

The prepare sequence now:

1. selects/stops each visible Cortex-A53 only to prevent Linux from touching the
   project DDR window;
2. switches the active XSDB target to the non-processor `PSU`;
3. falls back to `APU` if PSU selection is unavailable;
4. performs every `dow -data` and `verify -data` from that physical-memory
   target.

The dump sequence likewise selects PSU/APU before every post-run `mrd`.

The P02.4b preflight now requires this physical-target selection contract.

## Claim boundary

This failure contains no new evidence about the PL page mover or the original
core-1 state mismatch because it occurred before DDR provisioning completed.
