# P05.2f — Physical signed arithmetic/decay/refractory acceptance

**Status: PHYSICAL PASS — independent user-reported KV260 evidence (2026-10-12).**
**Branch:** `agent/v3-p05-board-regression` (unmerged).
**Evidence path:** user-provided `"$P05_2F_DIR/verify.log"` excerpt;
the exact expanded directory path and artifact SHA-256 identities
were not included in this reply.

## Real KV260 results independently submitted by user

```text
PASS: P05.2f physical five-over-three signed/decay/saturation/refractory steps=6 dispatches=30 packets=8 resident_deliveries=8 nonresident_deliveries=0 barriers=6 checkpoints=30 evictions=27
PASS: P05.2f five complete 512KiB physical DDR images byte-exact to independent signed 24-bit LogicalChip reference
P05_2F_VERIFY_EXIT=0
```

The strict physical verifier is `scripts/p05_2f_arithmetic_verify.py`.
The reported result indicates an actual A53 terminal satisfying
the required 30 dispatches, six barriers, 30 checkpoint CRCs and
five complete, unmasked 512 KiB DDR images exactly matching the
separately generated Python `LogicalChip` reference. The fixture
encodes +/− signed 24-bit saturation, signed weight, decay
endpoints/fractions, refractory, and dirty victim paging. One
physical FPGA HLS engine and three context slots were used.
The accepted original P03 shell and existing P05 A53 ELF remain
unchanged.

## Coverage boundaries

- **All eight packets were delivered to already-resident
  destinations.** This run does **not** demonstrate nonresident
  delivery. P05.2e independently demonstrated 24 resident and 24
  nonresident deliveries, including repeated dirty paging.
- The physical output snippet does not include pytest totals, raw
  ELF/XSA/bitstream SHA-256 identities, or the full mailbox JSON.
  Do not claim these were independently reviewed here.
- A 4,096-event bank, overflow/backpressure, and calibrated AXI
  traffic remain separate acceptance gates.

**Disposition:** Accept the intended P05.2f physical functional
gate, with the explicitly reported scope. Retain native-suite
reverification at P05.2 closure.
