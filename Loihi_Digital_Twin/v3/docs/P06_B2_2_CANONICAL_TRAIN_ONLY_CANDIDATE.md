# P06-B2.2 — Canonical TRAIN-only optimization and candidate checkpoint

**Development status:** B2.1 foundation **USER-ATTESTED NATIVE PASS**, including full **UNTRAINED** 784→1000→10 / 794,000-connection 27-core B1.2 packed structural test. B2.2 deterministic fitting, validation, checkpoint integrity and native synthetic tests **IMPLEMENTED AS NEW B2 SOURCE; USER B2.2 VERIFICATION PENDING**. **No actual TRAIN run, validation accuracy, B2.3 quantization/parity, B2.4 freeze, official TEST unseal or FPGA scaled experiment has occurred.**

Branch: `agent/v3-p06-b2-training-foundation`; stacked draft PR #47 targets unmerged B1 PR #46 branch. Neither PR is authorized for merge.

## Source audit and reuse

`src/loihi_twin_v2/p06_b22_training.py` extends isolated B2.1 `B21IntegerSNN` rather than changing frozen Track A `IntegerForwardSNN` or `p06_a3_training`. It uses Track A's verified **TRAIN-ONLY** gzip MNIST IDX reader `p06_a3_data.load_train_validation(strict=True)`. That reader opens/checks **only** `train-images-idx3-ubyte.gz` and `train-labels-idx1-ubyte.gz`; the official `t10k` TEST archives are never named/read/downloaded by B2.2. Train indices and validation indices are exactly Track A's original 50,000/10,000 disjoint train-derived seed-20261013 split, and B2.2 independently recomputes and requires the previously frozen TRAIN and validation index SHA256s `1cbcb0b2bf481958d6c917ea6d70fa44a20839406f0c824540f8e691edfdd851` and `3b9520013f30742c3818f55024e7a3b4ed53e3e0632113c487c589fdfbb73c7d274831` respectively.

**The paper/scientific experiment identity:** independent newly trained **project** 784→1000→10 fully connected Loihi-inspired discrete-timestep integer LIF SNN, not a pretrained original Intel Loihi model. Preserve `p06-uint8-quota-phase17-v1` 25 raw-image input epochs plus one drain, NEXT hidden→readout packets, signed24 saturating strict-spike integer forward, 10 count-based outputs and lowest-index tie.

### Frozen-before-real-run development defaults

| Experiment field | Declared B2.2 default (not an outcome) |
|---|---|
| Shape | **784→1000→10** dense, 794,000 connections |
| New trial/weight initialization seed | 20261019, local CPU `torch.Generator` |
| Split source/seed | Original canonical **60,000 TRAIN** images, 50,000/10,000 train-derived split; split seed 20261013 |
| Epoch count | **8** complete TRAIN/validation epochs |
| Batch size | **64** |
| Optimizer | Adam |
| Learning rate | 0.05 |
| Objective | `cross_entropy(2.0 * exact_integer_output_spike_counts)` |
| Surrogate gradient | Track A's accepted fast-sigmoid backward, width=16 |
| Per-step forward | Track A exact signed24 / float64 25+1-tick STE kernel |
| Gradient bound | Global norm <=5 |
| Trainable weight clamp | ±512.0 (well inside signed24 P03 bounds) |
| Selection | Highest 10k TRAIN-derived validation accuracy; **earliest epoch** on exact tie |
| Validation-go engineering floor | **0.60**, predeclared; NOT a predicted performance result |
| Dataset augmentation/normalization | None; raw 784 uint8 pixel bytes |
| Device | CPU by default; optional explicit deterministic CUDA |
| Candidate output | **NEW directory only**, complete epoch history, best-epoch `weights_state_dict.pt`, byte SHA256 and dimensional effective signed24 integer-weight SHA256 |
| Official MNIST TEST | SEALED / NOT ACCESSED |
| Checkpoint frozen / B2.3 parity / board | **NO / NOT YET / NOT TESTED** |

