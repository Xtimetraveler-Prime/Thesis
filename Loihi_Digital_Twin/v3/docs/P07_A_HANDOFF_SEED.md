# P07-A HANDOFF SEED — Trained compact SNN → KV260 PS/PL inference

**Prepared/updated:** 2026-10-17. **Starting branch:** `main`, after the
P06-A4 closeout PR merges. **Repository:** `Xtimetraveler-Prime/Thesis`
(`https://github.com/Xtimetraveler-Prime/Thesis`). **Working root:**
`~/Git/Thesis/Loihi_Digital_Twin/v3` on the user's Linux VS Code machine.
**Next engineering branch (not yet created):**
`agent/v3-p07-a-784-axon-streaming`. Never develop P07 directly on main.

> **Continuing-assistant opening instruction:** You are taking over the
> P07-A FPGA-native inference implementation of an established thesis:
> a Loihi-1-inspired digital twin on the Kria KV260. Read THIS seed,
> `LOIHI_TWIN_ROADMAP.md`, `docs/P06_A4_FINAL_CLOSEOUT.md`,
> `docs/P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`,
> `docs/P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md`, and
> `docs/P05_FINAL_ACCEPTANCE.md` **before writing code**. Use the
> connected GitHub tools to inspect real APIs/files; do not guess their
> signatures. Branch from current main, commit small submilestones, give
> exact copy/paste Linux VS Code native/board verification commands,
> **stop for user confirmation**, and do NOT merge without explicit
> approval. Preserve accepted P03/P05 goldens and the frozen P06
> checkpoint/encoder/readout. Never call host validation “FPGA accuracy.”

## 1. Exactly where the project stands

The aim is an FPGA digital twin of a neuromorphic architecture, using
explicit neuron/axon/synapse state, integer Loihi-inspired LIF updates,
spike packets, per-timestep routing barriers, logical contexts, and
DDR-backed virtualization. This is NOT Intel Loihi silicon and should
not claim exact native Loihi microarchitecture, energy, or measured
performance.

Historical development:
- **P00/P01/P02:** architectural model and DDR-backed logical-context
  definition; accepted 512 KiB versioned P02.1 DDR record format.
- **P03:** packed signed-24 LIF and a validated physical compute-engine
  path; Py/P03 packed word and state/packet semantics established.
- **P04:** multi-engine path explicitly deferred for Track A; do not
  silently substitute a new engine or change old golden traces.
- **P05:** physical KV260 diagnostics accepted: **one P03 physical HLS
  engine**, **at most 3 concurrently resident logical contexts**, with
  FPGA controller, NEXT-bank packet timing, A53 dispatch and DDR paging
  for diagnostic workloads. **This does not currently execute MNIST.**
- **P06-A1:** actual compiler structural feasibility accepted for a
  one-core 784→32→10 event-driven classifier.
- **P06-A2:** independent 24-bit integer LIF oracle, deterministic
  25+1 event contract, independent packed replay and exact PyTorch
  TRAINING-FORWARD parity **accepted** (surrogate gradients only in
  backward pass).
- **P06-A3:** full reproducible, project-trained MNIST compact
  classifier **accepted**; the best validation-selected epoch is 8 of
  8, 50k canonical training images, 10k held-out train-derived
  validation images. Accuracy: **95.34% train, 94.39% validation**
  (9,439/10,000), all-silent 2/10,000. Predeclared GO floor: 60%.
  This is NOT official TEST accuracy or on-board accuracy.
- **P06-A4.1:** user pasted
  `P06_A4_SOFTWARE_SNAPSHOT_PASS=1`, exactly **5 frames × 26 ticks**
  across **four independent software paths**:
  (1) integer PyTorch forward,
  (2) independent dense signed24 oracle,
  (3) independently decoded P03 word replay,
  (4) accepted `LogicalChip`.
  Native software image: **42 compartments, 816 axon bindings**
  (784 pixel inputs + 32 hidden), **25,408 synapse words, 32 routes**.
  Byte counts and SHA256 for all six P03 word streams pinned in freeze
  JSON. The A4.1 script necessarily loaded and checked the real
  checkpoint before reporting success.
