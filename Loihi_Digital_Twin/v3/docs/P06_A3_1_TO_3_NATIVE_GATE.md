# P06-A3.1–A3.3 — Train-only MNIST reproducibility + learning candidate

**Date:** 2026-10-13
**Branch:** `agent/v3-p06-lif-feasibility`
**Status:** A3.1–A3.3 initial dataset/smoke gate USER-ATTESTED PASS; A3.4
learning-activity pilot CODE COMMITTED / NATIVE VERIFICATION PENDING.
Do NOT mark P06-A3 accepted or start
P06-A4 / P07 from this implementation alone.

## Scope and official-test firewall

The native training data loader `p06_a3_data.py` opens exactly these two
files and never accesses `t10k*` test files:

- `train-images-idx3-ubyte.gz`: upstream torchvision/MNIST archive
  MD5 `f68b3c2dcbeaaa9fbdd348bbdeb94873`.
- `train-labels-idx1-ubyte.gz`: upstream torchvision/MNIST archive
  MD5 `d53e105ee54ea40749a09fcbcd1e9432`.

A dedicated explicit download action fetches **only** these two files
from `https://ossci-datasets.s3.amazonaws.com/mnist/`, verifies
the pinned MD5 before finalizing them, and neither downloads nor opens
the official test images or labels. The loader also validates IDX
magic/dimensions/counts/trailing bytes/label range, requires exactly
60,000 training examples, and records each compressed SHA256 and full
decoded IDX SHA256, the split hashes, and runtime seed. The SHA256 is
the project-specific provenance digest; the published MD5 checks
canonical archive identity.

**Default immutable split:** shuffle indices 0..59999 using
`random.Random(20261013).shuffle`; the first 50,000 are train and
the remaining 10,000 are held-out validation. The ordered lists are
hashed as concatenated little-endian unsigned 32-bit indices.
Canonical pixels are raw 28x28 row-major uint8 (no torchvision
normalization/augmentation); the accepted `p06-uint8-quota-phase17-v1`
encoder transforms them to fixed 25+1 event time. No official test
labels or predictions are available to training or selection.

## Initial fixed, fully declared hypothesis

**Model:** 784→32→10 dense, same-core routed integer SNN.
Neuron configurations are **fixed** and uniform within each layer.
No unvalidated per-neuron learned bias support is introduced.

| Parameter | Hidden 32 | Output 10 |
|---|---:|---:|
| current decay / 4096 | 4096 | 4096 |
| voltage decay / 4096 | 4096 | 4096 |
| strict spike threshold | 32 | 8 |
| bias, reset voltage, refractory | 0, 0, 0 | 0, 0, 0 |
| initialization | uniform (-6, 6) | uniform (-4, 4) |

The default training trial is 8 epochs, batch size 64, seed 20261013,
Adam learning rate 0.05, surrogate width 16, gradient-norm clip 5,
clamped learnable real weights to ±512 (well within signed24).
Loss is `cross_entropy(2 * integer_forward_output_spike_counts, label)`
and backward uses the already accepted A2.5 surrogate/STE.
The **forward** produces exact integer counts and the training gradient
is approximate, by design. Validation-only epoch selection maximizes
validation accuracy (ties keep the earlier epoch). Train and validation
metrics include sample counts, loss, accuracy and validation silent
fraction. These are exploratory defaults, not proven optimal.

**Predeclared validation GO/NO-GO floor: 60.0%** (0.60), fixed before
seeing any real MNIST validation results. Failing to meet this floor
is a reportable NO-GO, not a reason to read sealed test labels.
Additional optimization trials require documented new settings and
distinct output directories, with every trial disclosed.

## Reproducible checkpoint candidates (NOT A4 freeze)

