# P06 Track A — Sealed official MNIST test and physical evaluation protocol

**Frozen date:** 2026-10-17. **Do not open/download the official test partition
until the P07-A board application and its independent functional gates pass.**

## Immutable study unit

This is the **project-trained**, Loihi-1-inspired compact Track A model, not
an official Loihi chip, not an exact snnTorch Tutorial 5 implementation, and
not a published MNIST checkpoint. Its checkpoint, signed integer weights,
encoder and P03 word-stream hashes are pinned in
`P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`.

- Raw row-major 28×28 unsigned-byte image; **no normalization, augmentation
  or analog-current reinterpretation**.
- Input events at logical timesteps t=0..24:
  s=(t+17*i)%25; pixel i fires if
  floor((s+1)*pixel_i/255)>floor(s*pixel_i/255).
  t=25 has NO new external input and drains prior-tick hidden routes.
- Same-core hidden→output packets are consumed at **t+1**, not t.
  Last-tick hidden emission is **discarded** before the next image.
- Signed-24 saturating LIF, exact P03 numerical order. Hidden parameters
  current_decay=4096, voltage_decay=4096, threshold=32, bias/reset/
  refractory=0; output parameters same decays, threshold=8, others=0.
- Completely reset all current, voltage, refractory, output counts, and
  current/NEXT event banks for each image. Process exactly **26 ticks**.
- Readout: sum the 10 output neuron spike counts over all 26 ticks;
  choose argmax, resolving ties to lowest class index. All zero counts
  classify as digit 0, and silent proportion must be reported.

## Sealed official test population

**Primary prespecified evaluation:** the entire canonical 10,000-image
MNIST **test** partition, in original IDX order, with one predeclared
prediction per image. Do not select checkpoints, optimize hyperparameters,
adjust model numerics, or choose a preferred population after reading
test labels/predictions. Official training/validation data and official
test records must never be mixed. Record SHA256/MD5 for the actual
test IDX archives and decoded contents when first unsealed.

**Unsealing gate:** only once (1) P06-A4 frozen source artifact identities
and host static DDR-image audit are accepted, (2) P07-A's 784-axon
input-streaming ABI is independently validated without the test set,
(3) first-mismatch board-vs-host diagnostic frame traces pass with
known/synthetic + frozen validation fixtures, and (4) the chosen
computation/measurement boundaries and software hashes are recorded.

**If 10,000 physical evaluations cannot be performed:** STOP and freeze
a *separate* reduced-population protocol and deterministic image-ID
selection **before** opening test data, running inference, or seeing
test-label scores. Report evaluated denominator, selection rule, reason
for reduction and interval/uncertainty. Never describe a reduced sample
as a 10,000-example full-test accuracy.

## Scoring and reporting

For each evaluated image, preserve immutable image index, source image
SHA256 or dataset manifest link, predicted class, 10 spike counts,
silent/tie flags, software/PL/PS versions, core-record SHA256 and
execution/IO status. Align predictions with ground-truth labels only
after selection/model/run protocol is frozen. Count all attempted
images; errors/timeouts are reported rather than silently removed.
Calculate top-1 count/denominator accuracy, per-class counts and recall,
confusion matrix and all-silent rate. Distinguish `host oracle accuracy`,
`PS+PL complete board prediction accuracy` and any diagnostic partial
sample. Report exact first mismatch if PS/PL differs from frozen host.

Latency/energy in P08-A must include explicitly defined A53 dispatcher,
AXI/input encoding, context load, 26 barriers, result retrieval and
measurement wall-clock boundaries. Separate idle and active power and
do not present KV260 board measurements as original Loihi silicon.

## Hard research boundaries

- P05's accepted diagnostic ABI permits **one** external registered
  input axon per logical core; it is not a deployable 784-input MNIST
  driver. P07 must introduce a separately versioned, fail-closed
  many-axon streaming path with its own regressions.
- A 512KiB static DDR context record from P02.1 is a **valid initial
  core-memory image only**, not an A53 executable, input streamer, or
  complete P05 diagnostic packet containing 26-tick ingress.
- The currently accepted host validation figure **94.39%** is measured
  on held-out train-derived validation samples, NOT the sealed official
  test set and NOT the KV260.
- The larger 784→1000→10 Track B implementation does not start until
  the Track A P08-A physical baseline is accepted.