- **P06-A4.2 (LATEST):** after final host static DDR validation commands,
  user explicitly reported **“the DDR validation passed”** and asked
  to close A4 and merge. **Mark native static DDR generator/audit
  USER-ATTESTED PASS** on 2026-10-17, thereby **closing P06 Track A
  (A1–A4)**. The full-file 512 KiB DDR SHA256 and stdout were
  **not pasted**: record its actual digest from the already generated
  local artifact before P07 deployment. This provenance capture is
  not an unaccepted arithmetic gate. Do not fabricate a hash or
  rerun a generator onto an existing directory.
- The official MNIST 10,000-image **TEST** partition remains **SEALED**.
  No P07 full PS/PL MNIST inference, no P08-A measured latency/power
  baseline, and no claim of Loihi silicon physical comparison.

Git history: the long P06 source branch
`agent/v3-p06-lif-feasibility` was merged via **PR #42**, merge commit
`e3356f26acd2d9bf7b29cd079849aa818913dfa4`. The A4.2 native
closeout is merged in a **later PR**; find its final `main` SHA via
`git log -1 origin/main --oneline` or GitHub before commencing P07.

## 2. Crucial software and arithmetic contract — IMMUTABLE for P07

Model is **784 external pixel axons → 32 hidden LIF neurons → 10 output
LIF neurons**, 42 total compartments on logical **core 0**. Raw 28×28
MNIST image is **784 row-major uint8 values**, range 0–255; no analog
normalization, no Poisson generator, no stochastic encoding.

For each pixel index `i=0..783`, at each **input tick** `t=0..24`:
```python
s = (t + 17*i) % 25
fires = ((s+1)*pixel[i])//255 > (s*pixel[i])//255
```
Pixel i emits exactly floor(25*pixel_i/255) spikes in 25 input ticks.
**Tick 25 has no external spikes**: it drains delayed output routing.
Each tick's active pixel indices must map to the **compiler's explicit
destination axon IDs**, not be assumed equal to pixel index or source
neuron index. **Hidden spikes at t are processed by output at t+1,
never within the same step**. All last-tick outgoing hidden packets
are discarded at image boundary.

Signed24 saturating fixed point, exact P03 decay rounding and strict
`voltage > threshold`, not >=. Initial per-layer neuron settings:
- Hidden (32): `current_decay=4096`, `voltage_decay=4096`,
  `threshold=32`, `bias=0`, `reset_voltage=0`,
  `refractory_ticks=0`.
- Output (10): same settings but `threshold=8`.

For EVERY image, reset current, voltage, refractory and all event
banks/queues and class spike counters; one image has **26 total
barrier steps**, including drain. Classify from output spike counts
summed over all 26 ticks: **argmax, first/lowest-class index wins ties;
all-silent output selects class 0**. Preserve exact serialized weights,
axis order, signed24 saturation, bit widths, register/BRAM/DDR bank
semantics. Surrogate-gradient backward is irrelevant to physical
inference and must NOT be implemented on the board.

Avoid conflating event-*scheduled* logical computation with wholly
clock-free asynchronous silicon: the accepted FPGA executes explicit
logical barriers with NEXT queues; the HLS engine is clocked.

## 3. Frozen checkpoint/data/memory fingerprints

Exact project-trained local file:
```
artifacts/p06_a3_candidate_seed20261013/weights_state_dict.pt
```
SHA256 of saved `.pt` bytes:
`0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88`.

Effective integer weight hash:
`1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`.

Frozen TRAIN/validation ordered-index SHA256:
`1cbcb0b2bf481958d6c917ea6d70fa44a20839406f0c824540f8e691edfdd851` /
`3b9520013f30742c3818f55024ea39e3e0632113c487c589fdfbb73c7d274831`.

