# FPGA-v3 / Board-Local Loihi-1 Architectural Twin

This directory is the active FPGA-v3 development tree.

v3 was forked from the final accepted FPGA-v2 state at:

```text
a9329caa064fee3876d69fbbe6c626ac035e67b5
Close P08 and complete FPGA-v2 roadmap
```

The accepted v2 tree remains preserved under `../v2/`. v3 inherits the v2 implementation as its starting baseline so that development can focus on board-local execution, stronger physical testing, a better-specified published MNIST benchmark, and defensible latency/power/energy characterization.

Development authority is:

- `LOIHI_TWIN_ROADMAP.md` — v3 phases, deliverables, and acceptance tracker;
- `docs/LOIHI1_TARGET_SPEC.md` — inherited Loihi-1 architecture contract until P01 determines whether a v3 addendum is required.

## Current status

**P00 — Establish v3 baseline, directory, and roadmap: Complete.**

**P01 — Board-local architecture, ownership, and v3 contract: Complete.**

**P02 — DDR-backed logical-core virtualization: Complete.**

**P03 — Autonomous PS-resident runtime: Complete (independent KV260 physical acceptance, 2026-10-12).**

**P03.1–P03.5: Complete.** The final seven- and hundred-timestep functional KV260 gates passed; see `docs/P03_FINAL_ACCEPTANCE.md`.

**P04 — Multi-engine HLS parallelism: Deferred.** The accepted
physical design uses one FPGA HLS inference engine and
three resident logical-context slots.

**P05 — Board-local regression, observability and data-path
hardening: COMPLETE / physically accepted, 2026-10-13.**
P05.1 and P05.2a–P05.2i are independently confirmed on real
KV260 within the documented scope; see
[Phase 5 consolidated acceptance](docs/P05_FINAL_ACCEPTANCE.md)
and [final direct AXI measurement acceptance](docs/P05_2I_ACCEPTANCE.md).

**P06 — Two-track LIF MNIST research: COMPLETE AT HOST-SOFTWARE
LEVEL (Track A accepted separately; Track B B1/B2 user-accepted 2026-10-19).**

The active next milestone is **P07-B**, the *new* autonomous
27-logical-core deployment on the actual KV260 with one P03-compatible
physical HLS engine and three resident contexts. P06-B1/B2 source and
documentation were merged onto `main` in PR #46 and PR #47
(2026-10-19). The new trained Track B network is 784→1000→10,
794,000 dense source connections, 27 packed cores and 14,155,776 bytes
of **initial** P02 context backing. Its checkpoint achieved **97.08%
on 10,000 TRAIN-derived validation images**, not official TEST.
Three predeclared original TRAIN-derived validation frames passed full
26-tick host source/PyTorch/partitioned numerical parity. The user's
original local B2.4 freeze passed both regular and deep SHA verification
of 33 assets and all 27 initial DDR records; B2.5 host readiness
was user-attested PASS.

**Physical scaled execution remains NOT TESTED; official Track B MNIST
TEST remains SEALED.** B1.3's multiple-input streaming ABI and B1.5's
three-slot cache are host contracts/models, NOT a firmware implementation
of 27-core PS/PL scheduling. P07-B will require a separate real board
deployment and physical numerical acceptance. See
[`P06_B2_5_HOST_SOFTWARE_EXIT_AND_P07B_HANDOFF.md`](docs/P06_B2_5_HOST_SOFTWARE_EXIT_AND_P07B_HANDOFF.md)
and the [new-chat P07-B seed](docs/P07_B_NEXT_CHAT_HANDOFF_SEED.md).

**Historical P06 research direction (retained below for provenance):**
Published foundation: Eshraghian et al. (2023)
and the author's snnTorch MNIST LIF tutorial
(methodology, **not** a proven pretrained
checkpoint identity). User accepted the
**Track A 784→32→10 native structural
compiler-to-HLS-image feasibility gate** on
2026-10-12, including the corrected 31-spike /
310-next-bank fan-in regression. This proves
one real packed **42-neuron, 25,408-synapse,
816-axon, 32-route** one-core test image
with **synthetic test weights**, not trained
accuracy or physical KV260 inference.

## P06 Track A CLOSED / accepted — entry to P07 (2026-10-17)

