# P06.1 — Original publication metric, checkpoint attribution and GO/NO-GO review

**Status:** Original paper + supplementary benchmark audit COMPLETE; first
native P06.1 regression user-confirmed PASS after the strict-argmax sentinel
correction. **The separate real author-source/weights SHA/dtype/sparsity
audit is still awaiting user execution.** The Rao model is a
**PROVISIONAL candidate, not a frozen benchmark**. No official MNIST
test set was run and no KV260 classifier accuracy/energy was measured.

## Primary sources and the exact claim boundary

1. **Paper:** Rao, Plank, Wild and Maass (2022),
   *A Long Short-Term Memory for AI Applications in Spike-based
   Neuromorphic Hardware*, *Nature Machine Intelligence* 4:467–479,
   DOI https://doi.org/10.1038/s42256-022-00480-w.
   Author-hosted article **including supplementary information**:
   https://igi-web.tugraz.at/PDF/259maass.pdf
   (paper pages 3–4 / PDF physical pages 3–4; Methods PDF
   pp. 12–14; supplement Table S1 PDF p. 19).
2. **Paper-linked released code**:
   https://github.com/intel-nrc-ecosystem/models/tree/3dc53bfcfae1efe8772b8cb5e2c512bb28c872f8/nxsdk_modules_ncl/lsnn
   (pinned author-linked Intel Git commit
   `3dc53bfcfae1efe8772b8cb5e2c512bb28c872f8`).
   This snapshot publishes `v25_94per/w_in.npy`,
   `w_rec.npy` and `w_out.npy`; their official git
   blob identities, shapes and byte sizes are in
   `P06_1_LSNN_SOURCE_MANIFEST.json`.

### Verbatim publication observations (not our FPGA measurements)

| Attribute | What the paper actually claims | Source |
|---|---|---|
| Task | Sequential MNIST, 28×28 pixels presented as a sequence | Paper §sMNIST and Methods |
| Loihi model test accuracy | **96.0%** for the study's measured SNN on Loihi | Main manuscript Results, Fig. 2 discussion |
| Recurrent model | 240 neurons, **180 excitatory / 60 inhibitory**, **100** randomly selected excitatory units equipped with AHP; the remaining 140 use conventional dynamics | Methods: Network structure |
| Sparsity | **20% overall** potential input/recurrent/output connections, via DEEP-R rewiring | Methods: Network structure |
| Original model training dynamics | baseline threshold 127, τV=20, τadap=700, 1-step refractory/delay, AHP β=96 **in manuscript's own convention** | Methods: Network structure |
| Published source time budget | 784 pixel steps + 56 cue = **840 algorithmic steps** (one Loihi timestep corresponds to 1 ms of modeled time) | Methods: sMNIST input |
| Loihi published runtime | **14.11 ms wall-clock per inference**, averaged at the author's measurement boundary | Supplement Table S1 |
| Loihi wall-clock per timestep | **16.79 microseconds**, as reported by Table S1 | Supplement Table S1 |
| Loihi power | 0.59 mW static; 25.24 mW dynamic; 25.83 mW total; includes on-chip x86/neuronal contributions in authors' reporting | Supplement Table S1 |
| Loihi total energy | **~0.36 mJ per inference** in Table S1; quoted Loihi chip-level energy/power scope, not KV260 board telemetry | Supplement Table S1 |
| Benchmark platform | Nahuku board, `NxSDK 0.95`; CPU and GPU comparators have separate machines | Supplement Table S1 footnotes |
| Timing protocol | `timeit` Python-level wall clock / samples; power measured separately in steady state | Supplement §S1.1 |
| Loihi spatial placement | Paper says this small network occupies **one or two Loihi neuro-cores** depending on structure | Main Results discussion |

**Important units:** The 840 steps refer to **algorithmic
simulation time** under a 1 ms/step convention, *not*
840 ms of physically measured Loihi computation.
The published **14.11 ms** is the separate wall-clock
latency. Do not conflate these for our KV260 timing.

**Published manuscript β=96** is not a contradiction we
can resolve by fiat with released `src/lsnn.py`
`_beta=1390000`: the source's extra auxiliary compartment
and synapse exponent implement a different internal
fixed-point scaling of AHP. Their effective equivalence
must be proved from the exact Loihi state mapping, not
by setting the FPGA AHP coefficient to 96 or 1390000
arbitrarily.

### The critical missing source-to-result link

**Git provenance nuance:** GitHub history for the specific
`w_in.npy` and `seq_mnist.py` files shows
a generic `Add files via upload` commit
`fc1726700bead6a3f8e8b7be8668d4e34d2c9f46`
dated **2021-08-07**. This confirms the source
assets were publicly uploaded after the
**2021-07-08** arXiv v1 submission, but the
commit has no experimental identity/accuracy
metadata and **does not prove they correspond
to the journal's 96.0% Loihi experiment**.

The paper's code-availability section links the Intel
`models` repository and `lsnn` module at a **mutable**
branch name, not a unique training checkpoint hash.
The currently published selected source example
`seq_mnist.py` calls the **`v25_94per`** model.
The folder name is only a label; it is **NOT**
evidence of either 94%, 96%, or any test accuracy.
No inspected paper text, supplement, or linked code
establishes that these particular three weight
blob SHAs were the model that produced **96.0%**.
The example additionally runs a *seed-0 subset of
100 test images*, which is not automatically the
paper's published evaluation population.

