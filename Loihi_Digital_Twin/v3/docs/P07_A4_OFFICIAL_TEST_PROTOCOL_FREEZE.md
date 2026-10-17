# P07-A4 — Precommitted official canonical MNIST TEST evaluation

**Precommitted:** 2026-10-17 **BEFORE** opening, downloading, staging,
scoring or physically running any `t10k` test sample for this
project. **Official TEST remains SEALED** at the end of this document
authoring and A4.1 native implementation. No measured TEST result
is present. Development branch
`agent/v3-p07-a-784-axon-streaming`; do not merge without approval.

## A4.1: primary population and go/no-go

The authoritative `P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md`
specifies **all 10,000** original-order images as the
**primary** official test population. We **choose that
full-population protocol now**, before any test archive is read.
No post hoc class filtering, class balancing, confidence/difficulty
selection, or truncated scored denominator is permitted.

The frozen accepted *project-trained* 784→32→10 compact checkpoint,
P06-A4.2 512KiB immutable P02 DDR image, Loihi numerical
rules, 25 input +1 drain timestep encoder, one-tick hidden→readout
NEXT packet routing, tie/zero count rule, physical routed
P03.2c bitstream and corrected autonomous A53 ELF are
unchanged. No training/retraining, weight retuning or
hyperparameter/threshold selection may occur after viewing
official test labels, predictions or error cases. The
previously observed 94.39% 10k TRAIN-derived validation score
and 116/128 (90.625%) physical validation diagnostic are
*not* official TEST results.

### Canonical dataset identity

Canonical `torchvision` MNIST source and resource MD5:

- `t10k-images-idx3-ubyte.gz` MD5
  `9fb629c4189551a2d022fa330f9573f3`
- `t10k-labels-idx1-ubyte.gz` MD5
  `ec29112dd5afa0611ce80d1b7f02629c`

Pinned source:
`https://github.com/pytorch/vision/blob/main/torchvision/datasets/mnist.py`
and official `https://zenodo.org/records/10058130` mirrors.
The first explicit A4.2 unseal command must record
**SHA256 of the actual two compressed archives and
uncompressed IDX byte streams**. No expected SHA256 for
unseen local files is invented. Validate exact IDX big-endian
magic 2051/2049, 28×28 dimensions, exactly 10000 images,
one uint8 class (0..9) per image, zero trailing data and
correct compressed MD5 before accepting bytes. Original
IDX order is test IDs 0..9999. No training/validation
images or augmentation are allowed in the official test
batch. Raw image bytes are *not normalized*; map the
pixel-to-axon IDs from accepted P06 compiler.

## Hardware mapping and feasibility before unseal

The **existing, accepted P07-A2 versioned wire format** accepts
at most 16 P07-A1 2480-byte image records per 64-byte
P07A2B01 header, and returns a 64KiB physical mailbox for
each batch. Therefore, a complete **10,000-image TEST evaluation
on unchanged firmware** requires exactly
`10000 / 16 = 625` original-order physical batches:
`batch_0000` contains indices 0..15; `batch_0624`
contains indices 9984..9999.

Each physical batch requires one guarded A53 launch, an
accepted JTAG-owned reserved DDR re-provision, and an
independent oracle check. **The current previously accepted
runbook requires a KV260 reboot before every launch,
meaning 625 separate reboots/launches.** That is a material,
potentially very costly experimental constraint; it is
**not** already a practical high-throughput streaming solution.
No claim of board runtime scalability or full-test
completion is made by merely preparing 625 host batches.

Before unsealing, the user must explicitly assess whether
this physical run budget is feasible. A *future* separately
accepted persistent board-local streaming extension could
reduce launch overhead, but it must (1) freeze the
same 10000-image population, source hashes and every
sample's independent validation, (2) first pass distinct
synthetic/validation numerical and reset/repeatability
gates, and (3) never alter the frozen model/oracle.
Until accepted, the existing 16-frame A53 ABI is the
only verified physical mechanism. If 625 launches are
infeasible, **do not open the test set** and instead
predeclare a separate, explicitly named reduced
population/selection before reading any test labels or
predictions. Its report must say `N/10000` coverage,
not full 10k accuracy. This document does not
preapprove or silently substitute such a reduced run.