**A1/A2/A3 accepted, A4.1 trained host benchmark freeze accepted.**
The user trained our project-defined 784→32→10 signed24 integer-forward
spiking classifier using the canonical 50,000-example MNIST TRAIN split
and selected epoch 8 based on the predeclared 10,000-image held-out
validation split. **Train accuracy: 95.34%. Validation: 94.39%.**
The official test partition remains sealed; these numbers are NOT
physical KV260 accuracy. Checkpoint byte SHA256 and signed-integer
weight SHA256 are pinned, and the A4.1 native software run necessarily
reloaded and verified the checkpoint before exporting memory words.

The user reported **P06_A4_SOFTWARE_SNAPSHOT_PASS=1** with all four
host inference paths exactly equal on **5 frames × 26 logical steps**:
PyTorch integer forward, separate signed24 dense oracle, independent
P03 packed-word replay, and `LogicalChip`. The trained P03
one-core image contains **42 compartments, 816 input axons,
25,408 packed synapses and 32 routes**. Six packed-stream file
SHA256 and byte counts are frozen in
[the software benchmark manifest](docs/P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json).

**A4.2 COMPLETED — user-attested native DDR validation PASS (2026-10-17):**
`scripts/p06_a4_freeze.py` uses the accepted P02.1 `LTV3CTX1`
ABI to build the **524,288-byte initial core-0 DDR record** and
checks the banks, snapshot hashes and record digest. The user confirmed
this DDR gate passed. **The actual full-file SHA256 was not pasted**;
retrieve it from the existing local binary before P07 deployment.
The milestone is closed; an explicit DDR-file provenance value remains
to be recorded in the P07 loading manifest. See
[the final P06-A4 closeout record](docs/P06_A4_FINAL_CLOSEOUT.md),
[frozen Track A manifest](docs/P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json),
and [sealed official-test protocol](docs/P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md).

**Historical P07-A plan (already completed):** This was written
before P07-A/P08-A native physical acceptance. The accepted compact
Track A single-core FPGA MNIST result reached **94.56% on official
TEST** on the KV260, with separately accepted physical P08-A baseline.
**Do not re-open Track A's official TEST or confuse that result with
the new Track B validation 97.08%.** The outstanding P07-B challenge is
instead the **27-core** A53 multi-ingress/multi-context runtime, which
the old P05 single-external-axon diagnostic ABI cannot implement.

**Official sequential development plan:**

**Track A — Compact single-core classifier FIRST.**
P06-A2: exact P03 integer 24-bit LIF +
25 event ticks + 1 NEXT-bank drain
independent software oracle, with
deterministic uint8→spike input and
readout; P06-A3: train/freeze a real
project checkpoint on MNIST train/
validation only; P06-A4: checksum
dataset/weights/compiled context and
freeze the official test protocol;
P07-A: A53-autonomous per-image
many-axon injection, hardware
predictions and accuracy; P08-A:
full-system latency/throughput/
board energy baseline.

**Track B — Larger virtualized classifier HOST SOFTWARE COMPLETE.**
P06-B1.1–B1.6 delivered independently tested 27-core synapse-aware
packing, fail-closed capacities, source-preserving multi-core ingress
and NEXT routing contracts, independent numerical oracles and a
three-resident-slot **modeled** paging policy. B2.1–B2.5 delivered
the real project-trained 784→1000→10 signed24 checkpoint,
full 794,000-connection packed mapping, trained-dense host
numerical checks, byte-frozen 27 initial P02 contexts,
sealed official TEST protocol and a host-only P07-B handoff.
See [roadmap](LOIHI_TWIN_ROADMAP.md).

**P07-B / P08-B NEXT:** Implement the real scaled 27-core
A53/PL ingress, barrier, routing and dirty-page runtime on
KV260, independently compare actual board neuron states
and spikes to the accepted software oracle; then measure
physical page traffic, latency, throughput and energy.
Do not equate B1.5 host byte estimates with physical measurements.

**Experimental claim boundary:**
Both checkpoints are **our trained
project models**, based on published
LIF methodology, not identical to
the original 784→1000→10
snnTorch floating-analog-input
tutorial (different reset,
event encoder and timesteps).
Their measured accuracy and
hardware costs are separate
findings, not original author
Loihi metrics. NxTF remains
excluded. Archived Rao/AHP
source research is retained
but is **not** a prerequisite
for the chosen LIF paths.
Track A's separately frozen official MNIST TEST evaluation was
accepted physically at **94.56%**. No official MNIST TEST
evaluation for the **Track B 1000-hidden model** has occurred.

