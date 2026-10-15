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

**P06 — Two-track LIF MNIST research: IN PROGRESS.**
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

**P06-A2 CLOSED / user-accepted (2026-10-13):** A2.1–A2.5's
independent signed24 LIF oracle, deterministic 25+1-event encoder,
separately decoded P03 packed-image replay and PyTorch forward parity
have all been accepted by user native verification. Detailed native
pytest logs were not all provided; this does not imply physical FPGA
MNIST. Accepted P05/HLS goldens remain untouched.
[Closeout record](docs/P06_A2_5_TRAINING_FORWARD_GATE.md).

**P06-A3 IN PROGRESS (2026-10-13):** Implemented A3.1 canonical
MNIST TRAIN-only checksum/IDX validation, deterministic 50k train /
10k validation provenance; A3.2 seeded quantization-aware surrogate
learning and validation-only model selection; A3.3 signed24 checkpoint
candidates with config/data/weight hashes and tamper checks.
**The user accepted native tests, canonical TRAIN-only archive
preflight and initial optimizer smoke on 2026-10-13.** The smoke's
12/12 validation frames were entirely silent (synthetic accuracy 33.3%),
so it does not establish meaningful learning. A3.4 adds a bounded
256-TRAIN/128-validation, two-epoch learning-activity pilot with
quantized-weight, surrogate-gradient and per-class spike diagnostics.
**A3.4 pilot native verification is now user-accepted (2026-10-15).**
The canonical 256/128, two-epoch train-only pilot showed gradients in
both layers and integer-weight changes (4,864 input→hidden; 105
hidden→output). Pilot validation rose 10.16%→21.09%, but **77/128
(60.16%)** final validation cases still emitted zero output spikes,
biasing the tie-break toward class 0. The activity gate permits the
first unchanged full 50k/10k training experiment; the **60% full
validation GO criterion is now **EXCEEDED** by the first completed
full 50k/10k train/validation trial. The user-provided candidate manifest
reports epoch-8 best validation **94.39%**, train **95.34%**, and just
**2/10,000** all-silent validation images. This remains a reported
held-out validation result, NOT official MNIST test or KV260 accuracy.
The native checkpoint integrity reload is still required.
Validation GO/NO-GO criterion
was set at 60% before any dataset evaluation. Test labels stay sealed;
no accuracy, P07 execution or KV260 power/energy claim is made.
[Current native preflight gate](docs/P06_A3_1_TO_3_NATIVE_GATE.md).

**P06-A4.1 IMPLEMENTED — NATIVE VERIFICATION PENDING (2026-10-15):**
Pinned the exact candidate checkpoint SHA256
`0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88`
and effective signed integer weight SHA256
`1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`.
The new snapshot generator checks current 50k/10k dataset provenance,
compiles actual learned signed24 weights through unchanged P06/P03,
compares PyTorch/dense integer/packed replay/LogicalChip for 26-step
frames, then records endian-defined P03 words and hashes. **These
streams are not the A53/DDR full-page ABI or an FPGA run.**
[Current A4 native verification instructions](docs/P06_A3_TRAINED_CANDIDATE_A4_1_GATE.md).

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

**Track B — Larger virtualized
classifier SECOND, only after P08-A.**
Target **784→1000→10**, roughly **27
logical DDR-backed contexts**
(26 hidden shards + 1 output,
a **hypothesis** not an accepted
resource-aware map), using the
same 3 resident contexts and one
physical engine. P06-B1: new
**synapse-aware destination partitioner**
and full-core resource/route/paging
feasibility; P06-B2: separately trained
and frozen scaled checkpoint; P07-B:
actual multi-context autonomous
FPGA classification; P08-B:
measure real routing/page-in/out
overhead, latency, energy and
classification tradeoffs. Do not
assume increasing the
`max_logical_cores` option alone
will partition the network; the
present compiler partitions
compartments first and fails
on synapse-memory oversubscription.
Current A53 P05 event manifest
also permits only one registered
external input axon/core and
must be extended before either
full classifier physically runs.

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
No official MNIST test-set
evaluation has happened.

[**Complete compact-first, scaled-second plan**](docs/P06_TWO_TRACK_LIF_PLAN.md)
|
[Feasibility/resource audit](docs/P06_LIF_FEASIBILITY.md)
|
[Accepted native regression details](docs/P06_LIF_NATIVE_GATE.md)
|
[Exploratory frozen-schema candidate record](docs/P06_LIF_CANDIDATE_PROFILE.json)
|
[Original Rao source research (unselected)](docs/P06_1_PAPER_METRIC_AUDIT_AND_DECISION.md).

**P07–P09 — Pending; staged A then B as specified above.**

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
