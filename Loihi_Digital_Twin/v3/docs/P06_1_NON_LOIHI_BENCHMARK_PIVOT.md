# P06.1 — Evaluating a published MNIST SNN not originally run on Loihi

> **Subsequent project decision (2026-10-12):** This file preserves
> the earlier candidate research; it is **not** the active milestone
> decision record. The user selected **snnTorch-inspired,
> project-trained LIF** on the KV260, to be implemented **compact
> 784→32→10 first**, then **scaled 784→1000→10 only after the
> compact physical baseline**. Track A's synthetic native
> compiler/HLS-image feasibility gate passed on the user's host;
> no trained checkpoint, official MNIST accuracy or KV260 application
> pass exists yet. See [authoritative two-track plan](P06_TWO_TRACK_LIF_PLAN.md)
> and the [roadmap](../LOIHI_TWIN_ROADMAP.md). Rao and Diehl/Cook
> remain historical alternatives, **not parallel blockers**.


**Status: RESEARCH-ONLY OPTION REVIEW — NOT AN ACCEPTED BENCHMARK
SELECTION.** User asked whether a published non-Loihi model would
be a better target for the KV260 Loihi-1-inspired digital twin.
NxTF remains excluded. Does not change accepted P05 design or paper
selection; does not use MNIST official test results for tuning.

## Answer: scientifically legitimate and potentially a better thesis

**Yes.** The reconstructed classifier is an **application workload**
for a neuromorphic processor, not a required Loihi native software
binary. Training the network on a CPU/GPU (or taking a published
single-compartment SNN) and faithfully mapping it to the Loihi-like
digital twin can demonstrate architecture portability, actual
routing/event processing, inference correctness, and hardware
costs. In this path, the published paper provides the
**network design, checkpoint and accuracy reference**; our thesis
provides the **KV260 implementation and measurements**.

However, it changes what can legitimately be compared:
- **Directly comparable after a frozen protocol:** same MNIST split,
  *same checkpoint*, *same image-to-spike encoding*, time steps,
  network dynamics/quantization with separately verified traces,
  readout, prediction vector and accuracy measured on software
  baseline vs KV260.
- **Platform-only comparisons:** whole inference runtime,
  throughput, board/SOM energy versus **our own comparable**
  CPU/GPU host baseline, with clearly defined endpoints.
- **Not automatically comparable:** Loihi original-chip energy
  or power, if the source paper never ran on Loihi; do not
  invent a Loihi reference or call generic SNN simulation
  energy a measured neuromorphic hardware result.
  If a source paper published only CPU/GPU latency,
  exact hardware/batch scope must match before calling
  it an apples-to-apples benchmark.

A particularly credible central claim would be:
"A deterministic published MNIST SNN with pinned checkpoint
and source-level inference semantics was mapped to a Loihi-like
KV260 FPGA digital twin and verified end-to-end against
an independently reproduced software reference, including
logical core paging/traffic and measured inference
time/power. We do **not** claim original Loihi native
binary compatibility or its published silicon performance."

## Candidate 1 — original non-Loihi paper + author pretrained weights

**Peter U. Diehl & Matthew Cook (2015)**,
*Unsupervised learning of digit recognition using
spike-timing-dependent plasticity*, Frontiers in
Computational Neuroscience 9:99,
DOI https://doi.org/10.3389/fncom.2015.00099.
Open-access paper:
https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2015.00099/full

**Official paper-linked authors' original repository**
(not a later third-party port):
https://github.com/peter-u-diehl/stdp-mnist
contains actual pretrained
`weights/XeAe.npy` and `weights/theta_A.npy`,
along with original `Diehl&Cook_spiking_MNIST.py`
and evaluation script. Those files are
**source assets**, not an accuracy/metric match
until source/evaluation is independently run.

Original `readme.txt` says the default
test mode uses pretrained weights and yields
approximately **91.56%** in the included
quick evaluation. **Critical methodological
warning from that same author README**:
the demo assigns neuron digit labels using
**the test set**. That contaminates an
unbiased final-test comparison. Authors say
the *paper's* reported tests instead derive
digit assignments from **60,000 training images**.
We MUST reproduce the clean assignment procedure
with fixed training labels and seal test data,
not quote the demo's 91.56% as the paper's
uncontaminated classification accuracy.

**Hardware concerns:** Original paper's
400-excitatory-neuron implementation has
a full `784×400=313,600` input→excitatory
weight array before inhibitory connectivity,
adaptive thresholds, Poisson spikes,
duration, winner-take-all inhibition and
repeated stimulus/rest intervals. This exceeds
the current P05 **32,768 synapse slots per
logical context** by at least a factor 9.6
and requires partitioned mapping/paging.
The 400 excitatory + 400 inhibitory units
fit the global 1,024 compartment count only
if connectivity/resources can be mapped;
there are additional homeostasis and reset
dynamics not already tested in P05. Inference
probably does not need on-chip STDP update,
but **trained theta and inhibitory/readout
behavior still matter**. No claim that this
is *easy* compared to Rao merely because it
wasn't originally run on Loihi.

