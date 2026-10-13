# P06.1 — Source-backed published MNIST benchmark candidate audit

**Status: RESEARCH AUDIT IN PROGRESS — NO PAPER OR HARDWARE PROFILE
FROZEN, NO MNIST TEST EVALUATION AUTHORIZED.**
**Branch:** `agent/v3-p06-benchmark-audit`, branched from the merged
and accepted P05 `main`. NxTF is explicitly excluded from benchmark
selection. This file does not revise any accepted P05 evidence.

## Selection standard: no guesswork

P06 must distinguish **(1) publication-backed** properties,
**(2) recoverable verbatim from author-linked source and pretrained
artifacts**, **(3) explicit reproducible KV260 project decisions**,
and **(4) unknown or unsupported**. We will not infer a trained
weight matrix from a reported accuracy, silently retrain and
claim weight identity, use test labels to tune mapping, or call
an algorithmically different approximation a direct comparison.
A paper having code is insufficient if the **particular measured
weights and readout** are unavailable.

The roadmap requires auditing MNIST preparation, input encoding,
full neuron/synapse topology, quantization, neuron equations,
update order, sample/timestep schedule, readout, training,
weights/checkpoint, Loihi mapping, evaluation subset, hardware
timing/power scope and source licensing. A freeze requires
independent verification and any necessary hardware-model
extension to be accepted **before official-test scoring**.

## Recommended primary candidate (CONDITIONAL)

**Arjun Rao, Philipp Plank, Andreas Wild and Wolfgang Maass (2022),
"A Long Short-Term Memory for AI Applications in Spike-based
Neuromorphic Hardware", Nature Machine Intelligence 4, 467–479,
DOI 10.1038/s42256-022-00480-w.**

- Paper: https://www.nature.com/articles/s42256-022-00480-w
- Public preprint: https://arxiv.org/abs/2107.03992
- **Paper-linked primary source** (Intel):
  https://github.com/intel-nrc-ecosystem/models/tree/3dc53bfcfae1efe8772b8cb5e2c512bb28c872f8/nxsdk_modules_ncl/lsnn
- Pinned upstream commit SHA:
  `3dc53bfcfae1efe8772b8cb5e2c512bb28c872f8`
  (not mutable `master`).
- Training/inference task: **sequential MNIST (sMNIST)**, not
  ordinary simultaneous-image MNIST. It is the original MNIST
  **28×28** images presented *one pixel per timestep* for
  **784 image steps**, followed by a source-configured
  **56-step classification cue** (exact sample reset/decision
  timing and bridge semantics still need a detailed audit).
  Do not compare this paper's sMNIST results directly to
  a conventional single-frame MNIST inference result.
- Critical distinction: the paper-backed implementation
  actually supplies a pretrained model in `.npy` files
  *within the author's Intel source repository*. It
  does **not** require inventing W1/W2 or retraining
  to obtain initial coefficients.

### Frozen upstream file inventory — source evidence, not yet imported

Source: `nxsdk_modules_ncl/lsnn/apps/seqmnist/` in the pinned
upstream commit. All values below are **GitHub object
identifiers/sizes from its immutable Git tree**.
They are NOT unverified local SHA-256 values; independent
source-file shape/dtype/content audit comes next.

| Artifact | Git blob SHA-1 | Bytes | Expected matrix orientation |
|---|---|---:|---|
| `weights/v25_94per/w_in.npy` | `e1ed712f3af5af64cc3680bb5e50dc9447bd13aa` | 76,928 | (240 post, 80 pre) — verify from .npy header |
| `weights/v25_94per/w_rec.npy` | `c75f4c731b38b017f8d232b326801cba0fa65e40` | 230,528 | (240 post, 240 pre) — verify |
| `weights/v25_94per/w_out.npy` | `b067c855de56cdcb6f4e8ce468f56581544a178f` | 9,728 | (10 post, 240 pre) — verify |
| `src/lsnn.py` | `c958b3e3a0f510dc14cf17deacb1a05b8f145c66` | 34,141 | Actual Loihi source for adaptive/regular neuron dynamics |
| `apps/seqmnist/seq_mnist.py` | `9551c2b2d399649cce9ccbbc3bd049694095540a` | 7,239 | Main network creation / test selection |
| `apps/seqmnist/seq_img_classifier.py` | `6be7b2f27f840e23ccbc69b9ad393971b3aa8b40` | 17,494 | Input/decision cue & on-Loihi construction |

Those three weight files represent an expected **79,200**
dense feedforward/recurrent synapses
(80×240 + 240×240 + 240×10), before accounting for
extra adaptation/control connections. They are not
"the number of occupied Loihi synapse memory entries":
mapping, compression and placement matter.

