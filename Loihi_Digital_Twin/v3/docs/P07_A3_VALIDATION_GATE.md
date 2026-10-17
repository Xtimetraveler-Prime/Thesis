# P07-A3 — Frozen validation-only KV260 trained inference

**2026-10-17:** A2 exact-trace **PHYSICAL PASS, USER-ACCEPTED**
(`P07_A2_FINAL_ACCEPTANCE.md`). **A3.1 IMPLEMENTED,
PENDING INDEPENDENT USER NATIVE GATE.** A3 physical numerical and
validation-accuracy evaluation is **NOT YET RUN**. Branch
`agent/v3-p07-a-784-axon-streaming`; do not merge without explicit approval.

## Purpose, phases, boundaries

A2 demonstrated physically exact autonomous A53→PL execution for
three synthetic frames. A3 tests the actual trained physical classifier
on **real, held-out, TRAIN-derived validation images**, without opening
the canonical MNIST TEST partition. An independent packed replay must
match physical output spike counts and routing on every selected frame;
full 26×42 trace comparison remains available on the selected one
frame per 16-image batch. Labels are reconciled only *after* physical
numerical parity is established.

- **A3.1: immutable diagnostic validation corpus and provenance.** Select
  exactly **the FIRST 16 source indices in the frozen
  `random.Random(20261013).shuffle(range(60000))` 10k validation order**.
  Selection is entirely independent of labels, classifier predictions,
  confidence, image difficulty, or hardware performance. A fixed 16-image
  batch does not provide a population accuracy estimate. Trace index 0.
  Freeze exact image hashes, per-record hashes, corpus/order/label ledger,
  strict TRAIN-only source hashes, compiler/DDR identifiers, and byte
  compatibility with the accepted P07-A2 A53 batch header.
- **A3.2: physical validation diagnostic and first-divergence gate.**
  Execute on JTAG-controlled KV260 with one autonomous A53 batch,
  independently compare 16 output spike trains and route totals
  plus all 26×42 compartment traces for validation frame 0 against
  frozen packed oracle, and only then disclose 16 validation labels,
  top-1 correct/denominator, all-silent rate and confusion counts.
  The label file is **never** staged into physical DDR.
- **A3.3 (separate future gate):** Before broad physical validation or
  official test evaluation, predeclare a larger validation sampling
  plan and evaluate board reproducibility, independent run variation,
  timeout/error handling, A53 restart and batch boundaries. No chosen
  number, population success rate or physical accuracy claim yet.
- **A4 (separate future gate):** official *test* 10k remains sealed.
  Prespecify evaluation population/run budget, test IDX identities,
  repetitions, failure denominator and no-retuning policy **before**
  unsealing. Frozen `P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md` is
  authoritative; do not reinterpret a 16-validation-image diagnostic
  as official TEST accuracy.

No new Loihi arithmetic, FPGA bitstream, P03 scheduler, P05 accepted
diagnostics, A53 ELF or immutable P06 weights are changed by A3.1.
Do not confuse the *training-derived* validation subset with the
original/canonical MNIST test partition.

## A3.1 native reproduction — no need to rerun Vitis

With source code checkout updated to the latest P07 branch, the
existing standalone P07-A2 A53 firmware and accepted bitstream are
reused *as-is*. `p07_a3_prepare.py` validates the exact P06
training manifest against fresh strict canonical TRAIN-only gzip
archives and checks the frozen model/DDR/compiler fingerprints before
creating any output.

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-a-784-axon-streaming
git pull --ff-only origin agent/v3-p07-a-784-axon-streaming
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a3_validation.py \
  tests/test_p07_a2_batch.py \
  tests/test_p07_a2_evidence.py

PYTHONPATH="$PWD/src" python scripts/p07_a3_prepare.py \
  --data-dir data/mnist_raw \
  --out artifacts/p07_a3_val16_first_v1
```

Expected:
```text
P07_A3_FIXED_VALIDATION_SELECTION=FIRST_16
P07_A3_FRAME_COUNT=16
P07_A3_BATCH_HOST_PASS=1
P07_A3_OFFICIAL_TEST=SEALED
P07_A3_BOARD_STATUS=NOT_RUN
```

Outputs: existing A2 wire names
`p07_a2_header_64.bin`, `p07_a2_ingress_payload.bin` (16×2480B),
`p07_a2_mailbox_zero_64k.bin`, `p07_a2_manifest.json` plus
`p07_a3_validation_labels.json`, which is *host-only*.
The output directory is new and cannot be overwritten. For a rerun
choose a different suffix (do not delete old evidence).

## A3.2 physical run and independently scored readout (after A3.1 PASS)

**The guarded physical script halts A53 Linux and overwrites the
reserved 0x40000000..0x43FFFFFF DDR area.** Reboot into the
previously accepted dedicated bare-metal JTAG test state first,
do not run with Linux in ownership of that region, and reboot
afterward even on failure. The existing corrected trace-fix ELF
must still be present in `P07_A2_BUILD_DIR` and its staged source
must be byte-identical to the current branch.

```bash
# V3 root, with the accepted P03_DIAG_REPORTS,
# P03_2C_EXPECTED_XSA_SHA and corrected P07_A2_BUILD_DIR
# from the successful P07-A2 physical run:
export P07_A2_BATCH_DIR="$PWD/artifacts/p07_a3_val16_first_v1"
export P07_A2_RUN_DIR="/tmp/v3_p07_a3_val16_$(date +%Y%m%dT%H%M%S)"
export P07_A2_CONFIRM_KV260_DDR_OVERWRITE=YES
bash scripts/run_p07_a2_physical.sh

# Only after the exact physical gate above succeeds:
PYTHONPATH="$PWD/src" python scripts/p07_a3_verify.py \
  --batch-dir "$P07_A2_BATCH_DIR" \
  --mailbox "$P07_A2_RUN_DIR/p07_a2_mailbox.bin"
```

The P07-A2 physical runner first enforces
`P07_A2_PHYSICAL_TRACES_EXACT=1` for the selected frame and exact
all-frame spike/route totals before reporting
`P07_A2_GATE_FULL_PHYSICAL_PASS=1`. The A3 verifier then
*independently reloads the canonical TRAIN archives* and validates
each label, source index and image against the on-board inputs
before confirming first-divergence parity again. Only after both
gates pass does it produce:
```text
P07_A3_PHYSICAL_VALIDATION_EXACT=1
P07_A3_VALIDATION_ACCURACY=<integer>/16
P07_A3_VALIDATION_SILENT=<integer>/16
P07_A3_OFFICIAL_TEST=SEALED
P07_A3_PHYSICAL_GATE_PASS=1
```

The diagnostic score is NOT an official MNIST test result and is NOT
necessarily representative of the full held-out 10k validation population.

If something fails, **STOP at the first failure**, preserve the
raw mailbox and entire `P07_A2_RUN_DIR` with original file hashes,
reboot the KV260, and report the failure. No changes to the
frozen P06 checkpoint, Loihi numerical semantics, acceptance
goldens, or sealed TEST are justified by one diagnostic mismatch.
