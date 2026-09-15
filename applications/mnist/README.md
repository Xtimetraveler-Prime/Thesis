# MNIST Application

This directory tracks an MNIST workload built on top of the validated neuromorphic digital-twin platform. Application work is separate from baseline platform milestones and must not silently change the frozen core behavior.

See [`MILESTONES.md`](MILESTONES.md) for the rollout plan, [`docs/MNIST_01_CAPACITY_AUDIT.md`](docs/MNIST_01_CAPACITY_AUDIT.md) for the hardware-capacity decision, [`docs/MNIST_03_TRAINING_BASELINES.md`](docs/MNIST_03_TRAINING_BASELINES.md) for the accepted floating-point SNN baselines, [`docs/MNIST_04_05_ACCEPTED_VALIDATION.md`](docs/MNIST_04_05_ACCEPTED_VALIDATION.md) for the accepted quantized/golden results, and [`docs/NOTEBOOK_REUSE.md`](docs/NOTEBOOK_REUSE.md) for how the user-authored class notebooks are being repurposed.

## Dual FPGA-v1 profiles

The current core supports 1,024 axons but only 4,096 stored synapses, so a fully dense `784 -> 10` native-MNIST classifier does not fit. The application therefore develops two profiles in parallel:

```text
native-sparse
28x28 MNIST
 -> 784 deterministic spike-encoded axons
 -> <=4096 sparse/pruned synapses
 -> 10 LIF output neurons

cropped-dense
28x28 MNIST
 -> exact 20x20 center crop
 -> 400 deterministic spike-encoded axons
 -> <=4000 dense synapses
 -> 10 LIF output neurons
```

Both profiles use 16 algorithmic presentation ticks, the same deterministic rate encoding, the same output-neuron dynamics, and `argmax(output spike counts)` with lowest-ID tie breaking.

The native-sparse profile preserves the original MNIST representation and is the stronger Loihi-facing comparison. The cropped-dense profile is a controlled dense baseline that nearly fills the FPGA-v1 synapse table.

## Layout

```text
applications/mnist/
├── docs/           audit, accepted-result, and application notes
├── mnist_app/      reusable dataset, encoding, training, export, inference code
├── scripts/        command-line entry points
├── tests/          application-level regression tests
├── MILESTONES.md
└── pyproject.toml
```

Generated training/deployment artifacts belong under `applications/mnist/build/`, which is excluded by the repository-wide `build/` ignore rule.

## Notebook reuse

The software path intentionally reuses the user's own TensorFlow/Keras MNIST lab structure where it remains valid:

- `tf.keras.datasets.mnist.load_data()` and the standard train/test split;
- raw pixel handling and the `pixel / 255.0` normalization convention;
- Adam optimization and sparse categorical cross-entropy;
- training-time measurement with `time.perf_counter()`;
- final test accuracy evaluation;
- `argmax` predictions;
- incorrect-prediction indexing and later visualization/analysis.

The dense ReLU ANN itself is not copied as the deployable model because the target platform requires explicit spike input and LIF dynamics.

## Setup

A separate application environment is recommended so the TensorFlow dependency does not disturb the Brian2Loihi/reference environment:

```bash
python3.12 -m venv .venv-mnist
source .venv-mnist/bin/activate
python -m pip install --upgrade pip
python -m pip install -e "Neuromorphic Digital Twin"
python -m pip install -e "applications/mnist[train,test]"
pytest applications/mnist/tests -q
```

## Accepted training methodology

Training uses a deterministic stratified 5,000-image validation split drawn only from the official MNIST training set. Checkpoint selection uses validation accuracy; the official 10,000-image test split is evaluated only after model selection is frozen.

Accepted floating-point test accuracies are:

```text
cropped-dense: 90.29%
native-sparse: 91.62%
```

See `docs/MNIST_03_TRAINING_BASELINES.md` for training/selection details.

## Accepted MNIST-04/05 validation

The accepted checkpoints are exported into the project's existing encoded-weight and M08 CSR storage representation, then executed through the actual validated `NeuromorphicCore` on the same official 10,000-image MNIST test corpus.

```text
cropped-dense: float 90.29% -> golden 90.24%, 99.25% prediction agreement, 3893 stored synapses
native-sparse: float 91.62% -> golden 91.71%, 99.30% prediction agreement, 4086 stored synapses
```

Run the complete accepted export/comparison flow with:

```bash
python applications/mnist/scripts/run_accepted_validation.py
```

The generated validation directory contains:

```text
applications/mnist/build/accepted-validation/
├── accepted_software_validation.json
├── cropped-dense_matched_comparison.json
└── native-sparse_matched_comparison.json
```

The deployment images are written under `applications/mnist/build/accepted-deployment/`. The validation manifest records checkpoint/deployment SHA-256 hashes, quantization details, matched predictions, golden activity metrics, and exact stored synapse counts. See `docs/MNIST_04_05_ACCEPTED_VALIDATION.md` for the accepted result.
