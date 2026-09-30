# FPGA-v2 NxTF MNIST Emulation Application

This directory contains the P08 application for the Loihi architectural digital
twin v2. It is intentionally separate from the frozen FPGA-v1 MNIST application
under `applications/mnist_baseline/`.

P08 was realigned on 2026-09-29 after the first three hand-designed candidate
networks showed that matching only the published parameter count was not a
sufficient basis for comparison. The goal is to **emulate the published NxTF
frame-based MNIST work as closely as the available sources and FPGA-v2 framework
allow**, while explicitly labeling every reconstruction choice.

The authoritative P08 documents are:

```text
Loihi_Digital_Twin/v2/docs/P08_MNIST_COMPARISON_CONTRACT.md
Loihi_Digital_Twin/v2/docs/P08_NXTF_SOURCE_AUDIT.md
Loihi_Digital_Twin/v2/docs/P08_NXTF_RECONSTRUCTION.md
Loihi_Digital_Twin/v2/docs/P08_CONTEXT_PAGING.md
Loihi_Digital_Twin/v2/docs/P08_2_ACCEPTANCE.md
Loihi_Digital_Twin/v2/docs/P08_3_TRAINING_CONVERSION_FREEZE.md
Loihi_Digital_Twin/v2/LOIHI_TWIN_ROADMAP.md
```

## Current status

P08.1 was accepted on 2026-09-30 with the explicit `PROJECT_RECONSTRUCTION`:

```text
28x28x1
 -> Conv2D(14, 5x5, stride 2, valid) -> 12x12x14
 -> Conv2D(20, 3x3, stride 1, valid) -> 10x10x20
 -> Conv2D(12, 3x3, stride 2, valid) ->  4x4x12
 -> Conv2D(10, 4x4, stride 1, valid) ->  1x1x10
```

Frozen structural totals:

```text
neurons:                 4,218
convolution weights:     6,950
bias parameters:            56
trainable parameters:    7,006
expanded connections: 338,880
primary timesteps:          100
```

P08.2 was accepted after the deterministic paging software contract and Vivado
RTL paged-dispatch simulation passed locally. The execution boundary is:

```text
P06 logical/backing contexts: 5
resident K26 context slots:   3
physical HLS engines:         1
```

The NxTF paper reports 14 Loihi neurocores for its benchmark. P08 keeps that
published result separate from the project's five-core P06 placement. The
5-versus-14 difference is a documented mapping/model discrepancy caused by the
reconstructed topology and different partitioning, sharing, and storage models;
it is not forced to match artificially.

P08.3.1 now freezes the ANN training and ANN-to-SNN conversion policies before a
new training run. The active status marker is:

```text
P08_2_PAGING_ACCEPTED_P08_3_POLICY_FROZEN
```

The official 10,000-image MNIST test split remains locked.

## Source-backed reference boundary

The NxTF paper reports a frame-based MNIST experiment with a four-layer CNN,
approximately 4k neurons and 7k trainable parameters, 14 Loihi neurocores,
341k discrete convolutional connections represented by 6,746 shared weights,
and 100 algorithmic timesteps per sample. It reports 0.74% ANN error and 0.79%
converted-SNN error.

The surviving public Intel NxTF MNIST tutorial is a different, larger workload:

```text
28x28x1
 -> Conv2D(16, 5x5, stride 2)
 -> Conv2D(32, 3x3)
 -> Conv2D(64, 3x3, stride 2)
 -> Conv2D(10, 4x4)
 -> 10 outputs
```

That tutorial contains 33,802 trainable parameters and uses 512 timesteps in its
saved example. It is architectural/training/conversion evidence, not a substitute
for the paper benchmark.

## P06 structural contract

`mnist_v2_nxtf/structural.py` expands the accepted CNN into P06 connectivity for
resource accounting. Structural connection values are coefficient-identity
tokens, **not trained weights**.

The capacity-safe mapping policy is:

```text
compartments_per_core = 900
```

This leaves the neural graph unchanged and produces:

```text
logical cores:                 5
external ingress routes:       2,187
expanded connections:        338,880
P06 stored shared parameters: 64,235
static output routes:           7,860
```

