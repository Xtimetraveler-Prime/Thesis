# P05.2h — Independently accepted KV260 physical adversarial barrier test

**Status: PHYSICAL PASS (user-provided device verification, 2026-10-13).**
**Branch:** `agent/v3-p05-board-regression` (not merged).

## Original user-observed physical verification

```text
PASS: P05.2h physical adversarial 5-over-3 bank/barrier order steps=16 dispatches=80 packets=156 resident_deliveries=78 nonresident_deliveries=78 barriers=16 checkpoints=318 evictions=77
PASS: P05.2h both event-bank first words, state0 and emitted physical packet0 checkpointed at each barrier
PASS: P05.2h all five complete physical 512KiB DDR records byte-exact to model-derived route-ordered golden
P05_2H_VERIFY_EXIT=0
```

The user additionally stated that the test passed; a native pytest
count was not included in this message. The displayed `verify.log`
excerpt establishes the strict live A53 terminal and complete
device DDR verifier's conclusion, but does not separately list
original ELF/XSA SHA or the user's fully expanded evidence folder.

**Accepted coverage:** 16 global barriers, 80 physical HLS
dispatches, 318 model-derived per-barrier state/event0/event1/
packet0 checkpoint CRCs, 156 packets including 78 resident
and 78 nonresident destinations, 77 real victim evictions,
and five FULL unmasked 512 KiB raw DDR final records equal to
the logical-neural oracle with independently derived
registered physical output-route order.

**Limit:** This is neither runtime NEXT-bank overflow/recovery
nor an independent calibration of the FPGA page AXI traffic
counters. Both remain open. The P05.2i closeout gate will
evaluate hardware burst and byte accounting and write a
scope-conscious physical acceptance report. Do not invent
an unobserved routed-overflow recovery.
