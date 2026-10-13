# P06.1 offline official author checkpoint audit (no Loihi/FPGA required)

**Status: INITIAL NATIVE REGRESSION USER-CONFIRMED PASS;
additional source-coefficient-density unit tests and actual nine-file
author-source/weight audit PENDING.** Candidate NOT frozen.
Exact paper-96%-checkpoint identity remains UNKNOWN. Detailed
original paper/supplement metrics and GO/NO-GO analysis:
`P06_1_PAPER_METRIC_AUDIT_AND_DECISION.md`.

The candidate is Rao et al. (Nature Machine Intelligence 2022)
**sequential MNIST** with source files and pretrained weights from
the paper-linked Intel `intel-nrc-ecosystem/models` project.
The immutable source commit is
`3dc53bfcfae1efe8772b8cb5e2c512bb28c872f8`.

## 1. Pull only the P06 development branch

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p06-benchmark-audit
git pull --ff-only origin agent/v3-p06-benchmark-audit

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m py_compile \
    scripts/p06_1_lsnn_source_audit.py \
    scripts/p06_1_lsnn_io_contract.py \
    tests/test_p06_1_lsnn_source_audit.py \
    tests/test_p06_1_lsnn_io_contract.py
PYTHONPATH="$PWD/src" python -m pytest -q \
    tests/test_p06_1_lsnn_source_audit.py \
    tests/test_p06_1_lsnn_io_contract.py \
    2>&1 | tee /tmp/v3_p06_1_native.log
```

Only a synthetic parser/manifest regression runs here,
not an author's trained network nor a board experiment.

## 2. Fetch ONLY the immutable paper-linked source

In a separate folder, not underneath the Thesis repository.
This does not require access to NxSDK and does not alter the
accepted P05. It downloads only official committed file
content through Git sparse checkout.

```bash
mkdir -p ~/Git
cd ~/Git

git clone --filter=blob:none --no-checkout \
    https://github.com/intel-nrc-ecosystem/models.git \
    paper_lsnn_intel_models

cd ~/Git/paper_lsnn_intel_models
git sparse-checkout init --cone
git sparse-checkout set \
    nxsdk_modules_ncl/lsnn/apps/seqmnist \
    nxsdk_modules_ncl/lsnn/src

git checkout 3dc53bfcfae1efe8772b8cb5e2c512bb28c872f8

git rev-parse HEAD
git status --short
```

The checkout must also include `apps/seqmnist/seq_mnist.py` and
`apps/seqmnist/seq_img_classifier.py`. The prior sparse selection
included `weights/`, `snips/` and `src/` but omitted these **two
mandatory Python source files**, so it could not pass the actual
nine-artifact source audit. This corrected selection includes both.

`git rev-parse HEAD` MUST produce the pinned full commit
SHA above; `git status --short` should be empty.
If checkout cannot resolve the SHA, use:
`git fetch origin 3dc53bfcfae1efe8772b8cb5e2c512bb28c872f8`
then check it out. Do not blindly substitute today's
mutable branch contents.

## 3. Prove the source and pretrained weight identity

```bash
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python scripts/p06_1_lsnn_source_audit.py \
    --upstream-repo ~/Git/paper_lsnn_intel_models \
    --out /tmp/v3_p06_1_official_source_audit.json \
    2>&1 | tee /tmp/v3_p06_1_source_audit.log
