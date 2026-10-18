# P07-A4.3/A4.4 — Full canonical original-order 10,000 MNIST TEST closeout

**Precommitted on 2026-10-17, while official MNIST TEST remains SEALED.**
**A4.2c synthetic physical fail-closed acceptance PENDING.**
**A4.3 TEST unseal NOT YET AUTHORIZED BY SUCCESSFUL FAULT TEST;
official archives NOT OPENED by this implementation.**
**A4.4 10000-image official physical result NOT YET RUN OR SCORED.**
No changed Track A weights, neural arithmetic, FPGA bitstream, Vitis ELF,
input encoder, dataset source, prediction rule or FPGA execution ABI.

## Why the old 625-launch protocol still matters

A4.1 froze the complete, canonical independent MNIST TEST original
IDX-order population `0..9999`, all 10000 labels, fixed
784→32→10 frozen Track A model, original 25+1 ticks,
integer spike-count argmax with class-lowest tie policy
and all-silent count. Its historical A2 16-frame JTAG
protocol required **625 separate launches** and one
selected full 26×42 trace per 16-frame batch.

The user-approved A4.2 persistent amendment changes the
**hardware transport/observability, NOT the denominator,
population, model, metrics or acceptance arithmetic**:
one accepted A53 persistent ELF over 10000 raw images
in the reserved 64MiB DDR, one 1MiB journal with 10000
individually indexed CRC-protected 96B results, **each
image's full 26×10 output spike-bit history**, ten
counts/class, routing/drop/ingress totals; **ONE** full
26×42×32B compartment trace, **preselected last
original IDX image 9999**, in 64KiB DDR region.
This records **less full-compartment diagnostics**
than 625 old A2 batches and must never be described
as hardware full-state equality for every image.
The source/accepted measurements are precommitted
before canonical TEST is opened; physical A4.2c
sustained 1024 restart already proved output parity
and selected last-frame trace reset at image1023.
These are two **different** evidence granularities.

## Three hard gates, in order

