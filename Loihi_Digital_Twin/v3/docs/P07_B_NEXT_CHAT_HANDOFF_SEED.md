# P07-B — NEXT CHAT HANDOFF SEED (start from merged `main`)

> **Purpose:** Copy the entire document into a fresh ChatGPT project conversation, or give the new instance its GitHub URL and tell it to read it first. This is the successor to the detailed B1/B2 handoff seed. It preserves the accepted Track A/B research identity, software architecture, evidence boundaries, operator workflow, file paths and next-stage plan.
>
> **Snapshot:** 2026-10-19, after user-attested B2.5 native PASS and confirmed ordered B1/B2 PR merges. New work must be based on **`main`**, not either historical `agent/v3-p06-...` development branch.

## 0. Immediate instruction to next assistant

We are developing a **Loihi-inspired FPGA architectural digital twin** on an AMD/Xilinx **KV260 (K26 Zynq UltraScale+)** using a mixture of host Python model/oracles, Vivado/Vitis hardware, and a standalone Cortex-A53 runtime. The active code is GitHub repository **`Xtimetraveler-Prime/Thesis`**, folder **`Loihi_Digital_Twin/v3/`**, branch **`main`**. The user has closed and merged P06-B1 (software scalable packing) and P06-B2 (independent trained large checkpoint / host-verifiable freeze). Your next job is to **begin P07-B: real scaled 27-logical-core autonomous inference on the KV260**, carefully staged and user-gated.

**First actions:** fetch current GitHub `main`; read `Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md`, `README.md` in the v3 tree, `docs/P06_B2_5_HOST_SOFTWARE_EXIT_AND_P07B_HANDOFF.md`, `docs/P06_B2_5_USER_EVIDENCE_LEDGER.json`, and the existing P03/P05/P07-A runtime docs before changing implementation. Inspect the actual P05 A53 C code, P03/P02 hardware interfaces, B1.3 multi-ingress host ABI, B1.5 paging model and B2.4 frozen deployment format. Create a **fresh `agent/v3-p07-b-...` development branch from up-to-date `main`** for P07-B. Decompose into verified, independently testable P07-B submilestones. Give the user exact terminal `git fetch/pull` and native test commands **every time code changes**, and wait for user confirmation before advancing. **Do not merge until the user explicitly authorizes it.**

GitHub connection tools may be present via `functions.exec` using `tools.mcp__GitHub__*` methods. Use the connector for actual repository reads/writes, compare branches, create branch/PR and commits. Never claim GitHub/physical tests were run if only files were written.

## 1. Git/merge state — already integrated

The user explicitly said all B2.5 tests passed and authorized ordered merges. GitHub reported **both merged successfully**:

- **P06-B1 PR #46**, from `agent/v3-p06-b1-scalable-packing` into `main`: merge commit **`35ea181360ebf15627c2943090fbdc3c6bf3949e`**.
- **P06-B2 PR #47**, historically stacked on B1, retargeted to `main` after B1 merged: merge commit **`42f84de3bbbe62302599818c39e7e54747ce8aa2`**.
- Post-merge documentation-only commits on `main` updated the README, v3 README, roadmap, B2.5 closeout/evidence ledger and this seed. **`main` may advance after this seed is written; run `git fetch origin && git switch main && git pull --ff-only origin main` and inspect `git rev-parse HEAD` instead of assuming a historical hash is its current head.**
- P06-B1/B2 branch and PR references in older stage documents may retain historical `DRAFT/UNMERGED` wording that was true *when authored*. The authoritative integration truth is these GitHub merge commits and the latest top-level v3 roadmap, not old branch-status prose.

**All accepted Track A code, checkpoint identity, official-test observations and original P05 hardware artifacts are preserved.** The merged B1/B2 code adds new source modules and docs rather than mutating Track A.

## 2. Core architecture and exact neural contract (do not accidentally change)

