# P05.2a — First-error detection physically accepted

**Accepted on KV260 2026-10-12**, user-reported physical XSDB/mailbox
log and independent `verify.log`, `P05_2_FAULT_VERIFY_EXIT=0`.
Evidence: `/tmp/v3_p05_2_fault_20261012T181015Z`.

The only injected fault was flipping **one bit in the expected
state0 checksum** at checkpoint index 7 (completed timestep
2, logical core 1). The 3×512 KiB neural initial records,
15 inputs, routes, thresholds and weights remained equal
to the independently verified P05.1 triangle. This was
*not* an injected error in FPGA arithmetic.

Physical A53 stopped with intentional terminal **`0xDEAD000A`**
after one passive host polling iteration. Strict verifier:

```text
PASS: P05.2 deliberate bad checkpoint REJECTED by real A53 terminal=0xDEAD000A fault=11 fault_phase=13first_mismatch_timestep=2 core=1 class=state0 expected_bad_crc=0x6522DF68 observed_model_crc=0x6522DF69 dispatches_before_stop=9 packets=6 resident_deliveries=6 completed_barriers=2 checkpoints_passed=7
PASS: P05.2 prior real neural records/events unchanged; rejected only deliberately incorrect model expectation
P05_2_NEGATIVE_VERIFY_EXIT=0
P05_2_FAULT_VERIFY_EXIT=0
```

The joined `fault_phase=13first_mismatch` is purely console
formatting; the independent P05R verifier separately checked
the numerical values.

**Meaning:** the board reached the intended quiescence
barrier, correctly read the actual FPGA state0 checksum
`0x6522DF69` (matching the clean independent Python oracle),
rejected the deliberately wrong checksum `0x6522DF68`,
and reported exact first-error core, timestep, state class,
counters and sticky fault phase. The host did **not** issue
per-dispatch controls. An arbitrary failure would have failed
the strict gate.

No final DDR equality was claimed after early halt: resident
contexts were dirty and finalization was intentionally skipped.

**Acceptance scope:** P05.2a first hardware error-localization
gate **complete**. No claim that arbitrary naturally occurring
computation faults or all packet/backpressure faults have
physical first-error characterization. P05.2 overall remains
active. The next gate is P05.2b checkpoint-disabled/fast-mode
physical golden equivalence, followed by directed arithmetic,
fanout, pressure, paging and service-order coverage.