Only the best validation epoch is saved. A candidate folder contains
`weights_state_dict.pt` and `candidate_manifest.json` with schema,
architecture, Python/Torch version, predeclared settings and floor,
all loss/optimizer/initialization/forward details, exact hidden/output
LIF fields (which `state_dict()` does NOT serialize), dataset archive
and split hashes, per-epoch metrics, best validation score and epoch,
checkpoint file SHA256 and SHA256 of destination-major effective
quantized signed weights (portable signed32 LE). Loader checks hashes
and fixed encoder/readout/neuron profile before returning a model.
A synthetic-test manifest can **never** mark `candidate_go` True.

This is a software **candidate**, not the final checkpoint, packed
hardware image or official-test performance result. A4 must independently
prove actual trained image compilation, packet/state parity and frozen
test protocol; the official test stays sealed until A4.

## 2026-10-13 user-provided native acceptance (A3.1–A3.3 early gate)

The user explicitly confirmed the native pytest regressions PASS, and supplied:

- `P06_A3_SYNTHETIC_SMOKE_PASS=1`: optimizer and model invocation
  executed; 12/12 synthetic validation images were all-silent, with
  train/validation accuracy 0.333333 and validation cross-entropy
  2.302585092994046 = ln(10). **This is a computational smoke PASS,
  not evidence that actual learning/output activity is healthy.**
- Both training-only archives verified against the canonical pinned MD5,
  with no official MNIST test archives retrieved.
- `P06_A3_DATA_PREFLIGHT_PASS=1`, 60,000 canonical training records,
  50,000 training / 10,000 validation, split seed 20261013.
- Archive SHA256 compressed / decoded IDX:
  images 440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609 /
  ba891046e6505d7aadcbbe25680a0738ad16aec93bde7f9b65e87a2fc25776db;
  labels 3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c /
  65a50cbbf4e906d70832878ad85ccda5333a97f0f4c3dd2ef09a8a9eef7101c5.
- Train ordered-index SHA256:
  1cbcb0b2bf481958d6c917ea6d70fa44a20839406f0c824540f8e691edfdd851;
  validation:
  3b9520013f30742c3818f55024ea39e3e0632113c487c589fdfbb73c7d274831.
- Official test `SEALED`.

**Decision:** canonical dataset integrity and early A3 computational smoke
are ACCEPTED, as user-attested. No real training/validation model has run,
and the 100% all-silent synthetic output motivates an explicit *bounded
real-data learning-activity pilot* before full eight-epoch fitting.
This early gate alone does NOT accept P06-A3.

## NEW next verification gate: P06-A3.4 learning-activity pilot

User-supplied training-only archive integrity and the earlier computational
smoke passed. However, that smoke produced **100% silent output activity**
on its synthetic stimuli. This is not a learning-performance result and
must not be mistaken for adequate evidence to start lengthy full training.

The newly implemented `p06_a3_pilot.py` takes the **first 256 examples of
the previously frozen 50,000 shuffled train indices** and the **first 128
examples of the frozen 10,000 shuffled validation indices**, executes
**two epochs with batch size 32**, and **never reads the official test
partition**. It uses the currently declared training profile and records
a no-update gradient probe, before/after validation accuracy and silent
fraction, per-class spike/prediction histograms, and the number of
*changed quantized 24-bit* synapses per layer. No checkpoint is written.

To pass the narrow numerical activity gate, the measured run must have:
nonzero finite gradients in both layers, at least one exported integer
weight changing in EACH layer, and at least one validation example
producing an output spike after training. This is only a learning-activity
preflight, NOT proof of converged MNIST accuracy and NOT the independent
P06-A3 60% validation GO/NO-GO criterion.

`P06_A3_PILOT_STATUS=DIAGNOSE_BEFORE_FULL_TRAIN` is **not an exception**
and need not make the CLI exit nonzero: the diagnostic JSON will explain
which activity conditions failed. In that case, stop and inspect before
running the eight-epoch trial. This pilot deliberately does not silently
retune thresholds, scale weights, edit A2 goldens or alter the model
reference to manufacture a pass.

### Run exactly this

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-lif-feasibility
git pull --ff-only origin agent/v3-p06-lif-feasibility
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
set -o pipefail

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_a3_pilot.py \
  tests/test_p06_a3_data.py \
  tests/test_p06_a3_training.py \
  tests/test_p06_a2_train_forward.py \
  tests/test_p06_a2_train_export.py \
  2>&1 | tee /tmp/v3_p06_a3_4_native.log