The B2.1 settings object validates numeric bounds. A canonical real run must process exactly 50,000 train and 10,000 validation samples on **every epoch**. There is no `--subset`, `--skip-validation`, `--epochs-fast` or `--ignore-checksum` switch in the real training entry point. Configuration overrides are allowed only as recorded, separate declared trials; do not choose a preferred result by inspecting the official TEST set.

`fit_canonical_mnist` uses epoch-seeded training shuffles `torch.Generator().manual_seed(B2_seed+epoch)`, full validation in unshuffled held-out index order, aborts on nonfinite loss/gradients/parameters, clips gradients and trainable weights, compares validation metrics using `>` (earliest exact tie wins), retains the best epoch's **CPU state_dict clone**, and saves only a separate B2.2 **trained candidate**. If validation score is below 0.60, it reports `candidate_go=false` rather than inventing acceptance. It never overwrites an existing candidate directory.

`load_candidate` enforces original canonical TRAIN-only provenance fingerprints, dataset metadata, source/index SHA256s, unmodified TRAIN+validation population counts, complete declared epoch history, best-epoch selection, GO-floor logic, checkpoint filename+byte SHA256, strict state-dict keys and dimension-bound signed integer-weight SHA256. It refuses to treat B2.2 as a B2.4 frozen checkpoint. A missing/wrong-sha weight file, renamed architecture, corrupted source manifest, or an official TEST unseal field must fail closed.

## Memory/performance/physical boundary

The full H=1000 surrogate-gradient fit unrolls 26 timesteps. `scripts/p06_b22_train.py` defaults to **preflight only**, reporting mathematical tensor sizes, batch width, PyTorch device and **unknown actual peak autograd RAM/time**. The raw compressed TRAIN-only archives must already be present and verified. A normal invocation of the script, or its `--verify-training-data` mode, **cannot start training**. A complete fit requires explicit `--train` plus `--data-dir` and **previously nonexistent** `--output-dir`.

CUDA is optional and must be explicitly selected with `--device cuda`. For determinism, export `CUBLAS_WORKSPACE_CONFIG=:4096:8` **before** launching Python, and ensure your CUDA/PyTorch installation supports deterministic kernels. Validation/device-independent byte-identical checkpoint files are **not** guaranteed across Python/PyTorch/hardware versions; B2.2 records those versions and hashes each observed candidate.

Training runs may consume substantial CPU/GPU memory and processing time: `peak_autograd_RAM=UNKNOWN_MUST_MEASURE`. No measured training time, achieved validation score, trained weight file, full-dense 26-tick host numerical parity, KV260 inference, energy or FPGA latency has been claimed.

A successfully fitted B2.2 candidate still needs **B2.3 independent quantized/P03/P02 packed/26-tick oracle tests** and **B2.4 separate immutable freeze**, both before considering P07-B physical execution or any separately authorized official TEST protocol.

## Native PC/VS Code acceptance (safe, host-only; no real training yet)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-b2-training-foundation
git pull --ff-only origin agent/v3-p06-b2-training-foundation
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# New B2.2 deterministic tiny synthetic train/validation + integrity tests
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b22_training.py

# B2.1 and accepted B1.1–B1.5/Track A oracle regressions
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b21_training_foundation.py tests/test_p06_b15_paging.py \
  tests/test_p06_b14_differential.py tests/test_p06_b13_streaming.py \
  tests/test_p06_b12_partition.py tests/test_p06_b1_contract.py \
  tests/test_p06_lif_compiler_probe.py tests/test_p06_lif_input_probe.py

PYTHONPATH="$PWD/src" python -m compileall -q \
  src/loihi_twin_v2/p06_b22_training.py \
  tests/test_p06_b22_training.py \
  scripts/p06_b22_train.py

