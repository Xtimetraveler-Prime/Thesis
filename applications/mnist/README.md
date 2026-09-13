# MNIST Application

This directory tracks an MNIST workload built on top of the validated neuromorphic digital-twin platform. Application work is intentionally separate from the baseline platform milestones and must not silently change the frozen core behavior.

See [`MILESTONES.md`](MILESTONES.md) for the rollout plan and [`docs/MNIST_01_CAPACITY_AUDIT.md`](docs/MNIST_01_CAPACITY_AUDIT.md) for the first hardware-fit decision.

## Frozen first architecture

The FPGA-v1 core has a 4,096-synapse physical limit, so a dense 784-pixel-to-10-neuron network does not fit. The first workload uses the largest simple square dense input that does fit:

```text
28x28 MNIST
   -> exact 20x20 center crop
   -> 400 deterministic spike-encoded input axons
   -> 10 LIF output neurons
   -> 4,000 maximum dense synapses
   -> argmax(output spike counts)
```

Images are presented for 16 algorithmic ticks. Pixel intensities are converted to deterministic integer spike counts rather than random Poisson trains.

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

Generated training/deployment artifacts go under `applications/mnist/build/`, which is excluded by the repository-wide `build/` ignore rule.

## Setup

Install the already-validated core package, then the MNIST application:

```bash
python -m pip install -e "Neuromorphic Digital Twin[dev,compare]"
python -m pip install -e "applications/mnist[test]"
pytest applications/mnist/tests -q
```

For training, add TensorFlow:

```bash
python -m pip install -e "applications/mnist[train,test]"
```

The training dependency follows the TensorFlow 2.21 workflow used in the user-authored MNIST lab notebooks.

## Training and deployment flow

A small smoke run can be used before full training:

```bash
python applications/mnist/scripts/train_snn.py \
  --epochs 1 \
  --train-limit 2000 \
  --test-limit 500
```

Full baseline training:

```bash
python applications/mnist/scripts/train_snn.py --epochs 10
```

Export the trained weights to the project's integer/FPGA representation:

```bash
python applications/mnist/scripts/export_network.py \
  applications/mnist/build/training/mnist_snn_float.npz
```

Evaluate the exported network through the actual `NeuromorphicCore` golden model:

```bash
python applications/mnist/scripts/evaluate_golden.py \
  applications/mnist/build/deployment/deployment.json
```

Until the first local TensorFlow training run is accepted, MNIST-03 and the downstream trained-network milestones remain open even though their implementation scaffolding is present.
