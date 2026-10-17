# P07-A HANDOFF SEED — KV260 board-local inference after P06 Track A

**Prepared:** 2026-10-17 for next conversation.
**Repository:** `https://github.com/Xtimetraveler-Prime/Thesis`
**Project directory:** `Loihi_Digital_Twin/v3`
**Handoff source branch:** `agent/v3-p06-lif-feasibility`
**Target after explicitly approved merge:** `main`; see latest `git log -1 origin/main`
for the actual merge SHA. **Create a NEW feature branch for P07-A.**
**Human workflow:** implement incremental submilestones; run targeted native
tests and provide exact Linux/VS Code commands to the user after every
meaningful stage; user explicitly verifies before accepting/merging;
do NOT silently modify accepted P03/P05 firmware/HLS goldens.

## Milestones and scientific framing

- P00–P03 accepted: v3 logical architectural twin, 24-bit integer
  P03 LIF engine, packet scheduling and packed memory model.
- P04 multi-engine design explicitly deferred. P05 accepted on physical
  KV260: one P03 engine servicing up to three resident contexts,
  asynchronous-looking NEXT-bank logical barriers and DDR-backed
  virtualization. P05 work proves **diagnostic** workloads, not MNIST.
- P06 Track A **784 pixel inputs → 32 hidden LIF → 10 output LIF**:
  A1 structural compiler feasibility, A2 independent integer arithmetic,
  deterministic event/readout + PyTorch training-forward parity, and
  A3 actual MNIST training source are accepted at native host level.
- **Trained candidate:** 8 epochs, seed 20261013, 50,000 canonical
  MNIST TRAIN images and 10,000 held-out TRAIN-derived validation images.
  Epoch 8 selected; train accuracy **95.34%**, validation **94.39%**
  (9,439/10k), only 2/10k silent; original official TEST **SEALED**.
  This is NOT hardware accuracy, not the source snnTorch tutorial
  checkpoint and not original Loihi silicon performance.
- **A4.1 user native accepted:** `P06_A4_SOFTWARE_SNAPSHOT_PASS=1`,
  five diagnostic frames × all 26 timesteps EXACT across PyTorch
  integer forward, independent integer dense oracle, independently
  decoded P03 hardware-word replay, and `LogicalChip`.
  One-core packed image: 42 compartments, 816 registered input axons
  (784 external + 32 hidden next-tick), 25,408 synapse words,
  32 route descriptors and 32 routes. User supplied all six packed
  word-stream SHA256; source-pinned below.
- **A4.2 static DDR seed code implemented but NEW NATIVE AUDIT NOT YET
  USER-VERIFIED.** `p06_a4_freeze.py` creates a complete 524288-byte
  core0 initial record using **existing P02.1 LTV3CTX1 DDR layout**,
  verifying P03 bytes, sparse/dense banks, payload SHA256, and frozen
  user-trained checkpoint. It is NOT a P05 diagnostic payload, A53
  application, event streaming ABI or KV260 MNIST inference.
- P07-A is next: FPGA-board-local single-core inference with 784 distinct
  external axon events, 25 event ticks+1 drain, fresh reset per image,
  output spike counts and host-vs-board diagnostics.
- P08-A must accept a physical compact accuracy, latency/throughput,
  idle/active power and energy baseline before Track B.
- Track B planned afterward: independent 784→1000→10 training,
  synapse-aware sharded P06-B mapper; ~27 DDR logical cores only a
  planning hypothesis; not an accepted scalable mapping.

## Frozen computation semantics (do not change)

- Raw uint8 row-major 28×28 pixels, no float normalization.
- For timestep t in 0..24, pixel index i, brightness p:
  s=(t+17*i)%25. Emit a spike iff
  `((s+1)*p)//255 > (s*p)//255`. Exactly floor(25p/255)
  external spikes per pixel across 25 steps.
- Tick 25 has zero external input. One-core hidden spikes at tick t
  reach output at t+1 via NEXT-event bank. Drop hidden spikes
  emitted on t=25 at frame boundary; no cross-image leakage.
- Sign-24 saturating neuron arithmetic, strict `voltage > threshold`,
  P03 fixed-point round-away-from-zero decay.
  Hidden fixed LIF: current_decay=4096, voltage_decay=4096,
  threshold=32, bias=reset=refractory=0.
  Output fixed LIF: same decays, threshold=8, others=0.
- Reset current, voltage, refractory, output counters and all pending
  event banks for every image.
- Readout: count ten output neuron spikes over 26 ticks; argmax
  with first/lowest-class tie, including silence -> 0.
- Never substitute analog, stochastic, same-step propagation, or a
  different PyTorch `snn.Leaky` forward and claim numerical parity.

## Exact frozen artifact identity (local bytes NOT on GitHub)

`v3/artifacts/p06_a3_candidate_seed20261013/weights_state_dict.pt`
checkpoint SHA256:
`0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88`

Effective destination-major integer weight SHA256:
`1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`.

Frozen train/validation ordered-index SHA256:
`1cbcb0b2bf481958d6c917ea6d70fa44a20839406f0c824540f8e691edfdd851` /
`3b9520013f30742c3818f55024ea39e3e0632113c487c589fdfbb73c7d274831`.

`v3/artifacts/p06_a4_trained_word_snapshot_seed20261013/`:
- `compartment_config_le128.bin`: 672 bytes, SHA256
  `a3b520f46a65cc8ee7c1f616337d535d20b6d4f7200ababcd271d1eac1381b5a`.