P03 packed snapshot local directory:
`artifacts/p06_a4_trained_word_snapshot_seed20261013/`.
The six frozen streams (bytes / SHA256):
- `compartment_config_le128.bin`: 672 /
  `a3b520f46a65cc8ee7c1f616337d535d20b6d4f7200ababcd271d1eac1381b5a`.
- `compartment_state_le64.bin`: 336 /
  `52a3e0804d93dc525ec3c67ef8ac5b01756ecf0513e36f3c19435e4c82cb5d29`.
- `synapses_le64.bin`: 203264 /
  `d83b4e401cae33f92a2cba7c53f2f681453f88395b65d503c2c590f6c60e31d7`.
- `axon_index_le16_word_le64.bin`: 8160 /
  `bfec16a76eab97afd5d208e7c1dfd9e6f75ce9f3ff6f1a8f194d52a998d1de72`.
- `route_descriptor_index_le16_word_le32.bin`: 192 /
  `56769029563e60e87d68082e3a11977ec56cf267291ab42893a5f4721edb3510`.
- `route_words_le32.bin`: 128 /
  `0caaba89a0927126aaee06fff208c07c41f380ed9c4f18bb5cf2ccea6ae4a806`.

A4.2 accepted local **P02.1 `LTV3CTX1` DDR** seed directory:
```
artifacts/p06_a4_static_ddr_seed20261013/
  core0_initial_p02_ddr_512k.bin           # 524288 bytes
  p06_a4_static_ddr_freeze_manifest.json  # generator metadata
```
The host DDR-image code uses the **already accepted** 512 KiB dense
bank layout, not a new arbitrary serialization. The actual full
record SHA256 is NOT visible in conversation. **First P07 provenance
task:** capture it from the existing local artifact (no overwrite),
and pin it in P07 deployment metadata.

**CRITICAL:** both `data/mnist_raw/` and `artifacts/` are gitignored
in v3. The actual canonical IDX source bytes, trained checkpoint, P03
packed bins and DDR binary are **only in the user's checkout**,
not moved to `main` by merging code. Back up those exact bytes before
touching board tools or switching machines. Never claim that the
checkpoint lives on GitHub without explicit upload.

## 4. Real repository layout (commands run from v3 root)

```
~/Git/Thesis/                      # git repo root, Python virtualenv .venv-p08
  Loihi_Digital_Twin/
    v3/
      README.md                    # current Track A/P07 status
      LOIHI_TWIN_ROADMAP.md        # authoritative milestone map
      pyproject.toml               # Python project metadata
      .gitignore                   # excludes local artifacts/data
      src/loihi_twin_v2/
        arithmetic.py, compartment.py, axon.py, core.py, chip.py
        packet.py, router.py, barrier.py, runtime.py
        compiler.py, resources.py, mapping.py
        hardware_p03.py           # accepted P03 logical word packing
        hardware_p05.py           # existing 3-context/1-engine shell
        hardware_p08.py           # DDR backing context wrappers
        ddr_abi.py                # P02.1 524288-byte LTV3CTX1 ABI
        ddr_backing.py            # resident-context DDR software model
        p06_input_contract.py     # event encoder/readout
        p06_integer_oracle.py     # independent integer arithmetic
        p06_compact_inference.py  # dense 784/32/10 reference
        p06_packed_replay.py      # independent packed P03 replay
        p06_train_forward.py      # exact forward / surrogate backward
        p06_train_export.py       # CompiledDeployment translation
        p06_a3_data.py, p06_a3_training.py, p06_a3_pilot.py
        p06_a4_snapshot.py        # learned checkpoint -> P03 image
        p06_a4_freeze.py          # P03 stream audit -> P02 static DDR
      scripts/
        p06_a3.py, p06_a4_snapshot.py, p06_a4_freeze.py
        p06_lif_compiler_probe.py, p06_lif_input_probe.py
        p05_deployment.py
        run_p05_1_triangle.sh, run_p05_2_composite.sh
        run_p05_2h_barrier.sh, run_p05_2i_axi_closeout.sh
        run_p07_preflight.sh      # historical preflight, not P07-A acceptance
      tests/
        test_p06_a4_freeze.py, test_p06_a4_snapshot.py
        test_p06_a2_train_export.py, test_p06_a3_training.py
        test_p06_a2_input_contract.py, test_p06_a2_packed_replay.py
        test_p02_ddr_abi.py, test_p02_ddr_backing.py
        test_p05_1_deployment.py, test_p05_2h_barrier.py
        ...                       # extensive prior regression coverage
      software/
        p03/                      # accepted A53/P03 previous firmware
        p05/
          p05_regression_run.c     # accepted P05 A53 diagnostic runner
          p05_deployment.c        # P05 ABI validation
          include/                # relevant C structs/contracts
      hls/core_v2/                # HLS neuron compute implementation
      rtl/
        p03_memory_fabric.v
        p04_packet_router_barrier.v
        p05_context_memory_fabric.v
        p05_virtualized_controller.v
        p08_paged_dispatch_controller.v
        ...                       # accepted RTL and simulation rigs
      vivado/
        create_p05_impl_project.tcl, create_p08_impl_project.tcl
        p05_2i_read_axi_counters.tcl
        run_p05_impl.sh, ...      # device project/build/XSDB scripts
      hardware/
        run_p05_physical.sh, evidence/
      docs/
        P05_FINAL_ACCEPTANCE.md
        P06_A4_FINAL_CLOSEOUT.md
        P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json
        P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md
        P06_TWO_TRACK_LIF_PLAN.md
        P07_A_HANDOFF_SEED.md
        ...                       # dated accepted gates
      data/mnist_raw/             # GITIGNORED; local canonical TRAIN files
      artifacts/                 # GITIGNORED; trained .pt / P03 / DDR
```

