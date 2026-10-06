# P02.4b — Five-Logical-Core / Three-Resident-Context DDR-Backed Workload

**Status:** Verification candidate  
**Phase:** P02 — DDR-backed logical-core virtualization  
**Branch:** `agent/v3-p02-4-physical-ddr`

## Purpose

P02.4a proved byte-exact physical transfer between K26 DDR and one resident
context slot.

P02.4b raises the acceptance boundary to the architectural paging problem:
five logical cores must execute through only three resident context slots while
K26 DDR remains the authoritative store for every non-resident context.

The external PC is still the P02 control plane. It may:

- choose service order and page victims;
- issue page/dispatch commands;
- inspect emitted packets;
- maintain small routing/event-count bookkeeping;
- insert routed destination axons into resident NEXT-event banks;
- collect final evidence.

It must **not** retain or restore complete non-resident context images from PC
RAM. Those images live in K26 DDR and move only through the accepted PL page
path.

## Workload

The directed physical workload is a five-core ring derived from the accepted v2
P08 paging regression boundary.

Each logical core contains:

- one compartment;
- one logical input axon;
- one synapse with weight 3;
- threshold 5;
- retained voltage state;
- one output route to the next logical core in the ring.

One external event is injected into every core on every algorithmic timestep.

This produces:

- an initial accumulation step with nonzero state and no spike;
- later threshold crossings;
- cross-core packets;
- state that must survive repeated eviction/reload;
- CURRENT/NEXT event-bank alternation;
- logical destination IDs that are independent of resident slot identity.

The frozen execution length is:

```text
logical cores       5
resident slots      3
physical engines    1
timesteps           7
dispatches          35
service order       0,1,2,3,4
initial residency   core 0 -> slot 0
                    core 1 -> slot 1
                    core 2 -> slot 2
```

## Golden fixture

`scripts/p02_4b_ring_fixture.py` builds the workload with the accepted Python
architectural model.

It emits:

- five initial 512 KiB DDR records;
- a Tcl dispatch oracle;
- expected event counts per core/timestep;
- expected post-dispatch state words;
- expected spike counts;
- exact expected packed packet words;
- five complete expected final 512 KiB DDR records;
- a deterministic manifest and normalized trace fingerprint.

The final-record oracle models the physical bank behavior, including stale raw
event words outside the active count, last-dispatch trace/packet contents, and
the fact that the PL page mover does not refresh the 4 KiB DDR header digest.

## Physical runtime

The accepted P02.3b2/P02.4a bitstream and probes are reused unchanged.

Before execution XSDB:

1. boots only as a debugger after PS DDR initialization;
2. halts the visible Cortex-A53 cores;
3. provisions logical records 0..4 at:

```text
core 0  0x4000_0000
core 1  0x4008_0000
core 2  0x4010_0000
core 3  0x4018_0000
core 4  0x4020_0000
```

using `dow -data`, followed by `verify -data`.

Vivado then programs the accepted shell and drives both existing VIOs:

- `vio_p02_page` for DDR page-in/page-out;
- `vio_p08` for debug memory access and one-core dispatch.

### Resident policy

Three physical slots are explicitly initialized with logical cores 0, 1, and 2.

A deterministic round-robin victim cursor is used on a miss.

If a resident victim is dirty:

```text
resident URAM -> mutable-only page-out -> victim logical DDR record
```

Then the requested logical context is loaded with a full page-in:

```text
requested logical DDR record -> full page-in -> resident URAM
```

Static context banks are never rewritten during normal eviction. Runtime state,
both event banks, trace, and packet images are written back through the accepted
104 KiB mutable-only path.

## Algorithmic timestep protocol

For each timestep:

1. Select CURRENT event bank from `timestep & 1`.
2. Service logical cores in order 0..4.
3. Before each core dispatch:
   - ensure that core is resident;
   - append one external event to its CURRENT bank;
   - verify the resulting event count against the Python golden oracle.
4. Dispatch that resident slot through the single HLS engine.
5. Require exact equality for:
   - active logical core ID;
   - selected resident slot;
   - selected event bank;
   - HLS/core status;
   - spike count;
   - packet count;
   - every packed output packet;
   - packed compartment state.
6. Mark the consumed CURRENT event count zero. Raw words are left in memory and
   are overwritten when that physical bank is reused.
7. After **all five logical cores have completed**, decode every actual packet.
8. Route each packet by its logical destination core ID.
9. Ensure the destination context is resident and append the destination axon to
   that core's NEXT bank.
10. Require every packet target timestep to equal `t + 1`.
11. Compare NEXT-bank event counts with the golden model.
12. Advance the global algorithmic barrier only after all packets have been
    committed.

The page policy is implementation-only and is excluded from logical identity.

## End-of-run flush

After timestep 6, every dirty resident slot is mutable-written back to its
logical DDR record.

At that point all five complete final context images are authoritative in K26
DDR, regardless of final residency.

Vivado records:

- completed dispatches;
- barriers;
- routed packet count;
- page-ins;
- page-outs;
- evictions;
- page hits;
- AXI read/write burst totals;
- total AXI bytes.

XSDB then dumps all five final 512 KiB records.

The Python verifier requires each complete record to equal the corresponding
golden expected record byte-for-byte.

## Why this is the P02 workload

The workload intentionally targets the P02 research question rather than
benchmark accuracy.

Compared with the single-dispatch v2 physical evidence, it physically exercises:

- more logical cores than resident slots;
- all three resident slots;
- repeated dirty eviction and reload;
- retained architectural state across page replacement;
- logical packet destination independent of physical residency;
- both event banks;
- multiple global algorithmic barriers;
- full and mutable DDR transfer paths;
- five authoritative DDR backing records.