[**Complete compact-first, scaled-second plan**](docs/P06_TWO_TRACK_LIF_PLAN.md)
|
[Feasibility/resource audit](docs/P06_LIF_FEASIBILITY.md)
|
[Accepted native regression details](docs/P06_LIF_NATIVE_GATE.md)
|
[Exploratory frozen-schema candidate record](docs/P06_LIF_CANDIDATE_PROFILE.json)
|
[Original Rao source research (unselected)](docs/P06_1_PAPER_METRIC_AUDIT_AND_DECISION.md).

**P07-A/P08-A accepted; P07-B next (NOT physically implemented);
P08-B/P09 pending.** The old Track A paragraphs above include
historical forward-looking statements. Current authoritative phase
status is the [v3 roadmap](LOIHI_TWIN_ROADMAP.md).

The implementation code is intentionally copied from v2 before architectural changes begin. Therefore some inherited package names, scripts, comments, and documentation still contain `v2` identifiers. Those names are compatibility artifacts of the baseline copy and should only be renamed deliberately with regression coverage.

The v2 accepted architecture remains:

```text
5 logical cores
3 resident K26 context slots
1 physical HLS engine
host-owned cross-page routing/barrier
host/PC-RAM backing for non-resident contexts
```

The accepted P01 board-local partition is:

```text
logical cores backed by K26 DDR
PS/PL-owned runtime control
PC removed from the algorithmic timestep loop
full board-local inference where practical
substantially more physical regression/application testing
```

## Accepted P05 physical coverage at a glance

The unchanged accepted P03.2c FPGA and P05 standalone A53
successfully executed independently modeled multi-core
paging/routing and neuron arithmetic scenarios with a PC
restricted to initial provisioning, launch and evidence capture.

- Full directed corpus: separately accepted deployment
  variations, fast-vs-diagnostic identity, negative
  first-fault reporting, legal service permutation,
  two-destination fanout, signed 24-bit saturation and
  refractory behavior, both resident and nonresident
  packet routing, global barrier/bank alternation and
  dirty paging.
- P05.2g physical capacity: exactly **4096 external
  CURRENT-bank events** passed full-model state/DDR checks;
  separately CRC-valid 4097-event **deployment** rejected
  before A53 MMIO/dispatch and left full DDR unchanged.
- P05.2h: 5 logical cores, 3 resident slots,
  **16 barriers / 80 dispatches / 318 CRC checkpoints /
  156 routed packets (78 resident, 78 nonresident) /
  77 evictions**, five independent complete **512 KiB**
  actual FPGA DDR records byte-identical to the separate
  Python/model-derived physical ordering reference.
- Final P05.2i direct physical PL HP0 AXI:
  **136,960 completed read bursts** and **33,280
  completed write bursts**, 256 bytes each,
  **43,581,440 actually measured successful page-engine
  transfer bytes**. The A53-reported burst counters and
  the raw read-only FPGA register witness matched the
  independent P03 page replay; the final same-run
  P05.2h/DDR checks remained PASS.

**Deliberate coverage limits:** No physical demonstration
of a runtime HLS-routed **4097th NEXT-bank packet**
causing backpressure or successful continuation/recovery,
and no whole-system DDR traffic, calibrated benchmark
latency, energy or power, or simultaneous multi-HLS
engine execution. The portable C NEXT bank overflow
guard is a separate native-only result. Actual AXI
measurement is the **PL page-engine only**. P06–P08
will determine and separately qualify further
application requirements.

Primary records:
[P05 final accepted evidence](docs/P05_FINAL_ACCEPTANCE.md),
[P05.2i direct PL page AXI acceptance](docs/P05_2I_ACCEPTANCE.md),
[P05.2i reproduction and same-run debugger workaround](docs/P05_2I_AXI_CLOSEOUT_GATE.md),
and [roadmap](LOIHI_TWIN_ROADMAP.md).

## Baseline software verification

From this directory, the inherited Python regression suite can be forced to use the v3 source tree without changing the existing v2 package name:

```bash
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q
```

P00 was independently verified and accepted on 2026-10-05. See `docs/P00_ACCEPTANCE.md`.


## P02 accepted physical baseline

P02 closed on 2026-10-06 with:

```text
5 logical cores
3 resident K26 context slots
1 physical HLS engine
K26 DDR authoritative for non-resident logical contexts
35 physical dispatches
7 algorithmic barriers
30 routed packets
60 page-ins
60 mutable page-outs
57 evictions
all five final DDR records byte-exact to golden
```

Accepted P02 physical artifact identities:

