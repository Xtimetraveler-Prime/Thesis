# P07-A4.2c — Precommitted 128-image persistent KV260 hardware gate

**Prespecified on 2026-10-17 after user acceptance of persistent
ramp16, BEFORE any A4.2c physical 128-image launch.**
**STATUS: NATIVE HOST CODE IMPLEMENTED / CI PASS.**
**128-image persistent physical primary / cold-repeat NOT YET RUN.**
**Official canonical t10k MNIST TEST remains SEALED.**

## Provenance and frozen scope

- A4.2b new standalone persistent A53 ELF (the *same* executable
  user verified and used for the accepted ramp16 pilot):
  `/tmp/v3_p07_a4_persistent_20261017T190943/vitis_workspace/p07_a4_board.elf`,
  SHA256 `dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`.
- Same accepted P03.2c routed FPD128 FPGA XSA SHA256
  `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`;
  same frozen 512 KiB P02 master SHA256
  `9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`.
  No new bitstream/RTL/weights or ELF rebuild.
- Exact preselected **first 128 distinct images** from frozen
  TRAIN-derived validation set, using the same seeded original
  source IDs and order from P07-A3.3. This population includes
  the 16-image A3.2 overlap and is **not** an official TEST.
- Accepted prior A3.3 **8 original physical 16-frame PRIMARY
  mailboxes** in `/tmp/v3_p07_a3_3_val128_20261017T133340`;
  the old acceptance report there originally recorded
  `116/128` correct, 0 silent and two byte-exact old-format
  cold-start repeats. Do NOT count the 8 previously verified
  A3.3 batches as new persistent launches, and do not
  retroactively select source IDs based on new errors.

## Prespecified hardware runs: ONE primary, ONE cold-start repeat

1. `persistent_val128_primary`: reboot KV260 into dedicated
   JTAG-only bare-metal mode, provision immutable **single
   128-frame dataset** plus journal, load SAME accepted A53
   ELF ONCE, run all 128 frames autonomously for 26 ticks,
   capture full 1MiB journal and 64KiB frame0 full trace.
   All 128 per-image output spike bits/counts/routing/inputs
   and the selected 26×42 trace MUST EXACTLY match the
   independent P03 packed software oracle. Every result
   must be present; first failure aborts.
2. Independently compare the physical 128 journal against
   the **eight previously accepted A3.3 PRIMARY hardware
   mailboxes**: **128/128 exactly same original pixel→axon
   source records, original source IDs/labels, 26×10
   physical spike bits, ten counts, class/tie/silence,
   hidden NEXT packet totals, boundary discards and
   input event counts**. Also require physical frame0
   trace bytes `26×42×32` EXACTLY identical to the old
   frame0 physical trace. The old A3.3 result/report
   SHA256s and log-gate markers are checked.
3. `persistent_val128_repeat`: after a **second independent
   physical reboot**, rerun the exact same 128 inputs using
   the same ELF and separate immutable evidence directory.
   Require identical full 1MiB result journal and full
   64KiB selected trace **byte for byte** to primary.
   Independently repeat both software-oracle and old
   A3.3 physical-matches on the repeat.
4. Failed/timeout launches count as failed acceptance;
   preserve original evidence and original attempted order;
   do not skip/drop/tune source IDs, silently relaunch
   with same evidence directory or alter trained model.

Two 128-frame launches = 256 physical image executions,
**128 UNIQUE diagnostic images**. One selected full
compartment trace per launch; all 128 output spike histories.
This is NOT evidence of 256 distinct validation images,
not independent official TEST accuracy, and not a 10k
physical persistent pass.

## Native user preflight (safe, no FPGA access)

From the V3 directory after pulling this branch:

```bash
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a4_crosscheck.py \
  tests/test_p07_a4_persistent_board.py \
  tests/test_p07_a4_physical_gate.py

export P07_A4_BUILD_DIR=/tmp/v3_p07_a4_persistent_20261017T190943
export P07_A4_STAGE_DIR="$PWD/artifacts/p07_a4_2a_validation128_v1"
export P07_A4_A3_PROTOCOL="$PWD/artifacts/p07_a3_3_val128_first_v1"
export P07_A4_A3_EVIDENCE=/tmp/v3_p07_a3_3_val128_20261017T133340
export P03_2C_EXPECTED_XSA_SHA=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f

PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py \
  --stage-dir "$P07_A4_STAGE_DIR"
test -s "$P07_A4_A3_EVIDENCE/p07_a3_3_validation128_report.json"
test -s "$P07_A4_A3_EVIDENCE/batch_07_primary/p07_a2_mailbox.bin"
sha256sum "$P07_A4_BUILD_DIR/vitis_workspace/p07_a4_board.elf"
bash -n scripts/run_p07_a4_physical.sh
```