### Precisely identified architecture and dynamics

**Directly recoverable from pinned upstream source:**

- `apps/seqmnist/seq_mnist.py`, `runSequentialMnist()`:
  **80 threshold-change input channels, 140 regular
  recurrent units, 100 adaptive recurrent units,
  10 non-spiking output/readout compartments,
  784 sequential pixel timesteps, 56 output cue steps**.
  Weights loaded without retraining from the `v25_94per`
  directory.
- `apps/seqmnist/seq_img_classifier.py`:
  `thrAdaScale=4`, `_numDelayBits=4`,
  40 thresholds = floor(linspace(0,255,40)),
  batch configuration 10. Exactly **38 threshold indices 1..38** drive paired onset/offset channels, threshold 39 is a *pixel==255 touch* on port 78, and the 56-step output cue uses port 79; ports 0 and 1 are unused. Adjacent-pixel crossings use current→**next** pixel; there are no onset/offset crossings at pixel index 783. The output management SNIP reads the 10 membrane V registers at timestep 840 and uses strict `v>maxV` with `maxV=-8388608`, `maxVId=-1`: ties **above the minimum** favor the lowest index, but ten equal minimum voltages yield the original **`-1` sentinel**, not digit zero. Source-exact reconstruction must preserve this rare failure-to-classify boundary. Output readout groups
  use very high threshold mantissa `2**17-1`,
  specifically non-spiking integrated output;
  a simple count of output spikes would be
  a **different classifier**.
- `src/lsnn.py`, `ModelParams.__init__`:
  `vth=127`, `tauU=0`, `tauV=20`, `refrac=1`,
  `tauAdaption=700`, `beta=1390000`
  before any source-level mapping/scaling.
  The **actual Loihi fixed-point decay** is
  `decayU=4096`, `decayV=int(4096/20)=204`,
  `decayAdaption=int(4096/700)=5`;
  the adaptive cell includes an auxiliary
  compartment whose state feeds its soma.
  **Do not** assume these arithmetic fields by
  themselves reproduce all Loihi adaptation semantics;
  extract the Loihi connection prototypes, shifts,
  threshold and state update order in P06.2.
- The repository's `seq_mnist.py` demo
  randomly selects **100 test images with seed 0** and
  batch size 10. A result on those 100 selected images
  is **not** a 10,000-image full-test accuracy.
  The source folder `v25_94per` is a *file label*,
  **not a verified performance number or paper table
  row**. The paper's sMNIST reported score, exact tested
  trained checkpoint and evaluation/time/power
  conditions must be matched before quoting a
  numerical direct comparison.
- `datasets/mnist_dataset.py` uses
  `fetch_openml('mnist_784')` and the example
  selects rows 60000 onward for test. Preserve
  original image pixel `uint8` values; audit the
  SNIP `spiking.c` threshold-crossing rules (including
  the *next* pixel, last-pixel suppression and edge conditions) rather
  than invent Bernoulli/rate-coded spikes.

**Publication/source support, but NOT yet imported or demonstrated:**
- The paper uses multi-compartment AHP adaptation,
  recurrent feedback and sparse threshold-crossing
  spike encoding. This is the **actual** published
  sMNIST model; it must not be replaced by a convenient
  feed-forward 400–400–10 classifier while retaining
  the paper's performance headline.
- `NxSDK` runtime and Loihi 1 mapping/quantization
  are proprietary/dependency-specific; raw `.npy`
  coefficients are not proof that the FPGA's integer
  neuron state matches Loihi 1. We must establish
  a source-derived, cycle- and weight-exact oracle
  and validate FPGA conversion before benchmarking.

### Model compatibility with accepted v3: MAJOR OPEN BLOCKER

The accepted P05 FPGA's HLS core is based on
**one compartment per modeled neuron**; Loihi 1
multi-compartment trees are deferred by the inherited
`docs/LOIHI1_TARGET_SPEC.md`. In contrast, the
published LSNN uses 100 adaptive AHP units,
**each with a second dynamic compartment**, recurrent
240×240 weights and non-spiking readout accumulators.
An ordinary single-compartment LIF network with the
same dimensions/weights is *not the same model*.
Additionally current P05 deployments can encode
only one registered external axon ID per core;
their test schema was not designed for an 80-channel
temporally varying input encoder. A benchmark input
loader/contract must be added or carefully isolated,
rather than duplicating a single dummy axon.

This is therefore a **strong no-invented-weights
candidate but NOT yet accepted as directly runnable
on the existing FPGA**. P06.2 must design and
independently prove any multi-compartment AHP,
weighted fan-in and input-stream extensions, with
capacity/resource checks and a fallback to the
already accepted P05 single-compartment FPGA.
If these extensions are infeasible, choose a
simpler source-backed paper **before** using the
official MNIST test labels or modifying accuracy
targets. Do not close P06 merely because a
compatible but behavior-changing approximate
model runs on the KV260.

