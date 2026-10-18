# P07-A4 — Precommitted official canonical MNIST TEST evaluation

**Precommitted:** 2026-10-17 **BEFORE** opening, downloading, staging,
scoring or physically running any `t10k` test sample for this
project. **A4.1 user-native accepted. Official TEST remains SEALED**
through the A4.2 persistent engineering extension. No measured TEST result
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

## Required acceptance stages — 2026-10-17 approved amendment BEFORE unseal

This amendment changes **the implementation mechanism and phase numbering**,
**not the frozen study population**. A4.1 native full-TEST protocol review
has been user-accepted. User approved the persistent A53/DDR application
direction on 2026-10-17, still before opening any official TEST file.
The original primary 10000-image order, checkpoint, pixel encoder,
timestep/oracle semantics and failure denominator remain unchanged.
The original 625-reboot path is the **validated A2 implementation
baseline**. No one-launch persistent FPGA result is yet claimed.

**A4.1 — COMPLETE / USER NATIVE ACCEPTED (2026-10-17):**
Full original-order 10000 TEST protocol committed, exact official
archive MD5s pinned, sealed-source synthetic-only regressions passed,
manual 625-launch feasibility constraint declared. `--review`
returns SEALED and cannot download TEST.

**A4.2 — NEW: persistent A53 inference infrastructure,
official TEST remains SEALED:**
- **A4.2a COMPLETE / USER NATIVE ACCEPTED on 2026-10-17:**
  distinct versioned `P07A4P01` 256B descriptor + 1568B
  immutable mapping, 8MiB raw image DDR staging, 1MiB
  compact result journal, independent little-endian
  Python/C11 CRC/overflow/digest/record parity and 1/16/128/10000
  synthetic capacity tests, plus a validation-only native stage
  CLI and inspector. See `P07_A4_2_PERSISTENT_DDR_DESIGN.md`.
- **A4.2b COMPLETE / USER VITIS A53 BUILD ACCEPTED
  2026-10-17:** separate candidate persistent
  Cortex-A53 application in `p07_a4_board.c` uses the
  unchanged accepted P07-A2 per-image neural runtime
  and accepted P03 FPGA, new `p07_a4_supervisor.c`
  journal commit/error order, independently checked
  result fields and one selected full diagnostic
  compartment trace. New `build_p07_a4.sh` and
  `build_p07_a4.py` create a separate SHA-bound
  Vitis standalone ELF, with no edits to the accepted
  A2 application, P03 arithmetic or Track A checkpoint.
  User-recorded persistent ELF SHA256:
  `dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`;
  routed XSA matches accepted SHA256 and compiled ELF
  passed LOAD-section DDR isolation. This is a build
  acceptance only; no persistent physical image has
  been run yet. See `P07_A4_2B_VITIS_ACCEPTANCE.md`.
- **A4.2c RAMP16 FIRST PHYSICAL PILOT USER-ACCEPTED;
  FULL VALIDATION/REPEATABILITY PENDING:** guarded independent readback/provision and
  single persistent A53 launch on the accepted FPGA,
  1MiB result journal plus 64KiB trace capture and
  host independent P03 packed oracle first divergence
  on synthetic/TRAIN-derived validation only.
  Native CI does not represent a real FPGA run.
  Accept validation16, validation128, larger coverage,
  reset/repeats, failure cases and first-error evidence.
  See `P07_A4_2B_2C_PERSISTENT_GATE.md`.

**A4.3 — LATER: independently authorize official TEST unseal and
source provenance:** only after all A4.2 physical native gates
pass and a realistic physical dataset run procedure is frozen.
Explicit `--i-accept-unseal` TEST archive download, strict
canonical MD5/IDX and observed SHA256 and exactly original-order
full 10000 test-image staging. A4.1 precommit binds the sample
population; no hardware improvements may change it.

**A4.4 — LATER: full original-order 10000-image physical
evaluation and independent accuracy closeout:** require
complete evidence for every image and entire inference
numerical parity at the declared observability boundary,
terminal status, failures and 10000 exact original-order
labels. Release full score only after the complete
population is independently verified; no retuning.

