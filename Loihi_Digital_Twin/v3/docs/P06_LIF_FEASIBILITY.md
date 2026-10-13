# P06 LIF MNIST feasibility: a bounded hardware-first candidate

**Status: DEVELOPMENT / NATIVE HARDWARE-IMAGE PROBE IMPLEMENTED,
INDEPENDENT HOST VERIFICATION PENDING; NO PAPER NETWORK OR TRAINED
WEIGHTS FROZEN; NO MNIST ACCURACY/BOARD MEASUREMENT.**

**Branch** `agent/v3-p06-lif-feasibility` forked from
`agent/v3-p06-benchmark-audit`, which contains the independent Rao
source investigation. Frozen P02/P03/P05 remain untouched.
Source-identity lessons from Rao remain in docs even if we pivot.

## Legitimate external published foundation — and what is not published

- **J. K. Eshraghian et al., 2023**, *Training Spiking Neural
  Networks Using Lessons From Deep Learning*, Proceedings of the
  IEEE, 111(9):1016–1054, DOI
  https://doi.org/10.1109/JPROC.2023.3308088 .
  This is a **tutorial/review/architectural methodology** source,
  **not** a paper reporting a uniquely identifiable pretrained
  784→32→10 checkpoint to reproduce on Loihi.
- Source-linked author [snnTorch Tutorial 5](https://snntorch.readthedocs.io/en/stable/tutorials/tutorial_5.html)
  gives an actual MNIST model: **784→1000→10** with
  **25 steps**, `beta=0.95`, two `nn.Linear` layers
  (including learned biases) and two `snn.Leaky` stages.
  Crucially, Tutorial 5 uses the *unchanged normalized
  analog pixels as continuous first-layer input at
  each timestep*. It is **not** using Poisson
  input event encoding in its network forward.
  Class is selected via **argmax of 10 accumulated
  output spike counts**. Training uses BPTT/surrogate
  gradient and an Adam optimizer; the tutorial is
  not a released trained-weight artifact for P06.
- Source-linked [snnTorch Tutorial 1](https://snntorch.readthedocs.io/en/latest/tutorials/tutorial_1.html)
  separately describes Bernoulli/rate-coded
  image-to-event conversion with `spikegen.rate`.
  It is **different from Tutorial 5's actual input
  contract**. This distinction must not be hidden.
- `snn.Leaky` uses floating-point state
  and by default **subtract-threshold reset**
  (`reset_mechanism="subtract"`, `reset_delay=True`),
  whereas P03 immediately **hard-resets to
  reset_voltage** on `voltage > threshold`,
  rounds fixed-point decay away from zero and
  applies signed 24-bit saturation.
  Setting beta=0.95 in both does NOT prove
  bit-for-bit equivalence.
- The original source tutorial model has **784×1000
  + 1000×10 = 794,000 possible dense weight
  entries**, compared to at most **32,768 packed
  synapses** per existing logical FPGA context;
  existing P05 provisioned five full DDR
  records (5×32768=163,840 physical entries).
  **One source-unchanged dense 1000-unit
  checkpoint cannot be mapped unchanged**
  in that five-record profile without
  substantially extending the architecture,
  external banking or special lossless
  compression. Nothing in this paper gives
  an accepted smaller 32-neuron checkpoint.

## Project-defined *exploratory* candidate

A bounded, one-context proof-of-structural-fit:
`784 image input ports → 32 LIF hidden → 10
LIF outputs` and **25 event-driven image
steps plus 1 final NEXT-bank drain**. This
is explicitly a **PROJECT-RESIZED MODEL**
inspired by the published LIF training
method; **not the original published
784→1000→10 model** and currently no
trained weights exist for it.

The v3 core configuration uses one
`CompartmentConfig` per neuron:
`current_decay=4096` (current consumed in
the current tick), `voltage_decay=205`
(fixed-point nominal voltage multiplier
`1-205/4096≈0.94995`), `threshold=2048`,
`reset_voltage=0`, `refractory_ticks=0`
for **synthetic compiler testing only**.
No conversion from snnTorch to those
integer values has been scientifically
accepted; preserving learned logits and
accuracy requires training against
this exact FPGA numerical contract.

The test-only fully dense positive signed
integer weights are deterministically
generated and intentionally give each
pixel source a distinct connection pattern
so the actual HLS image cannot pass by
collapsing 25k identical synapse rows.
**These are not trained weights and carry
no MNIST accuracy claim.**

### Exact resource arithmetic from existing v3 hardware spec

| Quantity | One-core project test profile | Actual P03/P05 limit |
|---|---:|---:|
| Pixel input ports / maximum external spikes per tick | 784 | 4,096 per core / 4,096 per event bank |
| LIF hidden + output compartments | 32+10=42 | 1,024 per core |
| Dense pixel→hidden synapse entries | 784×32 = 25,088 | — |
| Dense hidden→output entries | 32×10 = 320 | — |
| **Total hardware synapse entries** | **25,408** | **32,768 per core** |
| Input+hidden destination axons (1 each) | 784+32=816 | 4,096 per core |
| Hidden source output route words | 32 | 4,096 per core |
| Worst-case current event bank, including prior hidden packets | 784+32=816 | 4,096 |
| 25-step raw all-pixel event maximum | 25×784=19,600 | board-local event stream provision needed |
| Extra output drain timestep | 1 | 26 actual algorithmic steps/sample total |

The **same existing** `compiler.compile_network`,
`LogicalCoreConfig`, `hardware_p03.export_one_core_image`
and 512KiB DDR bank metadata define the authoritative
resource check. The actual programmatic single-core
image is created by
`scripts/p06_lif_compiler_probe.py`;
not by hand-built fake MMIO or a new hardware
format. The probe refuses to assert success
unless its HLS image contains **exactly
25,408 synapse words, 816 allocated
destination axons, 32 route words and 42
compartments**. The compiler's more
conservative 128KiB logical template cost
must also pass. Unlike the source tutorial,
this should fit the one physical 32,768
bank *if the native test passes*. No
KV260 bitstream/run has tested it yet.

### Scaling contingency (before test data, not post hoc)

The one-core 32-unit probe is the **minimum
structural demonstration**, not a promise
of competitive MNIST accuracy. A dense
`784→64→10` network has
`784×64 + 64×10 = 50,816`
source synapses, which **does not fit
one existing 32,768-entry HLS synapse
bank**. It might fit in **two distinct
destination-partitioned logical contexts**
if the P06 mapper, route barrier
schedule and repeated external
input fanout are extended and verified.
The existing deterministic mapper
assigns compartments first, then
validates synapse resources; it does
**not** automatically partition a
single population based on synapse
overflow, so a one-core 64-hidden
dense attempt is expected to fail
closed rather than become a valid
two-core deployment.

A 64-, 128-, or sparse variant
must be **selected based only on
training/validation and documented
hardware feasibility**, not on
the sealed 10,000-image test
performance. A 32-unit classifier
may have materially lower accuracy
than the author's 1000-unit
tutorial and should not inherit
its published learning/result
claims.

**External sample storage planning:**
one raw 28×28 8-bit image is 784
bytes, so all 10,000 official test
images require **7,840,000 bytes**
of board DDR input storage, excluding
metadata; a full worst-case
pre-expanded 25-step stream is
19,600 one-event words per image
(78,400 bytes if packed as 4-byte
axon events). It is more practical
to provision raw image bytes once
and generate deterministic 784-port
events in the autonomous A53 per
time step. This has NOT been
built or benchmarked.

### Project-only input encoding and scheduler design

`scripts/p06_lif_input_probe.py` implements an
**exploratory deterministic quota code** from
each original unsigned 8-bit pixel `p` to
`floor(25p/255)` spikes distributed across
25 steps, with a reproducible pixel-index
phase offset. This is neither snnTorch
Tutorial 5's **analog** input nor Tutorial
1's **stochastic Bernoulli** input.
There is no hidden randomness or
use of MNIST labels. An alternate exact
`spikegen.rate` bitstream generator is also
possible, but its Torch PRNG algorithm,
seed, pixel scaling, training
semantics and encoded test-byte hash would
have to be frozen before comparing accuracy.

The 26th tick is an **empty external input
drain** because P05 physically routes a
hidden neuron spike into the NEXT event bank,
even when destination readout is on the
same logical core. Tutorial 5's software
forward processes both linear layers in one
step. **That timing difference cannot be
hidden**; our future software trainer must
use the chip's one-step edge delay, or
we need a separately accepted new
zero-delay intra-core compute path.
The candidate currently chooses to **train
to the P05-timed graph**, not to represent
it as Tutorial 5's exact forward.

Source labels determine only training/validation
loss; the project sample input stream may be
pre-encoded and placed in DDR once by the PC,
then scheduled by the **A53 without PC
per-timestep instructions**. A53 also must
zero neural state, event banks and output
count registers per sample, invoke 26 steps,
emit 10 spike counts and an argmax
classification with documented first-index
tie rule, and preserve provenance.

No physical A53 image streaming implementation
exists for this feasibility branch. These
are P06.2/P06.4 engineering requirements,
not claimed PASS items.

## Main residual feasibility blockers

1. **Original trained checkpoint/provenance.**
   Our 32-hidden network is a changed model;
   no paper claims its accuracy, and it has
   not been trained. We must either train
   and freeze a project checkpoint *before*
   official MNIST testing (source-inspired
   **new model** rather than exact paper
   model) or select a paper with exactly
   released 32-hidden LIF weights.
2. **Behavior parity.** snnTorch defaults to
   floating-point subtract reset and can
   apply hidden→output in the same source
   step. The accepted FPGA uses integer
   hard reset, 24-bit saturation, discrete
   decay rounding, strict `>` threshold
   and NEXT-bank routed edges. Need a
   differentiable FPGA-equivalent training
   forward (custom surrogate gradient),
   then an **independent nontraining
   integer software reference** and
   first-mismatch traces. Do not use
   post-test accuracy tuning.
3. **Board autonomy.** P05 validated
   dynamic state/route/cross-DDR traffic
   and external event boundary cases,
   but **not** board-local 784-input
   MNIST sequences across 10,000
   samples. New A53 streamed input
   scheduler, DDR sample reader and
   per-image reset are still mandatory.
4. **Exact score/performance scope.**
   Only trained model's own sealed
   10,000-image accuracy is valid;
   no published 1000-hidden accuracy
   or Loihi chip energy may be silently
   assigned. P07/P08 must measure CPU
   and KV260 inference independently
   using declared batch/input boundaries.
5. **Dataset governance.** Pin original
   MNIST canonical train/test hashes,
   reserve a validation split from
   training only, publish all training
   seeds and package versions, freeze
   checkpoint, integer quantization,
   encoding, model time and readout
   **before official test**.

## Decision gate

**GO for a one-core, single-compartment
structural prototype, conditional on the
independent native actual-compiler gate.**
This is significantly lower hardware
scope than extending the P05 HLS model
to Rao's AHP, and the small graph fits
the nominal existing bank/event limits.

**HOLD for claiming published-model
reproduction.** This exact
784→32→10 checkpoint is not from the
published snnTorch tutorial. A legitimate
thesis claim is *published LIF
methodology + project-frozen,
independently trained checkpoint
implemented on KV260 and compared
against its exact software twin*.
If the original P06 no-guesswork
requirement means **identical published
weights and published accuracy**, this
project choice alone does **not**
satisfy it.

P06.1 native feasibility and the user's
benchmark-scope decision should precede
P06.2 modeling/training. No original
P05 acceptance artifact was changed.
