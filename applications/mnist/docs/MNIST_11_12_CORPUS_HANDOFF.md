# MNIST-11/12 — 30-Image Matched Corpus Handoff

The two-image anchor gate is accepted. This document defines the next execution gate using the existing frozen 30-image conformance corpus. No network retraining, parameter retuning, re-encoding, or backend-specific image selection is allowed.

## 1. Pull and run the normal regression

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/mnist-11-12-matched-comparison-dev
git pull --ff-only origin agent/mnist-11-12-matched-comparison-dev

source .venv-mnist/bin/activate
pytest applications/mnist/tests -q
```

## 2. Generate one immutable 30-image bundle

Still in `.venv-mnist`:

```bash
python applications/mnist/scripts/prepare_matched_reference_bundle.py \
  --scope corpus \
  --output applications/mnist/build/matched-reference/corpus.bundle.json
```

This reuses exactly the 30 official test indices frozen in `mnist-v1/fpga_validation_corpus.json`.

## 3. Run Brian2Loihi on the corpus

```bash
deactivate 2>/dev/null || true
source .venv-mnist-brian2loihi/bin/activate

python applications/mnist/scripts/run_mnist_11_brian2loihi.py \
  --bundle applications/mnist/build/matched-reference/corpus.bundle.json \
  --output-dir applications/mnist/build/mnist-11/corpus
```

The desired suite boundary is exact matched behavior. Any nonzero mismatch is preserved for investigation rather than retuned away.

## 4. Run Catalyst N1 CPU on the same corpus

```bash
deactivate 2>/dev/null || true
source .venv-mnist-catalyst/bin/activate

export PYTHONPATH="$PWD/Neuromorphic Digital Twin/build/m13_1/catalyst-n1/sdk:$PWD/Neuromorphic Digital Twin/src:$PWD/applications/mnist"

python applications/mnist/scripts/run_mnist_12_catalyst.py \
  --bundle applications/mnist/build/matched-reference/corpus.bundle.json \
  --output-dir applications/mnist/build/mnist-12/corpus
```

The primary harness gate is:

```text
transport_consistent=30
```

FPGA-v1/Catalyst state or prediction disagreement is experimental evidence and does not itself make the command invalid.

## 5. Classify Catalyst's first divergence per image

```bash
python applications/mnist/scripts/analyze_mnist_12_divergence.py \
  --result-dir applications/mnist/build/mnist-12/corpus \
  --output applications/mnist/build/mnist-12/corpus/divergence_summary.json
```

The classifier labels a case `CATALYST_SUB_REST_CLAMP` only when both independent Catalyst views are trace-identical and their first FPGA-v1 mismatch is exactly the component-wise transformation `candidate=max(reference, 0)` with at least one negative project voltage. Other first divergences remain separately labeled.

## 6. Assemble a scope-checked matched summary

```bash
source .venv-mnist/bin/activate

python applications/mnist/scripts/build_matched_comparison_summary.py \
  --brian-suite applications/mnist/build/mnist-11/corpus/suite.json \
  --catalyst-suite applications/mnist/build/mnist-12/corpus/suite.json \
  --output applications/mnist/build/matched-reference/corpus.comparison_summary.json
```

This command refuses to combine the suites unless Brian2Loihi and Catalyst contain the exact same MNIST indices in the same order.

## 7. Archive compact source-controlled evidence

```bash
python applications/mnist/scripts/archive_mnist_11_12_evidence.py \
  --scope corpus \
  --bundle applications/mnist/build/matched-reference/corpus.bundle.json \
  --brian-dir applications/mnist/build/mnist-11/corpus \
  --catalyst-dir applications/mnist/build/mnist-12/corpus
```

Expected output directory:

```text
applications/mnist/evidence/mnist-11-12/matched-corpus-v1/
```

It contains the immutable request bundle, both suite summaries, all 30 compact per-case results for each backend, Catalyst semantic/feasibility/divergence summaries when present, the cross-backend comparison summary, SHA-256 hashes, and a manifest. It does not copy virtual environments or Catalyst source/build trees.

Then commit only that compact evidence package:

```bash
git status
git add applications/mnist/evidence/mnist-11-12/matched-corpus-v1
git commit -m "Archive MNIST-11/12 matched corpus evidence"
git push origin agent/mnist-11-12-matched-comparison-dev
```

## Acceptance interpretation

After the 30-image corpus:

- Brian2Loihi exact trace/spike/prediction agreement across all 30 cases is sufficient to close MNIST-11.4 and strongly motivates a full-test run for MNIST-11.5.
- Catalyst `transport_consistent=30` validates the application adapter independently of whether Catalyst matches FPGA-v1.
- Catalyst prediction agreement and first-divergence classifications quantify the application-level consequence of the known translated dynamics.
- The pinned physical Catalyst K26 blocker remains unchanged; the CPU corpus does not silently convert that blocked hardware path into a physical result.

Do not start the full 10,000-image external runs until this corpus is reviewed. The corpus is selected for conformance coverage rather than unbiased accuracy, but it is large enough to determine whether the anchor behavior generalizes and whether the semantic divergence affects output spikes or classifications.