```text
bitstream_sha256=0d96ae6af0cc313ccbd8f9c802aeb0c8c7946bfeabaca3152ef5c7b9d2b23f26
probes_sha256=f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
```

The PC still owns scheduling, packet-routing bookkeeping, and global barriers in
this P02 baseline. P03 moves those responsibilities onto the Cortex-A53.


## P03 accepted autonomous PS execution

P03 **moved the algorithmic control loop from the external host to
Cortex-A53 #0** (standalone bare-metal executable, not a Linux
service). The PC is needed to provision DDR, program/load once,
passively poll terminal completion, and retrieve final records,
but does not select core victims, dispatch, route packets, or
advance barriers inside the algorithmic loop.

Independent physical KV260 validation, using the same V2 A53 ELF
and accepted FPD128 PL shell:

| Gate | Timesteps | Dispatches | HLS packets | Barriers | Page-ins/outs | Golden DDR |
|---|---:|---:|---:|---:|---|---|
| P03.4 | 7 | 35 | 30 | 7 | 35 / 35 | 5 x 512 KiB byte-exact |
| P03.5 | 100 | 500 | 495 | 100 | 500 / 500 | 5 x 512 KiB byte-exact |

**Hardware routing coverage limitation:** both runs reported
`resident_deliveries=0`; the live FPGA route into an
*already-resident* destination is **not** physically claimed
(native adapter tested). P05 can add a directed physical
test. Power/energy, full MNIST application and multi-engine
parallelism also remain separate roadmap gates.

**Primary technical docs:** [Standalone A53 PS app architecture,
ownership, DDR/manifest/mailbox ABI, packet/cache operations and
problem-solving](docs/P03_PS_AUTONOMOUS_APPLICATION.md);
[phase-wide functional closeout](docs/P03_FINAL_ACCEPTANCE.md);
[7-step result](docs/P03_4_ACCEPTANCE.md);
[100-step result](docs/P03_5_ACCEPTANCE.md).
The original planned contract froze:

- exact runtime/barrier/error transitions;
- deterministic service and page-replacement policy;
- resident/non-resident packet-delivery behavior;
- cache ownership and the reserved 64 MiB DDR backing window;
- board-local timing/counter boundaries;
- sticky fail-closed recovery;
- the FPGA-v3 addendum to the inherited Loihi-1 target specification.

Primary record: `docs/P03_1_AUTONOMOUS_RUNTIME_CONTRACT.md`.


## P03.2 hardware history (superseded original candidate)

The final accepted physical shell exposes a **32-bit AXI4-Lite**
control endpoint at **`0xA4000000..0xA4000FFF`** through
`M_AXI_HPM0_FPD` (booted **128-bit** PS AXI4 master through a
SmartConnect width/protocol bridge). The old 32-bit-master
route and its fingerprints below are **historical P03.2b
build artifacts, not the final P03.2c / P03.4 / P03.5
acceptance bitstream**. See
`docs/P03_2C_PS_HPM_WIDTH_BOOT_REMEDIATION.md` and
`docs/P03_2C_ACCEPTANCE.md`.

It replaces VIO command ownership for:

- DDR page commands;
- HLS dispatch commands;
- low-rate resident-memory reads/writes.

The accepted P02 HP0 DDR page data path is retained. VIO remains only for
observation and pre-run reset during bring-up.

Primary record: `docs/P03_2_PS_MMIO_CONTROL.md`.


## Historical P03.2b routed 32-bit-master attempt

The PS-visible HPM0/MMIO shell is now routed and accepted:

```text
MMIO base/range: 0xA4000000 / 0x00001000
WNS:             +0.539 ns
WHS:             +0.010 ns
resident slots:  3
physical engines:1
URAM:            47
```

Accepted artifacts:

```text
bitstream_sha256=8b4d1d3996147e73bbe71ec2a5036f0a4d23efc5cc3fe3d25237f855acf72119
probes_sha256=a745b96c24f4e01480d1d89d706e90c52c822b4a7fda7ea43d2ad794a0b86def
xsa_sha256=703fa7a44abc56e88e67e1d09424ac59ea96e53aac1708c2c7e6028dcb616f40
```

P03.2c later completed its physical A53 page/dispatch/PS-MMIO
smoke on the corrected FPD128/SmartConnect route, followed by
successful P03.3b3, P03.4 and P03.5 board-local runtime acceptance.
Primary acceptance records: `docs/P03_2C_ACCEPTANCE.md` and
`docs/P03_FINAL_ACCEPTANCE.md`.