- `compartment_state_le64.bin`: 336 bytes, SHA256
  `52a3e0804d93dc525ec3c67ef8ac5b01756ecf0513e36f3c19435e4c82cb5d29`.
- `synapses_le64.bin`: 203264 bytes, SHA256
  `d83b4e401cae33f92a2cba7c53f2f681453f88395b65d503c2c590f6c60e31d7`.
- `axon_index_le16_word_le64.bin`: 8160 bytes SHA256
  `bfec16a76eab97afd5d208e7c1dfd9e6f75ce9f3ff6f1a8f194d52a998d1de72`.
- `route_descriptor_index_le16_word_le32.bin`: 192 bytes SHA256
  `56769029563e60e87d68082e3a11977ec56cf267291ab42893a5f4721edb3510`.
- `route_words_le32.bin`: 128 bytes SHA256
  `0caaba89a0927126aaee06fff208c07c41f380ed9c4f18bb5cf2ccea6ae4a806`.

The manifest `docs/P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`
and closeout `docs/P06_A4_FINAL_CLOSEOUT.md` are source tracked.
Raw `data/mnist_raw/` and `artifacts/` are **gitignored** and reside
ONLY in the user's host checkout. Preserve and back up these files
before changing branches or machines. Do not commit raw archives,
trained binary checkpoints or generated artifacts without an
explicit separate storage/reproducibility decision.

## FIRST continuation task — final native DDR seed audit

Run on user's PC (after merge) in VS Code terminal:

```bash
cd ~/Git/Thesis
git fetch origin
git switch main
git pull --ff-only origin main
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
set -o pipefail

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_a4_freeze.py \
  tests/test_p06_a4_snapshot.py \
  2>&1 | tee /tmp/v3_p06_a4_closeout_native.log

PYTHONPATH="$PWD/src" python scripts/p06_a4_freeze.py \
  --candidate-dir artifacts/p06_a3_candidate_seed20261013 \
  --snapshot-dir artifacts/p06_a4_trained_word_snapshot_seed20261013 \
  --output-dir artifacts/p06_a4_static_ddr_seed20261013 \
  2>&1 | tee /tmp/v3_p06_a4_final_ddr_freeze.log
```

Expected `P06_A4_STATIC_DDR_FREEZE_PASS=1`, actual
`P06_A4_DDR_SHA256=<64hex>`, and both official-test and
P07 streaming caveat statuses. Preserve exact checksum in the
next P07 reproducibility record. If output directory already exists,
DO NOT overwrite; audit the existing manifest/bytes before choosing a
fresh output directory. Do not claim this gate passed until user reports
native results; do not label P06's full static DDR image accepted before
that final audit.

Backup example (from v3 root):
`tar -czf ~/p06_track_a_local_artifacts_backup.tar.gz artifacts/p06_a3_candidate_seed20261013 artifacts/p06_a4_trained_word_snapshot_seed20261013`

## Next P07-A engineering plan (no implementation until gate)

1. Begin feature branch from accepted `main`:
   `git switch -c agent/v3-p07-a-784-axon-streaming` or create the
   branch via GitHub integration, no edits on main.
2. Audit `src/loihi_twin_v2/ddr_abi.py`, `hardware_p05.py`,
   `hardware_p08.py`, `software/p05/`, FPGA block diagram,
   KV260 A53 MMIO and barrier schedule against frozen P03 traces.
3. Design new **versioned** A53 deployment/ingress ABI for up to
   784 external pixel axons/tick, one core and 26 timesteps/image;
   validate order, no duplicates, event capacity, next-tick packet
   barriers and reset lifecycle independently, without changing
   accepted P05 diagnostic golden tests.
4. Build deterministic host emission of 25x active pixel axons and
   no-input drain tick; PS/PL first-mismatch trace compares one-step
   current/voltage, spikes, packets and ten readout counts with frozen
   software diagnostics; then on-board first synthetic, then frozen
   validation fixtures. Never silently alter signed24 or readout rules
   to accommodate board behavior.
5. Before official test access, obey
   `docs/P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md`: full 10,000
   official test population in original order when feasible, or
   separately freeze a reduced sampling plan **BEFORE** accessing test
   labels/results. No test-set hyperparameter tuning.
6. Report how power, latency and energy measurement boundaries include
   the board's input encoding, PS dispatch, context load, 26 barriers,
   reading outputs and idle/active baselines. Do not compare to Loihi
   silicon power as if measured.

## GitHub documents and responsibilities

- `LOIHI_TWIN_ROADMAP.md`: authoritative milestone tracker.
- `README.md`: current user-facing status.
- `docs/P06_TWO_TRACK_LIF_PLAN.md`: Track A and delayed Track B.
- `docs/P06_A4_FINAL_CLOSEOUT.md`: exact A4.1 acceptance and
  remaining A4.2 static DDR native gate.
- `docs/P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`: accepted
  checkpoint/byte manifest.
- `docs/P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md`: sealed test protocol.
- `src/loihi_twin_v2/p06_a4_snapshot.py`: trained P03 reference path.
- `src/loihi_twin_v2/p06_a4_freeze.py`: new P02 DDR static seed.
- `docs/P05_FINAL_ACCEPTANCE.md`: accepted physical P05 diagnostics.
- `docs/P06_A3_TRAINED_CANDIDATE_A4_1_GATE.md`: reported training
  and host P03 parity gate.

**Communication workflow:** Run or develop actual code, commit on a
feature branch, stop for user's native/physical verification with
copy-pastable VS Code terminal commands; update roadmap only after
user confirms. Do not claim tools can physically access the KV260.