The FPGA virtualizes logical neuromorphic cores into fixed **P02 512 KiB DDR backing records**, with up to **three physical resident context slots** and **one accepted P03-compatible HLS inference engine**. P03-P05 physically demonstrated standalone A53 ownership of a smaller diagnostic paging/routing workload. This is a **digital synchronous, global-barrier/tick, event-driven simulator** inspired by Loihi-1, NOT proof of truly asynchronous silicon, genuine original Intel Loihi SRAM/NoC/power equivalence, or Loihi 2 silicon behavior.

The trained SNN application uses:
- Raw **MNIST 28×28 unsigned-byte images = 784 input channels**. Original canonical 60k MNIST **TRAIN** IDX archives; frozen deterministic **50k training/10k TRAIN-derived validation** index split, seed `20261013`.
- Deterministic **`p06-uint8-quota-phase17-v1`** quota-and-phase17 encoder: **25 input ticks** plus **one external-free drain tick**, exactly **26 logical ticks per image**; keep strict timing and no hidden normalization.
- **Signed-24-bit saturating integer LIF** state/current/voltage recurrence, signed quantized weights, strict **`>` threshold**, accepted refractory/reset behavior. Route hidden-to-readout spikes to the **NEXT logical tick**, not the same tick. Clear/reset per-image neuron states, CURRENT/NEXT banks, packets and readout counters.
- Readout ten output spike counts over all 26 ticks; **`argmax`, first/lowest-index tie**, including all-silent output -> class 0.
- Use existing accepted source-level independent reference and P03 P02 signed-int packing. Never silently substitute analog floating inputs, different weight widths, subtract-reset, a different input schedule or different readout function.
- A P07-B A53/PL runtime must preserve the **source graph and all 794,000 dense connections**, *including explicit signed zeros*; P03 packing may exploit source-preserving template sharing, but cannot drop observable semantics.

## 3. Accepted Track A is frozen; historical P07-A/P08-A physical baseline

Track A's original project-trained **784→32→10** LIF classifier (one logical FPGA core) was independently trained/selected on TRAIN-derived validation **94.39%**, then achieved **94.56% = 9456/10000** on the official MNIST TEST through **actual KV260 P07-A physical inference**. The frozen Track A tensor SHA256 identities:
- Checkpoint file SHA256 **`0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88`**.
- Signed-integer weights SHA256 **`1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`**.
- Track A hardware acceptance: `docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`, original 26-tick integer oracle, physical board readout and 10k official TEST protocol, frozen image/ELF/bitstream evidence.
- P08-A **LATENCY-ONLY physical baseline accepted**. Power/energy P08-A4 deferred/unmeasured. Read `docs/P08_A1_MEASUREMENT_CONTRACT.md` and the P08-A timing closeout sections before comparing physical costs. A baseline source here records examples of ~35.7 ms original A2.1/A2.2 image timings and ~30.3 ms RAW784→CLASS CPU/physical endpoint, but CPU/FPGA endpoints differ and these are not an isolated PL throughput or energy speedup. **Do not rerun Track A official TEST**, use its frozen evidence.

## 4. Accepted Track B B1 — host scalable multicore feasibility

