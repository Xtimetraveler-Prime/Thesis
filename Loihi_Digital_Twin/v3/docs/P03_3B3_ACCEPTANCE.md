# P03.3b3 — Physical nonresident packet and dirty-paging acceptance

**Status:** ACCEPTED from independent physical KV260 user verification.  
**Accepted:** 2026-10-11 local (evidence folder UTC 2026-10-12).  
**Branch:** `agent/v3-p03-autonomous-runtime`; not merged.

## Independent evidence

The user ran the fixed standalone ELF on the accepted FPD128
SmartConnect P03 control-plane bitstream, then independently displayed
the strict verifier output:

```text
PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released
PASS: P03.3b3 standalone ELF downloaded to Cortex-A53 #0
P03.3b3 physical mailbox target: PSU
PASS: P03.3b3 A53 smoke executed and 128-byte mailbox dumped
PASS: P03.3b3 physical packet/page roundtrip ps_width=128 first_packet=0x2000000020000581 second_packet=0x2000000040000A00 core1_ddr_event1=11 core0_ddr_event0=20 page_ins=3 page_outs=3 dispatches=4 barriers=2 routed_packets=2
P03_3B3_VERIFY_EXIT=0
P03_3B3_EVIDENCE_DIR=/tmp/v3_p03_3b3_fixed_20261012T034337Z
PASS: P03.3b3 physical Cortex-A53 two-core HLS packet/DDR/dirty-page roundtrip
```

The user separately ran:

```bash
cat "$P03_3B3_EVIDENCE_DIR/verify.log"
```

which reported the same strict PASS.

## What is established

- PS FPD HPM0 is correctly boot-matched at 128 bits, routed to the
  accepted 32-bit custom MMIO interface via SmartConnect.
- The A53 owns actual two-core/two-step scheduling, page replacement,
  packet routing and global barrier decisions.
- The PL produced the exact two 64-bit packet words from the directed
  compiled workload. These were captured from resident packet bank 8,
  not synthesized by PS test software.
- The adapter routed events into **nonresident** DDR NEXT banks:
  core1 event1 = 11 and core0 event0 = 20.
- Physical dirty page-out and reload preserved the routed event
  while the scheduler completed three replacement page-ins,
  three mutable page-outs, four dispatches and two barriers.
- The 128-byte mailbox verifier independently asserted no faults
  and the expected physical output words/counts.

## Scope and follow-up

This test does **not** independently prove packet delivery via MMIO
to a destination **already resident** at routing time. That branch
was tested in the native C adapter mock; direct physical verification
remains useful for P03/P05 closeout.

The user has not supplied the raw bitstream/ELF SHA256 fingerprints,
which are retained in their local evidence directory. No SHA is
invented here. Previous preflight error-2 physical attempts are
historical and were resolved by fixing the inverted zero-is-success
check in the A53 probe.

**Decision:** Accept P03.3b3 directed physical nonresident routing and
dirty-context roundtrip. Proceed to the combined P03.3c/P03.4/P03.5
board-local golden workload. No change to accepted RTL or P02/v2 record.