**Toolchain details:** User runs Ubuntu/Linux VS Code terminal with
`~/Git/Thesis/.venv-p08` Python environment including PyTorch CPU;
physical Vivado/Vitis/XSDB tools and KV260 board are on the user's
computer. This chat's connected GitHub app can edit tracked source
files and commits; it cannot directly inspect local `.pt`/DDR
artifact bytes or access the physical board. Avoid assuming all
local proprietary tools are available to the assistant. If compiler
or C toolchains are unavailable locally, run legitimate Python tests
and ask the user to verify actual board results.

## 5. Startup / verification / provenance commands

**Normal sync from repository root:**
```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git log -1 --oneline
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
```
New P07 branch later, after inspecting source:
```bash
cd ~/Git/Thesis
git switch main
git pull --ff-only origin main
git switch -c agent/v3-p07-a-784-axon-streaming
cd Loihi_Digital_Twin/v3
```
If branch was already created through GitHub connector:
`git fetch origin && git switch --track origin/agent/v3-p07-a-784-axon-streaming`.
**Do not blindly create a duplicate branch or overwrite local user
changes.** Work on remote feature branch with incremental GitHub
commits, then pull and native test when user is asked.

**Existing immutable local DDR verification (do NOT regenerate it):**
```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
ls -lh artifacts/p06_a4_static_ddr_seed20261013/
sha256sum artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin
python -m json.tool artifacts/p06_a4_static_ddr_seed20261013/p06_a4_static_ddr_freeze_manifest.json
sha256sum artifacts/p06_a3_candidate_seed20261013/weights_state_dict.pt
```
Expected checkpoint digest is given above. **Do not infer/generate
the DDR hash in source unless actual bytes or user's stdout verifies
it**. If user later supplies it, put it in a separately versioned
P07 deployment manifest or explicitly amended source freeze record.

Useful native host regression commands (from v3 root, activated env):
```bash
set -o pipefail
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_a4_freeze.py \
  tests/test_p06_a4_snapshot.py \
  tests/test_p06_a2_train_export.py \
  tests/test_p02_ddr_abi.py \
  tests/test_p02_ddr_backing.py \
  tests/test_p05_1_deployment.py
```
Do not rerun long full MNIST training, replace accepted checkpoint,
overwrite artifacts, or open the official test set.

