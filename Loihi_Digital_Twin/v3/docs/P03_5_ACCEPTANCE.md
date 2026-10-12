# P03.5 — 100-step autonomous Cortex-A53 / FPGA golden acceptance

**Decision:** **ACCEPTED** against the frozen P03.5 board-local
functional gate on 2026-10-12, from the user's independent KV260 run.  
**Repository branch at acceptance:** `agent/v3-p03-autonomous-runtime`;
merged to `main` through the P03 closeout process.  
**Design:** same corrected **V2** Cortex-A53 ELF and previously
accepted FPD128 PS-MMIO bitstream used for P03.4; the only run input
change is the DDR launch manifest's `100` timestep selection
and its independent golden fixture.  
**Physical evidence on user's Ubuntu PC:**
`/tmp/v3_p03_finish_100_20261012T145336Z`.

## Physical execution / verifier evidence

The user supplied the full standalone A53 terminal run and then
independently displayed `cat "$P03_FINISH_EVIDENCE_100/verify.log"`.
The recorded output included:

```text
PASS: P03 unified board-autonomous A53 ELF downloaded
P03 board-local terminal result=0x600D600D after 5 poll(s)
PASS: P03 A53 terminal mailbox captured after board-local execution
P03_RESULT_MAILBOX=/tmp/v3_p03_finish_100_20261012T145336Z/p03_a53_result.bin
PASS: P03 five authoritative DDR records captured from KV260
PASS: P03 autonomous five-over-three P02/v2 normalized golden
      timesteps=100 dispatches=500 packets=495 resident_deliveries=0
      barriers=100 page_ins=500 page_outs=500
      trace_sha256=b10387cb7930e6e4452548ff4d025c8dffe52e9eeebde2d5b43ed9c5475cfcac
      manifest_sha256=30076c118d312e57674f716e50fe3d080e7a057ed55ba1f2ae58a9a7dba51c4b
PASS: P03 all five final 512KiB DDR records byte-exact to frozen Python P02 oracle
P03_FINISH_VERIFY_EXIT=0
P03_FINISH_EVIDENCE_DIR=/tmp/v3_p03_finish_100_20261012T145336Z
PASS: P03 100-step independent board-autonomous physical golden gate
```

The original stdout omitted a space between `packets=495` and
`resident_deliveries=0`: it displayed
`packets=495resident_deliveries=0`. These represent two
distinct independently parsed result fields, **495 packets** and
**zero resident destination deliveries**, not an unusual packet
encoding or a different packet count.

## Accepted quantitative checks

| Check | Required | Observed |
|---|---|---|
| Logical core count | 5 | 5 |
| Physical resident context slots | 3 | 3 |
| Physical HLS engines | 1 | 1 |
| Algorithmic timesteps | 100 | 100 |
| Logical dispatches | 500 | 500 |
| Routed packets | independent 100-step Python oracle | 495 |
| Global barriers | 100 | 100 |
| Total full page-ins (initial + replacements) | scheduler/PL oracle | 500 |
| Total mutable page-outs (evictions + final flush) | scheduler/PL oracle | 500 |
| Terminal result | `0x600D600D` | `0x600D600D` |
| Runtime fault and application error | 0 | 0 |
| All five final complete 512 KiB context images | byte-exact raw golden | PASS |
| Architecture model trace fingerprint | independent **reference** 100-step trace | `b10387cb...` |
| `resident_deliveries` coverage | measured, not inferred | 0 |

**Final physical DDR record digests from the user-provided verifier:**

| Logical core | Final complete 512 KiB SHA-256 |
|---|---|
| 0 | `8b39255112eef43bbcbaca2411c4e7617bc320414e9d43a8af91c3c7817b8928` |
| 1 | `35339ae11942406dc19db96cb5d0b63ddbb6e941df09ffad722165fbfc596a69` |
| 2 | `41d2b3df0c4919951cf9e7043640edb5825ea246f8a3c9ca51950555a58f8927` |
| 3 | `bef1a426393d19c6d69eaf503cb17058afc110d3d59f8286e23845c1569db48c` |
| 4 | `2ac6cf00e2362a663eda01b0cc04c008d32018c37e2915c62870749d12749586` |

`P03_RESULT_METADATA` additionally reported:

```text
inference_ticks=338781827
pl_dispatch_cycles=13420
pl_page_cycles=333218583
ps_timer_hz=99999001
resident_deliveries=0
```

These are raw counter values, **not independently calibrated
end-to-end wall-clock latency**, throughput, power, or energy
measurements. The PS `inference_ticks` measurement excludes
initial resident loads and result finalization; the PL page
cycles are not in the same clock domain as the PS timer.

## What the pass establishes

- A **single** Cortex-A53 standalone program owned the entire
  100-timestep logical scheduler, physical page-victim decisions,
  HLS dispatches, packet routing, double-buffered event-bank
  barriers and finalization, with **no PC algorithmic loop**.
- Five logical cores were time-multiplexed through three physical
  context slots and a single actual HLS inference engine.
- The ring delivered 495 real packet events using the accepted
  destination/time encoding; the runtime completed all 100
  global quiescent barriers.
- One hundred timesteps and repeated DDR page-out/in retained
  the architectural state required for **all five complete
  final records** to match the frozen P02/v2 Python physical
  record model **byte-for-byte**.
- The physical result independently satisfied the previously
  frozen strict P03.5 verifier, including packet/count
  expectations and the V2 finalization protocol.
- A PC was still needed for preparation, initial JTAG launch,
  passive terminal polling, and evidence acquisition; this is
  *algorithmic-loop autonomy*, not fully untethered boot.

## What the pass does NOT establish

- Physical MMIO delivery into an **already resident** packet
  destination: `resident_deliveries=0` for **both** seven- and
  hundred-step accepted runs. Direct-resident routing logic
  exists and passed **native mock regressions**, but is not
  claimed physically accepted in P03.
- Single-step inspection of **all intermediate physical**
  neuron states against the reference trace. The printed
  `trace_sha256` is the frozen reference trace digest;
  observed physical evidence is the **complete final-DDR
  golden comparison**, hardware packet/counter checks and
  A53 control-flow invariants.
- Autonomous full MNIST application, general-purpose arbitrary
  network support, multi-engine parallel execution, persistent
  onboard Linux boot, or published Loihi hardware-equivalence
  and energy benchmarking. Those require separately defined
  P05/P07/P08/P09 acceptance.

## Verification record and next phase

The user previously confirmed all combined native pytest
regressions and a Vitis build passed; the assistant did not
execute tests on the user's hardware. P03.4 independently
passed 35 dispatches/30 packets/7 barriers with five golden
DDR records (`docs/P03_4_ACCEPTANCE.md`). This P03.5
100-step run establishes the outstanding frozen closeout
gate. See `docs/P03_PS_AUTONOMOUS_APPLICATION.md`
for the execution/DDR/packet/code walkthrough and solved
P03 bring-up issues, and `docs/P03_FINAL_ACCEPTANCE.md`
for the phase-wide decision.

**Disposition:** Accept P03.5. P03 functional milestone
is complete under the roadmap's original scope. Carry
direct-resident physical routing coverage and release-shell
diagnostics cleanup as explicit future hardening items,
not retroactive claims of P03 verification.
