# P05.2b — Fast/no-checkpoint physical equivalence ACCEPTED

**Physical evidence:** User-supplied independent KV260 `verify.log`,
2026-10-12. Existing accepted P05 A53 ELF and P03.2c FPD128
FPGA bitstream unchanged. P05.2b **physically accepted**.

**Physical result:**
```text
PASS: P05.2 fast/no-checkpoint A53 triangle timesteps=5 dispatches=15 packets=12 resident_deliveries=12 barriers=5 events=15 checkpoints=0
PASS: P05.2 fast mode three final 512KiB DDR records byte-exact to BOTH independent Python oracle and earlier physical diagnostic-mode KV260 SHA256s
```

**Reported deployment identity:** P05G header CRC32 `0x76E6409B`,
payload CRC32 `0x1AF530B0`. Neural model reference trace fingerprint
`c2fde59f694508003fb6b0d17f5ed2945db5f03c427a2690b13acc7bc71b717e`.
The trace fingerprint remains a Python **reference**, not a captured full
intermediate physical trace.

**Actual physical three full-record SHA-256s**, equal to the
independently recorded P05.1 *diagnostic-mode* run and the
Python golden:
- core 0: `5c4288e41e1599aea5f854a4022fb88a6b04ddc003b01238e16f5a7c59665381`
- core 1: `2767f8cbca59d8e9bb85d0f37d055a7b4a7c4e94676d56bbd3efeff4f4f6c0f2`
- core 2: `d6c8982882023c8b0065ca856a3caf35a1b6fa54196a6fb546b774deca32c82f`

**Counters (same run):** `pl_dispatch_cycles=357`,
`ps_inference_ticks=25994`, checkpoint observations `0`.
No published performance or calibrated speedup claim is justified
by these independent timing-domain counters.

**Conclusion:** For the accepted three-core triangle and its
five timesteps, disabling model-derived checkpoint reads
did not change final neural results or packet/dispatch/routing
counters. Fast/no-checkpoint mode physically works for this
case. This is **not** proof of timing equivalence, benchmark
efficiency or all supported workloads.

P05.2c begins testing deterministic **permuted service order**
while holding the same neural model, core IDs, external events,
hardware and ELF fixed. Arithmetic boundary vectors, packet
fanout/backpressure, dirty paging/replacement and metric
provenance remain P05.2 gaps. P05.2 overall is still IN PROGRESS.
No merge to `main`.
