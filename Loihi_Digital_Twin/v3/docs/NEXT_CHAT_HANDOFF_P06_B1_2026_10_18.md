# NEXT CHAT HANDOFF SEED — P08-A MERGED → P06-B1 SCALED MAPPING

**This is a copy/paste-ready continuity seed for a NEW ChatGPT conversation working on the same Thesis repository.**  
**Date:** 2026-10-18 America/Denver (user-local); raw evidence filenames use UTC 2026-10-19.  
**Canonical project:** `Xtimetraveler-Prime/Thesis`; source directory `Loihi_Digital_Twin/v3`.  
**Primary reading:** `Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md` → **P06 Track B**, **P07-B**, **P08-B**; `docs/P08_A_LATENCY_ONLY_FINAL_ACCEPTANCE_CANDIDATE.md`; `docs/P08_A5_CPU_PHYSICAL_LATENCY_RESULTS.md`; `docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`; `docs/P05_2I_ACCEPTANCE.md`.  
**Status:** **P08-A latency-only scope EXPLICITLY USER-ACCEPTED AND PR #45 MERGED INTO `main`**. GitHub successful merge commit: `b1ead8a2983e555e762f3176ffcdc5c7de819aee`, verified that `main` matched that SHA immediately after merge. This handoff document is created **after** that merge on `main`.

---

## 1. How to work with this user

The user is an EE thesis researcher building an **FPGA digital twin inspired by Intel Loihi-1 neuromorphic processing** on a **Xilinx Kria KV260**, with Cortex-A53 software orchestrating a frozen P03 FPGA/PL neural engine. It is **NOT** a transistor-accurate Loihi clone, an Intel Loihi chip, or physically asynchronous FPGA circuitry; event-driven behavior is represented with deterministic discrete spike ticks, routes, state and packet epochs.

User preferences (high priority):
- Work incrementally, with clearly numbered milestones/sub-milestones, robust fail-closed behavior, original-source numerical oracles, exact SHA provenance, and explicit user verification gates.
- User runs Linux/VS Code on PC and executes real board tests. Assistant can change GitHub source through the connected GitHub tools, but has **no direct physical KV260 access**; do not invent actual hardware outcomes or say a new board test passed.
- **After EVERY remote source or documentation change, provide terminal commands** to `git fetch`, `git switch`, `git pull --ff-only`, activate `~/Git/Thesis/.venv-p08` (unless later changed), `PYTHONPATH="$PWD/src" python -m pytest ...`, and relevant compile/syntax checks. Always specify exact path and explain whether commands access the physical board.
- Never merge without explicit user permission for the **particular next PR**, even though the user explicitly authorized **PR #45**; do not reuse that authorization for P06-B.
- When user reports native test failures, inspect and repair the actual code/fixture, do not relax genuine hardware safety guards, then stop for user rerun. Report honestly if CI/new native tests were not independently run.
- Preserve original accepted sources and evidence; keep new experiments on separate branch and in uniquely named evidence directories. Do not quietly recompute model weights, change accepted checkpoints, alter original packed P03/P07 neuron semantics or access official TEST data during engineering.

Tool workflow available via `functions.exec`: discover tools on `ALL_TOOLS` by name, use `tools.mcp__GitHub__fetch_file({repository_full_name:"Xtimetraveler-Prime/Thesis",path:"Loihi_Digital_Twin/v3/...",ref:"main"})`, `create_file`, `update_file`, `compare_commits`, GitHub PR tools. User's PC paths are **not** files in GitHub. Never equate reading a terminal excerpt with independently rehashing raw evidence.

---

## 2. Accepted frozen Track A infrastructure — DO NOT REGRESS

