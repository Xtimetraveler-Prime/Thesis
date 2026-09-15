# MNIST Application

This directory tracks an MNIST workload built on top of the validated neuromorphic digital-twin platform. Application work is separate from baseline platform milestones and must not silently change the frozen core behavior.

See [`MILESTONES.md`](MILESTONES.md) for the rollout plan, [`docs/MNIST_01_CAPACITY_AUDIT.md`](docs/MNIST_01_CAPACITY_AUDIT.md) for the hardware-capacity decision, and [`docs/NOTEBOOK_REUSE.md`](docs/NOTEBOOK_REUSE.md) for how the user-authored class notebooks are being repurposed.

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
├── docs/           audit and application notes
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
- raw pixel handling and 0..255 / 255 normalization concept;
- Adam optimization and sparse categorical cross-entropy;
- training-time measurement;
- test accuracy evaluation;
- `argmax` predictions;
- incorrect-prediction indexing and later visualization/analysis.

The dense ReLU ANN itself is not copied as the deployable model because the target platform requires explicit spike input and LIF dynamics.

## Setup

Install the validated core package and MNIST application:

```bash
python -m pip install -e "Neuromorphic Digital Twin[dev,compare]"
python -m pip install -e "applications/mnist[test]"
pytest applications/mnist/tests -q
```

For training, add TensorFlow:

```bash
python -m pip install -e "applications/mnist[train,test]"
```

## Planned software flow

Inspect either encoder profile:

```bash
python applications/mnist/scripts/inspect_encoding.py --profile native-sparse --index 0
python applications/mnist/scripts/inspect_encoding.py --profile cropped-dense --index 0
```

Train the simpler cropped-dense baseline first, then the native-sparse baseline:

```bash
python applications/mnist/scripts/train_snn.py --profile cropped-dense --epochs 10
python applications/mnist/scripts/train_snn.py --profile native-sparse --epochs 10
```

The native-sparse training path trains the direct classifier, prunes to the physical 4,096-synapse budget, and fine-tunes the surviving masked connections before acceptance.

Each accepted checkpoint is then exported into the existing integer/M08 storage representation and evaluated through the actual `NeuromorphicCore`, not through a separate application simulator.