The P06 shared-parameter count is intentionally not equated to NxTF's 6,746
shared weights; the representations and partitioners differ.

## P08.2 paging boundary

The accepted P05 K26 shell has three resident full logical-context slots and one
physical HLS compute engine. P08.2 keeps all five logical cores in backing state
and pages any required core into one of those three resident slots.

`loihi_twin_v2.hardware_p08` exports all five logical cores into backing images
while preserving logical route identities. `loihi_twin_v2.paging` defines the
deterministic paging policy and paged golden-model wrapper.

`rtl/p08_paged_dispatch_controller.v` adds the accepted host-orchestrated one-core
dispatch primitive. The host owns page save/load, logical-ID packet delivery into
backing next-event images, and the global barrier.

See `P08_CONTEXT_PAGING.md` and `P08_2_ACCEPTANCE.md` for the full protocol and
acceptance boundary.

## P08.3.1 frozen training policy

The ANN builder in `mnist_v2_nxtf/ann.py` uses the accepted topology with learned
biases and source-style training choices:

```text
hidden activation:           ReLU
output activation:           softmax
Dropout:                     0.1 after each hidden convolution
optimizer:                   Adam
learning rate:               1e-3
loss:                        categorical cross-entropy
batch size:                  32
maximum epochs:              30
early-stop patience:         5
checkpoint selection:        max validation accuracy
selection tie breakers:      min validation loss, then earliest epoch
input scaling:               float32 / 255
training / validation:       55,000 / 5,000
```

The 30-epoch early-stopping rule and deterministic selection policy are project
reconstruction choices because the paper does not publish its exact benchmark
training configuration. The public NxTF tutorial supports the Keras/Adam/loss/
batch/dropout style but its two-epoch demonstration is not treated as an exact
paper rule.

## P08.3.1 frozen conversion boundary

The conversion policy in `mnist_v2_nxtf/policy.py` freezes:

```text
method:                       SNN-Toolbox-style rate conversion
calibration:                  training remainder only, every 10th sample
primary horizon:              100 timesteps
characterization:             16, 32, 64, 100 timesteps
weight precision:             signed 8-bit project range -127..127
bias precision:               signed 12-bit project range -2047..2047
weight exponent reference:    0
source bias exponent ref:     6
threshold mantissa:           512
threshold normalization:      enabled
reset:                        FPGA-v2 hard reset to zero
threshold/input ratio:        8
current decay:                4096
voltage decay:                0
refractory ticks:             0
input encoding:               deterministic evenly-distributed rate
output decoder:               argmax accumulated output spikes
```

The historical SNN Toolbox Loihi example uses soft reset. FPGA-v2 retains its
already validated hard-reset neuron arithmetic and records that difference as a
project adaptation rather than claiming soft-reset equivalence.

## Environment

Keep P08 dependencies out of the long-lived `.venv-v2` environment. From the
repository root:

```bash
python3.12 -m venv .venv-p08
source .venv-p08/bin/activate
python -m pip install --upgrade pip
python -m pip install -e Loihi_Digital_Twin/v2
python -m pip install -e 'applications/mnist_v2_nxtf[train,test]'
```

## Current verification gate

P08.3.1 policy freeze:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash scripts/run_p08_3_policy_preflight.sh
```

This gate builds and compiles the Keras model but does **not** load MNIST and does
not train or inspect the official test split.

Accepted P08.2 regression gates remain available:

```bash
bash scripts/run_p08_2_preflight.sh
# after sourcing Vivado 2025.2:
bash rtl/run_p08_paged_dispatch_controller_sim.sh
```

## Next development sequence

1. Independently verify and accept P08.3.1 policy freeze.
2. P08.3.2 trains the ANN using only the fixed 55k/5k training-validation split.
3. Select exactly one ANN checkpoint from validation metrics only.
4. P08.3.3 applies the frozen rate-conversion/quantization/reset/decoder policy
   and demonstrates validation behavior at the primary 100-timestep horizon.
5. Freeze the converted deployment and all conversion scales/thresholds.
6. Only then unlock the official test split for P08.4 full ANN/SNN evaluation.
7. Later run representative physical K26 differential validation and build the
   final bounded NxTF comparison.