**Gate 1 — A4.2c PHYSICAL fail-closed:** perform the
separate synthetic ramp16 one-word post-provision
physical descriptor corruption. Require immutable
accepted A53 ELF SHA256
`dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`,
FPGA accepted XSA SHA256
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`,
original reserved-word mutation evidence and CRC-validated
`0xDEAD0001`, completed=0, 1 requested sentinel,
**ZERO** result records and full zero selected trace,
`P07_A4_2C_PHYSICAL_FAIL_CLOSED_GATE_PASS=1`.
This run is **negative expected rejection**, NEVER an
ordinary physical inference pass. Original successful
16/128/1024 stages and raw evidence must stay untouched.
The new official preparation/check/run scripts
**independently revalidate the ORIGINAL negative
evidence before allowing canonical t10k access**.

**Gate 2 — A4.3 EXPLICIT OFFICIAL TEST UNSEAL:**
a user-controlled CLI invocation must pass BOTH
`--i-accept-unseal` and
`--i-accept-one-trace-policy` *after* Gate 1.
The optional `--download-test` accesses only canonical
`t10k-images-idx3-ubyte.gz` MD5
`9fb629c4189551a2d022fa330f9573f3`
and `t10k-labels-idx1-ubyte.gz` MD5
`ec29112dd5afa0611ce80d1b7f02629c` from the
preaccepted MNIST mirror. Every compressed source
MD5, decoded IDX magic/shape/count/exact length
and observed SHA256 is preserved. Original
0..9999 images exactly row-major raw 784B, no
normalization/reencoding, no sampling. All labels
remain **HOST-ONLY** in a SHA-pinned ledger, never
written to A53 or FPGA. Stage a NEW immutable
`P07A4P01` descriptor, mapping, exact 7840000B
raw pixel blob, initial zero-result 1MiB journal,
host source/label manifest. Trace index exactly
9999. The former A4.1 625 envelopes are historical
precommit evidence; no new 625-launch staging is
required for the approved persistent run.
**No labels, predictions or test accuracy are read
or scored in the preparation step.**

**Gate 3 — A4.4 PHYSICAL ALL 10000 and numerical
closeout:** unique new evidence directory, separate
KV260 bare-metal JTAG-only reboot, reserved 64MiB
DDR exclusive to A53, verify accepted XSA/ELF/master
SHA and unchanged neural C sources, original
six physical raw DDR staging readbacks. Explicit
physical consent `P07_A4_CONFIRM_OFFICIAL_TEST_PHYSICAL=YES`,
`P07_A4_CONFIRM_UNSEALED_TEST=YES`,
`P07_A4_ACCEPT_ONE_TRACE_POLICY=YES`,
and existing `P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES`.
Reuse accepted P03.2c FPGA bitstream and A4.2b
ELF SHA, ONE autonomous Cortex-A53 launch for
**all 10000 original IDX-order images**.
No 625 cold launches, no host-per-frame dispatch
or class-selected CPU fallback. Any first failure,
timeout, missing frame, altered source digest,
incomplete journal, incorrect output spikes,
packet route/drop, class/count/silent,
selected image9999 trace or original 6 DDR
readback = STOP, preserve original raw evidence,
**do not calculate or report accuracy**.
A4.4 independent verifier loads all canonical
archive bytes again, rebinds the entire source
ledger, decodes complete `P07A4R01` CRC
journal, and executes the exact frozen independent
packed P03 oracle for **each of all 10000** images.
Requires **all 26×10** output spike-bit flags,
ten counts, readout, routing/ingress and selected
last-image 26×42 full compartment trace to match
before calling `full_score`.
The report includes 10000 predictions/labels,
class counts and image hashes, correct/10000,
accuracy, all-silent, confusion matrix (rows
truth, columns predicted), class support/recall,
all input/ELF/XSA/bitstream and journal/trace
SHA provenance. Physical power/energy and
latency are P08-A gates, **NOT** claimed by P07-A.

**Predeclared successful final denominator = EXACT 10000,
without exclusions.** A failed or incomplete 10k run is
an unresolved experimental failure, not a reduced-sample
result or permission to retune. Preserve full first-failure
evidence. No merging branch to main until final user-accepted
A4.2c negative and A4.4 verified physical report.

## Step 1 — run synthetic physical negative experiment FIRST

From `~/Git/Thesis/Loihi_Digital_Twin/v3`, with
`.venv-p08` and accepted Vivado/XSDB tools:

```bash
export P07_A4_BUILD_DIR=/tmp/v3_p07_a4_persistent_20261017T190943
export P03_2C_EXPECTED_XSA_SHA=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
export P07_A4_FAULT_STAGE_DIR="$PWD/artifacts/p07_a4_2a_ramp16_v1"
export P07_A4_VAL1024_STAGE_DIR="$PWD/artifacts/p07_a4_2c_val1024_first_v1"
export P07_A4_VAL1024_PRIMARY_EVIDENCE=/tmp/v3_p07_a4_val1024_primary_20261017T200134
export P07_A4_VAL1024_REPEAT_EVIDENCE=/tmp/v3_p07_a4_val1024_repeat_20261017T201021

PYTHONPATH="$PWD/src" python scripts/p07_a4_2_val1024_verify.py \
  --stage-dir "$P07_A4_VAL1024_STAGE_DIR" \
  --primary-dir "$P07_A4_VAL1024_PRIMARY_EVIDENCE" \
  --repeat-dir "$P07_A4_VAL1024_REPEAT_EVIDENCE"

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a4_fault.py \
  tests/test_p07_a4_official.py
bash -n scripts/run_p07_a4_fault_physical.sh

export P07_A4_FAULT_RUN_DIR="/tmp/v3_p07_a4_fail_closed_$(date +%Y%m%dT%H%M%S)"
```

**After independent reboot into bare-metal JTAG-only,
no Linux owner of the reserved 64MiB DDR**, and
with accepted `P03_DIAG_REPORTS` still set:

```bash
export P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES
export P07_A4_CONFIRM_DESTRUCTIVE_FAULT_INJECTION=YES
bash scripts/run_p07_a4_fault_physical.sh
```

Reboot the KV260 AFTER run, even on failure.
Require expected `0xDEAD0001` and
`P07_A4_2C_PHYSICAL_FAIL_CLOSED_GATE_PASS=1`,
`P07_A4_2C_NEGATIVE_TEST_PASS=1`.
**Stop on any other result and do not open TEST.**

## Step 2 — after NEGATIVE acceptance, explicitly unseal and stage

```bash
# Reuse the ORIGINAL, successfully verified negative evidence:
export P07_A4_FAULT_EVIDENCE_DIR="$P07_A4_FAULT_RUN_DIR"
export P07_A4_OFFICIAL_TEST_DATA_DIR="$PWD/data/mnist_official_test_raw"
export P07_A4_OFFICIAL_STAGE_DIR="$PWD/artifacts/p07_a4_3_official_full10000_v1"

