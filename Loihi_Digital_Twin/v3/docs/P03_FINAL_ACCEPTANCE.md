# P03 — Final autonomous PS-resident runtime acceptance

**Decision: COMPLETE — accepted 2026-10-12.**  
**Authority:** The frozen `LOIHI_TWIN_ROADMAP.md` P03 goal and
functional exit gate, independently reported native regressions,
A53/FPGA physical results and byte-exact final DDR oracles.  
**Branch:** Developed and verified on
`agent/v3-p03-autonomous-runtime`, merged into `main`
as requested at closeout.  
**Primary technical walkthrough:**
`docs/P03_PS_AUTONOMOUS_APPLICATION.md`.

## Original P03 goal / decision

Move algorithmic scheduling, packet routing, page replacement,
quiescence/barrier control and timestep advancement from the external
host to the KV260 processing system.

The physical Cortex-A53 **standalone** executable demonstrably
executes all these operations in its local C loop. The PC provisions
the initial five DDR records, chooses the 7/100-step workload
configuration, loads the executable once, passively polls terminal
state and acquires results **after completion**. It does not
participate in the algorithmic loop.

The accepted platform is the FPD HPM0 128-bit PS AXI4 master,
SmartConnect AXI4-to-32-bit AXI4-Lite control at `0xA4000000`,
the pre-existing HP0 DDR page data path, three resident URAM
context slots and one physical HLS engine. The accepted diagnostic
ILA/VIO visibility was retained through this experimental P03
gate; this does not mean the PC makes runtime scheduling decisions.

## Signed-off phase elements

| Roadmap unit | Evidence and disposition |
|---|---|
| P03.1 | Run state/phase, ownership and error protocol frozen and documented; complete. |
| P03.2a/b/c | 32-bit AXI-Lite register shell, routed FPD128 SmartConnect hardware, physical PS control/page/dispatch smoke; complete. |
| P03.3a | Portable C11 round-robin/core service, victim paging, packet/barrier/timestamp counters, host-native regression; complete. |
| P03.3b1/b2/b3 | Native hardware adapter, physical one-core and two-core directed A53 packet routing/dirty-paging with two actual FPGA-generated packets; complete within directed scope. |
| P03.3c | V2 standalone launch configuration, CRC-checked DDR, event ingress, 256B terminal result/error protocol, timing, final page flush, no host algorithmic loop; complete. |
| P03.4 | **Physical PASS:** five logical cores, three slots, 7 timesteps, 35 dispatches, 30 packets, 7 barriers, 35 page-ins / 35 page-outs; five complete final DDR records exact to Python golden. |
| P03.5 | **Physical PASS:** five logical cores, three slots, 100 timesteps, 500 dispatches, 495 packets, 100 barriers, 500 page-ins / 500 page-outs; five complete final DDR records exact to separate 100-step Python golden. |

### P03.4 seven-step accepted evidence

```text
PASS: P03 autonomous five-over-three P02/v2 normalized golden
  timesteps=7 dispatches=35 packets=30 resident_deliveries=0
  barriers=7 page_ins=35 page_outs=35
  trace_sha256=9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac
PASS: P03 all five final 512KiB DDR records byte-exact to frozen Python P02 oracle
```

Reference: `docs/P03_4_ACCEPTANCE.md`.

### P03.5 hundred-step accepted evidence

```text
P03 board-local terminal result=0x600D600D after 5 poll(s)
PASS: P03 autonomous five-over-three P02/v2 normalized golden
  timesteps=100 dispatches=500 packets=495 resident_deliveries=0
  barriers=100 page_ins=500 page_outs=500
  trace_sha256=b10387cb7930e6e4452548ff4d025c8dffe52e9eeebde2d5b43ed9c5475cfcac
  manifest_sha256=30076c118d312e57674f716e50fe3d080e7a057ed55ba1f2ae58a9a7dba51c4b
PASS: P03 all five final 512KiB DDR records byte-exact to frozen Python P02 oracle
P03_FINISH_VERIFY_EXIT=0
PASS: P03 100-step independent board-autonomous physical golden gate
```

