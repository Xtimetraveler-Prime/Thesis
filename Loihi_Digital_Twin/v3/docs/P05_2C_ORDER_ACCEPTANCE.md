# P05.2c — Legal service-order physical invariance ACCEPTED

**User-supplied KV260 physical PASS** (2026-10-12).
The A53 actually serviced **logical core 2, then 0, then 1**
within each timestep, as directed by P05G input manifest,
while running the unchanged P05 ELF and P03.2c PS/PL design.
This is a different scheduler order than accepted P05.1
`0→1→2`, not a simple reorder of reported results.

```text
PASS: P05.2c permuted service-order physical golden order=2,0,1 timesteps=5 dispatches=15 packets=12 resident_deliveries=12 barriers=5 events=15 checkpoints=15
PASS: P05.2c three full 512KiB DDR records byte-exact to BOTH independently reordered and baseline Python models and previously accepted original-order KV260 physical SHA256s
```

**P05G CRC32s**: Header `0x22ECC007`, payload
`0xC0AFC18C`. Independent reference model trace
fingerprint `c2fde59f694508003fb6b0d17f5ed2945db5f03c427a2690b13acc7bc71b717e`
(the model's trace fingerprint, **not** independently
collected intermediate physical trace).

**Actual complete physical DDR SHA256s** (matching both
Python permutations and accepted prior diagnostic/fast
KV260 results):

| Core | 512KiB physical final record SHA-256 |
|---|---|
| 0 | `5c4288e41e1599aea5f854a4022fb88a6b04ddc003b01238e16f5a7c59665381` |
| 1 | `2767f8cbca59d8e9bb85d0f37d055a7b4a7c4e94676d56bbd3efeff4f4f6c0f2` |
| 2 | `d6c8982882023c8b0065ca856a3caf35a1b6fa54196a6fb546b774deca32c82f` |

**Scope:** P05.2c service-order permutation
`[0,1,2]→[2,0,1]` with three resident cores and no
page replacements physically **accepted**.
It verifies both direct resident next-event routing
and global timestep-order invariant final states for
this directed workload, **not** arbitrary legal
permutations under five-over-three paging.

**Remaining:** Broad fanout/event-buffer pressure,
arithmetic boundaries, replacement paging, barrier
pathologies, and counter/AXI observability. P05.2
overall still active. Branch not merged to `main`.