P06-B1.1–B1.6 **USER-ATTESTED HOST SOFTWARE PASS**; PR #46 **MERGED**. Important files:
- `src/loihi_twin_v2/p06_b1_contract.py`: real B1.1 exact source-independent P03/P02 capacity (1024 compartments, 4096 axons, 4096 routes, ≤32768 P03 synapse words, ≤131072 logical synapse bytes, ≤4096 CURRENT events and ≤4096 NEXT/emitted packets per core). Fixed P02 **524,288 bytes/core**; one engine and three resident slots.
- `src/loihi_twin_v2/p06_b12_partition.py`: deterministic **synapse-aware destination-neuron** packing; source-preserving `NetworkSpec` → `CompiledDeployment` and original packed P03/P02 images. The previous simple P06-A compartment-first compiler is NOT an acceptable substitute for this 1000-neuron graph.
- `src/loihi_twin_v2/p06_b13_streaming.py`: **host-only versioned proposed wire protocol**, `P06B13I1` for many 784-channel source ingress/per-core destination binding and `P06B13R1` for next-epoch packet frames. The accepted old P05 A53 diagnostic supports **one registered external input axon/core**, NOT the B1.3 ABI. **No equivalent A53 or PL B1.3 physical parser has been accepted**. P07-B must implement hardware-oriented streaming and prove ABI layout, payload CRC, deployment digest, limits, ordering, buffer bank ownership and fail-closed behavior.
- `src/loihi_twin_v2/p06_b14_differential.py` and `p06_b14_monolithic.py`: true **independent monolithic scalar LIF** and actual partitioned logical-core 26-tick state/input/spike/NEXT packet differential. Not a mere same-implementation self comparison.
- `src/loihi_twin_v2/p06_b15_paging.py` (inspect actual filename/import paths in `docs/P06_B1_5_THREE_SLOT_PAGING_ESTIMATE.md`): **HOST-ONLY** three resident slots, single physical engine, LRU/page-traffic model. P05 original physical page-transfer sizes **438,272 bytes in** and **106,496 dirty bytes out**, 256-byte AXI bursts; prior **5-core/80-dispatch physical P05 run 43,581,440 measured page-engine bytes**.
- **B1.2 synthetic full dense 784→1000→10** source had 794,000 edges, **27 cores: 26 hidden cores + one 10-neuron readout**, 14,155,776 initial DDR bytes, max logical synapse cost **128,576 bytes/core**, max worst CURRENT demand **1,000/core**.
- B1.5 *modeled* scaled 702-dispatch ascending cache order: 702 full ins+outs, **382,427,136 estimated** bytes; alternating order 627 full ins+outs / 75 hits, **341,569,536 estimated** bytes. These **ARE NOT physical scaled measurements**. Sparse27 separately had true 26-tick host numerical parity, not full trained-dense until B2.3.
- B1 source, acceptance gates and limitations: `docs/P06_B1_6_FINAL_HOST_SOFTWARE_ACCEPTANCE.md`, `docs/P06_B1_6_USER_ACCEPTANCE_LEDGER.json`, B1.3/1.5 documents and `LOIHI_TWIN_ROADMAP.md`.

## 5. Accepted Track B B2 — actual trained model and frozen P02 contexts

P06-B2.1–B2.5 **USER-ATTESTED NATIVE HOST SOFTWARE PASS**; PR #47 **MERGED**. This was a genuinely **new separately trained project-defined** model using published LIF methodology, not an original Loihi chip pretrained model, not the original snnTorch tutorial's analog/reset semantics.

**B2.1** (`src/loihi_twin_v2/p06_b21_training_foundation.py`): 784→H→10 H≤1000 with original accepted signed24 STE/26-tick forward, explicit 794k source edges, real B1.2 packer; no Track A mutation. B2.1 initially untrained 1000-neuron shape physically NOT tested, structural 27-core packing native PASS.

**B2.2** (`src/loihi_twin_v2/p06_b22_training.py`, `scripts/p06_b22_train.py`): independent full 50k TRAIN + 10k train-derived validation model; default seed 20261019, 8 epochs, batch64, Adam lr0.05, surrogate width16, 0.60 engineering validation GO floor. **Best epoch 6; train-derived held-out validation accuracy `0.9708` = 97.08% on all 10,000 images, zero silent outputs; mean output spikes 34.1821/image.** This is **NOT official B2 MNIST TEST**. Real candidate local `artifacts/p06_b22_candidate_1000/`.
- Original checkpoint `weights_state_dict.pt` file SHA256 **`93e43915b38cf3c815a125bbab2788e45209f0ccd024d098b25b82a0a8cd0957`**.
- Dimension-bound signed integer weight SHA256 **`4a20357fc5e77465380c1600e7e82cda515bbafc233fb9e3a1205bca9d00d8b0`**.