## Frozen run order / integrity

- Full test: one primary physical prediction and complete
  ten output spike counts per canonical index 0..9999.
  Exactly 625 `batch_0000` through `batch_0624`,
  16 immutable A1 wire records each, trace-selected
  first image in each batch.
- Every A53 run must terminate with mailbox
  `0x600D600D`, all 16 complete frame records,
  accurate source-CRC, per-step spikes/counts, input
  event totals and NEXT packet drain/drop totals.
  `compare_to_packed_oracle` must find ZERO
  divergences in all 16 output spike trains/routing,
  and all 26×42 detailed compartment trace fields
  for the trace-selected first image.
- Raw 64KiB mailboxes, full original XSDB/provision/
  bitstream/width/verify logs, first-failure details,
  XSA/ELF/DDR SHA256, fixed batch hashes, original
  image index and image hash must be preserved under
  immutable per-batch evidence directories. A physical
  `PASS` requires original-run evidence, not host
  mocking or an empty zero mailbox.
- Host labels remain in a **separate ledger never
  staged to the A53 or reserved DDR**.
  Only after numerical parity and provenance checks
  for the complete precommitted population may
  official classification accuracy be released.
- **Errors and timeouts:** stop on first failed
  batch; preserve everything and classify failure.
  Do not omit an image and silently decrease the
  denominator, backfill a different image, relabel
  or retune; do not report a partial successful
  subset as unbiased full 10k evaluation.
  Any remediation/retry is documented, with the
  failed attempt retained and labeled. The primary
  `10000` denominator is never changed after
  test data has been viewed.
- **Readout/reporting:** exact correct/10000,
  confusion matrix, per-class support and recall,
  all-silent count/10000, full 10000 prediction
  entries with class counts, canonical source ID,
  image SHA256, payload/ELF/XSA/DDR identities,
  failures/timeouts and explicit success denominator.
  A 95% Wilson interval may be shown as descriptive
  test uncertainty; report study scope, not a
  competing Loihi chip accuracy.
- **Measurement policy:** A4 is primarily numerical/
  classification verification. No latency/throughput/
  power/energy number from A53 launch overhead,
  Vivado programming, PS processing, FPGA dispatch
  or external PC provisioning may be called complete
  inference latency without explicit timer endpoints.
  P08-A subsequently freezes and measures these
  separately. Hardware programming/boot/staging
  overhead is a separate setup cost, never hidden.

## Required acceptance stages

**A4.1 — FREEZE and independently verify (CURRENT):**
Commit this full-10k protocol, canonical MD5, immutability/
no-skip logic, 625-batch hardware feasibility gate, mock
dataset parsing and no-unseal Python tests. CI pass does not
open official test data.

**A4.2 — Authorize explicit unseal/data provenance:**
Only after user accepts A4.1 and 625-launch feasibility
(or formally versions an alternative pretest protocol).
Execute *explicit* test-only archive download and
native manifest/importer integrity gate, pin observed
SHA256; never let test labels affect checkpoint/hardware
design. No GitHub CI should fetch MNIST TEST.

**A4.3 — Complete FPGA physical primary population:**
Reproduce exact per-index records and run every sample
with the accepted hardware; strict first-divergence gate
and evidence ledger for each batch. Do not start until
hardware scheduling/dataset unseal gates clear.

**A4.4 — Independent final scoring and closeout:**
Verify every run, original-order 10k label alignment,
all raw evidence and correct denominator before
calculating official physical accuracy; publish failures
and comparability limitations without retuning.

The first failed acceptance condition halts this phase
until separately investigated. **There is no accepted
P07-A4 official test score yet.**