The full source-recovered MNIST application remains a later P03/P07 end-to-end
target. P02.4b is not presented as a physical MNIST inference result.

## Acceptance

P02.4b passes only if:

- the offline golden/preflight gate passes;
- the accepted P02.3b2 artifact identities are unchanged;
- all five initial DDR records are provisioned and verified;
- three initial physical resident slots are established;
- all 35 dispatches match the golden event/state/spike/packet boundary;
- all seven barriers complete only after packet delivery;
- physical eviction/page-in occurs;
- page transfer burst/byte accounting is internally exact;
- all five final DDR records match their golden images byte-for-byte;
- the final physical result identifies `authoritative_backing=k26-ddr`.

Primary scripts:

```text
scripts/p02_4b_ring_fixture.py
scripts/run_p02_4b_preflight.sh
scripts/run_p02_4b_five_over_three.sh
vivado/p02_4b_five_over_three.tcl
vivado/p02_4b_xsdb_prepare.tcl
vivado/p02_4b_xsdb_dump.tcl
```

## Claim boundary

A clean P02.4b result proves the P02 DDR-backed virtualization mechanism for a
directed five-logical-core workload.

It does not prove:

- autonomous PS scheduling/routing/barrier ownership;
- absence of a PC control plane;
- full MNIST physical inference;
- final board-local latency/power/energy.

Those belong to P03, P07, and P08.


## Physical attempt 1 diagnostic update

The first physical P02.4b attempt reached initial residency, then failed at
timestep 0 because logical core 1 retained state `0x0` instead of the golden
`0x03000000`.

The retry candidate now performs exact resident-image readback after page-in and
exact external-event readback before every dispatch. This is diagnostic
instrumentation only; the workload and acceptance semantics are unchanged.

See `docs/P02_4B_ATTEMPT1.md`.


## Physical attempt 2 diagnostic update

The resident-image diagnostic initially failed because the Tcl helper sampled
debug ACK and RVALID/RDATA using separate VIO refreshes across the arbiter's
response-ownership window. The retry candidate captures ACK/RVALID/ERROR/RDATA
from one VIO refresh for every debug transaction.

This is a harness correction only. The original core-1 physical state mismatch
remains unresolved pending the next board run.

See `docs/P02_4B_ATTEMPT2.md`.


## Physical attempt 3 diagnostic update

A later reboot exposed an XSDB address-space dependency: leaving Cortex-A53 #0
selected caused `dow -data ... 0x40000000` to treat the backing address through
the processor MMU and fail with a level-0 translation fault.

The reproduction path now halts the A53 cores for safety but performs all DDR
provision/dump operations from the non-processor PSU target, with APU fallback.
This makes the P02 backing addresses physical debugger addresses rather than
Linux virtual addresses.

See `docs/P02_4B_ATTEMPT3.md`.


## Physical attempt 4 diagnostic update

The physical-target correction reached the non-processor `PSU` target and
successfully issued the binary download, but XSDB `verify -data` rejected the
PSU context.

The current reproduction path therefore verifies each provisioned 512 KiB
record using physical `mrd -bin -file` readback followed by an exact binary
comparison. The entire transaction remains on PSU/APU and no processor/MMU
context is required.

See `docs/P02_4B_ATTEMPT4.md`.


## Physical attempt 5 diagnostic update

The latest physical run completed timestep 0 for all five logical cores and
passed barrier 0. During timestep 1, logical cores 0, 1, and 2 reloaded with
correct static images, but logical core 3 reloaded with route word 0 equal to
zero instead of the expected `0x00000704`.

Because core 3's route had verified correctly on its earlier timestep-0 page-in,
the next diagnostic is a post-failure PSU/APU DDR dump before reboot. All static
banks are compared against their initial fixture images to distinguish DDR
corruption from later page-in materialization loss.

See `docs/P02_4B_ATTEMPT5.md`.


## Paging-only stress result

The exact pre-failure page-transfer sequence was replayed physically without
compute/event activity and passed:

- 9 full page-ins;
- 6 mutable-only page-outs;
- 15,408 AXI read bursts;
- 2,496 AXI write bursts;
- 4,583,424 AXI bytes;
- exact resident static-image verification after every load.

The final core-3 to slot-2 reload was correct. Therefore the route-loss trigger
is not the paging sequence by itself; it requires interaction with the full
dispatch/debug workload path.


## Physical attempt 6 root cause

An attach-only probe after the apparent post-page-out config mismatch repeatedly
read the correct resident config and route without rebooting or reprogramming.
The apparent zero was therefore a stale debug-response artifact, not URAM
corruption.

The root cause is a request-level re-arm in `p02_page_host_arbiter`: a VIO
debug request can remain asserted after ACK long enough for the arbiter to
re-arm while the previous P05 ACK/RVALID remain visible.

The arbiter now latches a completed debug ACK/RVALID/ERROR/RDATA response and
holds it until the VIO request returns low. While that response is pending, the
same request cannot re-arm. This both removes the stale-response race and keeps
the response visible long enough for software polling. A dedicated held-request
simulation freezes this behavior.

This RTL change requires a newly routed P02 shell and new artifact fingerprints
before the physical P02.4b gate can resume.

See `docs/P02_4B_ATTEMPT6.md`.


## Arbiter-fix routed candidate

The corrected page/debug arbiter was rerouted successfully on K26 with:

- WNS: +0.807 ns;
- WHS: +0.010 ns;
- 47 URAM;
- 3 resident contexts;
- 1 physical engine;
- 128-bit HP0 transport.

The current P02.4b candidate artifacts are:

```text
bitstream_sha256=0d96ae6af0cc313ccbd8f9c802aeb0c8c7946bfeabaca3152ef5c7b9d2b23f26
probes_sha256=f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
```

See `docs/P02_4B_ARBITER_FIX_ROUTE.md`.
