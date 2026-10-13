# P06.2 preliminary gap analysis — paper-linked AHP-LSNN vs P05 KV260

**Status: PLANNING ONLY — NO FPGA/C/Python GOLDEN PATCH,
NO MAP, NO NEURAL BENCHMARK FREEZE, NO TIMING CLAIM.**

Target under consideration:
[Rao et al. 2022 sMNIST LSNN](P06_1_PAPER_CANDIDATE_AUDIT.md),
author-published 80-input/140-regular/100-AHP/10-readout
network with immutable source-trained matrices. This is
**sequential MNIST (784 pixel steps + cue)**, not a
one-step 28×28 image feedforward inference.

### Paper source versus accepted P05 hardware contract

| Requirement | Rao source contract | Accepted P05 status | Next evidence required |
|---|---|---|---|
| Per-sample input | 784 ordered 8-bit pixel values; 38 onset and 38 offset threshold streams, one pixel==255 touch and one 56-step cue stream (80 total declared input ports, 2 unused) | P05 input descriptor currently registers **one external axon per core**, not arbitrary 80-source spike trains | Freeze exact SNIP threshold algorithm and build a separate versioned variable-axon input descriptor; prove sample sequencing/reset, full 10k comparison uses no per-sample host scheduler |
| Recurrent neuron state | 140 regular and 100 AHP adaptive recurrent units | P05 computes independent Loihi-like 1-compartment current/voltage/refractory primitives | Implement independently tested source-equivalent auxiliary AHP compartment, coupling and two-state update order, or find another paper |
| Synapse weights | **actual official w_in / w_rec / w_out .npy bytes** (80×240, 240×240, 240×10) | P05 packed signed synapses with hardware 24-bit weight; not necessarily Loihi native 8-bit quantization/shift/saturation | Determine original array dtypes/ranges, Loihi weight exponent/effective shifts and actual per-connection delay, then fail-closed transform with bit-exact trace parity |
| Dense fan-in | 80 input and 240 recurrent source neurons converge onto 240 recurrent targets | 4096 input axons and up to 32768 packed synapse slots per logical context, 1024 compartments per core; P05 models explicit axon→synapse list | Partition by **destination compartment**, preserve all 79,200 source weight entries and recurrent route fanout; no unmeasured dropped connections |
| Source-route multicast | recurrent spikes must reach targets in multiple logical shards and output integration | P05 physically accepted resident/nonresident fanout, NEXT banks and 16 barriers | Verify source/target mapping maintains original multi-shard delay; avoid per-source route list overflow and hidden per-step spikes |
| Readout | 10 Loihi output compartments set to **non-spiking** integrated potential; classification through author SNIP/readout | P05 neuron test checkpoints state0 and packet banks only | Recreate exact 56-step cue/readout integration and strict `>` first-winner tie behavior; all ten minimum signed V values must preserve source sentinel `-1` (unclassified), never be coerced to digit 0; no output spike-count substitution |
| Timing/power | measured **Loihi 1 sMNIST** on its original Loihi board; single-image latency/EDP method paper-specific | P05 raw PS timer and PL cycle counters; no power/energy calibration | Freeze included/excluded time, workload/batching, supply rails and scope; P07/P08 only compare like with like |
| Test data | source uses OpenML `mnist_784`, rows 60k–70k and demo samples 100 with seed0 | No application loader/protected dataset freeze yet | Pin dataset origin, byte digest, conversion, labels and single evaluation universe before looking at official test accuracy |

### Minimum hypothetical mapping (NOT validated)

Recurrent dense weights require
`240×240 + 80×240 = 76,800` individual
input/recurrent entries. The accepted backing
schema provides 32,768 × 8-byte synapse records
per logical 512KiB core. At least
`ceil(76,800 / 32,768)=3` logical target-core
shards are needed, **assuming NO deduplication**.
A first design exploration might use **three
recurrent shards of 80 primary neurons each**:
`80×(240+80)=25,600` per shard, plus their
adaptive auxiliary state and any extra coupling
connections. Separate output readout requires
another `240×10=2400` connections. These
figures are a **resource lower-bound estimate**,
not a proven legal Loihi 1 or P03 hardware image.
Each core's actual axon/route/synapse descriptors,
128KiB Loihi logical budget, physical bank
occupancy and dirty-paging costs must be
counted independently with the real exporter.
No claim of 3-core mapping or performance yet.

### Most significant scientific risk

AHP is **not** merely a different voltage decay
constant. It is a second dynamical compartment
that slowly stores spike history and feeds
the soma to permit long-term memory. Replacing
it with the already supported refractory bit
or a scalar LIF would change model behavior,
classification accuracy and meaning of a
Loihi comparison. This needs either (a) an
explicit independently validated architectural
extension, with a backwards-compatible
P05 standard mode, or (b) rejection of the
candidate in favor of a simpler reproducible
published model. Do not patch accepted v2/v3
goldens to force an approximate output match.

### Proposed P06 sequence and hold points

**P06.1 — Paper/weight source audit:** Verify immutable
paper/source code snapshot and source `.npy` shapes,
dtypes and matrix digests using stdlib-only audit.
Associate exact paper's claimed metric to that
specific model and Loihi configuration. **HOLD**:
do not declare it identical until citation supports it.

**P06.2 — Source-informed equivalence contract:**
Extract source SNIP encoder, neuron/weight/mapping
prototypes, update order, readout, reset, delays
and application scheduling. Design backwards-
compatible AHP/multi-axon extension on a **new
submilestone branch** if warranted. Accept model
equivalence tests **before running official test**.

**P06.3 — Immutable benchmark freeze:** One source
commit plus SHA of all three weight blobs, byte
digest of a canonical MNIST training/test snapshot,
input-pixel sequence and threshold algorithm, full
fixed-point graph/decay/delay, readout rule,
original Loihi metric denominator, accepted
hardware mapping and trace parity report. Lock
train/development/test boundaries; prohibit
test-driven tuning.

**P06.4 — Offline conversion/acceptance package:**
Deterministically pack checked source weights,
quantization, routing/context records, sample
descriptor and independent software reference;
native negative capacity tests, first-mismatch
diagnostics, regression preserving P05. No
KV260 MNIST performance claim before P07.
Closure requires audited viable implementation,
not merely a named publication or header-only
data inventory.

**Decision gate:** Do **NOT** select/freeze
the source model until we establish the AHP
extension is feasible and source-to-FPGA
bit-exactness is independently tested. If the
cost is unacceptable, prefer a paper with
published trained weights and a compatible
single-compartment model rather than invent
a substitute network. The user can approve
that fork once model compatibility is evaluated.
