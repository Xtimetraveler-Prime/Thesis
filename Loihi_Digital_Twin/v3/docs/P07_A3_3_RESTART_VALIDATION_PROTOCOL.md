# P07-A3.3 — Prespecified 128-validation-image / ten cold-start launch gate

**Protocol frozen in source on 2026-10-17, BEFORE any A3.3 physical
result. Status: IMPLEMENTED / CI HOST REGRESSION PASS / USER NATIVE AND
PHYSICAL VALIDATION PENDING.**

**Prior acceptance:** P07-A3.2 accepted on real KV260 with 15/16
validation diagnostic predictions correct, all numerically identical
to the frozen oracle (`P07_A3_2_PHYSICAL_ACCEPTANCE.md`).
A3.3 has **no board run, no measured larger-population accuracy, no
repeat evidence** as of this protocol freeze.

## Why we need A3.3

A3.2 proved actual frozen trained physical inference but only on
16 validation images and one A53 launch. A3.3 independently checks a
larger locked set and the ability to reproduce exact results after
fresh hardware provisioning/A53 launch. A3.3 is **not** an official
MNIST test evaluation and is **not** a latency or energy study.
The accepted A53 firmware, P03.2c bitstream, weight tensor, encoder,
25+1 schedule, DDR record, compiler map, and output readout remain
**unchanged**. The official t10k TEST IDX remains SEALED.

## Immutable precommit BEFORE seeing new A3.3 predictions

- **Primary sample population:** exactly the first **128** indices in
  the frozen, seeded 10,000-image **TRAIN-derived validation
  permutation** from the canonical 60,000-image *training* archives.
  This rule is not selected by class, oracle predictions, confidence,
  or hardware outcome. Since A3.2 already tested the first 16, the
  first 16 of the 128 are **known overlap**; 112 source images are
  not part of A3.2. Do not describe 128 as an independent official
  test population or pretend the overlapping results were unseen.
- **Eight primary batches:** IDs `batch_00_primary` through
  `batch_07_primary`, each exactly 16 disjoint validation images
  in the original seeded validation order. Trace-selected index 0
  within each batch (26×42 compartments), while every image must
  match all 26 output-spike flags, ten counts and NEXT-route totals
  against immutable P03 packed replay. Each A53 launch resets all
  frames internally.
- **Two independently provisioned repetition launches:**
  `batch_00_repeat` and `batch_07_repeat`, in that order
  **after all eight primary launches**. Both MUST produce complete,
  byte-identical 65,536-byte physical result mailboxes to their
  respective primary batch (including all full trace bytes). This
  tests restart/reset/provisioning repeatability at the beginning
  and end of the sequence, not merely software recopy.
- **Total hardware execution:** 10 separately launched batches of
  16 frames, or **160 physical frame executions**. Classification
  diagnostic denominator remains **exactly 128 unique primary
  frames**, never 160. Repeats are reported as 2/2 exact or failed.
- **Evidence failure policy:** all ten attempts have preassigned IDs.
  Missing/failed/timeout runs and any numerical or repeat divergence
  FAIL A3.3; do not silently skip, replace, aggregate only passing
  runs, or launch a different population. Preserve failed evidence;
  any new retry experiment requires a separately named addendum,
  not a rewrite of the prespecified 10-run result.
- **Sample score/report:** report 128 primary true labels and board
  predictions, complete ten-class confusion, silent fraction and
  correct/128. Compute a **descriptive Wilson 95% binomial interval**
  but state the limitation: the 10k TRAIN-derived validation split
  previously influenced model checkpoint selection, so this interval
  does **not** replace unbiased official TEST evaluation.
  There is **no minimum predeclared accuracy threshold** for
  A3.3; physical **semantic agreement/repeatability and full
  denominator reporting** define the gate.
