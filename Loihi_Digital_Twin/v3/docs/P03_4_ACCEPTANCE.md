# P03.4 — Five-over-three autonomous physical acceptance

**Status:** Accepted from independently provided KV260 physical output, 2026-10-12 UTC (2026-10-11 Denver local).  
**Branch:** `agent/v3-p03-autonomous-runtime`; do not merge without explicit approval.  
**P03.5:** pending 100-step physical run.

## User-verified seven-timestep physical results

The user confirmed that the complete corrected V2 A53 runner and strict
post-run golden verification passed:

```text
PASS: P03 autonomous five-over-three P02/v2 normalized golden timesteps=7 dispatches=35 packets=30 resident_deliveries=0 barriers=7 page_ins=35 page_outs=35 trace_sha256=9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac manifest_sha256=ce94b1127c33ccb64ea397a8f84546ef4a8fdd1d6ce6d21ecd6bdaaedb92aae0
PASS: P03 all five final 512KiB DDR records byte-exact to frozen Python P02 oracle
```

The user supplied `verify.log` containing a successful
`P03_RESULT_METADATA` object:

- `dispatches=35`; `packets=30`; `timesteps=7`;
- `page_ins=35`; `page_outs=35`; `resident_deliveries=0`;
- `ps_timer_hz=99999001`, `inference_ticks=21819988`;
- `pl_dispatch_cycles=865`, `pl_page_cycles=22964299`;
- all five final record SHA-256s as reported in the user's original
  physical evidence were produced by the same strict verification run.

The seven-step runtime was autonomous *within its algorithmic loop*:
the PC provisioned the records and config, started the A53, passively
polled the terminal mailbox, and read back final memory. The A53
performed scheduling, physical page replacement, ingress event
injection, FPGA dispatch, packet delivery, barriers, and final flush.

The P03 reference used the frozen P02.4b five-core ring and its
accepted seven-step trace fingerprint. Its exact final five 512 KiB
DDR images matched, rather than checking only counters.

## Scope

This physically demonstrates five logical cores time-multiplexed
through three resident slots and one FPGA HLS inference engine over
seven complete algorithmic timesteps, under the A53 control plane,
with repeated dirty DDR paging and actual FPGA-generated packets.

`resident_deliveries=0` is **not** proof of MMIO direct packet
delivery into an already-resident target. The physical five-over-three
ring exercises nonresident routing for this order; the already-resident
destination branch remains supported by native adapter tests but not
yet by an independent targeted physical probe.

No latency/power/energy claims are made from raw counters alone.
No change to accepted FPGA bitstream, DDR ABI, or golden arithmetic
was required after the V2 finalization-fault fix.

## Next gate

Proceed to **P03.5**, same accepted V2 ELF and routed FPD128 bitstream,
with `scripts/run_p03_finish.sh 100 <new-evidence-dir>`.
This creates a fresh 100-step frozen P02-ring model oracle requiring
**500 dispatches, 100 barriers** and five byte-exact final DDR records,
while keeping all scheduling/routing/barrier decisions on the A53.
Reboot the KV260 before and after the standalone physical run.
No P03.5 physical acceptance is claimed yet.
