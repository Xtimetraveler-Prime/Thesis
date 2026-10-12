# P03.2c — Physical PS-MMIO control smoke acceptance

**Independently verified:** 2026-10-11 (local KV260 test; UTC evidence directory
uses 2026-10-12 timestamp)  
**Decision:** **ACCEPTED** — P03.2c *functional physical smoke* requirements met.  
**Branch:** `agent/v3-p03-autonomous-runtime`; no merge to `main`.  
**Hardware:** AMD KV260 / K26 (Zynq UltraScale+ MPSoC)  
**Tools:** Vivado/Vitis 2025.2; XSDB/JTAG to standalone Cortex-A53 #0

## Accepted physical configuration

```text
PS runtime FPD HPM0 static width = 128 bits
       |
       v
Vivado M_AXI_HPM0_FPD AXI4 width = 128 bits
       |
       v
1x1 SmartConnect 128-bit AXI4 -> 32-bit AXI4-Lite
       |
       v
P03 register slave @ 0xA4000000 (fixed ABI)
       |
       +-- PS-managed page commands -> P02 HP0/DDR paging
       +-- slow resident-memory debug/config read
       +-- HLS dispatch and status
```

Previous FPD32/LPD32 physical failure and the live PS width measurement
are documented in `P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md`.

This accepted build **retains two ILAs, reset/observation VIO, and the
temporary otherwise-unmapped diagnostic signature** for P03.3
engineering bring-up. Decision: retain nonintrusive diagnostic hardware
in the current experimental shell; defer final non-diagnostic release
route/acceptance to a separate cleanup gate. Do not alter the accepted
P03.2a register contract or consider the signature part of the production
ABI.

## Two independent board-local passes

### Read-only MMIO gate (completed earlier 2026-10-11)

The standalone A53 program read four physical registers and wrote
completion into a DDR mailbox:

```text
P03_2C_A53_MAGIC=0x50335244
P03_2C_A53_RESULT=0x600D600D
P03_2C_A53_COMPLETE=0xC0DEF00D
PASS: Cortex-A53 MMIO 0xA4000000 returned 0x4C543302
PASS: Cortex-A53 MMIO 0xA4000004 returned 0x00010000
PASS: Cortex-A53 MMIO 0xA4000008 returned 0x0001031F
PASS: Cortex-A53 MMIO 0xA4000018 returned 0xD1A60018
PASS: P03.2c read-only Cortex-A53 MMIO diagnostic
```

This gate proved **read** integrity; it did not issue page/dispatch
commands and was not used as the sole P03.2c acceptance basis.

### Full command/page/resident/dispatch gate (completed 2026-10-11)

The user independently executed
`scripts/run_p03_2c_full_smoke.sh` with the *same corrected FPD128
candidate hardware family* and an ELF built against that candidate's
fixed XSA. Supplied console and verification output:

```text
PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released
PASS: P03.2c standalone ELF downloaded to Cortex-A53 #0
P03.2c physical mailbox target: PSU
PASS: P03.2c A53 smoke executed and 64-byte mailbox dumped
PASS: P03.2c mailbox verified id=0x4C543302 capabilities=0x0001031F page_bytes=438272 config0=0x14001000 dispatches=1
P03_2C_FULL_SMOKE_VERIFY_EXIT=0
P03_2C_FULL_SMOKE_EVIDENCE_DIR=/tmp/v3_p03_2c_fullsmoke_20261012T020320Z
PASS: P03.2c full A53 physical page/resident/dispatch smoke (independent review pending)
```

The independent user then ran:

```text
$ cat "$P03_2C_FULL_EVIDENCE_DIR/verify.log"
PASS: P03.2c mailbox verified id=0x4C543302 capabilities=0x0001031F page_bytes=438272 config0=0x14001000 dispatches=1
```

The verifier `scripts/p03_2c_verify_mailbox.py` has a strict
16-word/64-byte schema and additionally checked (even though the
concise PASS line does not print them individually):

- full mailbox magic `0x50333243`, schema version `1`,
  `result=0x600D600D`, and `fail_code=0`;
- ID `0x4C543302`, VERSION `0x00010000` and
  CAPABILITIES `0x0001031F`;
- page-done, clean page error bits, `438272` transfer bytes,
  `1712` AXI read bursts, **zero** write bursts;
- debug resident read completion/rvalid, clean debug error bits, and
  `config[0]=0x14001000` from resident slot 0;
- HLS dispatch completion, clean dispatch errors, and exactly one
  completed dispatch;
- clean global status.

These are read directly from the completed A53 DDR mailbox, not
extrapolated from simulation. This is the physical control
functionality required by P03.2c.

**Evidence limitation:** The chat transcript contains the independent
console output and verification log text; it does not include the
complete binary mailbox, bitstream, XSA, ELF, artifact SHA-256 hashes or
all raw run logs for this passing build. Their exact values must be
extracted from the preserved local evidence folder, not invented. The
full acceptance decision is based on the project's own strict verifier
and user-reported independent physical pass.

## Scope and exclusions

**Accepted:** Cortex-A53 PS-to-PL MMIO transport, real DDR context
page-in, resident configuration readback, no-current-event HLS dispatch,
completion/status counters, and error-free completion via the corrected
boot-compatible 128-bit FPD bridge.

**Not yet accepted by this test:**

- dynamic multi-core page replacement and mutable page-out;
- packet decoding, routing into NEXT event banks or cross-page delivery;
- PS autonomous barrier/timestep control;
- a seven-timestep/35-dispatch board-local run;
- 100-timestep model-agreement or final performance results;
- a clean release bitstream without temporary diagnostic instrumentation.

Those are P03.3, P03.4, P03.5 and later release-cleanup tasks.

The prior PuTTY/Linux freeze was not independently diagnosed; its
explanation is outside this P03.2c functional acceptance.

## Review and forward action

**P03.2c: ACCEPTED.**  
**P03.2: ACCEPTED for the functional experimental MMIO shell.**
Preserve the working FPD128 candidate build as the P03.3 hardware
baseline. Document any subsequent diagnostic cleanup or new route
with its own hashes/evidence and rerun the physical gates.

Next: **P03.3** standalone A53 scheduler/router/barrier runtime.
Start with the host-native C policy/ordering core (P03.3a), then
connect the physical MMIO/DDR/packet adapter (P03.3b), and proceed to
the seven-timestep physical workflow in P03.4 only when standalone
P03.3 runtime verification is complete.

Do not merge to `main` until the user explicitly requests it.