- **Physical ownership:** same dedicated JTAG/bare-metal DDR test
  mode proven in A2/A3.2. A human reboots KV260 before **every**
  independent physical launch, including repeats, and afterward
  regardless of success. No Linux ownership of the memory window
  0x40000000..0x43FFFFFF. The host only provisions, launches and
  observes each fixed batch; A53 owns all 26 timesteps.

This protocol may evolve **only in a separately versioned future
milestone**, never retroactively after physical observations.

## A3.3.1 — Prepare original training-only IDX and freeze all 8 batches

Use the current P07 branch from the repository. A3.2 physical
evidence must remain preserved. Run from V3 root:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-a-784-axon-streaming
git pull --ff-only origin agent/v3-p07-a-784-axon-streaming
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a3_3_protocol.py \
  tests/test_p07_a3_validation.py \
  tests/test_p07_a2_batch.py \
  tests/test_p07_a2_evidence.py

PYTHONPATH="$PWD/src" python scripts/p07_a3_3_prepare.py \
  --data-dir data/mnist_raw \
  --out artifacts/p07_a3_3_val128_first_v1

PYTHONPATH="$PWD/src" python scripts/p07_a3_3_one.py \
  --protocol-dir "$PWD/artifacts/p07_a3_3_val128_first_v1" \
  --evidence-root "/tmp/v3_p07_a3_3_val128_native_preflight" \
  --run-id batch_00_primary
```

The last CLI **defaults to DRY-RUN**; it does NOT program FPGA or
overwrite DDR without `--execute` and the external affirmative
DDR overwrite admission flag.

Successful preparatory markers:
```text
P07_A3_3_VALIDATION_SELECTION=FROZEN_FIRST_128
P07_A3_3_UNIQUE_FRAMES=128
P07_A3_3_PRIMARY_BATCHES=8
P07_A3_3_REPEAT_BATCHES=2
P07_A3_3_REQUIRED_A53_LAUNCHES=10
P07_A3_3_DIAGNOSTIC_DENOMINATOR=128
P07_A3_3_CORPUS_NATIVE_PASS=1
P07_A3_3_PHYSICAL_STATUS=NOT_RUN
P07_A3_3_OFFICIAL_TEST=SEALED
P07_A3_3_DRY_RUN=1
```

The batch destination is **never overwritten**. Each
`batch_00` through `batch_07` contains an accepted
`P07A2B01` wire header, 16×2480-byte source records,
64KiB zero mailbox, an A2-compatible hash manifest and a
**host-only** canonical label ledger. The root
`p07_a3_3_protocol.json` cryptographically pins every
batch, 128 frame source IDs, and the ten physical run IDs.
The official TEST set is never accessed.

## A3.3.2 — One (explicit) physical run at a time

Only after the user's independent A3.3.1 native acceptance.

Keep the previously accepted **corrected** P07-A2 A53 ELF,
`P07_A2_BUILD_DIR` and accepted FPD128 XSA/bitstream;
the guarded script rejects mismatched C, P03 headers,
ELF identity, XSA, DDR master and input-record hashes.

```bash
# Same V3 root, original accepted P07 A53 toolchain environment.
# P07_A2_BUILD_DIR, P03_DIAG_REPORTS, and P03_2C_EXPECTED_XSA_SHA
# must still refer to your SUCCESSFUL A3.2 physical artifacts.
export P07_A3_3_PROTOCOL="$PWD/artifacts/p07_a3_3_val128_first_v1"
export P07_A3_3_EVIDENCE="/tmp/v3_p07_a3_3_val128_$(date +%Y%m%dT%H%M%S)"

# Before this command, reboot the KV260 into dedicated JTAG/bare-metal.
export P07_A2_CONFIRM_KV260_DDR_OVERWRITE=YES
PYTHONPATH="$PWD/src" python scripts/p07_a3_3_one.py \
  --protocol-dir "$P07_A3_3_PROTOCOL" \
  --evidence-root "$P07_A3_3_EVIDENCE" \
  --run-id batch_00_primary --execute