**P07-A4.2c physical persistent 16, 128 and 1024-image
TRAIN-derived validation runs have now been accepted;
the independent 1024-image COLD REPEAT was accepted
2026-10-17 with 1MiB journal and 64KiB last-image
trace byte-identical across the two actual KV260 launches.
These are NOT official TEST results or classification
scores. The canonical official t10k TEST remains
SEALED/NOT READ. Physical fail-closed fault telemetry
remains the last A4.2c gate before separate A4.3
authorization.**

### Frozen full-TEST observability clarification before unseal

The previously accepted 625-launch A2 baseline stored **one
selected full 26×42 trace per 16-frame batch** (625
selected traces for all 10000 TEST frames); the candidate
persistent A4.2b journal stores **all 26×10 hardware
output spike bits and routes for every one of 10000**
but only **ONE** selected 26×42 full-compartment trace
per autonomous dataset launch. This is *different
diagnostic observability*, not a claim of identical
full-state readback coverage. A4.2c must independently
validate full selected trace integrity, every physical
output spike and route, resetting across many frames
and byte-identical cold runs. Before A4.3 unsealing,
explicitly accept the reduced selected-trace coverage
as part of a separately frozen measurement policy
or plan supplemental traces without changing
the official 10000-image population. No validated
full official TEST accuracy has been produced.

### A4.2c persistent physical pilot update (2026-10-17)

The user independently ran the new persistent ELF and accepted
its first **one-launch 16-image synthetic ramp** physical gate.
The A53 journal completed with `0x600D600D`, and all
16 output spike sequences and selected 26×42 complete
compartment trace exactly matched independent P03 oracle.
The original evidence is on user's PC at
`/tmp/v3_p07_a4_ramp16_20261017T191755`, and the
attested console markers are preserved in
`P07_A4_2C_RAMP16_PHYSICAL_ACCEPTANCE.md`.

A4.2c remains **open**, with a new original-order **128-image
TRAIN-derived validation persistent** primary and cold-start
repeat protocol frozen *before the experiments*. New read-only
`p07_a4_2_crosscheck.py` directly validates this new one-launch
physical evidence against **eight previously accepted actual
P07-A3.3 primary JTAG mailboxes**, every 26×10 output bit,
readout, input event/route and selected full trace; it also
pins the original A3.3 mailbox hashes recorded at acceptance.
See `P07_A4_2C_VALIDATION128_PROTOCOL.md`. A larger
TRAIN-derived validation-only stress gate and physical fault
handling are still required before official unseal. Nothing
from the canonical MNIST TEST has been opened or scored.

### A4.2c sustained-repeat acceptance (2026-10-17)

The user reported `P07_A4_2C_1024_PHYSICAL_LAUNCHES=2/2`,
`P07_A4_2C_1024_HARDWARE_IMAGE_EXECUTIONS=2048`,
`P07_A4_2C_1024_UNIQUE_TRAIN_VALIDATION=1024`,
`P07_A4_2C_1024_JOURNAL_1M_BYTE_EXACT=1`,
`P07_A4_2C_1024_TRACE_64K_BYTE_EXACT=1` and
`P07_A4_2C_1024_RESTART_GATE_PASS=1` on actual KV260
hardware, with original XSDB and independent P03 oracle logs
verified. The original acceptance JSON is on the user's PC at
`/tmp/v3_p07_a4_val1024_repeat_20261017T201021/p07_a4_2c_1024_physical_restart.json`.
See `P07_A4_2C_VAL1024_RESTART_ACCEPTANCE.md`.

Before A4.2c may close, the separately precommitted
**synthetic only** one-word physical descriptor fault must
produce `0xDEAD0001`, zero completed frames and zero neural
results/trace under unchanged A53 ELF, with full original
physical readback and negative-result CRC/provenance checks.
See `P07_A4_2C_FAIL_CLOSED_PROTOCOL.md`.

Before unsealing any official t10k data in A4.3, the project
must also explicitly accept/freeze the different full-compartment
trace sampling coverage of the new persistent implementation,
which physically stores **one selected full 26×42 trace per
entire dataset launch** while recording 26×10 spike flags and
routing for **every image**. The full official 10,000 original
IDX-order population and scoring denominator remain frozen.