## Runner-up, reviewed and NOT selected for a freeze

**Alpha Renner, Forrest Sheldon, Anatoly Zlotnik,
Louis Tao and Andrew Sornborger (2024),**
"The backpropagation algorithm implemented on
spiking neuromorphic hardware",
Nature Communications 15, 9691,
DOI 10.1038/s41467-024-53827-9.
- Publication: https://www.nature.com/articles/s41467-024-53827-9
- Code linked by paper: https://github.com/lanl/spikingBackprop
- Publishes explicit CUBA neuron equations and
  feedforward **400 (20×20) input – 400 hidden –
  10 output** inference topology, with a four-gating-step
  reduced inference architecture and published Loihi
  throughput/energy methodology. The *full training
  implementation* uses additional learning/gating
  compartments; do not equate 400–400–10 with
  its complete on-chip learning hardware.
- Source includes `SFC_backprop/network_parameters_2layer_MNIST.py`,
  `network_topology_2layer.py`,
  `SFC_backprop_main.py`,
  `backprop_network.py` and `weight_init.py`.
- **Critical failure of our no-guesswork criterion:**
  inspection of the official repository's recursive
  version-controlled file tree found **no released
  learned weight/checkpoint archive**. The code has
  `--weight_mode rand_He` by default or restoration
  from a separately saved `saved_weights/` file,
  but no corresponding model artifact was
  published in the inspected tree. The published
  headline 96.3% spike-readout/97.5% top-1
  cannot legitimately be attributed to a
  newly retrained FPGA model with different
  seed and shuffled examples. Its Loihi
  NxSDK dependency makes exact retraining
  additionally challenging.
- **Disposition:** Keep as a secondary paper and
  possible future architecture-only comparison.
  **NOT eligible for P06 benchmark freeze**
  until an original trained model/checkpoint
  is obtained or the study explicitly authorizes
  comparison to an independently reproduced
  training run with distinct reported accuracy.

## Another usable asset but not an eligible published paper

R-Gaurav, `mnist-on-loihi`:
https://github.com/R-Gaurav/mnist-on-loihi
provides Loihi 2 Lava/SLAYER code and a serialized
`.pt`/`.net` trained network (784–128–64–10).
This is a **tutorial/source repository**, not
by itself a peer-reviewed original Loihi
MNIST hardware paper with a matching published
result/measurement protocol. Loihi 2 neuron/
Lava semantics also differ from our Loihi-1
digital twin. Useful for code experiments,
not a defensible paper-to-chip direct
benchmark claim.

## P06.1 hold point / next deliverables

1. [IMPLEMENTED SOURCE INVENTORY; VERIFICATION PENDING]
   Pin/check all three official binary weight files,
   code Git blobs and exact `.npy` dtype/shapes from
   the upstream immutable commit. See
   `scripts/p06_1_lsnn_source_audit.py`,
   `tests/test_p06_1_lsnn_source_audit.py`,
   `docs/P06_1_LSNN_SOURCE_MANIFEST.json`.
   **Do not bundle proprietary NxSDK or assume
   a torch-converted network is the same model.**
2. [OPEN] Read source-linked paper *and supplementary
   tables* closely enough to associate the specific
   pretrained model with the actual published Loihi
   sMNIST accuracy, test set size, energy/latency
   and measurement clock/method; any unsupported
   field must stay `UNKNOWN`.
3. [OPEN] Write a concrete FPGA architectural
   compatibility study for 240 recurrent neurons,
   100 second AHP compartments, streaming
   80-channel threshold encoder, output readout
   and the already accepted paging/bank buffers.
   Explicitly separate Loihi-specific features
   requiring new v3 implementation from model
   features currently supported.
4. [OPEN] Freeze **one** paper, one immutable
   checkpoint, one dataset checksum, one exact
   input encoder, neuron/synapse equations and
   sample schedule, readout and performance
   denominator, after independent source
   validation and user review. Train/validation
   sets may be used to develop the converter,
   but the official MNIST test labels must
   remain sealed until the contract is accepted.
5. [OPEN] Run independently reproduced source
   model as the software baseline, then its
   versioned fixed-point/mapped hardware twin
   with first-mismatch trace diagnostics. Only
   P07 can call hardware MNIST accuracy/latency
   measured after physical KV260 evaluation.

**Recommendation at this point: prioritize Rao et
al.'s paper because the actual pretrained synaptic
arrays exist. Do NOT mark P06 complete or freeze
the network until the two-compartment compatibility
gap and paper/checkpoint metric association are
resolved.**