**B2.3** (`src/loihi_twin_v2/p06_b23_trained_audit.py`): actual trained 794,000-edge graph, **27 actual trained P02 cores**. SOURCE SHA **`0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a`**, B1.2 COMPILED SHA **`02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`**, B1.1 CAPACITY-AUDIT SHA **`82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498`**. User ran actual full trained dense 26-tick monolithic vs partitioned LIF and PyTorch readout parity for frozen *TRAIN-derived validation ordinals* **0, 1, 2**, original TRAIN IDX IDs **37384, 27347, 20178**. True every-neuron state/spike/routed packet parity for all 26 ticks. Monolithic/partitioned trace SHA strings differ because **they use different schemas** (do not demand byte-identical SHA). Three frames do NOT imply all 10,000 packed numerical frames verified.

**B2.4** (`src/loihi_twin_v2/p06_b24_freeze.py`, `scripts/p06_b24_freeze.py`): actual local no-overwrite snapshot `artifacts/p06_b24_frozen_1000/` containing **33 SHA-indexed files** + top-level manifest: unchanged checkpoint/candidate metadata, signed full source graph JSON, serialized B1.2 mapping, frozen three-frame B2.3 numerical trace evidence, the **sealed official TEST protocol**, and **27 initial P02 512 KiB DDR binaries** = **14,155,776 bytes** initial backing. User ran both ordinary and `--deep` original P02 byte reconstruction and reported `P06_B24_FROZEN_INTEGRITY_PASS=1` for **all 33 assets, all 27 initial contexts**.
- B2.4 *canonical unsigned content* manifest SHA256 **`d01ccd2d5a85b22f81580cd7800933642e19d1a43e8a2f38eac1f6c4d83cab90`**.
- SHA256 of on-disk, pretty-printed **`frozen_manifest.json` file bytes** **`d71e2827a81ab1f00ef1e89446540ac04b7d7b34d89b30d46cd6e4ff013c7a63`**.
- These are **two distinct hash domains**. The immutable original manifest has historical `user_native_B2_4_accepted=false` even though *subsequent native user verification passed*. Never edit it merely to flip status because this would destroy both accepted hashes. Acceptance history is appended **externally**, in `docs/P06_B2_5_USER_EVIDENCE_LEDGER.json`.
- The freeze is tamper evident/no-overwrite, NOT OS-WORM or cryptographically signed external custody. Initial DDR records are not runtime mutable DDR dumps and do not prove hardware ownership.

**B2.5** (`src/loihi_twin_v2/p06_b25_acceptance.py`, `scripts/p06_b25_acceptance.py`): independently read-only acceptance for the original B2.4 33 assets, dual SHA, original 27 P02 records/capacity limits, 3 trace witnesses and sealed protocol; outputs **P07-B design and planning GO** but `go_for_p07b_scaled_physical_execution=false` and `go_for_official_mnist_test_unseal=false`. User reported **all B2.5 native tests and acceptance commands passed**, then explicitly authorized merges. B2.5 exact raw stdout/test count wasn't pasted; don't invent it. Full closeout `docs/P06_B2_5_HOST_SOFTWARE_EXIT_AND_P07B_HANDOFF.md` and external ledger `docs/P06_B2_5_USER_EVIDENCE_LEDGER.json`.

**User-local gitignored files** are **not on GitHub**:
```text
~/Git/Thesis/Loihi_Digital_Twin/v3/data/mnist_raw/
  train-images-idx3-ubyte.gz
  train-labels-idx1-ubyte.gz
~/Git/Thesis/Loihi_Digital_Twin/v3/artifacts/
  p06_b22_candidate_1000/
  p06_b24_frozen_1000/
```
Do not request uploads of these massive/private-ish binaries unless absolutely needed. They remain unchanged, and B2 official `t10k` TEST has NEVER been unsealed for B2.

## 6. Physical P03/P05/P07-A groundwork to reuse, not overclaim