### Board, route, persistent model and original checkpoint
- Board: **KV260**, one FPGA/PL HLS compute engine and P05 **three full resident hardware contexts**, with additional 512 KiB logical core images in DDR and A53-managed paging. P05 physical proof: **five distinct complete DDR logical cores over three resident slots**, original 80 PL dispatches, 16 barriers, 77 evictions, 318 checkpointed neural state/packet/DDR assertions and read-only FPGA HP0 AXI transaction counters passing. See `docs/P05_2I_ACCEPTANCE.md`.
- Dedicated **JTAG-only bare-metal** FPGA/ARM boot required before **each** destructive physical DDR capture. **Never run any JTAG-overwrite test while KV260 Linux or other program owns DDR. Never resume a halted Linux system afterward; reboot.** Original reserved 64 MiB DDR range **`0x40000000–0x43FFFFFF`**. Explicit operator confirmation is required per physical test.
- Original accepted routed P03.2c XSA SHA256: `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
- Original accepted frozen 512 KiB DDR master SHA256: `9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`.
- Track A model: **784 input → 32 hidden → 10 output**, **42 compartments**, **25 event-input ticks + one drain tick = 26**, **25,408 real synapses**, **816 registered axons**. Original deterministic raw uint8 MNIST pixel→spike event encoder and 64-bit wrap integer LIF/packed signed24 weights, **NEXT-bank** packet delivery and tie/silence class policy must remain unchanged.
- Frozen packed trained state_dict SHA256 `0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88`; effective integer weights SHA256 `1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`. See original `src/loihi_twin_v2/p06_a4_snapshot.py`, `p06_packed_replay.py`, `p06_integer_oracle.py`, `p06_input_contract.py`, `p07_a1_ingress.py` before any new mappings.
- Original P07 official TEST physical FPGA accuracy **9,456/10,000 = 94.56%** (544 incorrect including 2 all-silent in denominator); physically original P07 **10,000/10,000 packed-output numerical parity** with accepted oracle. **TEST is sealed** for all subsequent P08 and P06-B engineering; never use official TEST for parameter decisions, debug, synthetic stress, CPU baseline reruns or P06-B1 feasibility.
- P07 original standalone persistent A53 ELF SHA256: `dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`.

### P08-A completed latency-only baseline (MERGED, no further A3 board runs needed)
- PR #45 `agent/v3-p08-a-physical-baseline` → `main`: **SUCCESSFUL merge SHA `b1ead8a2983e555e762f3176ffcdc5c7de819aee`**, exact P08-A acceptance explicitly user-authorized. Original A3 source/physical run evidence and A5 host report are user-attested, with source-bound checks. **P08-A4 physical power/energy was explicitly DEFERRED BY USER, never measured; this was not a P08-A latency-only blocker.**
- Original timing ELF SHA: **A2.1** (A53 per-image) `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`; **A2.2** (per-tick) `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`. **No regenerated firmware or bitstream**.
- Physical A3.1 pilot 16 TRAIN-derived images: A53 full-service median **35.4432 ms**; original oracle neural/output/trace and CRC PASS. Detailed A2.2 pilot spans: event encode **499.955 µs**, event-bank append **312.458 µs**, MMIO dispatch/poll **70.011 µs**, barrier **0.940 µs**, trace readback **33.030 µs**, routing **54.631 µs** (stage medians non-additive).
- A3.2 full validation: **same first 1,024 TRAIN-derived validation frames per session**, original order, final selected full 26×42 trace index 1023; **1,023 ordinary frames** in per-run service stats. Three paired **separate cold-boot** physical sessions per original A2.1/A2.2 variant, total **six board runs**. Original independent P07 replay/oracle, image/tick sidecar CRC and source SHA gates user-reported PASS.
  - Pair 1 order A2.1→A2.2: ordinary A53 service medians **35.7023 / 35.7234 ms**; same-image matched A2.2−A2.1 median **+16.840 µs**.
  - Pair 2 order A2.2→A2.1: medians **35.6946 / 35.7163 ms**; paired median **+25.400 µs**.
  - Pair 3 order A2.1→A2.2: medians **35.6696 / 35.7220 ms**; paired median **+29.710 µs**.
  - Mean of **three independent pair-level median differences** **+23.984 µs**, sample SD **6.551 µs**. For each fixed image, range across three repeated paired differences: median **24.730 µs**, p95 **73.541 µs**. Repeated 1023 images do not create 3069 independent samples. This is **not** calibrated timer overhead.
  - Arm A53 self-reported `CNTFRQ_EL0=99,999,001 Hz` in first two physical pairs; **NOT** FPGA PL clock. Raw PL dispatch cycles remain separate, achieved PL Hz **NOT independently verified**, hence **no pure PL seconds or bare-FPGA speedup**.
- P08-A5 actual offline CPU benchmark on **Intel Core i5-4590S, 4 logical cores, x86_64, CPython 3.12.3**, `schedutil` governor, single-threaded **pure Python scalar packed integer** replay (not optimized C/native, not same service boundary as A53+PL); original 1024-frame physical P07 packed-neural journal output parity and 26×10 tick outputs PASS.
  - Preloaded 26-tick packed-integer CPU core **three sequential per-run medians 25.6147 / 25.6001 / 25.5735 ms**; its median over 1023 per-image medians of three runs **25.552718 ms**.
  - Full raw784 original encoder→26-tick CPU classification **three per-run medians 30.3930 / 30.3147 / 30.2579 ms**; median over per-image medians **30.200338 ms**. CPU raw-image p95 ≈**43.17 ms** vs A53 physical full-service p95 ≈**41.9–42.0 ms**; CPU has lower median but metrics not fully scope-identical. **Never call this an FPGA acceleration ratio or hardware-only speedup.**
  - All A5 physical/CPU same frozen first1024 TRAIN source pixel/descriptor/manifest SHA gate PASS and final original comparison generated successfully. **Original report `P08_A5_FINAL_USER_ACCEPTANCE=PENDING` was written BEFORE user explicitly accepted later; do not rewrite original immutable report to claim prior acceptance.** User later explicitly approved P08-A merge. Last post-correction A5 pytest summary was **not pasted**; do not invent it or pretend GitHub CI ran.
- User-local immutable evidence + SHA256:
  - TRAIN stage `/home/dna/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z`.
  - Physical A3 pair 1 JSON `/home/dna/Thesis_Evidence/p08_a3_2_pair_20261019T004713Z.json`.
  - Pair 2 JSON `/home/dna/Thesis_Evidence/p08_a3_2_pair2_report_20261019T011632Z.json`.
  - Pair 3 JSON `/home/dna/Thesis_Evidence/p08_a3_2_pair3_report_20261019T013553Z.json`.
  - Pair3 A2.1 capture `/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_1_20261019T012641Z`, pair3 A2.2 `/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_2_20261019T013054Z`.
  - CPU dual-endpoint JSON `/home/dna/Thesis_Evidence/p08_a5_cpu_ref_20261019T023137Z.json`, **SHA256 `790072259dab211b57bf40f60bba2b7cb293d7a544ab3aae2660fc8d8c63127d`**.
  - Revalidated 3-pair aggregate `/home/dna/Thesis_Evidence/p08_a5_physical_revalidation_20261019T023728Z.json`, **SHA256 `afd4e91f0106266179072c7242d7e361c033d9d78720d79a3a807e3ed400bf7b`**.
  - Final A5 original closeout report `/home/dna/Thesis_Evidence/p08_a5_closeout_20261019T023733Z.md`, **SHA256 `17e88feb9330ffca5ecbbfb8735bc08b7fe68f76e74392c0c5c4a538e40233b1`**.
  - These untracked physical files reside on **user's PC**, were **not uploaded** to ChatGPT/GitHub, and the user supplied verifier terminal outputs and file hashes. Do not independently assert their bytes were personally inspected.
- Original measured results/docs on `main`: `docs/P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md`, `docs/P08_A5_CPU_PHYSICAL_LATENCY_RESULTS.md`, `docs/P08_A_LATENCY_ONLY_FINAL_ACCEPTANCE_CANDIDATE.md`, `docs/P08_A1_MEASUREMENT_CONTRACT.md`; `LOIHI_TWIN_ROADMAP.md`.

---

## 3. NEXT DEV TASK: START P06-B1 — DETERMINISTIC SYNAPSE-AWARE MULTI-LOGICAL-CORE PACKING

**Priority:** Read the actual current **P06 Track B** roadmap before touching implementation. The user specifically directed that the next chat continue new development. The accepted sequence is:

`P06-A compact/frozen → P07-A physical/accuracy ACCEPTED → P08-A latency-only ACCEPTED/MERGED → P06-B1 synapse-aware partitioner + exact integer oracle [NEXT] → P06-B2 independent scaled model training/freeze → P07-B physical multi-core inference → P08-B measured scaled traffic/latency → P09 thesis comparison`.

**P06-B1 has NOT been implemented or verified.** Do not skip to P08-B, P07-B hardware, official TEST, large model training or multi-engine RTL. Build software-first B1 gates and ask user to verify host-native tests before any destructive physical tests.

### Hard Track B constraints from roadmap
- Planning target: **784→1000→10** dense LIF model (~**794,000 possible dense synapses**), but **not an accepted/frozen checkpoint or resource mapping**. ~**26 destination-partitioned hidden logical cores + 1 readout = 27 cores** is **only a planning hypothesis**, not a promise or source-verified layout. 27×512KiB DDR records = **13.5 MiB** logical backing.
- P05 one engine with **three physical resident full-context slots**; A53 diagnostic deployment address map supports up to **126 logical core IDs**, but deployment/ABI must be independently checked for a much larger model.
- **Each logical core: exact 512 KiB DDR image**. Relevant hard limits include **32,768 packed synapse words** and the **128 KiB logical template/axon/synapse accounting**; respect actual hardware layout/occupancy, route descriptor and event-bank capacities, packet fanout, event forwarding and P05 3-resident paging invariants, not just raw core count.
- Old P05 deployment ABI supports **one valid external axon per core** (adequate for prior diagnostic, inadequate for 784-dimensional replicated event input). Old diagnostic payload bound **896 KiB** also cannot represent all dense new per-core data. **A newly designed versioned model/packet-streaming ABI is needed** for scaled physical deployment; in B1, first define the software/data contract, do not casually patch accepted frozen P05 firmware or call the old ABI compatible.
- **Fanout can replicate up to 784 input channels across ~26 hidden partitions**; account for worst-case **all-255 pixels** throughout the 25 input ticks, per-core incoming event banks, emitted packets, routes, source replication, packet delivery at the proper **NEXT logical timestep**, and cycle/barrier semantics. Never overflow a core's packed event bank silently; define explicit fail-closed limit and capacity proof/stress.
- Need **deterministic synapse-pressure-aware partitioning**, not naïve `compile_network(max_logical_cores=27)` and not only capacity estimation. The partitioner must preserve neuron IDs and unique source/destination semantics, classify readout core separately, and produce independently checkable per-core memory maps and signed integer synapse/axon/route tables.
- **Oracle plan:** have a truly independent **monolithic integer LIF reference** and separately partitioned multi-core/epoch routing oracle, apply same deterministic encoder/input/signed24+wrap recurrence, show per-tick **all compartment states, spikes, next-epoch packets, readout counts/class** exact (small synthetic networks, adversarial high-fanout/stress and realistic planned large structural networks as computationally affordable). Ensure page scheduling order cannot change logical result.
- Page-traffic modeling should use P05 measured physical page sizes and accepted page-in/full vs mutable-out semantics, keep raw traffic accounting and cycles/elapsed clocks separate, and produce **estimated** traffic only for unexecuted scaled Track B, never measured board performance.
- P06-B2 later trains a **separate independently pinned/quantized project checkpoint** on canonical TRAIN/validation only and freezes mapping/checkpoint/independent traces before any sealed official TEST evaluation. If 1000-hidden target fails capacity, transparently predeclare a feasible intermediate topology—do not relabel/overstate model size.
- Keep Track A 784→32→10 files/checkpoints/physical evidence **read-only**. No official MNIST TEST unseal or retest during B1. No claim of 27 cores executing on KV260 until P07-B independently validates all actual logical contexts/pages/routing and physical inference.

### Suggested P06-B1 working milestones (plan and negotiate from source audit)
- **B1.1 Audit/contract:** read current P03/P04/P05 packed DDR layout, routing/axon/synapse/event memory limits, `compile_network`, exported per-core images and existing oracle modules. Write a *contract/limits table* and tests for minimum viable partition, 512 KiB exact layout, 128 KiB budget, 32,768 synapses, input ingress and 3-resident paging. Avoid changing any accepted Track A code.
- **B1.2 Deterministic partitioning:** new opt-in algorithm, synapse-aware capacity fitting with deterministic ordering, route-fanout accounting and versioned independent manifest, tests for impossible shapes/fail-closed bounds.
- **B1.3 Multi-core ingress/packet contract:** configurable per-core axon ID allocation, source event replication, hidden→readout fan-in, NEXT-bank epoch correctness, all-255 worst-case maximum events and packet buffers; define versioned streaming ABI independently of original P05.
- **B1.4 Independent differential oracle:** original integer monolithic LIF reference vs partition-aware asynchronous-in-spike but timestep-synchronized multi-core replay, compare per-compartment 26-tick states/spikes/flags and class exactly. Randomized deterministic seeds and adversarial fanout/drain/silence/overflow tests.
- **B1.5 Scheduling/paging model:** three resident slots with one physical engine, deterministic barrier and evictions, per-core exact 512 KiB ingress/state image manifests, page hits/misses/evictions, full page-ins/mutable page-outs, estimated bytes/time only, scheduling-order equivalence; explicit physical deployment limitations.
- **B1.6 B1 acceptance report:** complete source/manifest SHA ledger, occupancy/budget proofs on declared target and intentionally infeasible counterexamples, test commands, feasibility recommendation for B2 training and first hardware step P07-B (NO actual P07-B physical PASS yet).

**If there are inconsistencies** between these proposed sub-gates and current source layout, **audit first and explicitly refine the plan**, preserving the roadmap's scientific acceptance criteria. The target 1000 hidden neurons/27 logical cores remains a *hypothesis* until independently proven.

---

## 4. NEXT CHAT FIRST ACTIONS AND COMMANDS

1. **Verify merge and audit main.** Use GitHub connected tools on repository `Xtimetraveler-Prime/Thesis` and fetch `LOIHI_TWIN_ROADMAP.md` and this handoff seed from `main`. Report the actual current main HEAD if different from P08 merge SHA due to this handoff documentation commit. Confirm no unwanted changes to Track A. Read original P03/P05 resource/memory/layout code and P06-A compiler/replay tests before design changes.
2. **Create a fresh branch FROM latest `main`**, suggested `agent/v3-p06-b1-scalable-packing`. Do NOT revive `agent/v3-p08-a-physical-baseline`. Implement B1.1 first; do not begin B1.2 until the source-audited contract is checked. Maintain a **new draft PR**, provide diff and unmerged test status; new PR merge needs explicit user consent.
3. **Host-only tests first:** use synthetic deterministic 26-tick networks; no JTAG needed for B1.1/B1.2 feasibility. Before physical P07-B later, require new user-approved operator safety/record protocols and bare-metal isolated DDR ownership.
4. **Always give user exact VS Code terminal fetch + tests after code changes**, for example:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
# AFTER THE NEW BRANCH EXISTS ON ORIGIN:
git switch agent/v3-p06-b1-scalable-packing
git pull --ff-only origin agent/v3-p06-b1-scalable-packing
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
# Use ACTUAL newly created B1 test files; these are not invented before implementation.
PYTHONPATH="$PWD/src" python -m pytest -q tests/test_p08_a5_cpu.py tests/test_p08_a5_closeout.py tests/test_p08_a3_2_repeats.py
```

