# P05.1 first autonomous PS regression profile — independently accepted

**Result:** **PASS** (reported by user, 2026-10-12).  
**Branch:** `agent/v3-p05-board-regression`.  
**Physical evidence on user's Ubuntu workstation:**
`/tmp/v3_p05_1_probe_20261012T173751Z`.  
**Profile:** exact P03/P02 five-core seven-step ring **neural workload**
with NEW P05G descriptor and NEW P05-only A53 ELF, same accepted
FPD128 PS MMIO shell, three resident slots and one HLS engine.  
**Disposition:** Accept **first** physical P05.1 checkpoint only. Do
not close P05.1 until a genuinely different physical neural network
and subsequent diagnostic checks pass.

## Verified board output

```text
P03 board-local terminal result=0x600D600D after 2 poll(s)
PASS: P05.1 independent physical 35-checkpoint ring replay steps=7 cores=5 slots=3 dispatches=35 packets=30 barriers=7 events=35 checkpoints=35 resident_deliveries=0
PASS: P05.1 all five final 512KiB DDR records byte-exact to frozen P02 oracle
P05_1_VERIFY_EXIT=0
PASS: P05.1 first 7-step 35-checkpoint A53 physical golden probe
```

The user also supplied the independent `verify.log`, including:

- P05G header CRC32 `0x8AEB46A0`;
  payload CRC32 `0x520815C1`.
- `pl_dispatch_cycles=865`; `pl_page_cycles=22959330`;
  PS inference ticks `21830306`; PS timer frequency `99999001`.
  These are not published energy or end-to-end wall latency metrics.
- Final 512 KiB SHA256s:
  - core 0: `2e1900e14c9d852747afbb60e94e606523aee420c7077702a59da89fd5bcbba5`
  - core 1: `a9c1eef68fe63a1dd370bfe020388f681d8d2b2bc2c7e8ef05687b006ae136d0`
  - core 2: `d0b520c108b4c2d9989128b35a39aea85cbe58ceb4c06a058192a30d7c216e3a`
  - core 3: `28e9a7963404de53aa2cafcdc6ede2583d1ee4b88797068b5cc6579c7d0553fe`
  - core 4: `94d4e244234143a58daf925937a97b2047a650818158a09a4bf246ad26dc9d72`
- Frozen P02 reference trace fingerprint
  `9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac`.
  This is a **model trace fingerprint**, not independently captured
  time-by-time physical neuron state log. The **35 barrier
  checkpoints did pass independently on the physical A53**, and
  all five final images were independently byte-exact.

## What this does/does not prove

The new deployment-driven PS app correctly read the
P05G source tables, injected exactly 35 external events, preserved
five-over-three paging and routing, matched 35 actual FPGA
state0 barrier checks, and produced precisely five golden DDR
final images without PC algorithmic steering.

The measured `resident_deliveries=0` is **not** direct resident
packet-delivery evidence. The second planned physical P05.1
profile intentionally uses **three logical cores resident in
three physical slots, five timesteps, lower threshold, and
a three-core triangle** to produce resident-to-resident
spike deliveries on every dispatch. This profile requires
its own independently generated model final DDR records
and diagnostic checkpoints.

Full P05.1 completion also requires first-fault/checkpoint
negative evidence and a final review of diagnostic vs fast
mode behavior; both remain distinguishable from this
first physical PASS. No P05 source has been merged into
`main`, and the accepted P03 sources/RTL remain untouched.