# SAFE default — NO TRAIN archive I/O or training
PYTHONPATH="$PWD/src" python scripts/p06_b22_train.py
```

Expected preflight `P06_B22_PREFLIGHT_PASS=1`, `P06_B22_TRAINING_STATUS=NOT_STARTED`, `official_mnist_test_status=SEALED_NOT_ACCESSED`. Native B2.2 acceptance is **PENDING user verification**.

## Next: optional canonical TRAIN-only source preflight (NO optimizer)

Substitute **the directory on your PC that already contains only the original two canonical MNIST TRAIN .gz IDX archives**; do not put the official `t10k` archives into the CLI arguments. The script opens only the two known TRAIN filenames.

```bash
PYTHONPATH="$PWD/src" python scripts/p06_b22_train.py \
  --verify-training-data \
  --data-dir /PATH/TO/YOUR/EXISTING/CANONICAL/MNIST-TRAIN-IDX-FILES
```

Expected: `P06_B22_TRAIN_DATA_SEAL_PASS=1`, both pinned train-derived split hashes, 50k/10k. This is not official TEST unsealing.

## Separate real training invocation (only after synthetic tests and memory/device preflight)

**This command DOES start a complete training run; do not accidentally mix it into the test script block above.** The output folder must not exist, and its parent must already exist.

```bash
# Default CPU; omit --device to keep CPU. If choosing NVIDIA CUDA:
# export CUBLAS_WORKSPACE_CONFIG=:4096:8
PYTHONPATH="$PWD/src" python scripts/p06_b22_train.py \
  --train --hidden 1000 --epochs 8 --batch-size 64 \
  --seed 20261019 --learning-rate 0.05 \
  --surrogate-width 16 --validation-go-floor 0.60 \
  --device cpu \
  --data-dir /PATH/TO/YOUR/EXISTING/CANONICAL/MNIST-TRAIN-IDX-FILES \
  --output-dir /PATH/TO/A/NEW/B2-CANDIDATE-DIRECTORY

# After a complete fit, recompute file + effective signed integer digests
PYTHONPATH="$PWD/src" python scripts/p06_b22_train.py \
  --verify-candidate --candidate-dir /PATH/TO/A/NEW/B2-CANDIDATE-DIRECTORY
```

Expected *after actual successful fitting*: `P06_B22_TRAIN_ONLY_CANDIDATE_PASS=1` / `P06_B22_CANDIDATE_INTEGRITY_PASS=1`. Capture the emitted best-epoch full-population train/validation metrics, silent fraction, candidate GO, file SHA256 and integer-weight SHA256. **These markers are NOT yet observed.** B2.3/B2.4 will perform additional acceptance/freeze.

## Future B2 acceptance

B2.3: signed-integer dense state/source oracle, B1.2 exact full 27-core P02 images and per-core occupancy on **actual trained** weights, P06-B1.4 independent 26-tick validation-image trace identity, fail-closed malformed checkpoint/source/packet. B2.4: versioned immutable new model and per-core DDR SHA freeze + official TEST protocol declared before P07-B. Do not merge PR #46 or #47 without separate explicit approval.

## Post-merge integration addendum (2026-10-19)

The branch/PR status in earlier sections of this phase document is
**historical provenance from when this submilestone was under review**,
not the current integration status. After the user accepted B2.5 and
explicitly authorized sequential integration, GitHub confirmed:
**P06-B1 PR #46 merged to `main`** as
`35ea181360ebf15627c2943090fbdc3c6bf3949e`;
**P06-B2 PR #47 retargeted and merged to `main`** as
`42f84de3bbbe62302599818c39e7e54747ce8aa2`.
The B2.1–B2.5 host gates are user-accepted, and B2.4's original
33-asset/27-P02-context freeze is locally SHA-verifiable. Next work
starts from merged `main` at **P07-B**; see
`docs/P07_B_NEXT_CHAT_HANDOFF_SEED.md`.

All original experimental distinctions persist: B2's **97.08%**
comes from canonical **TRAIN-derived validation**, not the sealed
official B2 MNIST TEST; three complete B2.3 dense trained
26-tick validation frames do NOT imply a physical 27-core run.
P07-B KV260 multi-core hardware integration, physical paging/
latency/energy and B2 official TEST are **NOT YET ACCEPTED**.
