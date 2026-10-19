# P06-B2.3 — Trained signed-integer / 27-core packed / independent numerical audit

**Status:** SOURCE/TEST CANDIDATE COMMITTED — USER NATIVE VERIFICATION PENDING.

**B2.2 user-reported acceptance (2026-10-19):** Candidate at
`artifacts/p06_b22_candidate_1000` passed the read-only integrity loader.
Canonical 10,000 train-derived validation images: **97.08% accuracy**,
best epoch **6**, zero all-silent validation frames, mean readout spikes
34.1821/image. The user-reported checkpoint byte SHA256 is
`93e43915b38cf3c815a125bbab2788e45209f0ccd024d098b25b82a0a8cd0957`;
quantized effective signed-integer SHA256 is
`4a20357fc5e77465380c1600e7e82cda515bbafc233fb9e3a1205bca9d00d8b0`.
These hashes identify the **trained** candidate, distinct from B2.1
seeded **untrained** hashes. The user has not uploaded the checkpoint
bytes; source implementation and official TEST data were not accessed.

The 97.08% result is *TRAIN-derived validation* accuracy, **not official
MNIST TEST accuracy** or KV260 board inference accuracy.

## B2.3 purpose and code

`src/loihi_twin_v2/p06_b23_trained_audit.py` and
`scripts/p06_b23_trained_audit.py`:

1. Independently invoke the accepted B2.2 checkpoint load gate that hashes
   the original `weights_state_dict.pt` bytes, state_dict tensor shapes,
   original canonical TRAIN source split and dimension-bound signed integer
   quantization hash. Additionally require the exact user-reported B2.2
   checkpoint file/effective integer hash, 784→1000→10 architecture, epoch 6,
   10,000 validation population, 0.9708 held-out score, zero silent and
   `candidate_go=true`. This is source **identity**, not an assertion that
   the assistant directly verified local checkpoint bytes.
2. Export all **794,000** trained integer connections (including zero-weight
   edges) from actual trained tensors as a `NetworkSpec`. The original
   Track A weights/compiler are read-only. Compile with the real B1.2
   synapse-aware mapper and original P03/P02 initial-core backing writer.
   Enforce 27 logical cores / 14,155,776 initial DDR backing bytes, max
   131,072 logical synapse bytes per core and <=4,096 events/core.
   Report source, compiled and packed-audit SHA256s for new trained weights.
3. Optionally load ONLY canonical TRAIN IDX via the frozen strict downloader-
   independent loader. Select user-chosen distinct sorted ordinals in the
   **canonical 10,000 train-derived validation** index ordering; log both the
   validation ordinal and original TRAIN IDX ID. Every requested frame
   independently runs the original B1.4 monolithic flat signed24 source-graph
   oracle and actual B1.2 `LogicalChip` partitioned execution for **all 26
   ticks** with complete neuron state/current/refractory/packet verification.
   Independently compare the resulting readout counts to the B2.1
   PyTorch signed-integer forward. Fail closed on first mismatch. Record each
   raw validation image SHA256, readout counts/class, and both separately
   normalized trace SHA256s. No official TEST archives are loaded.
4. Do not overwrite checkpoint or claim B2.4 freeze/real scaled KV260
   execution. Optional JSON output path must not already exist.

**Important scale distinction:** Default run does full **trained dense
structural packing only**, no 26-tick neural inference. A command with
`--validation-ordinals` performs real dense trained numeric execution for
exactly the listed validation images; this may be computationally expensive.
A PASS for one or more selected validation images is not a claim of
re-evaluating 10,000 images numerically or physical inference.

## Native workstation verification, no FPGA/JTAG

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-b2-training-foundation
git pull --ff-only origin agent/v3-p06-b2-training-foundation
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# Host-only B2.3 rejection/integrity-contract tests. Does not read checkpoint:
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b23_trained_audit.py

# Previous B2.1/2.2 and B1 numerical/packed regression suites:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b22_training.py tests/test_p06_b21_training_foundation.py \
  tests/test_p06_b15_paging.py tests/test_p06_b14_differential.py \
  tests/test_p06_b13_streaming.py tests/test_p06_b12_partition.py \
  tests/test_p06_b1_contract.py

# Syntax:
PYTHONPATH="$PWD/src" python -m compileall -q \
  src/loihi_twin_v2/p06_b23_trained_audit.py \
  scripts/p06_b23_trained_audit.py tests/test_p06_b23_trained_audit.py

# Trained 1000-neuron 27-core structure: no numerical inference
PYTHONPATH="$PWD/src" python scripts/p06_b23_trained_audit.py \
  --candidate-dir "$PWD/artifacts/p06_b22_candidate_1000"

# Trained 27-core full-numerical independent parity for 1 validation image.
# Costly: execute after structural test, do not claim TEST inference.
PYTHONPATH="$PWD/src" python scripts/p06_b23_trained_audit.py \
  --candidate-dir "$PWD/artifacts/p06_b22_candidate_1000" \
  --data-dir "$PWD/data/mnist_raw" --validation-ordinals 0

# Optional more source-predeclared validation ordinals:
PYTHONPATH="$PWD/src" python scripts/p06_b23_trained_audit.py \
  --candidate-dir "$PWD/artifacts/p06_b22_candidate_1000" \
  --data-dir "$PWD/data/mnist_raw" --validation-ordinals 0 1 2
```

Expected *after user runs*:
`P06_B23_TRAINED_PACKED_AUDIT_PASS=1`,
`P06_B23_VALIDATION_NUMERICAL_PARITY=NOT_RUN` for structural-only,
`P06_B23_VALIDATION_NUMERICAL_PARITY=PASS` for selected frames,
`P06_B23_OFFICIAL_TEST_STATUS=SEALED`, and
`P06_B23_FREEZE_STATUS=NOT_FROZEN`.

**No assistant-run native pytest result, user-local checkpoint run, new
board result or official TEST accuracy claimed.** B2.4 immutable freeze is
not yet started, and B1/B2 stacked PRs remain unmerged.

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