**Consequently: never describe this released
checkpoint as the original 96.0% paper
checkpoint without further author-level evidence.**
The correct frozen comparison (if pursued) must
first evaluate the **unaltered published-source
weights** with the source-faithful Loihi oracle
and separately report their own measured
accuracy, alongside the paper's 96.0% as
a *publication context result*. No silent
tuning to match the paper is acceptable.

### Source-code versus methods-level descriptions

The author's manuscript describes 80 input
neurons and its Supplement Listing S1 uses
inclusive comparisons (`<=`, `>=`).
The actual pinned Loihi source
`apps/seqmnist/snips/spiking.c` is **more
specific and not textually identical**: it
uses **38** paired onset/offset threshold
indices 1..38 with **strict** `<`/
`>=` transitions, a current-pixel
equal-to-255 touch event on port 78,
port 79's **56-step cue**, and no
onset/offset at the last pixel.
The source `snip_mgmt.c` uses a strict
10-way membrane-voltage `>` selection
and returns `-1` if all V equal the
minimum signed-24-bit value.
Its end-of-image management routine
**clears the Loihi compartment state,
compartment metadata and dendritic
accumulators** before the next image.

For **the released checkpoint**, the pinned
executable source is the most specific
reconstruction contract; preserve the
paper/source discrepancies explicitly.
Do not claim the source's threshold
encoding necessarily matches every
published experimental checkpoint.

### FPGA compatibility: changed by the 20% sparsity finding

The released matrix files store **79,200
potential coefficients** (80×240 + 240×240
+ 240×10). That is not the hardware's
actual nonzero synapse count: the
paper specifies **20% overall connectivity**,
and the Loihi author's source explicitly
uses `connectionMask=(wgts>0)` and
`connectionMask=(wgts<0)` for sparse
synapses. Under 20% connectivity,
the total expected order of magnitude is
**~15,840 nonzero connections**, plus
the 100 AHP main→aux coupling entries.

Our v3 logical context is limited to
**32,768 packed synapse entries/core**
(8-byte entries), 1,024 primitive
compartments/core, 4,096 axons and
4,096 routes. The adaptive implementation
needs **140 + 2×100 + 10 = 350**
internal compartments, plus the 80
host-generated input axons. This suggests
a **single logical context might fit**
the packed bank, **provided the actual
released weight occupancy, axon/route
mapping and hidden adaptation resources
pass the real exporter**. The original
three-core estimate assumed ALL 76,800
input/recurrent matrix positions were
allocated as hardware synapses and
is **NOT a lower bound** for the
paper's sparse trained model.

The hard engineering blockers are therefore
**bit-exact 2-compartment AHP update,
adaptive fixed-point scale, 80 dynamic
spike-input axons, recurrence and per-image
state reset**—not yet established
synapse-bank capacity. A P06.2 P05-safe
compatibility profile and explicit resource
mapper would still be required.

### Decision matrix (user's goal: exact comparative benchmark without guesses)

| Question | Present answer |
|---|---|
| Has an alternative non-NxTF peer-reviewed paper with real Loihi sMNIST accuracy/energy been identified? | **YES** |
| Are author-released pretrained arrays and original Loihi I/O/model code available? | **YES, nine pinned Git objects; local byte/dtype verification PENDING** |
| Are paper's 96% source weights proven identical to released `v25_94per` weights? | **NO, LINK UNVERIFIED** |
| Are actual published weights known to fit our current P05 profile unchanged? | **NO** |
| Is a correct adapter an easy deployment-only Python converter? | **NO — requires AHP/Loihi multi-compartment and source-stream extensions** |
| Could the sparse model plausibly fit the FPGA logical memory budget? | **POSSIBLY, promising; must measure real nonzero occupancy and exporter** |
| Is a fair Loihi-vs-KV260 power/latency comparison possible? | **POSSIBLY after P07/P08 scoped measurement; not established by P05 telemetry** |
| Can the 96.0%/0.36mJ/14.11ms paper results be attributed to the 3 released weight files today? | **NO** |

## P06.1 disposition and recommendation

**Research/document-source audit: DONE.**
**Corrected native source-level I/O and manifest regression:
user independently confirmed PASS.**
**Separate nine-file original pretrained artifact
and literal NPY header audit: PENDING
on the user's host.**
**Chosen paper benchmark freeze: NOT ALLOWED yet.**

**Scientific GO / conditional engineering HOLD.**
This paper is scientifically valuable to a Loihi
digital twin and has real weights, and the paper's
20%-sparse 350-compartment network looks much
more manageable than a fully dense layout.
But it is a **NO-GO right now for claiming an
exact 96%-checkpoint, 14.11ms, 0.36mJ
apples-to-apples reproduction** because checkpoint
identity is unproven, AHP semantics aren't
implemented, and measurement scope differs.

Recommended next gate after the real nine-file
provenance audit: a **short P06.2 feasibility
spike**, not a full AHP/RTL implementation:
(1) inspect actual 3 weight matrices' dtypes,
nonzero density and value range;
(2) build **resource accounting only** using
P05 DDR bank capacities;
(3) extract exact source Loihi auxiliary prototype
and input/reset/readout contracts; and
(4) seek explicit original-checkpoint attribution
from paper/repo or authors. If (4) remains absent,
**do not use this model as a claimed identical
96% baseline**. Either use it as a clearly
qualified independent replication (different
measured accuracy), or switch to a paper with
a demonstrably corresponding public checkpoint.

No official MNIST test accuracy has been
measured, no paper metric has been invented
and `main` is unchanged.