If the validation128 stage was **not** already prepared,
generate it *exactly once* with the approved old command:

```bash
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_prepare.py \
  --validation-first 128 --data-dir data/mnist_raw \
  --trace-index 0 --out artifacts/p07_a4_2a_validation128_v1
```

The creation script refuses overwriting an existing stage.

## First physical primary — only after reboot / JTAG-only state

```bash
# P03_DIAG_REPORTS must still point to the accepted P03.2c XSA,
# bitstream, routed metrics, etc.
export P07_A4_RUN_DIR="/tmp/v3_p07_a4_val128_primary_$(date +%Y%m%dT%H%M%S)"
export P07_A4_PRIMARY_EVIDENCE="$P07_A4_RUN_DIR"

# DANGEROUS: bare-metal exclusively owned 0x40000000..0x43FFFFFF.
# Reboot board first; never run while Linux owns that DDR.
export P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES
bash scripts/run_p07_a4_physical.sh
```

The guarded wrapper revalidates accepted XSA/ELF/master, staged
sources and input checksum, reprograms the existing FPGA,
launches the A53 ONCE for all 128 frames, and calls
`p07_a4_2_verify.py` before printing
`P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1`.

**Only after this physical pass**, run the new
cross-hardware check. This is read-only; no JTAG:

```bash
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_crosscheck.py \
  --stage-dir "$P07_A4_STAGE_DIR" \
  --journal "$P07_A4_PRIMARY_EVIDENCE/p07_a4_journal_1m.bin" \
  --trace "$P07_A4_PRIMARY_EVIDENCE/p07_a4_trace_64k.bin" \
  --a3-protocol-dir "$P07_A4_A3_PROTOCOL" \
  --a3-evidence-dir "$P07_A4_A3_EVIDENCE" \
  | tee "$P07_A4_PRIMARY_EVIDENCE/crosscheck.log"
```

Required new markers:

```text
P07_A4_2C_PHYSICAL_FRAMES=128
P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1
P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1
P07_A4_2C_FULL_PHYSICAL_GATE_PASS=1
P07_A4_2C_CROSSCHECK_OLD_PHYSICAL_BATCHES=8/8
P07_A4_2C_CROSSCHECK_PRIMARY_FRAMES=128/128
P07_A4_2C_CROSSCHECK_FIRST_TRACE_BYTE_EXACT=1
P07_A4_2C_CROSSCHECK_ALL_FRAME_SPIKES_ROUTES_EXACT=1
P07_A4_2C_CROSSCHECK_OLD_REPORT_MAILBOX_SHA_PASS=1
P07_A4_2C_PRIOR_AND_PERSISTENT_PHYSICAL_MATCH=1
P07_A4_OFFICIAL_TEST=SEALED
```

**Halt on any missing marker or failure.** Reboot KV260
after the primary even if it fails; DO NOT continue
to the repeat if the primary isn't accepted.

## Second run: independent cold-start repeat — after primary acceptance

After reboot:

```bash
export P07_A4_RUN_DIR="/tmp/v3_p07_a4_val128_repeat_$(date +%Y%m%dT%H%M%S)"
export P07_A4_REPEAT_EVIDENCE="$P07_A4_RUN_DIR"

export P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES
bash scripts/run_p07_a4_physical.sh
```

Run the same `p07_a4_2_crosscheck.py` with
`--journal "$P07_A4_REPEAT_EVIDENCE/p07_a4_journal_1m.bin"`
and `--trace "$P07_A4_REPEAT_EVIDENCE/p07_a4_trace_64k.bin"`
while keeping other arguments identical, and verify
both full hardware output files byte-for-byte:

```bash
cmp "$P07_A4_PRIMARY_EVIDENCE/p07_a4_journal_1m.bin" \
    "$P07_A4_REPEAT_EVIDENCE/p07_a4_journal_1m.bin" &&
cmp "$P07_A4_PRIMARY_EVIDENCE/p07_a4_trace_64k.bin" \
    "$P07_A4_REPEAT_EVIDENCE/p07_a4_trace_64k.bin" &&
echo "P07_A4_2C_128_COLD_REPEAT_ALL_BYTES_EXACT=1"
```

Keep all primary, repeat, accepted A3.3 and ramp16
physical evidence folders. **Reboot after each run.**

## Further pre-unseal acceptance still required

A4.2c overall will remain OPEN after the 128 gate:
we still need prespecified larger (e.g. 1024 TRAIN-derived
validation images) single-launch run and separate
fault/failure telemetry physical verification without
tampering with the sealed official TEST population.
Physical runtime/end-to-end timing and power remain P08
topics. The full canonical original-order 10000 official
test evaluation remains the fixed goal of A4.3/A4.4,
**not yet opened**.
