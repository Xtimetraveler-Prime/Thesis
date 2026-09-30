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
Loihi_Digital_Twin/v2/LOIHI_TWIN_ROADMAP.md
```

## Current status

There is deliberately **no active/frozen network topology** in this package.
Revision-1/2/3 candidate topology, training, conversion, inference, mapping-probe,
and candidate CLI code were removed from the active tree so they cannot be
mistaken for the accepted workload.

The reusable pieces retained here are:

- the dedicated P08 Python package/environment boundary;
- standard 28x28 MNIST loading;
- the deterministic 55,000/5,000 train/validation split policy;
- deterministic rate-encoding helpers; and
- tests that verify the split/encoding contract and assert that the topology is
  still unfrozen.

The official 10,000-image MNIST test set must remain untouched until the topology,
training policy, ANN-to-SNN conversion, thresholds/scales, timestep policy, and
decoder are frozen from source evidence plus training/validation data only.

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
must not be silently substituted for the paper's ~7k-parameter/100-timestep
benchmark. See `P08_NXTF_SOURCE_AUDIT.md` for the distinction and source links.

## Important virtualization rule

The accepted P05 K26 shell retains three full logical-core contexts and services
them with one physical HLS engine. **Three resident contexts are not a P08
network-size limit.**

If the source-faithful NxTF-style workload requires more logical cores than can be
resident at once, P08 must extend the virtualization path with deterministic
logical-context paging/loading while preserving logical IDs, architectural state,
resource limits, packet semantics, barriers, and normalized Python/FPGA traces.
The workload must not be shrunk merely to fit the current three-context physical
shell.

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

The current preflight validates only the reusable P08 scaffold/data contract plus
accepted P05/P06 regressions. It intentionally does **not** produce a candidate
mapping artifact or permit ANN/SNN evaluation, because the NxTF-emulation
topology has not yet been frozen.

## Next development sequence

1. Finish the P08.1 source reconstruction: recover the exact paper topology and
   conversion details wherever public evidence supports them; label unknowns.
2. Freeze the closest source-backed topology and quantify its expected neuron,
   parameter, connection, and logical-core footprint before training.
3. If it exceeds three resident K26 contexts, add deterministic context paging
   rather than reducing the network to fit the current shell.
4. Train using only the official training split plus the frozen validation split.
5. Freeze ANN-to-SNN conversion using validation data only.
6. Compile through P06, run full software accuracy, then perform representative
   physical K26 differential validation.
7. Compare against NxTF with directly comparable and contextual quantities kept
   separate.
