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
