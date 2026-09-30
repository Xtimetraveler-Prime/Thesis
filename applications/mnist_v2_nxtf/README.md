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
Loihi_Digital_Twin/v2/LOIHI_TWIN_ROADMAP.md
```

## Current status

P08.1 was accepted on 2026-09-30 after the independent local preflight reported
21 passing tests and reproduced the reconstruction/resource counts exactly.

The exact layer dimensions of the paper's frame-based MNIST benchmark were not
recovered from the audited primary/public artifacts. The accepted network is
therefore an explicit `PROJECT_RECONSTRUCTION`, not a claim that the unpublished
NxTF graph was recovered:

```text
28x28x1
 -> Conv2D(14, 5x5, stride 2, valid) -> 12x12x14
 -> Conv2D(20, 3x3, stride 1, valid) -> 10x10x20
 -> Conv2D(12, 3x3, stride 2, valid) ->  4x4x12
 -> Conv2D(10, 4x4, stride 1, valid) ->  1x1x10
```

Its frozen structural totals are:

```text
neurons:                 4,218
convolution weights:     6,950
bias parameters:            56
trainable parameters:    7,006
expanded connections: 338,880
primary timesteps:          100
```

The active status marker is:

```text
P08_1_RECONSTRUCTION_ACCEPTED_P08_2_PENDING
```

P08.2 is now implementing/validating deterministic logical-context paging. ANN
training and the official 10,000-image MNIST test set remain locked until P08.2
is accepted.

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
saved example. It is architectural/conversion evidence, not a substitute for the
paper benchmark. The evidence classifications and reconstruction rule are in
`P08_NXTF_RECONSTRUCTION.md`.

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

The accepted P05 K26 shell has:

```text
3 resident full logical-context slots
1 physical HLS compute engine
```

The accepted P08 graph requires five P06 logical cores, so it is not reduced to
fit those three slots. P08.2 instead uses:

```text
5 logical/backing contexts
3 resident K26 context slots
1 physical HLS engine
```

`loihi_twin_v2.hardware_p08` exports all five logical cores into backing images
while allowing any three to be materialized into P05 slots. Routes retain
logical destination IDs even when the destination is not resident.

`loihi_twin_v2.paging` defines a deterministic round-robin page schedule and a
paged golden-model wrapper. Directed tests require normalized execution to remain
identical across legal service/page/drain orders and explicitly verify that
architectural state survives eviction and reload.

`rtl/p08_paged_dispatch_controller.v` adds a host-orchestrated one-core dispatch
primitive. The host owns page save/load, logical-ID packet delivery into backing
next-event images, and the global barrier. The existing three-slot P05 memory
fabric is reused rather than enlarged.

See `Loihi_Digital_Twin/v2/docs/P08_CONTEXT_PAGING.md` for the full protocol.

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

## P08.2 verification

Software/context-paging gate:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash scripts/run_p08_2_preflight.sh
```

RTL dispatch gate, after sourcing Vivado 2025.2:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash rtl/run_p08_paged_dispatch_controller_sim.sh
```

P08.2 is not accepted until both gates pass independently in the repository
environment.

## Next development sequence

1. Verify the P08.2 software/context-paging preflight.
2. Verify the P08 paged-dispatch RTL simulation.
3. Record P08.2 acceptance while keeping the five-core/three-resident/one-engine
   quantities separate.
4. Begin P08.3 by freezing ANN training and ANN-to-SNN conversion policies using
   source evidence plus explicit reconstruction decisions.
5. Train/select using only the training/validation split.
6. Keep the official test set locked until training/conversion/decoder policies
   are frozen.
7. Later perform full software evaluation and representative physical K26
   differential validation before the final NxTF comparison.
