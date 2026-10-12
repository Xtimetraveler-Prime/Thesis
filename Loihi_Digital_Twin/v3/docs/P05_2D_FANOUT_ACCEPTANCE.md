# P05.2d — Physical two-route fanout accepted

**Accepted physical KV260 gate** from user's independent `verify.log`
(2026-10-12); same existing P05 A53 ELF and P03.2c
FPD128 bitstream. Three logical cores were permanently
resident in three physical context slots.

```text
PASS: P05.2d physical two-route fanout model timesteps=5 dispatches=15 packets=24 resident_deliveries=24 barriers=5 events=15 checkpoints=15
PASS: P05.2d three complete 512KiB final DDR records byte-exact to independent fanout LogicalChip model (2 routes/source; two NEXT deliveries/destination on firing timesteps)
```

**P05G identity:** header CRC32 `0xD6B1D9AC`,
payload CRC32 `0x20423406`; Python reference trace
SHA-256 `931ce506074695b567f97076b0b58bc65d796dd4c468e4d320a9e02b9182a759`
(is a *model reference*, not a captured physical step-by-step trace).

**Complete physical 512KiB final DDR record SHA256:**
- core0 `f545f5d7fa3d896ad2792ada1515f2db9676d80b7095ec8c8c817ca1d5e95da6`
- core1 `051d61da564a0d160265c620f384c7ede18c88f2551b146a6bdb556edb428a27`
- core2 `b806caf750a820b050a73f280d3ebdf08893b4d8b66a6a2d87ccdc77630807c4`

**Scope of proof:** each firing source emitted two routed packets
to different cores, multi-source NEXT-bank convergence reached
each destination, 24 total real packets delivered to already
resident contexts, all 15 on-chip state checkpoints passed and
all three authoritative DDR final records were byte-exact to
independent Python `LogicalChip` model including event,
packet, trace and state banks.

**Not proven:** 4096-entry event-depth limit/true producer
backpressure, simultaneous resident/nonresident fanout during
dirty eviction, multiple arithmetic parameter regimes, or
many-core service permutations under actual page replacement.

**Next composite P05.2e target:** Five logical cores in
three slots, two outgoing destinations per source, per-core
arithmetic parameter diversity, deliberately changed service
order and repeated dirty eviction/reload. Require independent
P02-compatible full-record model golden and an independently
simulated C scheduler paging/packet-residency ledger; no false
pressure/saturation claims.

No `main` merge; P05.2 remains in progress.
