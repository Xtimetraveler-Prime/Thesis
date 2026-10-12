# P05.1 second physical acceptance — three-core resident triangle

**Decision:** **ACCEPTED** from the user's independent KV260 physical run
on 2026-10-12. **P05.1 functional subphase COMPLETE** with explicit
P05.2 follow-up for diagnostic negative/fast-mode physical hardening.

**Evidence directory (on user's Ubuntu host):**
`/tmp/v3_p05_1_triangle_20261012T175547Z`.
**Branch:** `agent/v3-p05-board-regression` (not merged to `main`).

## Observed terminal and strict result

```text
P03 board-local terminal result=0x600D600D after 1 poll(s)
PASS: P05.1 3-core resident triangle physical golden
      timesteps=5 dispatches=15 packets=12 barriers=5
      events=15 checkpoints=15 resident_deliveries=12
      initial_ins=3 replacement_ins=0 final_outs=3
PASS: P05.1 three 512KiB final DDR records byte-exact to
      independent 3-core Python LogicalChip oracle
P05_1_TRIANGLE_VERIFY_EXIT=0
PASS: P05.1 SECOND independent 3-core resident triangle
      15-checkpoint physical gate
```

**Physical P05G ABI:** Header CRC32 `0x7D2F877B`, payload CRC32
`0x46400C0B`. **Independent reference-model trace fingerprint:**
`c2fde59f694508003fb6b0d17f5ed2945db5f03c427a2690b13acc7bc71b717e`
(not an independently captured physical trace).

**Final, byte-exact 512 KiB DDR images:**

| Logical core | Physical final DDR record SHA-256 |
|---|---|
| 0 | `5c4288e41e1599aea5f854a4022fb88a6b04ddc003b01238e16f5a7c59665381` |
| 1 | `2767f8cbca59d8e9bb85d0f37d055a7b4a7c4e94676d56bbd3efeff4f4f6c0f2` |
| 2 | `d6c8982882023c8b0065ca856a3caf35a1b6fa54196a6fb546b774deca32c82f` |

Three resident slots held the three logical cores throughout; the
physical instrumentation reported **12 resident deliveries**.
This closes the missing *physical path coverage* identified in
P03/P05.1's first test (`resident_deliveries=0`). No replacement
paging occurred in this directed topology. The different neural
threshold (4 vs 5), three-core network, five-timestep horizon
and different golden images establish this is not a disguised P03
replay. Both P05.1 physical workloads used the **same isolated P05
A53 ELF**, the accepted FPD128 shell and unchanged P03 scheduler/
adapter; the host provisioned once, passively polled and dumped
final DDR, not controlled algorithmic timesteps.

## P05.1 closeout ledger

| Component | Status |
|---|---|
| Python P05G generator and C11 fail-closed deployment validator | Host tests independently reported PASS |
| Versioned bounded inputs, core/slot choices, deterministic order | Implemented and physically exercised with 5 and 3 cores |
| Separate standalone A53 program, accepted P03 scheduler/adapter | Vitis ELF independently built and physically executed |
| First five-over-three P02 ring (7 steps, 35 checkpoints) | **Physical PASS**, `docs/P05_1_FIRST_PHYSICAL_ACCEPTANCE.md` |
| Second three-over-three resident triangle (5 steps, 15 checkpoints) | **Physical PASS** (this record) |
| Independent full-record oracle comparisons | Five and three complete DDR images byte-exact |
| First mismatch fields and malicious/altered mailbox handling | Host synthetic-negative regressions; **physical negative test not yet run** |
| Fast/passive no-checkpoint mode | Encoded in v1 descriptor and native tests; **separate physical fast-mode run not yet performed** |

The original P05.1 functional gate required two distinct valid
deployments executing autonomously with byte-exact model results and
useful state checkpoints. Both now passed on actual KV260, and
the user expressly authorized closure. **P05.1 complete under
the agreed functional milestone**. Claim **no physical negative
first-fault test** and **no validated low-overhead fast-mode
equivalence yet**: P05.2 will perform both as directed hardware
robustness/observability tests, without retconning the P05.1 PASS.

P05.2 still requires broad directed arithmetic, fanout,
backpressure, barrier, event-capacity, paging/eviction,
service-order and counter-provenance coverage. P05 overall
is **not complete**. No branch merge to `main` authorized.