```

Expected end:

```text
PASS: P06.1 official paper-linked upstream git commit and all nine immutable author artifacts exact
PASS: P06.1 all three genuine pretrained source weight files verified, no retraining or fabricated weights
P06_1_SOURCE_AUDIT_EXIT=0
P06_1_PAPER_FREEZE=NOT_ACCEPTED_AHP_EXTENSION_AND_BENCHMARK_METRIC_AUDIT_REQUIRED
```

The source checker uses git blob identifiers and independent
`.npy` literal-header parsing, requiring **exact shapes**:

- `w_in.npy`: on disk **80 × 240** (source × destination), runtime **240 × 80** after `.T`;
- `w_rec.npy`: on disk **240 × 240**, runtime **240 × 240** after `.T`;
- `w_out.npy`: on disk **240 × 10** (source × destination), runtime **10 × 240** after `.T`.

**Previously observed P06.1 source-audit FAIL:** the
original verifier wrongly demanded the **runtime
transposed** shape from the genuine **on-disk**
`w_in.npy`. The author loader in
`apps/seqmnist/seq_mnist.py` actually says
`out = (wIn.T, wRec.T, wOut.T)`. The pinned
author Git blob bytes contain `<f4` stored
matrices of shapes (80,240), (240,240),
(240,10). The checker, manifest and regression
have been corrected to enforce **both**
the authentic stored and transposed runtime
shapes. There was never evidence of a
bad published weight file.

Dtype is intentionally extracted from the actual
binary header; it is not guessed from the file name.
The tool also enumerates the **actual sign and zero/nonzero
populations** and minimum/maximum coefficients for each
unchanged .npy array. The paper quotes 20% sparse
connectivity for **its tested network**. We
independently decoded the pinned Git blobs:
**4,263** `w_in`, **10,566** `w_rec`,
**846** `w_out` nonzero values, or **15,675
of 79,200 positions = 19.79%**. All are
finite `float32` containing integer-valued
coefficients in [-254,255]. These content
counts are now part of the pinned manifest
and are rechecked locally by the tool. Inspect the JSON
`topology.source_weight_occupancy` before planning
how many resident logical cores are necessary.
All nine source/weight Git blobs must match the pinned
paper-linked tree byte-for-byte. A missing artifact,
modified source, unexpected rank/shape/dtype, or altered
Git checkout **FAILS**. The final JSON includes both
Git blob SHA-1 and each actual file's SHA-256.

Do NOT run `seq_mnist.py` on official test images
yet. The protocol, the author's measured checkpoint
and the real KV260 AHP compatibility have not been
independently frozen. `P06_1_SOURCE_AUDIT_EXIT=0`
proves only authentic data provenance, not equality
to the published accuracy or FPGA suitability.

If this source fetch succeeds, paste **the native pytest
summary, `P06_1_SOURCE_AUDIT_EXIT=0` and
`P06_1_SOURCE_AUDIT_METADATA`** (especially the
measured nonzero density and real weight dtype).
The source audit's PASS is **not** proof that
these weights produced the published 96.0%.
We will review whether a source-verified
replication is acceptable or instead change
papers, before committing to AHP HLS modifications.

### P06.1 native readout-boundary correction (awaiting independent rerun)

The first user-run P06.1 regression surfaced a mismatch in
`test_argmax_reads_nonspiking_membrane_V_not_output_spikes`:
our model returned `ValueError` (and the test incorrectly
expected digit 0) when all ten `V == -8388608`.

The **author's actual** `snips/snip_mgmt.c` initializes
`maxV=-8388608`, `maxVId=-1` and updates only for
`v>maxV`. Ten minimum voltages therefore return `-1`;
this is a source sentinel/unclassified boundary, not a
digit and not a simulator error. The Python port readout
now returns `-1` without changing the valid 0..9
readout behavior. Added minimum/+1 and strict-tie
tests, and corrected source manifest/audit prose.
A standalone compiled-C versus Python semantic cross-check
covered **2506** original-loop vectors with **2506/2506
identical decisions** (including all-minimum); this is
NOT a full local repository pytest run or an upstream NxSDK
runtime execution. Await user-native pytest rerun before
accepting P06.1.

## 4. Source-specific I/O behavior already extracted

The pinned author C `snips/spiking.c`, `snips/snip_mgmt.c`
and `snips/common.h` are verified along with the
three weight arrays and three Python model sources.
`scripts/p06_1_lsnn_io_contract.py` is a separately
tested, pure logical port-index and decision-rule
transliteration (**not** an Loihi/AHP execution oracle):

- Exactly 840 timesteps/sample: 784 pixel steps
  + 56 classification-cue steps.
- 40 evenly spaced thresholds (original
  `floor(linspace(0,255,40))`), but t=0 is
  skipped; thresholds t=1..38 emit
  rising/falling crossing ports `2*t` and
  `2*t+1`, crossing from pixel[i] to pixel[i+1].
  No crossing may look past the last image pixel.
- t=39 emits **touch** only when current
  pixel==255 (port 78). Input ports 0 and 1
  never occur. Cue emits port 79 for all
  final 56 timesteps. Ports reflect C's
  on-chip input index, not a made-up rate code.
- Classification compares **the ten signed
  output membrane V states** at the end of
  840 steps. The original `snip_mgmt.c` initializes
  `maxV=-8388608` and `maxVId=-1` and uses
  **strict `v>maxV`**. Thus ties **strictly
  above the minimum** select the lowest
  matching index, but if all ten V readings
  equal the signed 24-bit minimum, the original
  SNIP returns the sentinel **`-1`**, not
  digit `0`. Preserve and flag that result
  as unclassified, not a valid MNIST class.
  Output is not a count of outgoing spikes.

`tests/test_p06_1_lsnn_io_contract.py`
verifies these boundaries against the exact
upstream code and `numpy.floor(linspace(...))`
thresholds in the existing v3 Python environment.
This only freezes an **I/O component's identified
source-level semantics**, not the full SNN
or an approved P06 benchmark.

## 5. Publication cross-check and benchmark decision

The author-hosted complete manuscript + supplement
https://igi-web.tugraz.at/PDF/259maass.pdf reports
**96.0% Loihi sMNIST test accuracy** and
**14.11 ms wall-clock / 0.36 mJ Loihi chip-level
energy per inference**, with **20% overall source
connectivity** and **100 AHP neurons** among
240 recurrent cells. The paper's abstract/Methods
do not identify the released
`weights/v25_94per/*.npy` SHA values
as the checkpoint that achieved 96.0%.
The label `94per` is **not** an
accepted numerical accuracy measurement.

Therefore **P06.1 checkpoint-to-paper link
is OPEN** despite accurate paper-level
metric transcription and genuine files.
The correct options are either obtain
author-confirmed original weights/commit,
compare the source-released weights
only to their **own separately measured
source-level accuracy**, or choose a
different paper with public checkpoint identity.
Don't freeze 96.0% as this artifact's baseline.

The supplement's threshold pseudo-code uses
inclusive boundary tests, while the pinned
Loihi C `snips/spiking.c` has additional
strict comparisons and special touch/cue
ports. Our versioned I/O reference follows
the **specific released executable C code**
without quietly substituting the broader
paper pseudo-code. The end-of-image C SNIP
also clears neuron states and accumulators,
a requirement for the future board inference.

See `P06_1_PAPER_METRIC_AUDIT_AND_DECISION.md`.