PYTHONPATH="$PWD/src" python scripts/p06_a3.py \
  --pilot --data-dir data/mnist_raw \
  2>&1 | tee /tmp/v3_p06_a3_4_pilot.log
```

Expected: native pytest PASS, no Torch skips; the pilot reports
`P06_A3_PILOT=` JSON, one of two explicit `P06_A3_PILOT_STATUS=`
values, and `P06_A3_OFFICIAL_TEST_STATUS=SEALED`.

**Stop and return** the complete native pytest summary and
`P06_A3_PILOT_STATUS` plus the JSON diagnostics,
`baseline_validation`, `gradient_probe`,
`changed_integer_weight_counts`, and final validation metrics.
Do **not** run full MNIST training yet.

---

## Native verification gate — do this before a full MNIST training run

Run these commands in the user's ordinary Linux VS Code terminal:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-lif-feasibility
git pull --ff-only origin agent/v3-p06-lif-feasibility
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
set -o pipefail

python -c 'import torch; print("torch", torch.__version__)'

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_a3_data.py \
  tests/test_p06_a3_training.py \
  tests/test_p06_a2_train_forward.py \
  tests/test_p06_a2_train_export.py \
  tests/test_p06_a2_packed_replay.py \
  2>&1 | tee /tmp/v3_p06_a3_dev_native.log

PYTHONPATH="$PWD/src" python scripts/p06_a3.py --synthetic-smoke \
  2>&1 | tee /tmp/v3_p06_a3_synthetic_smoke.log
```

Expected: all selected tests pass, no Torch skips; synthetic smoke
prints `P06_A3_SYNTHETIC_SMOKE_PASS=1` and explicitly warns no MNIST
training/official-test/FPGA inference.

### Actual canonical MNIST dataset preflight (explicit download only)

If the archives are not already present in `data/mnist_raw`, use:

```bash
PYTHONPATH="$PWD/src" python scripts/p06_a3.py --download-train-only \
  --data-dir data/mnist_raw
```

This requires network access and downloads the two canonical
*training* IDX archives; it never downloads `t10k*`.
Once present, run:

```bash
PYTHONPATH="$PWD/src" python scripts/p06_a3.py --preflight \
  --data-dir data/mnist_raw \
  --manifest-file artifacts/p06_a3_data_preflight.json \
  2>&1 | tee /tmp/v3_p06_a3_data_preflight.log
```

Expected: `P06_A3_DATA_PREFLIGHT_PASS=1`, exactly 60,000 total,
50,000 train, 10,000 validation, canonical upstream MD5 matches,
persistent archive + split SHA256 and `official_test: "SEALED"`.

**STOP HERE AND RETURN** native test/smoke results and the preflight
summary including SHA256 values. This is the next meaningful independent
gate. Do not edit old P05 goldens, open official MNIST test labels,
declare MNIST accuracy or begin a full training/benchmark trial before
verifying the data and early loss/gradient behavior.

### Prepared training command for next phase (NOT requested for this gate)

After native preflight acceptance and a specific controlled trial decision:

```bash
PYTHONPATH="$PWD/src" python scripts/p06_a3.py --train \
  --data-dir data/mnist_raw \
  --output-dir artifacts/p06_a3_candidate_seed20261013 \
  --seed 20261013 --epochs 8 --batch-size 64 \
  --learning-rate 0.05 --surrogate-width 16 \
  2>&1 | tee /tmp/v3_p06_a3_training_trial.log

PYTHONPATH="$PWD/src" python scripts/p06_a3.py --validate-candidate \
  --output-dir artifacts/p06_a3_candidate_seed20261013
```

This can be CPU-intensive. A fresh output directory is required;
checkpoint metadata and validation are not claims of official-test
accuracy or FPGA performance. Run only after the native verification
gate and reviewing the synthetic-smoke trace.