**Status:** REAL primary-source/paper with
pretrained weights, strong next candidate
for P06 *if* we want a classic SNN without
Loihi-specific two-compartment AHP; however,
the mapping is much larger and its
test-label-leakage pitfall requires care.
No Diehl source-file binary hashes,
readout trace parity or actual accuracy
audited by this project yet.

## Candidate 2 — simple surrogate-gradient LIF architecture

**Eshraghian et al. (2023)**,
*Training Spiking Neural Networks Using
Lessons From Deep Learning*, Proceedings
of the IEEE, 111(9):1016–1054, DOI:
https://doi.org/10.1109/JPROC.2023.3308088
(confirmed from the IEEE Xplore publisher
entry and Proceedings of the IEEE issue). Associated maintained
training library and published MNIST
LIF/classification examples:
https://github.com/jeshraghian/snntorch
and
https://github.com/snntorch/Spiking-Neural-Networks-Tutorials .

This is attractive for a **new, transparently
retrained model**, because source/tutorial
plain LIF dynamics resemble P05, training
can be offboard, a smaller version may
avoid complex AHP, and inputs can be
versioned as deterministic spike traces.

**Critical non-equivalence:** A tutorial
checkpoint retrained by us is **NOT the
original authors' measured trained network**.
The inspected official tutorials are a
reproducible training *recipe*, not verified
released pretrained checkpoint hashes
corresponding to one particular published
accuracy number. We may label such a study
a **published architecture independently
trained and replicated on KV260**, with
our own held-out/test accuracy; never
present it as an exact published-score
checkpoint comparison.

**Status:** Practical if the user prioritizes
fast hardware implementation and an honest
CPU/KV260 comparison; **not yet eligible
for the original P06 direct same-checkpoint
paper-accuracy criterion** without author
checkpoint proof.

## Candidate 3 — Rao's Loihi-1 AHP LSNN (current provisional)

[Existing Rao decision ledger](P06_1_PAPER_METRIC_AUDIT_AND_DECISION.md).
The original Intel source checkpoint is
indeed real. **Fixed author-file shape
audit on 2026-10-12/13:** the public `.npy`
files are stored pre×post
`(80,240), (240,240), (240,10)` and
the author's `loadWeightsAndDelays()`
returns `(wIn.T, wRec.T, wOut.T)`.
All are `<f4` matrices, integral-valued
source coefficients in `[-254,255]`,
with measured nonzero counts
`4263 + 10566 + 846 = 15675` of 79,200
(**19.79%**), consistent with the
paper's approximately 20% density.

**Pros:** tiny sparse network may fit one
logical 32,768-entry synapse bank (actual
mapped entries TBD), Loihi-1-relevant
native topology, exact frozen source I/O
and actual trained matrices.
**Cons:** 100 AHP auxiliary compartments,
input SNIP stream, per-image resets,
nontrivial Loihi native parameter scales,
old proprietary NxSDK and unverified
association of released `v25_94per`
weights with paper's reported **96%**.

## Recommendation / project decision

**For P06's original target ("no guesswork",
exact published checkpoint and score),
do not freeze *any* of these yet.**
There are two valid thesis strategies,
and they answer different scientific
questions.

**Strategy A — faithful published network
regardless of original platform:**
Prefer a small SNN whose *actual author
weights + parameter code + evaluation
protocol* are source-verifiably tied to
its published results. Validate exact
reconstructed predictions before mapping
to FPGA. This is the strongest way to
compare **algorithmic accuracy**. Compare
FPGA energy/latency to our own measured
CPU/GPU baseline, not a nonexistent
original Loihi chip metric. Check
Diehl/Cook author snapshot critically.

**Strategy B — practical architecture
demonstrator with independently trained
published LIF design:** Train with
fixed seed/parameter freeze on MNIST
train/validation only, export actual
weights, freeze them, then prove CPU
software vs KV260 predictions and measure
throughput/energy. This is a robust
*architecture demonstration* but NOT
a reconstruction of a published set
of trained weights or a comparison to
published original-chip energy.

**For the KV260 development effort:
a simple published single-compartment
feedforward LIF network, with genuine
released author checkpoints if they
exist, is preferable to Rao's Loihi-
specific AHP extension *if* it is small
enough to map without large DDR paging
and does not require inventing arithmetic
or trained parameters.* Diehl/Cook
deserves a measured feasibility gate but
is not automatically that easy network.*

No official-test MNIST score, alternate
trained artifacts or new hardware
submilestone is accepted in this review.
User decision is required before changing
the P06 paper target or splitting the
hardware scope.
