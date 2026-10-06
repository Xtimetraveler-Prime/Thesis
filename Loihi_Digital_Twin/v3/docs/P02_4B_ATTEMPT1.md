# P02.4b Physical Attempt 1 — Core-1 State Mismatch

**Date:** 2026-10-05  
**Result:** Physical workload failed during timestep 0; P02 remains open.

## Evidence before failure

The run successfully:

- generated the frozen 35-dispatch / 30-packet golden workload;
- provisioned and XSDB-verified all five 512 KiB K26 DDR backing records;
- programmed the accepted P02.3b2/P02.4a shell;
- full-page-loaded logical cores 0, 1, and 2 into the three resident slots;
- established initial residency `{0,1,2}`.

Observed markers:

```text
PASS: P02.4b five-over-three golden fixture generated dispatches=35 packets=30
PASS: P02.4b five authoritative DDR backing records provisioned and verified
PASS: P02.4b initial residency logical={0 1 2} physical_slots=3
```

## Failure

During algorithmic timestep 0, logical core 1 completed its dispatch but its
packed state word remained zero:

```text
P02.4b mismatch state t=0 core=1:
actual=0x0
expected=0x3000000
```

The expected value corresponds to the directed core receiving one weight-3
input and retaining voltage 3 below threshold.

The run stopped immediately. No P02.4b acceptance is claimed.

## Diagnostic interpretation

Core 0 had already passed the same timestep-0 state check, so the generic HLS
arithmetic path is not the first suspect.

P02.4a physically accepted the DDR transport using resident slot 0 only.
P02.4b is the first physical gate that depends on DDR page-in to all three
resident slots. The existing v2 P05 physical evidence had already exercised all
three context slots when loaded directly through the debug/host port.

Therefore the next retry instruments the boundary introduced by P02:

1. after each DDR page-in, read back the resident config word;
2. read the expected sparse axon descriptor at its logical axon index;
3. read synapse 0;
4. read route descriptor 0;
5. read route 0;
6. for initial residency, read initial state 0;
7. after every external event write, read that event word back before dispatch.

This distinguishes:

- wrong/stale DDR record selection;
- wrong resident-slot page destination;
- lost host event insertion;
- HLS execution/slot-consumption error.

The neural workload is intentionally unchanged; changing axon IDs or expected
semantics to hide the mismatch would invalidate the P02 paging test.