Backup immutable local bytes:
```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
tar -czf ~/p06_track_a_frozen_local_artifacts.tar.gz \
  data/mnist_raw \
  artifacts/p06_a3_candidate_seed20261013 \
  artifacts/p06_a4_trained_word_snapshot_seed20261013 \
  artifacts/p06_a4_static_ddr_seed20261013
```

## 6. Path A and Path B — purpose, order, and scientific comparison

**Track A = compact physical baseline FIRST**
- Frozen single-core **784→32→10** spiking classifier.
- Already trained and host-validated at 94.39% held-out validation.
- P07-A: implement PS/A53-controlled 784-axon event injection into
  frozen one-core P03/P02 record, exactly 25 input ticks + 1 drain;
  one-tick hidden→output routing, fresh frame reset, 10-class count
  readout; validate first mismatch with independent software engines.
- Only once software/device first-mismatch gates pass, use the frozen
  10k official-test policy. No prediction/label peeking beforehand.
- P08-A: board-level wall-clock latency, throughput, dynamic/idle
  power, energy per full image including A53 orchestration and 26
  barriers, plus software-vs-hardware classification agreement.
  Freeze resource utilization and experiment configuration.
- **Accept Track A physical baseline before pursuing Track B board
  implementation**, so comparisons have honest measurement boundaries.

**Track B = scaled DDR-virtualized comparison SECOND**
- Planned independent **784→1000→10** project-trained classifier,
  following the same event encoder, signed24 LIF and readout
  conventions. Do NOT borrow original snnTorch tutorial weights
  or report tutorial published accuracy as ours.
- Dense topology has **784,000 input→hidden + 10,000
  hidden→output = 794,000 synaptic connections**. Cannot fit in the
  compact one-core 32,768 packed-synapse table.
- Mapping plan **P06-B1**: implement a synapse-aware destination
  partitioner with strict 128KiB logical allocation, 32,768 word,
  4096 axon and 4096 route resource gates, and validate actual
  ingress/routing fanout. A tentative **~27 logical cores**
  (approximately 26 hidden shards + one output shard) is only a
  feasibility estimate, not an accepted placement. At 512 KiB per
  context, 27 logical cores occupy about **13.5 MiB** of DDR backing.
- **P06-B2**: train/freeze separate large project checkpoint with
  real model/weight/dataset/encoder hashes, validation-only GO,
  packed mapped numerical parity; do not unseal official test
  to pick a preferred architecture.
- **P07-B**: execute paged multi-core model using accepted
  **3 resident contexts / one physical engine**, enforce NEXT
  event barriers across residency/page swaps, packet queue order and
  large-fanout bounds; compare with an independent host replay.
- **P08-B**: measure and compare with compact Track A physical
  baseline using identical denominators, defined power/latency
  measurement boundaries and clearly different neural capacity.
  Do not assume larger is faster or more energy-efficient.
- A later unified P09/closure stage can synthesize results and
  differentiate architectural fidelity from inference utility.

**Do not confuse** older `P07_DEEP_SNN_*.md` or `P08_*ANN*`
historical work with these *new* Track A/B acceptance gates.
The current authoritative route is
`docs/P06_TWO_TRACK_LIF_PLAN.md` and
`LOIHI_TWIN_ROADMAP.md`. The old P05 A53 regression protocol is
not by itself a full 784-input MNIST inference app.

## 7. First engineering plan for P07-A (logical sequence and stops)

**P07-A1 — Freeze input/deployment ABI on host (new branch).**
Inspect actual compiler ingress-route IDs, P02 `ddr_abi.py`,
P05 `p05_deployment.c` / A53 runner, RTL memory controller, XSDB
scripts and accepted P05 goldens. Design a **new versioned
many-axon host→A53→PL ingress protocol**, supporting per-tick up
to 784 distinct external axons and bounded packet capacity, with
explicit counts, ordering, byte endianness, ownership and CRC/hash
validation. Validate 26-tick pixel spike schedules on synthetic
frames and several frozen TRAIN-validation images, plus negative
overflow/duplicate/invalid-axon packets. Do NOT change P03 LIF
arithmetic or retrofit P05 v1 silently. **Native host gate**.

