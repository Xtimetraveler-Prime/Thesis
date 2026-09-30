# FPGA-v2 NxTF-Oriented MNIST Application

This directory contains the P08 application for the Loihi architectural digital
twin v2. It is intentionally separate from the frozen FPGA-v1 application under
`applications/mnist_baseline/`.

The comparison and experiment boundary is defined in:

```text
Loihi_Digital_Twin/v2/docs/P08_MNIST_COMPARISON_CONTRACT.md
```

## Candidate topology

```text
28x28 MNIST
 -> Conv2D(3 filters, 5x5, stride 1, valid, ReLU, no bias)
 -> Conv2D(6 filters, 3x3, stride 2, valid, ReLU, no bias)
 -> Dense(8, ReLU, no bias)
 -> Dense(10, ReLU, no bias)
 -> spike-count / argmax decoder after conversion
```

The four weight-bearing layers contain 2,472 spiking neurons and 6,125 trainable
weights. The current structural probe maps the fully nonzero candidate to three
logical cores and one physical P05 engine.

## Environments

The source/mapping preflight only requires the existing v2 environment. Training
and full-corpus TensorFlow evaluation should use a dedicated application virtual
environment so TensorFlow dependencies do not disturb `.venv-v2`.

Example:

```bash
python3.12 -m venv .venv-p08
source .venv-p08/bin/activate
python -m pip install --upgrade pip
python -m pip install -e Loihi_Digital_Twin/v2
python -m pip install -e 'applications/mnist_v2_nxtf[train,test]'
```

## Workflow

1. Run the source/mapping preflight from `Loihi_Digital_Twin/v2`:

```bash
bash scripts/run_p08_preflight.sh
```

2. Train the floating-point candidate using only the official training split and
   the deterministic 5,000-image validation subset for model selection:

```bash
python applications/mnist_v2_nxtf/scripts/train_candidate.py \
  --output applications/mnist_v2_nxtf/build/training
```

3. Convert/calibrate using only the frozen validation subset and compile the exact
   integer SNN through P06:

```bash
python applications/mnist_v2_nxtf/scripts/convert_candidate.py \
  --training applications/mnist_v2_nxtf/build/training \
  --output applications/mnist_v2_nxtf/build/conversion
```

The conversion step reports validation SNN accuracy at 16, 32, 64, and 100
algorithmic timesteps and writes the exact P06 network/deployment artifacts.
The official test set is not touched by either of these steps.

Official-test evaluation and physical K26 validation are enabled only after the
candidate training/conversion gate is accepted.