Read `docs/P03_FINAL_ACCEPTANCE.md`, `docs/P03_PS_AUTONOMOUS_APPLICATION.md`, `docs/P03_1_AUTONOMOUS_RUNTIME_CONTRACT.md`, `docs/P05_FINAL_ACCEPTANCE.md`, `docs/P05_2I_ACCEPTANCE.md`, `docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md` and their associated C/Vitis/Vivado source. **P03 physical A53 is standalone/bare-metal**, not Linux; PC only initializes/programs, launches and gathers passive evidence. The accepted MMIO shell includes **0xA4000000..0xA4000FFF**, on correct **FPD 128-bit PS master + SmartConnect width/protocol bridge**. Existing P05 page engine uses **HP0 AXI** (256 B bursts). There is no physical second/third HLS engine; P04 multi-engine remains deferred.

Physical P05 accepted at **5 logical cores, 3 physical slots, 1 HLS engine**; 80 dispatches / 16 barriers / 43,581,440 measured **PL page-engine-only** transfer bytes, verified A53 + independently read register counters, not full-system DDR traffic. The new 27-core P06 software freeze is compatible *structurally* with original P02/P03 packing but **not yet proven physically runnable** with original P05 A53 ABI. Old accepted Vivado shell/bitstream/ELF are baselines, not evidence of new P07-B firmware. Do not infer new 27-core on-chip memory fits without considering 3-slot virtualization.

P07-A already physically validated a compact one-core 784-channel classifier; study its accepted per-image streaming/reset/model-verification approach for reuse. **P07-B differs** in need for 26 hidden partitions + one readout across paging/packet fanout barriers and transaction-safe current/next event delivery. Physical A53 may need new memory allocation and ownership for input frames, routing queues, DDR contexts, run control, debug evidence and failure rollback.

## 7. Next phase: P07-B planned development (new branch, individually gated)

Authoritative planned scope: `LOIHI_TWIN_ROADMAP.md` section **P07-B — Scaled multi-logical-core physical inference** and `docs/P06_B2_5_HOST_SOFTWARE_EXIT_AND_P07B_HANDOFF.md`. User has not yet adopted the following **proposed submilestone numbering**; present an accurate initial plan and implement one user-testable step at a time:

1. **P07-B.1 — Physical/runtime feasibility contract and owner map.** Inspect real accepted shell and standalone A53 code. Resolve exact PS/PL DDR reservation/addressing; 27×P02 stride; three HLS resident contexts; one engine, reset/status registers; payload/CRC boundaries; firmware RAM/linker/buffer capacities; page-engine bursts; and expected C/native tests. Define abort codes and resource admission. Pin a traceable versioned map and host/board contracts; **no new physical claim**.
2. **P07-B.2 — New A53-compatible B1.3 multi-ingress/multicore command stream**, corresponding to existing `P06B13I1/P06B13R1` host serialization or a rigorously explained versioned hardware adapter. No use of old P05 single-axon diagnostic path as if it implemented 784 input channels. Independently compare C/native frame parsing + per-core source fanout, ordering, deployed source+compiler SHA, CRC, limits and rejection atomicity to Python oracle.
3. **P07-B.3 — 27-context virtual paging, NEXT routing, 26-tick global barrier scheduling.** Three resident logical contexts, one engine, 27 backing P02 records; deterministic LRU/page replacement or justified equivalent; correct dirty evictions/page-outs; no stale state between images; packet queue ownership; full traffic counters. Prove all contexts serviced, including zero-spike cores, and exactly one tick NEXT routing.
4. **P07-B.4 — Bounded real KV260 provisioning/programming and trace comparison.** Reuse known-good P03/P05 firmware/bitstream workflow, preserve accepted original hardware baseline. Start with short synthetic 2–5 core routing/pages and one frame, gradually scale to all 27 with original trained snapshot. Include all-255 worst-case, negative oversubscription/CRC, per-core P02 bytes, full state/current/voltage/spikes/packet first-divergence diagnostics vs original independent source oracle. No official TEST yet.
5. **P07-B.5 — Predeclared 27-core physical TRAIN-derived validation corpus**, independently accepted host-vs-board complete 26-tick parity, predictions and trace SHAs, reproducible load/run IDs, available board-side SRAM/DDR ownership and immutable bitstream/ELF hashes. Only after an explicit user gate assess feasibility of the **separately frozen B2 official TEST protocol**. Never tune B2 weights/hyperparameters on TEST.
6. **P07-B.6 — P07-B physical acceptance and P08-B handoff**: exact artifact hashes, measured physical page-engine read/write bytes, last writeback, barrier/dispatch counts, end-to-end per-image time (proper CPU/PS/PL scope) and power/energy feasibility, remaining NO-GOs and P08-B measurement design. P08-B is future physical scaling characterization; not host estimates. Multi-engine remains optional/deferred.

