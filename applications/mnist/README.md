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

## Accepted results

Training uses a deterministic stratified 5,000-image validation split drawn only from the official MNIST training set. The untouched official 10,000-image test split is evaluated only after model selection.

```text
cropped-dense float: 90.29%
native-sparse float: 91.62%
```

After hardware-aware integer export and execution through the validated `NeuromorphicCore` on the same test corpus:

```text
cropped-dense: golden 90.24%, 99.25% prediction agreement, 3893 stored synapses
native-sparse: golden 91.71%, 99.30% prediction agreement, 4086 stored synapses
```

These accepted results are documented in `docs/MNIST_03_TRAINING_BASELINES.md` and `docs/MNIST_04_05_ACCEPTED_VALIDATION.md`.

## Setup

A separate application environment is recommended so TensorFlow does not disturb the Brian2Loihi/reference environment:

```bash
python3.12 -m venv .venv-mnist
source .venv-mnist/bin/activate
python -m pip install --upgrade pip
python -m pip install -e "Neuromorphic Digital Twin"
python -m pip install -e "applications/mnist[train,test]"
pytest applications/mnist/tests -q
```

## Reproduce accepted software validation

The accepted export/comparison flow validates both checkpoints, writes both project-native deployments, evaluates float and golden models on the same official test corpus, and records SHA-256 provenance:

```bash
python applications/mnist/scripts/run_accepted_validation.py
```

Generated validation artifacts are written under `applications/mnist/build/accepted-validation/`, and deployment images under `applications/mnist/build/accepted-deployment/`.
