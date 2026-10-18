# P07-A3.3 — 128-image physical validation and independent restart acceptance

**Status:** CLOSED / USER-ACCEPTED on **2026-10-17**.
**Scope:** frozen TRAIN-derived 128-image validation diagnostic. **Official
canonical MNIST TEST remains SEALED / NOT READ.**

## Physical experiment

The user ran the precommitted P07-A3.3 protocol across **ten** real
KV260 / Cortex-A53 autonomous 16-image launches:
eight primary 16-image batches (`batch_00_primary` through
`batch_07_primary`), followed by two independent A53
restart/reprovisioning repetitions (`batch_00_repeat` and
`batch_07_repeat`). The user invoked the strict aggregate
physical verifier `scripts/p07_a3_3_verify.py`. Its successful
return and printed markers attest (i) actual on-device results for all
ten launch IDs and their physical-run logs, (ii) first-mismatch
software replay agreement over all physical output spike
trains/routing and one full 26×42 trace per batch, (iii) two
**byte-for-byte identical full 64 KiB mailbox repeats**,
(iv) train-only source/image/label provenance, and (v)
score of all 128 unique source IDs without counting repeats.

User-pasted aggregate output (verbatim):

```text
P07_A3_3_PHYSICAL_RUN_EXACT=batch_00_primary
P07_A3_3_PHYSICAL_RUN_EXACT=batch_01_primary
P07_A3_3_PHYSICAL_RUN_EXACT=batch_02_primary
P07_A3_3_PHYSICAL_RUN_EXACT=batch_03_primary
P07_A3_3_PHYSICAL_RUN_EXACT=batch_04_primary
P07_A3_3_PHYSICAL_RUN_EXACT=batch_05_primary
P07_A3_3_PHYSICAL_RUN_EXACT=batch_06_primary
P07_A3_3_PHYSICAL_RUN_EXACT=batch_07_primary
P07_A3_3_PHYSICAL_RUN_EXACT=batch_00_repeat
P07_A3_3_PHYSICAL_RUN_EXACT=batch_07_repeat
P07_A3_3_VALIDATION_CORRECT=116/128
P07_A3_3_VALIDATION_SILENT=0/128
P07_A3_3_DIAGNOSTIC_WILSON95=0.843270,0.945556
P07_A3_3_PHYSICAL_LAUNCHES_EXACT=10/10
P07_A3_3_RESTART_REPEATS_BYTE_EXACT=2/2
P07_A3_3_PHYSICAL_ORACLE_EXACT=1
P07_A3_3_OFFICIAL_TEST=SEALED
P07_A3_3_PHYSICAL_GATE_PASS=1
```

**Measured small validation diagnostic accuracy:** 116/128 =
90.625%, silent 0/128. The [84.327%, 94.556%] interval is
the script's **descriptive** 95% Wilson interval, not an official
MNIST TEST confidence interval. The 128 selected validation samples
include the first 16 evaluated in A3.2, so they are not an
independent set of 128 never-observed validation images.

**Evidence directory on user's PC (from first accepted batch):**
`/tmp/v3_p07_a3_3_val128_20261017T133340`.
The aggregate command wrote
`p07_a3_3_validation128_report.json` inside the configured
`P07_A3_3_EVIDENCE` and its console was recorded to `score.log`.
The user has not provided independent SHA256 values or uploaded
all ten 64KiB mailboxes, report and logs into the repository; do not
claim that this repository itself contains those physical binary files.
The user-confirmed aggregate terminal output is the independent
acceptance basis. The first batch's actual terminal markers were also
provided separately in conversation.

## Acceptance decision and research boundaries

**P07-A3.3 CLOSED.** The measured results establish numerically exact
and restart-reproducible A53-controlled FPGA inference across the
precommitted 128 validation source images and ten launches.

This is **not** full MNIST TEST evaluation, unbiased held-out official
test accuracy, throughput/latency/energy measurement, a multi-core
fabric scale-up, or original Intel Loihi physical equivalence.
Do not use the validation score to tune/retrain/reselect the already
frozen P06-A4 checkpoint before official test. Official TEST is
still sealed.

**Next:** P07-A4.1 frozen official TEST run protocol. The authoritative
precommitted P06 contract requests the full **10,000 canonical test
images in original IDX order**, one accepted prediction per image.
The existing P07-A2 wire format carries at most 16 frames per
A53 launch, so current hardware would require **625 individual
batch launches** for a complete original-order evaluation.
No unsealing or physical official TEST result is authorized merely
by closing A3.3; dataset identities, run feasibility/handling and
scoring protocol must be committed first. Any later reduction
must be a **separately predeclared** protocol before viewing official
test predictions or labels. No merge to main without explicit approval.
