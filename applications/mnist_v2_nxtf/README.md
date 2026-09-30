# FPGA-v2 NxTF MNIST Emulation Application

This directory is the P08 application scaffold for the Loihi architectural
digital twin v2. It is intentionally separate from the frozen FPGA-v1 MNIST
application under `applications/mnist_baseline/`.

P08 was realigned on 2026-09-29 after the first three hand-designed candidate
networks showed that matching only the published parameter count was not a
sufficient basis for comparison. The goal is now to **emulate the published NxTF
MNIST work as closely as the available sources and the FPGA-v2 framework allow**,
then document every unavoidable difference explicitly.

The authoritative P08 documents are:

```text
Loihi_Digital_Twin/v2/docs/P08_MNIST_COMPARISON_CONTRACT.md
Loihi_Digital_Twin/v2/docs/P08_NXTF_SOURCE_AUDIT.md
Loihi_Digital_Twin/v2/docs/P08_NXTF_RECONSTRUCTION.md
Loihi_Digital_Twin/v2/LOIHI_TWIN_ROADMAP.md
```

## Current status

P08.1 now contains a **source-bounded topology proposal**, but it is deliberately
not marked accepted/frozen yet.

The exact layer dimensions of the paper's frame-based MNIST benchmark were not
recovered from the paper/preprint, Intel NRC repository history, SNN Toolbox
history, or the public author-repository artifacts inspected in P08.1. The
surviving Intel tutorial is clearly a different 33,802-parameter model.

Rather than invent an "exact" topology, P08.1 keeps the tutorial's public
four-convolution spatial scaffold and deterministically searches the three hidden
channel counts against the paper's aggregate anchors. The current proposal is:

```text
28x28x1
 -> Conv2D(14, 5x5, stride 2, valid) -> 12x12x14
 -> Conv2D(20, 3x3, stride 1, valid) -> 10x10x20
 -> Conv2D(12, 3x3, stride 2, valid) ->  4x4x12
 -> Conv2D(10, 4x4, stride 1, valid) ->  1x1x10
```

Its structural totals are:

```text
neurons:                 4,218
convolution weights:     6,950
bias parameters:            56
trainable parameters:    7,006
expanded connections: 338,880
primary timesteps:          100
```

These values are close to the paper's approximately 4k neurons, approximately 7k
parameters, 341k discrete connections, and 6,746 shared weights, but the graph is
explicitly `PROJECT_RECONSTRUCTION`; it is not claimed to be the unpublished NxTF
benchmark topology.

`TOPOLOGY_STATUS` remains:

```text
UNFROZEN_NXTF_EMULATION_REALIGN
```

until Diego independently verifies and accepts the P08.1 reconstruction/resource
audit.

The official 10,000-image MNIST test set remains locked. No ANN training or SNN
accuracy evaluation is authorized yet.

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

That tutorial is all-convolutional, contains 33,802 trainable parameters, uses
Dropout during ANN training, includes learned biases, and runs its example for
512 Loihi timesteps. It is useful architectural evidence for NxTF style, but it
must not be silently substituted for the paper benchmark.

The detailed evidence classifications and reconstruction rule are in
`Loihi_Digital_Twin/v2/docs/P08_NXTF_RECONSTRUCTION.md`.

## P06 structural probe

`mnist_v2_nxtf/structural.py` expands the proposed CNN into the existing P06
`NetworkSpec` boundary for connectivity/resource accounting only. It uses one
P06 population per convolution output channel so a later trained deployment can
represent the learned Conv2D bias per channel.

The structural connection values are stable coefficient-identity tokens, **not
trained weights**.

A stock 1,024-compartment first-fit placement is expected to overflow the current
project synapse-memory model. The P08.1 probe instead uses a mapping-only policy
of:

```text
compartments_per_core = 900
```

without changing the neural graph. The deterministic contract is five logical
cores, which is also the compartment-count lower bound for 4,218 neurons under
the project's 1,024-compartment/core limit.

Expected P06 totals asserted by the reconstruction test are:

```text
logical cores:                 5
external ingress routes:       2,187
expanded connections:        338,880
P06 stored shared parameters: 64,235
static output routes:           7,860
```

The P06 stored-shared-parameter count is intentionally not equated to NxTF's
6,746 shared weights; the compiler/storage models are different.

## Important virtualization rule

The accepted P05 K26 shell retains three full logical-core contexts and services
them with one physical HLS engine. **Three resident contexts are not a P08
network-size limit.**

The current P08.1 proposal requires five logical cores under the capacity-safe
P06 probe, so P08.2 must add deterministic logical-context paging/loading while
preserving logical IDs, architectural state, resource limits, packet semantics,
barriers, and normalized Python/FPGA traces. The workload must not be shrunk to
fit the current three-context physical shell.

The P06 five-core result is not expected to equal the paper's 14 native Loihi
neurocores because P06 and NxTF use different placement and compression models.

## Environment

Keep P08 application dependencies out of the long-lived `.venv-v2` environment.
From the repository root:

```bash
python3.12 -m venv .venv-p08
source .venv-p08/bin/activate
python -m pip install --upgrade pip
python -m pip install -e Loihi_Digital_Twin/v2
python -m pip install -e 'applications/mnist_v2_nxtf[train,test]'
```

## Current preflight

With `.venv-p08` active:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash scripts/run_p08_preflight.sh
```

The preflight validates:

- the reusable MNIST data/split/rate-encoding contract;
- the deterministic P08.1 reconstruction search;
- the expanded structural graph and P06 resource contract;
- the expected default-P06 synapse-capacity failure;
- the five-core capacity-safe P06 probe; and
- relevant accepted P05/P06 regressions.

Passing this preflight does not itself accept/freeze the topology. Diego's local
verification and review are the P08.1 acceptance gate.

## Next development sequence

1. Independently verify and accept/reject the P08.1 source-bounded reconstruction.
2. If accepted, record the P08.1 freeze in the roadmap/application config.
3. Begin P08.2 deterministic context paging because five logical cores exceed the
   three resident K26 contexts.
4. Preserve the exact reconstructed graph while adapting the execution mechanism.
5. Only after P08.2 is validated, freeze the P08.3 ANN training/conversion policy
   using training/validation data only.
6. Keep the official test set locked until topology, training, conversion,
   thresholds/scales, timestep policy, and decoder are frozen.
7. Later run software accuracy and representative physical K26 differential
   validation, then compare with NxTF using bounded/directly comparable metrics.
