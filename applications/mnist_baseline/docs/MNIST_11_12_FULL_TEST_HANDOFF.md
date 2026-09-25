# MNIST-11/12 — Full 10,000-Image Matched Software Handoff

This is the final large software/reference gate after acceptance of the exact 30-image matched corpus.

## Accepted starting point

The frozen 30-image corpus established:

```text
Brian2Loihi exact traces:                 30 / 30
Brian2Loihi prediction agreement:        30 / 30
Catalyst internal trace consistency:     30 / 30
Catalyst prediction agreement:           30 / 30
Catalyst final spike-vector agreement:   26 / 30
Catalyst first divergence = rest clamp:  30 / 30
```

See `MNIST_11_12_CORPUS_RESULTS.md`.

The full official MNIST test split is now useful because the adapter behavior is understood. Its purpose is to determine whether Brian exactness extends to all 10,000 images and quantify the application-level sensitivity to Catalyst's known sub-rest membrane clamp.

## 1. Pull and run the normal regression

```bash
cd ~/Git/Thesis

git fetch origin
git switch agent/mnist-11-12-matched-comparison-dev
git pull --ff-only origin agent/mnist-11-12-matched-comparison-dev

source .venv-mnist/bin/activate
pytest applications/mnist_baseline/tests -q
```

## 2. Generate deterministic full-test request shards

Do this in the normal MNIST environment so TensorFlow/MNIST loading stays outside the external reference environments:

```bash
python applications/mnist_baseline/scripts/prepare_matched_reference_shards.py \
  --scope full \
  --shard-size 100 \
  --output-dir applications/mnist_baseline/build/matched-reference/full-shards
```

Expected manifest scope:

```text
cases=10000
shards=100
shard_size=100
```

Generation loads MNIST and the frozen native-sparse deployment once. Every shard contains exact 16-tick schedules plus independent project golden spike-count/prediction metadata. The manifest SHA-256-verifies every shard and freezes the ordered `0..9999` test-index scope.

## 3. Run Brian2Loihi full test

```bash
deactivate 2>/dev/null || true
source .venv-mnist-brian2loihi/bin/activate

python applications/mnist_baseline/scripts/run_mnist_11_brian2loihi.py \
  --shard-manifest applications/mnist_baseline/build/matched-reference/full-shards/manifest.json \
  --output-dir applications/mnist_baseline/build/mnist-11/full \
  --resume \
  --progress-every 100
```

`--resume` verifies any existing result schema/index/profile before reusing it. Therefore the same command is safe to rerun after interruption.

The strongest possible result is:

```text
cases=10000
passed=10000
prediction_agreement=10000
spike_vector_agreement=10000
exact_trace=10000
all_passed=True
```

A mismatch is still scientifically usable; the runner preserves the exact first state divergence and exits nonzero only after writing the complete suite summary.

Brian CPU wall time is not a hardware-performance metric.

## 4. Run Catalyst N1 full test

```bash
deactivate 2>/dev/null || true
source .venv-mnist-catalyst/bin/activate

export PYTHONPATH="$PWD/Neuromorphic Digital Twin/build/m13_1/catalyst-n1/sdk:$PWD/Neuromorphic Digital Twin/src:$PWD/applications/mnist_baseline"

python applications/mnist_baseline/scripts/run_mnist_12_catalyst.py \
  --shard-manifest applications/mnist_baseline/build/matched-reference/full-shards/manifest.json \
  --output-dir applications/mnist_baseline/build/mnist-12/full \
  --resume \
  --progress-every 100
```

The critical harness requirement is:

```text
transport_consistent=10000
```

Prediction or spike-vector disagreement with FPGA-v1 is an experiment result, not an adapter failure. Prediction disagreement and transport failures print immediately. Spike-vector-only differences are counted in the final suite without flooding the terminal; add `--print-spike-disagreements` only when intentionally debugging those cases.

## 5. Classify Catalyst divergence compactly

```bash
python applications/mnist_baseline/scripts/analyze_mnist_12_divergence.py \
  --result-dir applications/mnist_baseline/build/mnist-12/full \
  --output applications/mnist_baseline/build/mnist-12/full/divergence_compact.json \
  --compact
```

The compact result records:

- classification counts;
- indices by first-divergence class;
- prediction-disagreement indices;
- final spike-vector-disagreement indices; and
- transport-inconsistent indices.

It deliberately does not duplicate the ten-neuron first-mismatch vectors for all 10,000 images.

## 6. Build the matched full-test comparison

Return to the normal application environment:

```bash
deactivate 2>/dev/null || true
source .venv-mnist/bin/activate

python applications/mnist_baseline/scripts/build_matched_comparison_summary.py \
  --brian-suite applications/mnist_baseline/build/mnist-11/full/suite.json \
  --catalyst-suite applications/mnist_baseline/build/mnist-12/full/suite.json \
  --output applications/mnist_baseline/build/matched-reference/full.comparison_summary.json
```

For the full 10,000-image scope the summary reports comparable software/reference accuracies alongside prediction/spike agreement. This is the first matched external-reference scope where accuracy is an unbiased official-test metric.

## 7. Archive compact full-test evidence

```bash
python applications/mnist_baseline/scripts/archive_mnist_11_12_full_evidence.py \
  --request-manifest applications/mnist_baseline/build/matched-reference/full-shards/manifest.json \
  --brian-dir applications/mnist_baseline/build/mnist-11/full \
  --catalyst-dir applications/mnist_baseline/build/mnist-12/full \
  --catalyst-divergence applications/mnist_baseline/build/mnist-12/full/divergence_compact.json
```

The source-controlled archive is created at:

```text
applications/mnist_baseline/evidence/mnist-11-12/matched-full-v1/
```

The archive contains the request manifest/provenance, complete Brian/Catalyst suite tables, compact Catalyst divergence indices, semantic/feasibility audits, a scope-checked comparison summary, and SHA-256 artifact manifest. It does **not** commit the large request shards or all per-image detailed result JSON files.

## 8. Commit the accepted archive

Only after the archive command succeeds:

```bash
git status

git add applications/mnist_baseline/evidence/mnist-11-12/matched-full-v1

git commit -m "Archive MNIST-11/12 matched full-test evidence"
git push origin agent/mnist-11-12-matched-comparison-dev
```

## Expected milestone effect

A reproducible full-test result is sufficient to close MNIST-11.5 and finalize the software side of MNIST-12.6. The pinned Catalyst physical path remains a separately documented capacity/platform blocker and is not manufactured into a matched hardware claim.