# Sealed, SAFE status review (never downloads or opens t10k):
PYTHONPATH="$PWD/src" python scripts/p07_a4_official_prepare.py --review

# These are the user's explicit TEST unseal & one-trace policy decisions.
# If canonical t10k archives are already present, omit --download-test.
PYTHONPATH="$PWD/src" python scripts/p07_a4_official_prepare.py \
  --prepare --download-test \
  --i-accept-unseal --i-accept-one-trace-policy \
  --fault-stage-dir "$P07_A4_FAULT_STAGE_DIR" \
  --fault-evidence-dir "$P07_A4_FAULT_EVIDENCE_DIR" \
  --test-data-dir "$P07_A4_OFFICIAL_TEST_DATA_DIR" \
  --out "$P07_A4_OFFICIAL_STAGE_DIR"

PYTHONPATH="$PWD/src" python scripts/p07_a4_official_check.py \
  --stage-dir "$P07_A4_OFFICIAL_STAGE_DIR" \
  --test-data-dir "$P07_A4_OFFICIAL_TEST_DATA_DIR" \
  --fault-stage-dir "$P07_A4_FAULT_STAGE_DIR" \
  --fault-evidence-dir "$P07_A4_FAULT_EVIDENCE_DIR" \
  --i-accept-unseal --i-accept-one-trace-policy
```

Do not download or invoke any `--prepare` command
until physical synthetic fault ACCEPTED. Never
overwrite the original staged official directory.
No full TEST predictions should be viewed before
the complete physical all-10000 run succeeds.

## Step 3 — physical final 10000 (after stage PASS)

Accepted Vitis ELF has original SHA256
`dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`.
Original accepted P03.2c reports and source
remain unchanged. Create a fresh absolute evidence
directory, then **physically reboot** into the
independent JTAG-only bare-metal state first:

```bash
export P07_A4_OFFICIAL_TIMEOUT=28800
export P07_A4_OFFICIAL_RUN_DIR="/tmp/v3_p07_a4_official_full10000_$(date +%Y%m%dT%H%M%S)"
export P07_A4_CONFIRM_OFFICIAL_TEST_PHYSICAL=YES
export P07_A4_CONFIRM_UNSEALED_TEST=YES
export P07_A4_ACCEPT_ONE_TRACE_POLICY=YES
export P07_A4_CONFIRM_KV260_DDR_OVERWRITE=YES
bash scripts/run_p07_a4_official_physical.sh
```

Board reboot AFTER execution, including failure.
Read-only independent closeout is part of the
runner; it produces `p07_a4_4_official_full10000_report.json`
only if full 10k physical oracle exact. It must
print:

```text
P07_A4_4_CANONICAL_FULL_ORIGINAL_ORDER=10000/10000
P07_A4_4_PHYSICAL_INDEPENDENT_OUTPUT_SPIKES_ROUTES_EXACT=10000/10000
P07_A4_4_FINAL_IMAGE9999_FULL_COMPARTMENT_TRACE_EXACT=1
P07_A4_4_ALL_SIX_ORIGINAL_DDR_READBACKS_EXACT=1
P07_A4_4_PREVIOUS_PHYSICAL_FAULT_ACCEPTANCE_PASS=1
P07_A4_4_COMPLETE_PHYSICAL_DENOMINATOR=10000
P07_A4_4_OFFICIAL_TEST_CORRECT=<correct>/10000
P07_A4_4_OFFICIAL_TEST_ACCURACY_PERCENT=<percentage>
P07_A4_4_FULL10000_KV260_INDEPENDENT_CLOSEOUT_PASS=1
P07_A4_4_FULL_CANONICAL_TEST_PASS=1
```

These are future expected markers, **not observed
results**. Do not invent accuracy, percentages,
raw SHA artifacts or claim A4.3/A4.4 closure
until the user independently reports actual full
FPGA verification and explicitly authorizes merge.

## Explicit limitations

This is an original-order canonical MNIST TEST
classification benchmark with a single accepted
A53/PL execution path. It does not claim 10000
full per-neuron compartment traces, end-to-end
latency/throughput measurement, rail-specific
energy/power, scaled Track B, a physical Loihi
silicon implementation or better generalization
than independently frozen training procedure.
