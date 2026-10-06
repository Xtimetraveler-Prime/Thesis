# P02.4b Physical Attempt 5 — Static Route Lost After Evict/Reload

**Date:** 2026-10-05  
**Result:** Physical paging failure after timestep-0 barrier; P02 remains open.

The run successfully verified all three initial resident images, loaded and
verified logical cores 3 and 4 during timestep 0, completed all five timestep-0
dispatches, and passed barrier 0.

During timestep 1, logical cores 0, 1, and 2 were reloaded and their static
images verified. Reloading logical core 3 into slot 2 then failed:

```text
P02.4b mismatch resident route core=3 slot=2:
actual=0x00000000
expected=0x00000704
```

Core 3's static route had previously verified correctly when core 3 first
entered residency during timestep 0. The failure is therefore bounded between
that accepted resident image, its later mutable-only eviction, and the
subsequent full reload from authoritative DDR.

The next diagnostic dumps the current five DDR records before reboot and
compares every static bank against its original fixture. This distinguishes
static DDR corruption from a later page-in/materialization failure.

Primary tools:

```text
scripts/run_p02_4b_forensic_ddr.sh
scripts/p02_4b_forensic_ddr.py
```


## Forensic result

The post-failure physical DDR dump preserved every static bank for all five
logical cores. In particular, logical core 3 retained:

```text
P02_4B_FORENSIC_ROUTE0 core=3
actual=0x00000704
expected=0x00000704
```

Therefore mutable page-out did not corrupt the authoritative DDR route image.

The remaining failure boundary is the later DDR-to-resident materialization.

## Paging-only replay

A dedicated physical stress gate now reproduces the exact sequence of page
transfers that occurred before the failure, but removes:

- HLS dispatch;
- external event injection;
- routed packet handling;
- algorithmic barrier logic.

It performs 9 full page-ins and 6 mutable page-outs, ending with the same target
operation:

```text
logical core 3 -> resident slot 2
```

Every page-in verifies the resident static image immediately.

Primary harness:

```text
scripts/run_p02_4b_paging_stress.sh
vivado/p02_4b_paging_stress.tcl
```

If this gate reproduces the route loss, the defect is fully inside the paging
transport/materialization path. If it passes, compute/debug activity is required
to trigger the failure and the next diagnostic must include those interactions.


## Paging-only physical replay result

The directed paging-only replay completed successfully after a board reboot.

Observed:

```text
P02_4B_STRESS_PAGE_INS=9
P02_4B_STRESS_PAGE_OUTS=6
P02_4B_STRESS_AXI_READ_BURSTS=15408
P02_4B_STRESS_AXI_WRITE_BURSTS=2496
P02_4B_STRESS_AXI_BYTES=4583424
PASS: P02.4b paging-only stress reproduced exact pre-failure transfer sequence without compute
PASS: P02.4b paging-only physical stress gate completed.
```

Every resident static image, including the final logical-core-3 to slot-2
reload, matched its golden source.

This proves the page-transfer sequence alone does not reproduce the route loss.
The trigger requires activity present in the full workload path, such as
dispatch, event/debug access, or an ownership handoff surrounding those
operations.

The full workload retry now checks static resident integrity immediately before
and after every mutable eviction and requires zero pending write-buffer bytes
after every page transfer.
