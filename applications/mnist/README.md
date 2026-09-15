# MNIST Application

This directory tracks an MNIST workload built on top of the validated neuromorphic digital-twin platform. Application work is separate from baseline platform milestones and must not silently change the frozen core behavior.

See [`MILESTONES.md`](MILESTONES.md) for the rollout plan, [`docs/MNIST_01_CAPACITY_AUDIT.md`](docs/MNIST_01_CAPACITY_AUDIT.md) for the hardware-capacity decision, [`docs/MNIST_03_TRAINING_BASELINES.md`](docs/MNIST_03_TRAINING_BASELINES.md) for the accepted floating-point SNN baselines, and [`docs/NOTEBOOK_REUSE.md`](docs/NOTEBOOK_REUSE.md) for how the user-authored class notebooks are being repurposed.

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

## Encoder inspection

Inspect the same source MNIST image through either mapping:

```bash
python applications/mnist/scripts/inspect_encoding.py --profile native-sparse --index 0
python applications/mnist/scripts/inspect_encoding.py --profile cropped-dense --index 0
```

## Accepted training methodology

Training uses a deterministic stratified 5,000-image validation split drawn only from the official MNIST training set. Checkpoint selection uses validation accuracy; the official 10,000-image test split is evaluated only after model selection is frozen.

Accepted runs:

```bash
python applications/mnist/scripts/train_snn.py \
  --profile cropped-dense \
  --epochs 10 \
  --validation-size 5000 \
  --output applications/mnist/build/accepted-training

python applications/mnist/scripts/train_snn.py \
  --profile native-sparse \
  --epochs 10 \
  --fine-tune-epochs 5 \
  --validation-size 5000 \
  --output applications/mnist/build/accepted-training
```

Accepted floating-point test accuracies are 90.29% for cropped-dense and 91.62% for native-sparse. See `docs/MNIST_03_TRAINING_BASELINES.md` for selection details.

## Export and matched golden-model evaluation

Each accepted checkpoint embeds its profile, so deployment artifacts are kept separate automatically:

```bash
python applications/mnist/scripts/export_network.py \
  applications/mnist/build/accepted-training/cropped-dense_snn_float.npz

python applications/mnist/scripts/export_network.py \
  applications/mnist/build/accepted-training/native-sparse_snn_float.npz
```

Then compare each floating-point SNN and exported integer deployment on the exact same official test images:

```bash
python applications/mnist/scripts/compare_float_golden.py \
  applications/mnist/build/accepted-training/cropped-dense_snn_float.npz \
  applications/mnist/build/deployment/cropped-dense/deployment.json

python applications/mnist/scripts/compare_float_golden.py \
  applications/mnist/build/accepted-training/native-sparse_snn_float.npz \
  applications/mnist/build/deployment/native-sparse/deployment.json
```

The comparison reports float accuracy, quantized/golden accuracy, accuracy delta, prediction agreement, input events, output spikes, synaptic visits, no-spike/tie frequency, and deployed synapse count on one matched corpus.