**P07-A2 — A53 runtime lifecycle and exact readout.**
Implement full-state reset between images; load pinned P02 static
context; process 25 external-input ticks and 1 drain with NEXT-bank
barrier; collect 10 output spikes/counts, tie-break and silent
reports; ensure no outstanding t=25 packets leak to next image.
Use host-side C11 replay and software/packed oracle first, then
cross-check on Vitis A53 builds. **Native C and device/firmware gate**.

**P07-A3 — KV260 first packet/state conformance.**
Integrate A53 ELF, board memory/MMIO, and any separately approved RTL
shim. Use board-controlled run with synthetic black/white and
preselected frozen validation fixtures; compare per-tick
current/voltage/spikes/packet order/counters to stored 26-step
oracle, stop at first divergence. Preserve existing P05 physical
triangle/composite/AXI goldens. **Physical board gate**.

**P07-A4 — Frozen official 10k MNIST physical evaluation.**
Only after prior gates pass, observe
`docs/P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md` and fix software
hashes, bitstream/ELF, image population and denominator. When
feasible, run **all 10,000 original test images**; if not feasible,
freeze a deterministic subsample rule **before opening test files
or measuring output**. Record full confusion matrix, per-class
counts/recall, silent/tie rates, error/timeout counts, host-vs-board
mismatch counts, tested denominator and uncertainty. Never tune on
official test outcomes.

**P08-A — physical baseline.**
Record KV260 end-to-end latency/throughput, FPGA/PS
input-generation and dispatch overhead, 26 barriers, resident
context load, idle vs active power/energy; compare only like-for-like
power boundaries. Preserve P05 physical acceptance data separately.

**Stop points:** At the end of each P07-A submilestone, commit code
on new feature branch, give user terminal commands for native pytest,
C build, XSDB/Vivado/Vitis and KV260 as applicable; wait for
user-confirmed PASS before progressing or merging. Do not invent
device outputs, timings, official-test results or a pinned DDR SHA256.

## 8. Helpful immutable and authoritative documents

- `LOIHI_TWIN_ROADMAP.md`: milestone status and A/B dependencies.
- `README.md`: concise user-facing status.
- `docs/P06_TWO_TRACK_LIF_PLAN.md`: technical research direction.
- `docs/P06_A4_FINAL_CLOSEOUT.md`: P06 A4 user-accepted software/static
  DDR gates and evidence limitations.
- `docs/P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`: stable model,
  encoder, weights, P03 word streams; A4.2 native status with null
  full-file hash until exact hash retrieved.
- `docs/P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md`: SEALED test policy
  and physical evaluation/reporting constraints.
- `docs/P05_FINAL_ACCEPTANCE.md`: accepted P05 FPGA hardware
  diagnostic context, not MNIST validation.
- `docs/P05_1_DEPLOYMENT_CONTRACT.md`: diagnostic input limitation
  and old P05 DDR metadata/ABI.
- `src/loihi_twin_v2/ddr_abi.py`: accepted static P02.1 DDR layout.
- `src/loihi_twin_v2/p06_a4_snapshot.py` and `p06_a4_freeze.py`:
  exact trained artifact → packed snapshot → 512KiB record.
- `software/p05/p05_regression_run.c`, `rtl/p05_virtualized_controller.v`
  and `vivado/create_p05_impl_project.tcl`: actual PS/PL boundary.
- `docs/P07_A_HANDOFF_SEED.md`: this living handoff.

**Working norms:** Source-specific, incremental research; separate
user-native vs assistant-executed tests; no fake FPGA results; no
unrequested merges; return runnable terminal commands after every
code/test change; be precise about hash evidence and validation vs
official TEST.
