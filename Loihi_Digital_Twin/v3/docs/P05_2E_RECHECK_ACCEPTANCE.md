# P05.2e — Independent retained-physical-evidence recheck

**Physical-evidence decision:** PASS, user independently reported on 2026-10-12.
**Branch:** `agent/v3-p05-board-regression` (NOT merged).
**Evidence location on user's machine:**
`/tmp/v3_p05_2_composite_20261012T190000Z/verify_route_order.log`.

This closeout is limited to the separately documented P05.2e physical
five-over-three composite gate. The original unsuccessful full-DDR
comparison and original evidence are intentionally preserved. It is
not a claim that the original sorted logical packet-RAM oracle was
physically correct or that the original run's generic A53 success
terminal alone established correctness.

## User-supplied independent recheck output

```text
PASS: P05.2e physical FIVE-over-THREE composite order=4,1,3,0,2 steps=8 dispatches=40 packets=48 resident_deliveries=24 nonresident_deliveries=24 barriers=8 events=40 checkpoints=40 replacement_ins=37 runtime_outs=37 evictions=37
PASS: P05.2e five complete 512KiB physical DDR records byte-exact to independent mixed-threshold LogicalChip neural model with separately derived physical output-route packet RAM ordering
PASS: P05.2e original A53/FPGA/mailbox/P05G and FIVE physical DDR records unchanged
PASS: P05.2e original normalized neural Python oracle unchanged; corrected *only* derived physical packet RAM word order
P05_2E_RECHECK_EXIT=0
```

The committed recheck source requires the original core3 packet0
0x04 physical / 0x00 logical mismatch, freezes original evidence SHA-256
identities before and after, re-derives the physical route-ordered packet
oracle solely from independent model + packed route configuration,
compares all **five complete original 512KiB physical DDR dumps** and
all original runtime/checkpoint/counter and P05G checks. No bank is
masked or skipped. It creates a new physical-layout oracle and ledger
beside the original logical golden.

This evidence establishes the P05.2e physical gate. The user supplied
only the recheck PASS-filter output here; native pytest regression
totals/exit logs were **not supplied in this reply**, so those are not
misrepresented as freshly witnessed. Before closing P05.2 overall,
reproduce the native regression suite, including the earlier
failed-packet-layout negative test.

## What it does NOT close

Signed saturation/decay boundary behavior, 4096-entry event-bank
backpressure/recovery, adversarial barrier behavior, and calibrated
physical memory-traffic counter provenance remain open P05.2 coverage
items. P05.2f addresses several arithmetic dimensions together, not
event-bank limit testing. No changes to accepted P03 runtime, golden
model, FPGA shell or A53 binary are implied by this acceptance.
