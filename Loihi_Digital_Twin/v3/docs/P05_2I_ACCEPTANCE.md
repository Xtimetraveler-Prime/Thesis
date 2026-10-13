# P05.2i — Final real KV260 PL page-AXI counter acceptance

**Status: PHYSICAL PASS, independently user-confirmed on 2026-10-13.**
**Gate:** `P05_2I_VERIFY_EXIT=0`.
**Original evidence directory:**
`/tmp/v3_p05_2i_axi_20261013T010913Z`.
**Historical development branch:** `agent/v3-p05-board-regression`.
**Original runtime/bitstream:** accepted unchanged P05 standalone A53 ELF
and P03.2c FPD128/SmartConnect PS–PL route; no new HLS or RTL build.

## Original user-provided final physical verifier output

```text
PASS: P05.2h physical adversarial 5-over-3 bank/barrier order steps=16 dispatches=80 packets=156 resident_deliveries=78 nonresident_deliveries=78 barriers=16 checkpoints=318 evictions=77
PASS: P05.2h both event-bank first words, state0 and emitted physical packet0 checkpointed at each barrier
PASS: P05.2h all five complete physical 512KiB DDR records byte-exact to model-derived route-ordered golden
PASS: P05.2i KV260 PL HP0 AXI successful 256-byte burst counters read=136960 write=33280 and direct read-only hardware bytes=43581440 exactly equal 80 complete full page-ins + 80 mutable-only page-outs
PASS: P05.2i independent A53 P05R page counters match halted-PL MMIO burst registers and directly measured page AXI byte register
PASS: P05.2i original 16-barrier/318-checkpoint neural and all five 512KiB physical DDR oracle preserved
P05_2I_VERIFY_EXIT=0
```

The reported strict verifier `scripts/p05_2i_axi_closeout.py` requires
the actual original 256-byte A53 `P05R`, immutable `P05G`
deployment/model ledger, all five physical complete 512 KiB
DDR dumps, and **two stable actual physical read-only MMIO
captures** of FPGA page-AXI registers at `0xA4000044`,
`0xA4000048`, `0xA400004C`, and `0xA4000050`.
It verifies the raw 128-bit (16 beats × 16 bytes per beat)
completed-burst/byte counters independently, against page
operations reconstructed from the separate logical model.
A fake or missing MMIO witness, an inconsistent A53 mailbox,
a single corrupted physical DDR byte, or a failed neural
barrier checkpoint would fail the verifier.

## Independently checked real hardware measurements

| Counter | Physical reported result | Model prediction |
|---|---:|---:|
| Completed page AXI read bursts | **136,960** | 80 full page-ins × (0x6B000/256) |
| Completed page AXI write bursts | **33,280** | 80 mutable-outs × (0x1A000/256) |
| Completed successful page AXI bytes | **43,581,440** | 170,240 × 256 |
| Initial full page-ins | 3 | 3 |
| Full replacement page-ins | 77 | 77 |
| Runtime mutable page-outs | 77 | 77 |
| Final mutable page-outs | 3 | 3 |
| FPGA dispatches | 80 | 80 |
| Completed global barriers | 16 | 16 |
| Actual device model-derived checks | 318 | 318 |
| Routed packets | 156 | 156 |
| Direct-resident packet deliveries | 78 | 78 |
| Nonresident packet deliveries | 78 | 78 |
| Logical-context evictions | 77 | 77 |
| Whole-device final DDR image comparisons | **5 × 512 KiB byte-exact** | 5 × 512 KiB |

The read-only captured hardware bytes **are observed actual FPGA PL
HP0 page-engine successful DDR traffic**, not simply the
programmed number of bytes or whole-system AXI traffic.
`P05R` read/write burst counters agree with the independent
`mrd -force` actual FPGA registers. No claim is made about
PS routing memory stores, cache traffic, host provisioning,
overall DDR utilization, or measured power.

Additional noncalibrated raw measurements independently supplied:

```text
pl_page_cycles_raw=52984749
ps_inference_ticks_raw=52681578
ps_timer_hz=99999001
ps_inference_seconds=0.526821042942219
```

This PS inference interval is for the **regression workload**;
it is not the P07 MNIST inference latency or a P08
application throughput/energy measurement.

## Original evidence SHA-256 identifiers (user-submitted verifier)

```text
P05R mailbox: 3de43163e98d3368ee1bf52afcdbdc4737840962f449850b842f4e1ab68f4cfb
PL AXI read-only counter witness: 51ea572f1cb83902d6d853da2fc1b657bcfc28371763201fad32de41cc7d01f9
core0 full DDR: 7228fc165d80d7aa0381494cd65fe43cfae7210768bdaf376e029cf8963e3eab
core1 full DDR: c0e49500682337ec52a8635cdc776785ade1884d2e661617985b80e2d3adc138
core2 full DDR: 7fc42a7f3f784c4f9af9f2e897a108b49d3b12a181cb7081d279c1e3c01b858d
core3 full DDR: 732be950023981292e76611ea4e9cc55e012310c001ef3dd245a98f412803fd3
core4 full DDR: a9ab65bc68993c14dd324faa48e335b25d5551f48c2982682594115a8c3434db
```

These digests are **the user's reported verifier metadata**;
no claim is made that the full original binary files were uploaded
into this repository or independently rehashed here. The physical
verification itself was executed by the user on the KV260.

## Recovery of the original read-only capture (not a re-inference)

The first P05.2i trial succeeded through original P05.2h
physical inference/checkpoint/DDR verification but halted at
XSDB's **software** memory-map admission check when unforced
`mrd -bin -file` attempted `0xA4000044`. There was no
P05.2i acceptance at that point.

The user expressly confirmed that the KV260 **had not rebooted**.
After the guarded capture script was corrected to
`mrd -force -bin -file`, the user executed
`scripts/run_p05_2i_axi_recover.sh` against the **same physical
trial's existing** mailbox, DDR dumps and model artifacts.
The read-only MMIO witness plus strict final verification
passed. This is not a second neural workload/inference run.
The original failed memory-map attempt is retained in the
project history rather than mislabeled as PASS.

## Accepted coverage and continuing exclusions

**Physically accepted in P05:** board-owned per-timestep
inference control, deployment admission/checksum, independent
full-record memory checks, Loihi-like signed arithmetic and
refractory, both routing residency paths, fanout, dual bank
alternation, service-order variants, global barriers,
paging/dirty eviction, exactly 4096 external CURRENT-bank
events, refusal of CRC-valid 4097-event deployment before
execution, and actual completed PL page-engine AXI
burst/byte telemetry.

**Portable C/native only:** NEXT bank at 4095 accepts one
additional routed event; already-full 4096 rejects
another before DDR store/clean.

**Not physically exercised:** a real HLS-originating **4097th
routed NEXT-bank packet** causing runtime backpressure,
stall latency and successful recovery after overflow.
Fail-closed rejection is implemented/tested at appropriate
other boundaries but is not evidence of runtime stall or
automatic resumption. Neither overall PS/PL DDR bandwidth
nor application-level energy/power/benchmark accuracy was
measured by P05. These remain outside the physically
accepted P05 scope and are separately reconsidered if P06
benchmark mapping needs them.

**Decision:** Accept P05.2i physical within these strict
bounds. P05 as a phase may be closed only with the
scope exclusions preserved; do not rewrite any frozen
P02/P03 source or evidence. See
`docs/P05_FINAL_ACCEPTANCE.md` for phase-wide closure.
