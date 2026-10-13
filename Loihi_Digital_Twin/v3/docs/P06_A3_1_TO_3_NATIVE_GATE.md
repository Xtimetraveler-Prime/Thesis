# P06-A3.1–A3.3 — Train-only MNIST reproducibility + learning candidate

**Date:** 2026-10-13
**Branch:** `agent/v3-p06-lif-feasibility`
**Status:** IMPLEMENTED / COMMITTED — native dataset preflight and training
smoke **AWAIT USER VERIFICATION**. Do NOT mark P06-A3 accepted or start
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
