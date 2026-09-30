# FPGA-v2 NxTF-Oriented MNIST Application

This directory contains the P08 application for the Loihi architectural digital
twin v2. It is intentionally separate from the frozen FPGA-v1 application under
`applications/mnist_baseline/`.

The comparison and experiment boundary is defined in:

```text
Loihi_Digital_Twin/v2/docs/P08_MNIST_COMPARISON_CONTRACT.md
```

## Active candidate topology

The initial 3-filter / 6-filter / Dense(8) candidate plateaued at 88.10%
validation accuracy after 50 deterministic epochs and was rejected before
conversion or official-test evaluation. The active revision spends the same
order-of-magnitude parameter budget on substantially more feature channels:

```text
28x28 MNIST
 -> Conv2D(12 filters, 5x5, stride 2, valid, ReLU, no bias)
 -> Conv2D(12 filters, 3x3, stride 2, valid, ReLU, no bias)
 -> Dense(20, ReLU, no bias)
 -> Dense(10, ReLU, no bias)
 -> spike-count / argmax decoder after conversion
```

The four weight-bearing layers contain 2,058 spiking neurons and 7,796 trainable
weights. The deterministic worst-case structural probe maps the candidate to
three logical cores and one physical P05 engine, with 81,800 expanded
connections, 10,076 stored shared parameters, and 1,772 static source routes.

## Environment

P08 uses NumPy for the structural mapping probe and TensorFlow for training and
conversion calibration. Keep those application dependencies out of the long-lived
`.venv-v2` environment and use a dedicated P08 environment for **all** P08
preflight/training/conversion commands.

From the repository root:

```bash
python3.12 -m venv .venv-p08
source .venv-p08/bin/activate
python -m pip install --upgrade pip
python -m pip install -e Loihi_Digital_Twin/v2
python -m pip install -e 'applications/mnist_v2_nxtf[train,test]'
```

## Workflow

1. With `.venv-p08` active, run the source/mapping preflight from
   `Loihi_Digital_Twin/v2`:

```bash
bash scripts/run_p08_preflight.sh
```

2. Train the floating-point candidate using only the official training split and
   the deterministic 5,000-image validation subset for model selection:

```bash
python applications/mnist_v2_nxtf/scripts/train_candidate.py \
  --output applications/mnist_v2_nxtf/build/training_revision2
```

3. Convert/calibrate using only the frozen validation subset and compile the exact
   integer SNN through P06 after the ANN gate is accepted:

```bash
python applications/mnist_v2_nxtf/scripts/convert_candidate.py \
  --training applications/mnist_v2_nxtf/build/training_revision2 \
  --output applications/mnist_v2_nxtf/build/conversion_revision2
```

The conversion step reports validation SNN accuracy at 16, 32, 64, and 100
algorithmic timesteps and writes the exact P06 network/deployment artifacts.
The official test set is not touched by training or conversion calibration.

Official-test evaluation and physical K26 validation are enabled only after the
candidate training/conversion gate is accepted.