```

The helper refuses to proceed if the predecessor run is
missing/failed, and never overwrites a previous physical
evidence directory. It drives **exactly ONE invocation** of
the existing guarded `run_p07_a2_physical.sh`, which stages
the specific batch, starts the A53 exactly once and checks
the full physical P03 oracle. It cannot auto-run ten launches.

After a **reboot before each launch**, repeat the same
single-run command with these remaining IDs, preserving the
*same* `P07_A3_3_EVIDENCE`:

```text
batch_01_primary
batch_02_primary
batch_03_primary
batch_04_primary
batch_05_primary
batch_06_primary
batch_07_primary
batch_00_repeat
batch_07_repeat
```

A final reboot is mandatory. The result folder stores
`<run_id>/p07_a2_mailbox.bin` and exact original
`physical_identity.txt`, `verify.log`, `a53_run.log`,
`ps_width.log`, `program.log` and `provision.log`.

## A3.3.3 — Independent full-population acceptance scorer

Only after all ten physical launches pass:

```bash
PYTHONPATH="$PWD/src" python scripts/p07_a3_3_verify.py \
  --protocol-dir "$P07_A3_3_PROTOCOL" \
  --evidence-root "$P07_A3_3_EVIDENCE" \
  --report "$P07_A3_3_EVIDENCE/p07_a3_3_validation128_report.json" \
  | tee "$P07_A3_3_EVIDENCE/score.log"
```

Before producing accuracy it independently reloads the
same canonical TRAIN archives/checkpoint, re-derives all
128 input records and label rows, and verifies all ten real
physical mailboxes against P03 packed replay. **Any first
numerical mismatch stops scoring**. The two cold-launch
repeat mailboxes must match their original primary
mailboxes byte-for-byte.

Acceptance markers (only after actual physical evidence):
```text
P07_A3_3_PHYSICAL_RUN_EXACT=<ten run IDs, one per line>
P07_A3_3_VALIDATION_CORRECT=<integer>/128
P07_A3_3_VALIDATION_SILENT=<integer>/128
P07_A3_3_DIAGNOSTIC_WILSON95=<lower>,<upper>
P07_A3_3_PHYSICAL_LAUNCHES_EXACT=10/10
P07_A3_3_RESTART_REPEATS_BYTE_EXACT=2/2
P07_A3_3_PHYSICAL_ORACLE_EXACT=1
P07_A3_3_OFFICIAL_TEST=SEALED
P07_A3_3_PHYSICAL_GATE_PASS=1
```

## Stop conditions and nonclaims

**A3.3 is NOT closed by native/CI tests**. Its physical acceptance
requires original 10 hardware-run mailboxes and their first-divergence
comparison. No results should be imagined from the previously
observed 15/16. No official test-set accuracy, P08 throughput/power
or scaled Track B results are implied. Do not merge without the
user's explicit authorization.

## Post-run user acceptance (2026-10-17)

**A3.3 CLOSED / independently user-accepted** after all eight primary
and two repeat physical runs were passed and the official aggregate
validation verifier reported `116/128` correct, `0/128` silent,
`P07_A3_3_PHYSICAL_LAUNCHES_EXACT=10/10`,
`P07_A3_3_RESTART_REPEATS_BYTE_EXACT=2/2`,
`P07_A3_3_PHYSICAL_ORACLE_EXACT=1` and
`P07_A3_3_PHYSICAL_GATE_PASS=1`. The original pre-run frozen
experimental plan above is retained for reproducibility and should
not be reinterpreted as still pending. See
`P07_A3_3_PHYSICAL_ACCEPTANCE.md` for user evidence and limitations.

**Next gate:** `P07_A4_OFFICIAL_TEST_PROTOCOL_FREEZE.md`,
which freezes full canonical 10,000-image TEST scope *before*
test archives are opened. The unchanged 16-frame A53 ABI implies
625 separate board launches; assess feasibility before unsealing.
