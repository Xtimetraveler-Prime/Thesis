# P06–P09 — Compact-first, scaled-second LIF MNIST research plan

**Decision:** pursue two **sequential** implementation tracks on the accepted
KV260 Loihi-1-inspired digital twin. **Track A must reach independently
accepted physical correctness and a measured baseline before Track B is
implemented as a hardware benchmark.** The scaled-network *planning* can be
audited during P06, but building its new mapper/runtime and running it on the
board occur only after the compact baseline is secured.

**Status (user-confirmed, 2026-10-12):** The current
`agent/v3-p06-lif-feasibility` 784→32→10 native regression and both
compiler-probe modes passed on the user's machine after fixing the
31-versus-32 synthetic spike assertion. **P06 structural feasibility
for Track A: ACCEPTED.** This acceptance covers *software-compiled*
resource packing and a directed Python golden-model routing test. It
does **not** imply trained accuracy, a final checkpoint, P07 board MNIST
execution, RTL re-synthesis, HLS behavioral equivalence or power results.

## Scientific framing

**Published foundation:** Eshraghian et al. (2023),
*Training Spiking Neural Networks Using Lessons From Deep Learning*
(DOI `10.1109/JPROC.2023.3308088`) and the
[snnTorch MNIST Tutorial 5](https://snntorch.readthedocs.io/en/stable/tutorials/tutorial_5.html).
The tutorial's actual example is 784→1000→10, 25 timesteps, float
`snn.Leaky`, static repeated **analog** pixel currents, default
subtractive reset, same-step software layer propagation and output-spike
readout. **It supplies a training method/example, not an identified
pretrained 32-hidden or 1000-hidden artifact we have reproduced.**

**Project model:** an event-input, deterministic **25-step rate encoder**,
P03's signed 24-bit saturating integer LIF, voltage/current decay and
strict threshold, **reset-to-zero**, and P05's **NEXT-event-bank routing**
of hidden→readout spikes (26 logical steps including the final drain).
Weights will be **trained by the project**, quantized using an
audited protocol and frozen independently per track. The existing
synthetic test-only weights are **not a trained checkpoint**.

**Permitted thesis comparison:** the same frozen *project* model run
through (i) an independent software oracle, (ii) the deterministic
compiler/physical packet ABI, and (iii) the actual KV260; plus a
**compact vs scaled** comparison of model capacity, accuracy,
hardware inference costs, routed traffic and paging when both
are evaluated under the same event/measurement protocol.
Do not claim the project models reproduce the source tutorial's
numerical predictions, published accuracy, original Loihi 1 chip
energy or native on-silicon asynchronous NoC.

The original Rao AHP paper investigation is retained as an
**unselected alternative** in `P06_1_*` documents. The separate
Rao original nine-file binary audit is **not** a blocking
requirement for the chosen LIF tracks; it remains an unfinished
optional archival provenance item unless that model is revived.

## Track A — Compact single-logical-core classifier (REQUIRED FIRST)

**Target:** `784 input axons → 32 hidden LIF → 10 output LIF`,
one logical context, the existing one physical HLS engine.
No new neuron RTL or Loihi AHP support is required in the
initial target.

| Accepted structural probe quantity | Value / gate |
|---|---|
| Actual synthetic compiler/HLS image synapse records | **25,408** / 32,768 physical-bank maximum |
| Compartment configs | **42** / 1,024 |
| Input axon bindings | **816** / 4,096 |
| Hidden output route words | **32** / 4,096 |
| Conservative combined packets at a barrier | **816** / 4,096 event-bank entries |
| V3 logical synapse accounting | **108,160 B** / 131,072 B |
| Simulation/input scheduling | **25** event steps + **1** drain |
| Provenance | Native `test_p06_lif_compiler_probe.py` and `test_p06_lif_input_probe.py` user-confirmed PASS; **no physical FPGA inference yet** |

### P06-A1 — Native structural feasibility [ACCEPTED]

Existing
`scripts/p06_lif_compiler_probe.py`,
`scripts/p06_lif_input_probe.py` and their associated tests
must remain green. The repaired routing test proves 31
*actual* hidden spikes (not 32 configured potential routes)
and 310 following-tick fan-in contributions for a
deterministic test-only stimulus. Negative inputs produce
no invented route traffic. These tests validate the
model/exporter's structural semantics **only**.

### P06-A2 — Freeze the precise *training-time forward contract* [CLOSED / USER-ACCEPTED 2026-10-13]

Write an **independently testable integer oracle** for P03
LIF arithmetic (signed 24-bit saturation, current/voltage
rounding, negative weights, `voltage > threshold`, reset,
refractory), **source→destination 1-tick routed latency**,
and all 26 steps. Freeze or explicitly revise the exploratory
`p06_lif_input_probe.py` deterministic 8-bit input code,
including exact byte order, phase and total spike counts.
Define ten-class output spike-count tie/zero-spike policy,
per-image state/event/accumulator/reset behavior, and
reference traces for overflow, thresholds, silence and
maximal activity. Regression against the **existing**
`LogicalChip` and packed hardware-image ABI must pass.
The training forward may use surrogate gradients, but its
**forward inference** must equal the independent integer
oracle; learning gradients need not be bit-exact.
*No MNIST test-set labels consulted.*

**2026-10-13 incremental status:** P06-A2.1 independent integer LIF
scalar oracle was user-accepted with native pytest PASS and both feasibility
probe PASS outputs. A2.2's versioned 25+1 input/readout, A2.3's independent
full-frame reference and A2.4's packed-image differential tests were
subsequently **user-attested accepted** (without a pasted pytest summary).
See `P06_A2_1_INTEGER_ORACLE_GATE.md` and
`P06_A2_2_TO_4_NATIVE_GATE.md`.

**A2.5 now IMPLEMENTED / PENDING native acceptance:**
`p06_train_forward.py` runs the exact signed integer 26-step inference
forward on quantized weights while using STE and surrogate spikes for
*approximate backward gradients*. A fixed per-layer, uniform LIF config
(including optional fixed bias) avoids unaccepted per-neuron compiler
changes; learned weights export through `p06_train_export.py` into the
unchanged P06 compiler, failing closed on unsupported per-neuron configs,
nonfinite or out-of-range weights. Local partial checkout verified 56 tests
with 1 native-only test deselected, while two new real-compiler exporter
tests await native run. See `P06_A2_5_TRAINING_FORWARD_GATE.md`. The user subsequently
confirmed the native A2.5 verification and explicitly authorized
**P06-A2 closeout on 2026-10-13** (the detailed pytest transcript
was not pasted). No actual MNIST training, official test-set evaluation,
or physical inference has occurred.

### P06-A3 — Train and select compact network [CLOSED: 94.39% VALIDATION GO + NATIVE A4 CHECKPOINT RELOAD]

Pin MNIST source, original dataset file hashes, train
split/held-out validation split and preprocessing; pin
all training seeds, package versions and loss/optimizer
configuration. Train to **FPGA-compatible forward
semantics**, using a reproducible gradient surrogate
or another justified training method. Permit only
predeclared architecture/hyperparameter trials using
training and validation; document underperformance
and an explicit GO/NO-GO floor before official-test
evaluation. Train floating/quantization-aware as needed
but **freeze the exported signed integer weight tensor,
biases, thresholds and decays** within P03 packer
ranges. Export independently verifiable checksum/dtype/
shape and a frozen per-class readout contract.
**Never call the tutorial's weights or accuracy ours.**

**2026-10-13 A3 work:** New `p06_a3_data.py` pins canonical
MNIST *training-only* gzip MD5, SHA256 provenance, strict IDX format,
seeded 50k/10k train/validation split and sealed official test boundary.
New `p06_a3_training.py` provides reproducible nonzero initialization,
quantization-aware PyTorch surrogate optimization, validation-only
best-epoch selection, error/silence telemetry, explicit model configs,
checkpoint/quantized weight SHA256 and tamper-checked candidate loading.
`scripts/p06_a3.py` adds explicit canonical-train-only download,
dataset preflight, *dataset-free* synthetic optimizer smoke and later
full-train modes. The fixed first-pass hypothesis uses signed24 hard-reset
LIF with full current and voltage decay, hidden threshold 32 and output
threshold 8, eight epochs, batch 64, Adam 0.05, width 16 and
**precommitted 60% validation GO/NO-GO floor**. This floor is a planning
criterion and is **not an accuracy claim**. No real MNIST preflight,
training/validation run or held-out official-test access was executed by
the assistant. The user subsequently verified the native pytest
suite and supplied PASS for synthetic smoke and canonical 60k training
archive preflight with hashes and a fully sealed official test set.
Critically, the synthetic smoke yielded 12/12 all-silent validation
outputs (train/val 33.3%, val loss ln(10)); this is a computational
pass, not evidence of training. The new A3.4 256-train/128-validation,
two-epoch real-data pilot independently checks gradients, changes to
actual integer weights and non-silent per-class readout before any
full eight-epoch run. A3.4 requires native user verification. See
`P06_A3_1_TO_3_NATIVE_GATE.md`; no actual full-MNIST checkpoint exists.

**2026-10-15 next gate:** The user reported A3.4 native pytest PASS and
pasted its pilot output (`GO_TO_CONTROLLED_FULL_TRAIN`): positive
finite gradients in both layers; 4,864 input→hidden and 105
hidden→output exported signed integer weights changed. Small-pilot
validation went from 10.16% to 21.09% over two epochs, but the final
validation still had **77/128 (60.16%) all-silent outputs**, resulting
in heavy class-0 argmax ties. This is enough to pass the bounded
learning-activity gate, **not** enough to assert MNIST benchmark
accuracy or likelihood of reaching the predeclared 60% validation
floor. The next controlled experiment is the originally fixed
8-epoch, 50k/10k train/validation trial, seed 20261013, Adam 0.05,
batch64, surrogate width16. No official test use or tuning changes
before its first completed outcome. See
`P06_A3_1_TO_3_NATIVE_GATE.md`.

**2026-10-15 full-data candidate update:** User supplied the completed
eight-epoch first trial `candidate_manifest.json` with epoch 8
selected, 50k train accuracy **95.34%**, 10k held-out validation
accuracy **94.39%**, 2/10k validation silent outputs, and
`candidate_go=True` against the predeclared **60%** threshold.
Official MNIST test set remains `SEALED / NOT READ`. This is a
user-provided report of a checkpoint, NOT assistant-verification
of the `.pt` file. Native `--validate-candidate` checksum/reload
confirmation is an explicit A4 entry gate. Full record:
`P06_A3_TRAINED_CANDIDATE_A4_1_GATE.md`.

### P06-A4 — Byte-precise deployment + freeze [CLOSED / USER-ACCEPTED A4.1 + A4.2, 2026-10-17]

Map the **trained**, quantized network through the real
P06 compiler into P03/DDR 512 KiB records. Prove
all capacities again **using real weights**, ensure
the compiler does not reinterpret zeros/duplicates or
silently change connectivity, and compare exact
spike/current/voltage/state/event predictions between
the independent integer oracle and the versioned
serialized image. Freeze tensor SHA-256, model/config
schema, training recipe, split, image normalization
and encoder, execution timesteps, reset/readout and
evaluation protocol **before unsealing the official
10,000-image test**. No golden P05 edits.

**P06-A4.1 initial implementation (2026-10-15):** The new
`p06_a4_snapshot.py` pins the exact first trained checkpoint and
exported integer weight SHA256, rechecks canonical split hashes,
compiles actual learned weights through accepted P06/P03,
checks 42 compartments, 784 external axons and image banks,
and runs exact full-26-tick PyTorch, independent dense integer,
independent packed hardware-word replay, and `LogicalChip`
differential traces on synthetic + three held-out validation
frames. Only after parity does it create reproducible little-endian
logical word streams and SHA256 manifests. This is **not** a
P05 physical DDR context record or working board inference.
Checkpoint integrity, trained-image compilation, parity traces and
snapshot hashes were subsequently accepted in the user native A4.1
run, as recorded below. Official test-set remains sealed.
See `P06_A3_TRAINED_CANDIDATE_A4_1_GATE.md`.

**2026-10-17 acceptance/closeout:** User ran the trained A4.1
native script and reported `P06_A4_SOFTWARE_SNAPSHOT_PASS=1`
and five 26-tick frames exactly equivalent across independent dense,
PyTorch, independent P03 replay and accepted `LogicalChip`.
The script ran checkpoint byte/digest reload before reporting PASS,
so A3's native checkpoint-integrity prerequisite is established
by that invocation even though a separate CLI marker was not pasted.
All six P03 packed bank streams' exact SHA256 are frozen in
`P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`.
The official 10k MNIST test partition remains sealed. Real
trained one-core hardware-word image: 42 compartments,
816 axons, 25,408 synapses, 32 routes.

A4.2's `p06_a4_freeze.py` invokes the existing P02.1
`build_initial_ddr_context_record` to produce a versioned
**512KiB static DDR core context**, verifying every bank and
record header digest after checking pinned P03 bytes. On 2026-10-17,
the user explicitly reported **DDR native validation PASS** and requested
A4 closeout. Thus both A4.1 software and A4.2 static DDR host
verification are user-attested accepted. The full record file SHA256
was not pasted; it can be read without regeneration from the already
verified local artifact before P07 deploys it. See
`P06_A4_FINAL_CLOSEOUT.md`.
The P07 A53 784-axon streamer, board readout, reset and end-to-end
timing remain wholly unimplemented. The old P05 diagnostic
header/payload is NOT an executable MNIST inference deployment.
`P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md` freezes the future test
denominator and readout conditions before test unsealing.

**P06 compact exit:** versioned training+inference
reference, reproducible legitimate trained checkpoint,
quantized deployed image, exact diagnostic trace
corpus, and an audited immutable benchmark manifest.
Native regressions user-accepted. **No claim of
KV260 application accuracy** until physical P07-A.

### P07-A — Physical board-local inference (after P06-A4)

A53 autonomously reads serialized image samples,
emits all required *distinct* destination input axons,
services 26 timesteps per image on the PL,
resets state/event buffers and output spike counters
per image, and retrieves 10 output counts/results.
**The currently accepted P05 A53 regression ABI
allows only one registered external input axon
per logical core**; it is **not already** a
784-axon streaming MNIST application. Implement a
separately versioned, fail-closed input/deployment
interface without modifying accepted P05 goldens.
Use full-system first-mismatch traces, then run
the predeclared official MNIST test protocol
on the board if the run budget permits.
If a smaller physical sample population is
necessary, justify/freeze it before evaluating
its predictions and report confidence limits.

### P08-A — Baseline physical performance and power

Record the compact model's dispatch, barrier,
input generation, complete-image latency,
steady-state throughput and board/SOM
idle/active/incremental power+energy using
explicit, independently reproducible measurement
boundaries. Separate FPGA/PS orchestration from
off-board PC setup and from original Loihi
silicon; do not compare unlike energy boundaries
as if they were direct measurements. **Accept this
physical baseline before starting Track B board
implementation.**

## Track B — Scaled, DDR-virtualized classifier (AFTER A baseline)

**Research target:** same FPGA-compatible LIF
operations, 784→1000→10 *project-trained* topology,
the same 25+1-event clock and the same input/data
and evaluation protocol, but **a separately trained,
frozen larger checkpoint**. Being the same
*dimensions* as snnTorch Tutorial 5 does **not**
make it the same pretrained tutorial model.

### First-pass feasibility estimate (NOT a mapping proof)

- **794,000** dense candidate connections:
  `784×1000 + 1000×10`. One core has 32,768
  hardware synapse words and 128 KiB logical
  synaptic accounting, so the existing
  5×32,768-entry P05 demo cannot retain the
  original dense graph without new logical
  records and partitioning.
- A completely unique dense **input→hidden**
  projection shard with **39 hidden destinations**
  requires `784×39=30,576` 4-byte
  logical synapse entries plus at least
  `784×(4-byte template header+4-byte axon
  binding)`=**6,272 B** of allocation
  overhead. Total **128,576 B < 131,072 B**;
  **40 destinations** would consume
  **131,712 B**, exceeding the versioned
  128 KiB logical model. Actual compiler
  layout, routes and transformed weights
  could change the fit.
- **At least ~26 input→hidden shards**
  for 1000 hidden neurons, **plus ~1
  readout logical core** is a useful
  **~27 logical-core design hypothesis**,
  *not a proven placement, exact lower bound,
  performance result or acceptance target*.
  An independent P06 mapper/export test
  must prove the placement and every full
  per-core bank/route/event occupancy.
- **27×512 KiB = 13.5 MiB** backing records.
  The P05 A53 diagnostic deployment header
  permits at most **126 logical IDs**, limited
  by the reserved DDR map; the general
  Python logical model allows 128. Thus
  address space **is not** the major blocker.
  The present FPGA retains **3 resident slots**
  and services cores using **1 HLS engine**.
- A worst-case all-pixel-active timestep
  replicates 784 distinct input events to
  ~26 hidden destinations: **~20,384
  external destination packets per global
  timestep**, but **only 784 per
  destination core**. Across 25 steps,
  ~509,600 events consume ~8.15 MiB
  as P05's 16-byte event descriptors;
  this **cannot be preloaded unmodified**
  into the current **896 KiB P05 diagnostic
  payload region**. Implement A53-local
  synthesis/streaming or a separately
  versioned larger event ABI.
- With **27 logical cores** and **26 global
  steps**, the simple all-cores-every-step
  schedule entails roughly **702 core
  dispatches/image**, compared with
  **26** for Track A. These are
  *counts, not latency predictions*.
  Page loads/evictions, event fanout,
  routing/barrier overhead, effective
  bandwidth and the output phase must be
  measured; no claim of 27× slower follows.

### P06-B1 — Valid resource-aware network partitioner [AFTER P08-A]

The current `compile_network` first assigns
compartments, and **only afterward** checks
per-core synapse-resource capacity. It
will **not** automatically shard a
784→1000→10 graph simply because
`max_logical_cores` is increased.
Implement/demonstrate a deterministic
synapse/axon-aware **destination-partitioning
strategy** with explicit stable ingress
fanout to all 26 destination shards,
per-core 128KiB cost model and P03
hardware bank checks, logical NoC routing
to the output core, valid core IDs and
well-defined barrier/NEXT-step behavior.
Reject overflow. Test alternative
placement and paging policies for
semantic invariance using an
**independent unpartitioned software
reference** (never use same
scheduler as both sides of an oracle).
Report estimated memory, DDR traffic
and schedule before hardware modifications.

### P06-B2 — Train, quantize and freeze the scaled checkpoint [AFTER B1]

Preserve Track A's frozen encoder,
one-tick routed semantics, reset/readout
and official test split. Train and freeze
**a separate 1000-hidden project
checkpoint** using train/validation
only; log capacity/accuracy tradeoff
without peeking at test labels.
Verify real per-core exported words
and routing against independent oracle
first-difference traces, and freeze
mapping, weight digests and
measurement/evaluation scope. If the
1000-hidden target is infeasible on
reasonable board time, report a
defensible pre-test decision and
optionally use an **explicitly declared
intermediate 64/128/… model** as a
scaling result, never silently call it
the original 1000-hidden model.

### P07-B — Physical multi-core board deployment [AFTER B2]

Use the existing 3 context slots /
one engine + 512 KiB DDR per logical
core, with autonomously controlled
A53 page loading/eviction, source
event duplication, routed packets
and global barriers. Extend diagnostic
input ABI and per-image reset/readout
as required. First demonstrate
trace-identical model-vs-KV260
multi-core inference for a small
**preselected**, label-independent
input corpus. Then run the sealed
official test protocol if feasible.
Every failure must identify the
first divergent core, timestep,
bank, state/packet or arithmetic
operation. **Do not claim** a
27-core physically accepted design
until the board proves it.

### P08-B — Scaling and resource-overhead characterization

Repeat Track A measurement boundaries
on Track B with the **same** board,
bitstream/clock policy, input
encoding, test population definition
and power methodology wherever
applicable. Report both (a) changes
in **model size/accuracy** and
(b) changes in hardware **logical
cores, page-ins/outs, bytes,
dispatch count, routed events,
end-to-end latency, throughput
and active energy**. These are
not a pure architectural
speedup comparison because the
two neural networks differ in size
and independently trained weights.
Optionally evaluate a hypothetical
second physical engine **after**
one-engine scaling behavior is
quantified. P04 remains deferred
until separately scoped and accepted.

### P09 — Thesis closeout

First guarantee a complete **Track A**
evidence chain. If Track B passes its
own gates, add a distinct **Track B**
chain and a side-by-side scaling
study, with separate model weights/
predictions/accuracy, resources,
paging and measured performance.
If Track B remains infeasible,
document the bounded attempt and
measured/constrained bottleneck
without weakening Track A's
reproducible result.

## Immediate next step / P07-A2 status (updated 2026-10-17)

**P06 Track A (A1–A4) and P07-A1 are complete and user-accepted.**
P06 produced a project-trained 784→32→10 compact SNN, exact software
word/trace replay and a frozen static P02.1 512KiB DDR context. P07-A1
then validated the many-axon ingress contract on the user's native
machine, with real DDR SHA256
`9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`
and compiler fingerprint
`e612a971cda11fae3f1be215c0ca3ed7de7b2af7339446e926ce559658db2f7f`.

**P07-A2 is the active engineering gate:** autonomous Cortex-A53 image
execution, 26 barriers per image, full reset, real output trace counts,
and first-mismatch verification. The portable P03 scheduler wrapper,
candidate bare-metal A53/DDR/PL integration, versioned image batching,
CI-native C/CRC/SHA tests, and evidence analysis tools exist on
`agent/v3-p07-a-784-axon-streaming`, but the user's Vitis ELF build
and physical KV260 trace acceptance are **PENDING**. See
`P07_A1_FINAL_CLOSEOUT.md` and `P07_A2_A53_RUNTIME_GATE.md`.
The official MNIST TEST partition is **SEALED**; no A53 MNIST
accuracy/latency/energy is claimed. P06-B1/B2 are deferred until
P08-A is physically measured and accepted.
