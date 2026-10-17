# P06-A3 validated candidate / P06-A4.1 native software snapshot gate

**Date:** 2026-10-15
**Branch:** `agent/v3-p06-lif-feasibility`
**Status update (2026-10-17): A4.1 USER-ACCEPTED.** The user's
actual trained A4.1 run reports PASS and all five 26-tick frames
exactly equal. That command necessarily executed load_candidate()'s
checkpoint byte SHA256 and signed-integer tensor digest validation.
The separate --validate-candidate stdout was not pasted. A4.2's
static P02 DDR freeze native audit remains pending; see
`P06_A4_FINAL_CLOSEOUT.md`.
This is not official MNIST test accuracy and not KV260 inference.

## Final A4.1 user log after instructions were issued

`P06_A4_SOFTWARE_SNAPSHOT_PASS=1`
`P06_A4_PARITY.status=ALL_TRACES_EXACTLY_EQUAL`,
`frames=5`, `timesteps_per_frame=26`,
`P06_A4_OFFICIAL_TEST_STATUS=SEALED`,
`P06_A4_FPGA_STATUS=NO_PHYSICAL_RUN_NO_DDR_PAGE_IMAGE`.

Native P03: core 0, 42 compartments, 816 axons, 25,408 synapses,
32 route descriptors and 32 routes. Six stream hashes are recorded
in `P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`.

The acceptance below originally requested further verification; it
remains as an archival reproduction recipe, not an open A4.1 blocker.

## First completed project-trained candidate (user-reported manifest)

| Frozen item | Value |
|---|---|
| Architecture | 784→32→10 one logical core |
| Source | canonical 60k TRAIN-only MNIST: fixed 50k/10k split |
| Trial | seed 20261013, 8 epochs, batch64, Adam LR0.05, surrogate width16 |
| Best epoch | 8 of 8 |
| Best training accuracy | 0.9534 |
| Best validation accuracy | **0.9439** (9,439/10,000) |
| Predeclared validation GO floor | 0.60: **GO** |
| Output silence | **2/10,000** validation images (0.0002) |
| Mean output spikes | 33.9087 per validation image |
| Original test set | `SEALED / NOT READ` |
| Hardware board | `NOT TESTED` |

Saved `weights_state_dict.pt` SHA256 from the provided manifest:
`0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88`.

Effective signed integer weights SHA256:
`1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`.

Train index SHA256:
`1cbcb0b2bf481958d6c917ea6d70fa44a20839406f0c824540f8e691edfdd851`.
Validation index SHA256:
`3b9520013f30742c3818f55024ea39e3e0632113c487c589fdfbb73c7d274831`.

**Evidence limitation:** This is an inspection of the user's pasted
`candidate_manifest.json`, not a downloaded `.pt` checkpoint verified
by the assistant. The real `--validate-candidate` native invocation
must confirm the bytes and quantized weight digest before accepting
A3 closeout or A4 freezes.

## A4.1 implemented

`src/loihi_twin_v2/p06_a4_snapshot.py`:

1. Calls `load_candidate` (which verifies checkpoint SHA256, expected
   fixed neuron parameters, readout/encoder version and exact exported
   signed integer weights digest). Then independently requires the
   **specific first trial's pinned** two hashes, accepted 0.9439
   validation score, epoch 8 and frozen split fingerprints. A new
   checkpoint must not be silently substituted.
2. Reopens **only** the canonical TRAIN archives, verifies their identity
   and full manifest equality to the saved training provenance.
   Does not read/download `t10k*` official test bytes or labels.
3. Converts trained signed24 weights into unchanged `NetworkSpec`,
   deterministic one-core `compile_network`, and
   `export_one_core_image`; checks compartments, axons,
   synapses/routes and core/ingress limits using actual learned weights.
4. For all-zero, all-255 and **first three frozen validation images**,
   compares 26 timesteps across the accepted PyTorch integer forward,
   separately implemented dense integer oracle, independent P03
   hardware-word decoder/replayer, and existing `LogicalChip`.
   First mismatch fails with component/timestep context. Each frame
   starts fresh; pending hidden packets at t=25 are excluded from
   the next image. No official test or board sample.
5. **Only after all gate checks pass** creates a new output directory
   containing six deterministic P03 logical-word streams with explicit
   little-endian record widths, SHA256 per stream,
   `diagnostic_traces.json` + SHA256, and
   `a4_software_snapshot_manifest.json` with all source/compiler/
   dataset/encoder/model fingerprints.

These word streams are *NOT* the physical 512KiB DDR context record
or the A53/KV260 application loader layout. A full PS/PL ABI, autonomous
input events, board state reset, and physical power/latency remain P07/P08.
P06-A4.1 is a software reproducibility and packed word gate only; do
not label it a physical FPGA run.

### Native commands

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-lif-feasibility
git pull --ff-only origin agent/v3-p06-lif-feasibility
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
set -o pipefail

# Mandatory independent checkpoint+manifest verification.
PYTHONPATH="$PWD/src" python scripts/p06_a3.py --validate-candidate \
  --output-dir artifacts/p06_a3_candidate_seed20261013

# A4 synthetic/compiler tests: must PASS, with PyTorch available and no skips.
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_a4_snapshot.py \
  tests/test_p06_a2_train_export.py \
  tests/test_p06_a3_training.py \
  2>&1 | tee /tmp/v3_p06_a4_1_native.log

# ACTUAL trained-weights software packed-image and four-way trace gate.
PYTHONPATH="$PWD/src" python scripts/p06_a4_snapshot.py \
  --candidate-dir artifacts/p06_a3_candidate_seed20261013 \
  --data-dir data/mnist_raw \
  --output-dir artifacts/p06_a4_trained_word_snapshot_seed20261013 \
  --validation-traces 3 \
  2>&1 | tee /tmp/v3_p06_a4_1_trained_snapshot.log
```

Expected checkpoint status:
`P06_A3_CANDIDATE_INTEGRITY_PASS=1`.

Expected snapshot result only on full four-way agreement:
`P06_A4_SOFTWARE_SNAPSHOT_PASS=1`,
`P06_A4_PARITY` with status `ALL_TRACES_EXACTLY_EQUAL`,
`P06_A4_OFFICIAL_TEST_STATUS=SEALED`, and
`P06_A4_FPGA_STATUS=NO_PHYSICAL_RUN_NO_DDR_PAGE_IMAGE`.

All outputs are under already gitignored `v3/artifacts/`. Refuse
to overwrite an existing snapshot directory; if a first attempt
fails after creating a partial output, **preserve its failure evidence**
before choosing a separate new output path.

## Native acceptance and follow-on boundary

Send the `--validate-candidate` pass marker, pytest summary and
`P06_A4_IMAGE`, `P06_A4_PARITY`, plus any first failing assertion.
Do not paste/upload the full binary checkpoint unless intentionally
making it a project artifact.

Only after native A4.1 acceptance may we complete A4's independent
reproducibility/manifest freeze and decide a sealed official evaluation
protocol. The official test set is not part of training or validation
and must remain unopened until that protocol is frozen. A4 software
acceptance does not mean A53 FPGA inference is working.