These are a **suggested outline**, not proof that every stage is implemented. In particular don't start with a speculative Vivado rebuild or direct FPGA programming before checking original accepted HLS memory/register owner map and A53 parser route.

## 8. Reproducible PC commands and required assistant workflow

Linux workstation likely checks out repository at `~/Git/Thesis`, Python venv `~/Git/Thesis/.venv-p08`; active tree `~/Git/Thesis/Loihi_Digital_Twin/v3`.

For first fresh handoff:
```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# Frozen accepted B2 source/negative host tests (no official TEST):
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b25_acceptance.py \
  tests/test_p06_b24_freeze.py \
  tests/test_p06_b23_trained_audit.py \
  tests/test_p06_b22_training.py \
  tests/test_p06_b21_training_foundation.py \
  tests/test_p06_b15_paging.py \
  tests/test_p06_b14_differential.py \
  tests/test_p06_b13_streaming.py \
  tests/test_p06_b12_partition.py \
  tests/test_p06_b1_contract.py

# Read-only real local freeze integrity (costlier with --deep):
PYTHONPATH="$PWD/src" python scripts/p06_b25_acceptance.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" --deep

# Later, after creating a new reviewed P07-B branch:
# git switch <new-p07b-branch>
# git pull --ff-only origin <new-p07b-branch>
# ... exact new phase tests supplied by assistant ...
```

The ordinary default tests may show historical **optional stress skips**, which should be recorded and not mislabeled as failing or as if they were run. User had previously run opt-in 1000-width structural and selected dense 27-core host numerical checks explicitly. The repository connector can read files and commit changes, but **assistant has no automatic access to the user's local frozen model/board**. Never call a code commit a native pass, or a host model a physical run. Always give native terminal commands after every substantive change; wait for user verification before moving to the next submilestone.

Work in a new branch and a reviewable PR from updated `main`, not historical B1/B2 branches. Keep later changes scoped: approved HLS/Vivado/source/C firmware files may be revised only deliberately, with regressions. Do not modify Track A frozen source/weights/tests, original Track B candidate/freeze byte artifacts or official TEST protocol. Maintain machine-readable evidence ledgers, versioned ABI schema, deterministic checksums, and identify **measured vs modeled vs user-attested vs not tested**.

## 9. Scientific/communication guardrails

The two checkpoints differ: Track A 32-hidden vs Track B 1000-hidden. Their separate 94.56% official TEST (A) vs 97.08% TRAIN-derived validation (B) cannot be directly compared as test accuracies or attributed wholly to hardware scaling. The P06 compiler/host oracle does not emulate original Intel Loihi silicon NoC, SRAM, true asynchronous analog timing or measured chip energy. Current P07/P08-A accepted physical baseline does **not** transfer automatically to 27-core execution. B1.5 predicted scaled page traffic remains only an **ESTIMATE**. Official B2 TEST remains **SEALED** until separate successful P07-B physical numerical acceptance and predeclared run identities.

**End of new-chat seed. Start P07-B from merged `main`; first inspect source/hardware + write the B.1 contract and native tests.**