Physical evidence on the user's Ubuntu host:
`/tmp/v3_p03_finish_100_20261012T145336Z`.
The strict verifier reported complete final DDR SHA-256 hashes
for all five cores (listed in `docs/P03_5_ACCEPTANCE.md`) and
PS/PL cycle/timer counters. Neither raw binary output nor exact
ELF/bitstream SHA-256 identities were uploaded to the GitHub
repository; `identity.txt` in local evidence retains artifact
hashes. This acceptance is based on the user's submitted
physical run and `verify.log`, **not** on an assistant-executed
FPGA run. The reference `trace_sha256` value is a golden
**model** trace fingerprint, not an independent physical
per-timestep trace capture.

## Main engineering issues resolved during P03

1. **PS HPM0 width mismatch:** Booted FPD master was 128-bit,
   not 32-bit; re-routed with 128-to-32 SmartConnect and a
   boot-width guard. This resolved failed physical PS/MMIO
   control while preserving the original register ABI.
2. **A53 hardware/DDR access:** Use PSU/APU physical target
   for XSDB `dow -data`/`mrd -bin` readback, rather than
   an A53 Linux MMU translation context; stop/reboot Linux
   around bare-metal execution.
3. **P03.3b3 false header error:** `validate_backing()`
   returned zero on success, but an early caller inverted
   this return contract. Corrected to `!= 0`, verified
   by physical two-core spike/DDR roundtrip; retained
   actual-ELF version checking and diagnostic overlays.
4. **P03.4 fixture import and test design:** Python
   subprocesses accidentally resolved the older venv
   `loihi_twin_v2` package. Both scripts explicitly
   prefer `v3/src`; regression tests shadow that module.
   A negative mailbox test was also fixed after it
   attempted a no-op overwrite of an already-zero state.
5. **P03.4 first finalization failure:** A full seven-step
   run reached `WRITE_RESULT` but returned `0xDEAD000B`
   with `flush_outs=0x800023`. V2 explicitly initializes
   application counters, reports per-predicate tagged
   finalization errors and compares DDR on a terminal error.
   The corrected V2 **passed P03.4 and P03.5 physically**;
   the precise origin of the original V1 counter anomaly
   remains unproven. A late-result PASS race was prevented
   by publishing terminal success only after `DONE`.
6. **Preserved ownership semantics:** Physically generated
   64-bit HLS packets are verified before A53 routing;
   nonresident event delivery writes NEXT directly into
   DDR with proper cache maintenance; dirty victim mutable
   state is written back before replacement; final dirty
   resident slots are explicitly saved before complete
   DDR comparison.

The chronology, code paths, register/DDR/mailbox ABI, physical
commands and diagnostic field map are documented in
`docs/P03_PS_AUTONOMOUS_APPLICATION.md` and
`docs/P03_4_PHYSICAL_ATTEMPT1.md`.

## Open coverage limitations and future owners

The completed experimental P03 **does not prove** direct
delivery to an **already-resident** logical destination on
real hardware: `resident_deliveries=0` in both accepted
five-over-three runs. That specific route branch is
native-tested and should be exercised deliberately in
future P05 regression/observability hardening. It is not
silently relabeled physically accepted.

The accepted FPGA configuration contains diagnostic
ILA/VIO observation and an otherwise-unmapped signature.
Their removal/re-timing is a subsequent release-shell
decision, not an unseen change to the previously
verified P03.2c bitstream.

This phase also does not claim persistent Linux orchestration,
untethered flash boot, physically parallel engines
(P04 deferred), full MNIST board-autonomy (P07),
calibrated latency/power/energy metrics (P08), or
the final source-backed cross-system comparison (P09).

**Final determination:** P03 is functionally complete
against the roadmap's 100-step five-over-three criterion.
The follow-on hardening and application benchmarks are
tracked separately; no additional P03 subphase is required
to accept the reported experiment.