Do not claim the user's old `/tmp` Vitis builds or original evidence are automatically mounted in a new conversation. Confirm original source/evidence paths still exist only when necessary for a non-destructive host verification. No background/asynchronous work can be promised.

5. **Provide a staged design and first B1 implementation**, not only a summary. Prefer producing a first submilestone with actual code/tests/doc improvements where source audit allows it; then stop for user native verification. If the user instead requests a B1 roadmap discussion, explain proposed scope and pitfalls before coding.

---

## 5. Citations/decisions to preserve for the thesis and later P09

- P07 Track A model official accuracy **94.56% real KV260 FPGA TEST**. A3 and A5 use only separate frozen TRAIN-derived validation IDs. Never combine accuracy populations or use official TEST for development.
- Loihi-inspired SNN with deterministic discrete-time spikes is **not** an asynchronous physically independent neuromorphic chip or Intel-Loihi equivalent. 784→1000→10 tutorial foundation is not an available original pretrained Intel checkpoint; the planned scaled model is project-trained and must be frozen separately.
- The observed **~35.7 ms physical A53 full-image service** includes ARM software/DDR/MMIO/poll/PL; it is **not FPGA PL neuron-engine computation alone**. The pure Python reference CPU medians ~25.6/30.3 ms have different boundaries and host hardware; do not conclude chip accelerates/slows CPU from raw ratios.
- A2.2 − A2.1 three paired median differences +16.84/+25.4/+29.71 µs are descriptive full-service differences, not timer-operation causal overhead. n=3 physical paired runs.
- P08-A4 power/energy **DEFERRED**. Any Track B P08-B energy characterization would require explicit new user scope/equipment decision; never backfill a measured power claim into completed A.
- The P05 one-engine, three-resident-context, 512 KiB logical image architecture **demonstrated five physical logical cores**, but scaled P06-B1 27-core model, many-to-many ingress and extra paging are **not yet proven**.
- Preserve frozen numerical identity and source SHAs, exact accepted comparison boundaries, first-mismatch diagnostics and original immutable user-provided evidence; P09 thesis reporting must cite scope and non-comparable claims honestly.

**Next-chat kickoff instruction to user/assistant:** “Begin P06-B1 from the latest merged `main`, audit the actual accepted packed-core/DDR/event/route capacity limits and original LIF oracles, create a new branch, and implement B1.1 deterministic scalable packing contract with synthetic fail-closed native tests. Keep Track A read-only, use no official TEST data, and send exact pull/test commands for personal verification. Advance toward B1.2 only after the B1.1 gate is proven.”
