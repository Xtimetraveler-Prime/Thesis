# P05.2g — Independent physical event-bank capacity acceptance

**Status: PHYSICAL PASS, independent user-reported KV260 execution, 2026-10-12/13.**
**Development branch:** `agent/v3-p05-board-regression` (unmerged).

## Exact supplied physical evidence

```text
/tmp/v3_p05_2g_capacity_20261013T004149Z/full/verify.log:PASS: P05.2g exactly 4096 genuine FPGA CURRENT-bank input events, 1 dispatch, 1 barrier, 3/3 device checkpoints
/tmp/v3_p05_2g_capacity_20261013T004149Z/full/verify.log:PASS: P05.2g complete 512KiB real DDR record byte-exact to independent full-bank Python oracle
/tmp/v3_p05_2g_capacity_20261013T004149Z/full/verify.log:P05_2G_FULL_VERIFY_EXIT=0
/tmp/v3_p05_2g_capacity_20261013T004149Z/overflow/verify.log:PASS: P05.2g CRC-valid 4097-event descriptor rejected by real A53 before MMIO/dispatch with 0xDEAD0002
/tmp/v3_p05_2g_capacity_20261013T004149Z/overflow/verify.log:PASS: P05.2g no dispatch/page/barrier andoriginal full 512KiB device DDR record unchanged
/tmp/v3_p05_2g_capacity_20261013T004149Z/overflow/verify.log:P05_2G_OVERFLOW_VERIFY_EXIT=0
```

The user separately confirmed successful native regressions, without
a full pytest summary. The physical result uses a **complete**
512 KiB DDR comparison at exactly 4,096 CURRENT input events and
three real barrier observations (state0/event0/event1). The
CRC-valid 4,097-event P05G was **specifically** rejected at
descriptor admission with `0xDEAD0002`, zero dispatch/page/barrier,
and an unchanged full DDR record. No acceptance is inferred from
synthetic P05R mailboxes or a generic A53 error.

**Do not overclaim:** This does not physically show a 4,097th
routed packet, in-loop backpressure, or automatic recovery after
a runtime route overflow. The NEXT-bank 4,095/4,096 overflow
boundary has a separate portable C test with synthetic I/O,
not a physical test. AXI bus-traffic provenance is also unproven.

Acceptance procedure and guarded inputs: `P05_2G_CAPACITY_GATE.md`.
P05.2h/remaining runtime packet/barrier load validation stays open;
do not merge P05 or mark all of P05.2 complete.
