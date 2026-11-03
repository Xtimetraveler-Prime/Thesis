# P08-B — NEXT CHAT HANDOFF SEED (2026-11-03; B4.4.2 physically accepted)

> **How to use this seed:** Copy this entire document into the next ChatGPT project conversation, or give that instance the GitHub URL and instruct it to read this file and the linked roadmap/runbooks before taking action. This supersedes the older P07-B handoff seed for current project status; it preserves the original research/architecture context while moving the active work to P08-B4.5 reset-integrity optimization.

## 0. Immediate instructions to the next assistant

We are developing a **Loihi-inspired neuromorphic architectural digital twin** on an AMD/Xilinx **KV260 (K26 Zynq UltraScale+)**. The repository is `Xtimetraveler-Prime/Thesis`, active implementation tree `Loihi_Digital_Twin/v3/`.

**Current work branch:** `agent/v3-p08-b45-reset-integrity`, created from the live PR #54 head `1669eec7b4b520a32f717d3276b042e3b9ea1929`. This is intentionally stacked on the current P08-B4.4 profiling branch, not on stale `main`.  
**Current parent PR:** **#54**, “P08-B4.4 profiling: separate original 27-context reset SHA/copy/cache timing candidate,” still **OPEN / DRAFT / UNMERGED**.  
**Dependency stack (rechecked 2026-11-03):** PR #52 `agent/v3-p08-b-scaled-latency` → `main`; PR #53 `agent/v3-p08-b4-fullscale` → PR #52 branch; PR #54 `agent/v3-p08-b44-profiling` → PR #53 branch. All three remain open drafts. PR #52 head: `6fbf748a7987c4f173c4070dc27b78fc01329683`; PR #53 head: `235c3eef2672706e6c784b344ae29c1bc6e50f3a`; PR #54 head at B4.5 branch creation: `1669eec7b4b520a32f717d3276b042e3b9ea1929`. Recheck live PRs and branch heads before acting. No B4.5 PR has been opened yet.  
**Do not merge any PR unless the user explicitly authorizes it.** Keep the dependency chain intact. The new B4.5 branch deliberately includes the #52/#53/#54 ancestry; do not rebase it onto stale `main` or merge the parent stack without user authorization.

The B4.4.2 physical result is accepted, but the user has not yet locally verified the B4.4 regression suite on their workstation. The new B4.5 branch adds portable-C experimental variants, native tests, a no-board workflow and the B4.5 protocol. Those new native tests and the inherited B4.4 regression suite must be run locally; do not claim they passed. Distinguish native tests, CI, operator-supplied evidence, and physical acceptance.

**First actions in a fresh chat:**
1. Read this seed, `Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md`, `docs/P08_B4_4_2_RESET_PROFILE_PHYSICAL_RESULTS.md`, `docs/P08_B4_5_RESET_INTEGRITY_OPTIMIZATION_PROTOCOL.md`, `docs/P08_B44_PROFILE1024_PHYSICAL_RUNBOOK.md`, `docs/P08_B4_4_SINGLE_SESSION_TIMING_ANALYSIS.md`, `docs/P08_B1_MATCHED_TRACK_A_LATENCY_CONTRACT.md`, and `docs/P08_B2_2_CONTEXT_RESET_AND_METER.md`.
2. Check live PR #52/#53/#54 status and branch `agent/v3-p08-b45-reset-integrity` head; do not assume these SHAs remain current.
3. Give the user the Section 9 pull/test commands and wait for their exact output.
4. Continue PC-only B4.5 development after the inherited B4.4 regression and new native variant tests pass. Do **not** start a Vitis build or destructive JTAG/DDR run until the full memory-owner/protection audit, ELF admission, recovery plan and fresh explicit operator approval are complete.

GitHub connector tools may be available through `functions.exec` as `tools.mcp__GitHub__*`. Use them for repository reads/writes and verify the actual commit/PR state. A repository commit does not mean local native tests or board tests passed.

## 1. Research identity and overall architecture

The thesis direction is one project with two cooperating models: a transparent software model/reference and an FPGA implementation that acts as its **architectural digital twin**. The software model exposes state transitions, integer arithmetic, event scheduling, routing, and memory semantics so the physical implementation can be independently checked. Early exploration considered Brian2Loihi as a reference and a separate SNN actor-critic/PPO-on-MuJoCo idea; those are historical exploratory directions, **not the current implementation scope**. Do not pivot this work into PPO/actor-critic or treat Brian2Loihi as a substitute for the frozen accepted scalar oracle.

The current accepted system is a **digital, synchronous, event-driven Loihi-inspired model** with global tick/barrier scheduling, not proof of truly asynchronous Loihi silicon, original Intel Loihi SRAM/NoC equivalence, Loihi-2 behavior, or chip-level power equivalence.

### Physical architecture

- Board: AMD/Xilinx KV260, K26 Zynq UltraScale+.
- Processing System: Cortex-A53 standalone/bare-metal firmware owns image orchestration, reset, scheduler, DDR paging, packet routing, and P03 MMIO control.
- Programmable Logic: one accepted P03-compatible HLS inference engine; up to **three resident context slots**.
- Logical network: **27 logical cores** backed by P02 records in DDR (26 hidden partitions plus one readout core), with 1,010 total neurons (1,000 hidden + 10 output).
- Each logical context is a **512 KiB** P02 DDR backing record. The 27 records total **14,155,776 bytes (13.5 MiB)**.
- The runtime performs 26 logical ticks, 702 HLS dispatches per image, and 26 global barriers. This is PS-orchestrated board-local execution, not a fully asynchronous hardware network.
- The one-engine/three-slot architecture is accepted; a second/third physical engine is deferred until the single-engine bottlenecks are measured.

### Frozen neural/model semantics — do not change casually

- Input: raw MNIST 28×28 unsigned-byte images, 784 channels.
- Dataset: canonical MNIST TRAIN source, with frozen deterministic 50k training / 10k TRAIN-derived validation split. The Track B engineering validation result is **97.08% on TRAIN-derived validation**, not official TEST.
- Encoder: `p06-uint8-quota-phase17-v1`, 25 input ticks plus one external-free drain tick = 26 logical ticks/image.
- Neuron: signed-24-bit saturating integer LIF recurrence, signed quantized weights, strict `>` threshold and accepted refractory/reset behavior.
- Hidden-to-readout spikes route to the **NEXT** logical tick, not the same tick.
- Reset CURRENT/NEXT banks, packets, neuron states and readout counts per image.
- Ten output spike counts across all 26 ticks; `argmax` with lowest-index tie break, including all-silent output -> class 0.
- The source graph has 794,000 dense connections; preserve source semantics including explicit signed zeros. Do not silently alter weights, arithmetic width, tick count, event schedule, routing, reset semantics or readout behavior.

## 2. Frozen Track A and accepted P07-B status

### Track A (compact 784→32→10)

- One logical core, 42 neurons.
- Accepted actual KV260 P07-A official MNIST TEST accuracy: **94.56% (9,456/10,000)**.
- Its frozen checkpoint/weights and physical evidence are authoritative. Do not rerun or tune on its official TEST.
- P08-A latency-only baseline was accepted. P08-A4 power/energy was deferred/unmeasured.
- Track A's earlier three A2.1-vs-A2.2 pairs are **instrumentation pairs within Track A**, not the new Track A-vs-Track B paired benchmark required by P08-B.
- Track A ordinary service medians are approximately 35.67–35.72 ms in accepted P08-A sessions. These are useful system context only; they do not support pure PL speedup or a fair same-complexity ratio against Track B.

### Track B (scaled 784→1000→10)

- P06-B1/B2 host software, trained checkpoint, 27-core P02 packing and frozen 33-asset B2.4 deployment were accepted.
- The separate project-trained Track B checkpoint achieved **97.08% on 10,000 TRAIN-derived validation images**. This is not official MNIST TEST.
- P07-B final physical acceptance was user accepted; PRs #49/#50/#51 were subsequently merged into `main` in dependency order. See `docs/P07_B6_3_FINAL_HANDOFF_P08_BOUNDARY.md` and `docs/P07_B6_3_2026_11_01_FORMAL_OPERATOR_ACCEPTED_P07_B_CLOSEOUT.json`.
- P07-B physical evidence covers the original TRAIN-only validation scope and its accepted physical sessions/raw trace. It does not prove full official TEST accuracy or exclusive boot/Linux/DMA DDR ownership.
- **Track B official MNIST TEST remains SEALED_NOT_ACCESSED.** No P08 development task authorizes unsealing it.

The Track A and Track B networks have different sizes and computational work. A future repeated comparison is a **system/workload comparison**, not a matched-neural-complexity comparison or pure FPGA acceleration ratio.

## 3. P08-B progress and authoritative documents

P08-B is the scaled physical resource/traffic/latency study. Read the roadmap and the following stage documents before changing implementation.

### B1 — matched source and measurement contract

`docs/P08_B1_MATCHED_TRACK_A_LATENCY_CONTRACT.md` defines the primary comparison as complete A53 image service, measured from before image ingress to after durable result journal commit, with each session's actual `CNTFRQ_EL0`. B must include per-image reset, ingress, scheduler/pager re-init, all 26 ticks, dispatches, routing, physical reads needed for parity and journal commit. Host preparation/JTAG prelaunch is excluded. Do not omit B reset and call the remainder equivalent to A.

A/B detailed subspans must be carefully defined. The accepted B P07 trace hook reads physical trace data during each core dispatch before eviction, so A's boundary definitions cannot be mechanically copied if that makes trace reads disappear or double-counted. Keep PL cycle counters in their own clock domain; never divide PL cycles by A53 frequency.

### B2 — original 1024-frame source, reset, timing and firmware

Important documents:
- `docs/P08_B2_1_ORIGINAL_MATCHED_INGRESS_AND_DDR_CANDIDATE.md`
- `docs/P08_B2_2_CONTEXT_RESET_AND_METER.md`
- `docs/P08_B2_3_IMAGE_ONLY_A53_OFFLINE_VITIS.md`
- `docs/P08_B2_4_FIRST16_SCALAR_AND_RECORD_GATES.md`

The reset primitive authenticates all 27 original immutable backup contexts before the first destructive mutable copy, copies each 512 KiB context, performs cache clean/barrier/invalidate operations, and verifies restored destination contents. It is designed to preserve the frozen original model and prevent a corrupted context from silently entering another image. The B4.4 profile has now measured the cost of these subphases.

### B3 — real 16-frame physical pilot

The accepted first16 pilot established a genuine bounded physical path with independent scalar comparison. Key operator evidence paths/hashes are retained in the runbooks; the signed B3 independent report used by B4.2/B4.4 is:

`/home/dna/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json`

SHA256:
`b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11`.

### B4.1 — original full1024 scalar oracle

The independently generated original 64-shard scalar oracle is:

`/home/dna/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json`

SHA256:
`7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8`.

Original scalar shard directory:
`/home/dna/Thesis_Evidence/p08_b4_1_original_scalar_shards_20261102T060939Z`.

### B4.2 — original full1024 physical neural/timing run

The accepted independent physical report:

`/home/dna/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json`

SHA256:
`297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032`.

Exact original physical evidence root:
`/home/dna/Thesis_Evidence/p08_b4_2_original1024_physical_20261102T145943Z`.

It passed all 1,024 original neural/FNV/scalar comparisons and timing-row checks in one genuine physical session. The original B2.3 production ELF/map and P03 shell are frozen; do not rebuild or replace them to run new experiments.

### B4.4 — original full1024 uninstrumented six-phase descriptive timing

Read `docs/P08_B4_4_SINGLE_SESSION_TIMING_ANALYSIS.md`.

Operator report:
`/home/dna/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json`

SHA256:
`4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81`.

Actual A53 counter frequency: **99,999,001 Hz**. For 1,023 ordinary images (selected trace ordinal 1023 excluded), whole image service median was **13,034.111501 ms** and nearest-rank P95 **13,167.109029 ms**. The six original A53 phase medians were approximately:
- 27-context restore: 5,826.693269 ms (44.695321% of summed whole-service ticks).
- Original input encode: 18.673677 ms (0.143253%).
- Pager/scheduler reset: 228.098739 ms (1.749822%).
- All 26 ticks, 702 dispatches, paging, MMIO/polling, routing and nested trace: 6,935.069581 ms (53.215729%).
- Receipt validation: 0.000430 ms.
- Journal commit: 25.534815 ms.

The reset phase includes SHA integrity scans/cache maintenance/copy/verification; the all-tick phase includes PS control and paging/routing/trace as well as PL dispatches. Neither is pure PL compute. Do not add phase medians to claim the total median.

### B4.4.1/B4.4.2 — separately built reset profiler and genuine physical acceptance

Authoritative latest result:
`docs/P08_B4_4_2_RESET_PROFILE_PHYSICAL_RESULTS.md`.

Physical runbook:
`docs/P08_B44_PROFILE1024_PHYSICAL_RUNBOOK.md`.

Source/build history:
`docs/P08_B4_4_1_RESET_PROFILING_DEV_RUNBOOK.md`.

Successful new physical evidence root:
`/home/dna/Thesis_Evidence/p08_b44_profile1024_retry_20261103T061707Z`.

Independent PC-only report:
`/home/dna/Thesis_Evidence/p08_b44_profile1024_independent_20261103T100712Z.json`

Operator-supplied SHA256:
`47f25cada89dd9220636fbb9539aba5bf0d7705ea3788fdc3ebd1d85f1145cfa`.

The operator supplied all of these markers:
```text
P08_B44_NEW_RESET_PROFILE1024_INDEPENDENT_SAME_SESSION_JTAG_PROVENANCE_PASS=1
P08_B44_NEW_RESET_PROFILE1024_ORIGINAL_1024_NEURAL_FNV_SPIKE_PARITY_PASS=1
P08_B44_NEW_RESET_PROFILE1024_ALL_1024_REAL_SHA_COPY_CACHE_SUBSPAN_COUNTERS_PASS=1
P08_B44_NEW_RESET_PROFILE1024_NEW_PAIRED_AB_BA_AB_BENCHMARK_ACCEPTED=0
```

The 1,024 original neural results match the scalar oracle; all 1,024 reset-profile rows pass independent checks. The selected trace ordinal 1023 is analyzed separately; the ordinary reset distribution has 1,023 frames.

**Measured reset-profile results** (actual A53 `CNTFRQ_EL0=99,999,001 Hz`):
- Overall reset-service median: **5,826.767549 ms**.
- P95: **5,826.881051 ms**; min 5,826.591948 ms; max 5,827.041922 ms.
- Mutable 27-core memcpy: 7.0247 ms median (0.12%).
- Mutable cache clean/invalidate: 1.6885 ms (0.03%).
- Mutable SHA-256 readback: 2,908.5991 ms (49.92%).
- Original immutable cache invalidate: 0.8392 ms (0.01%).
- Original immutable SHA-256: 2,908.5978 ms (49.92%).
- Unattributed counter/control residual: 0.0157 ms median (0.00% after rounding).

The two SHA scans account for approximately **99.84% of summed reset-service ticks**. The mutable copy is only ~7 ms; full-context integrity verification dominates. These are subphase measurements inside the reset service, not the whole image-service interval. Percentages are based on summed ticks, not sums of medians.

New profile ELF SHA256:
`bed1301c69594bf7ebeaa37765ad2cb3035aa0f6d5e9cb4d1fb4637042be3ab3`.
New profile map SHA256:
`d94fa2695e82cc3a501442313bb77e89eb046f01450167108832a190fd9fd2c9`.
Offline profile ELF admission SHA256:
`7a5818dc5469ea288fefcefb87ebc4fd3ab1e5c7bdce0bbfda717a6f2787b129`.

The initial failed B4.4 JTAG attempt remains preserved at
`/home/dna/Thesis_Evidence/p08_b44_profile1024_physical_20261102T201705Z`.
It failed closed at the inherited A53 #1 stop gate with “External debug access is disabled”; this is not an admissible powered-down response. It did not reach P03 programming, DDR source staging, profile ELF download or inference. Do not weaken the original P07-B4i stop gate.

**Limitations:** one instrumented physical profiling session; no accepted six-session paired A/B benchmark; no PL-only neural time, pure speedup, energy result, or independent boot-firmware/PS/RPU/DMA exclusive-DDR-owner proof. Experimental profile region `[0x42400000,0x42440000)` (262,144 bytes) still has unproven exclusive ownership. Track B official MNIST TEST remains sealed.

## 4. Next work — P08-B4.5 reset-integrity optimization, then P08-B4.6 paired A/B

P08-B4.4.2 is physically accepted and remains the full-SHA reference. The
new P08-B4.5 milestone compares two separately versioned reset variants.

### P08-B4.5.1 — authenticate once, lightweight per-image checks

- Establish persistent, exclusive, read-only ownership/protection of the
  immutable 27×512KiB backup range.
- Authenticate all 27 original P02 records with SHA-256 once at session bind.
- For each image, confirm the protection is still active, check all 27 source
  headers before the first write, restore all 27 records, perform the original
  cache maintenance/barriers, and check all 27 destination headers.
- No per-image SHA-256 checks. A post-bind payload mutation is not detectable
  by header checks; the real protection mechanism is therefore essential.

### P08-B4.5.2 — unchecked-content performance bound

- No SHA-256, P02-header, CRC or payload-content validation in the reset path.
- Keep pointer/range/size admission, persistent backup ownership/protection,
  quiescence, cache maintenance, barriers, callback error handling and
  fail-stop poisoning. This removes content-integrity checks, not operational
  safety controls.
- Treat it only as a diagnostic lower-bound experiment, not production code.

### Shared B4.5 execution gates

1. Run inherited B4.4 regression tests and new strict C11 native tests.
2. Prove that the physical backup region remains exclusively owned and
   immutable for the whole session. A native mock callback or no-op is not
   hardware evidence.
3. Build separate genuine Vitis A53 ELF/map artifacts for each variant and
   independently audit PT_LOAD/BSS/heap/stack and DDR ranges.
4. Only after fresh read-only preflight, recovery readiness and new explicit
   approval, run a bounded 16-image physical pilot per variant. Require
   exact independent scalar output/spike/FNV parity.
5. After each pilot passes, run a separately approved 1,024-image session.
   Keep trace ordinal 1023 separate from the 1,023 ordinary timing frames.
   Record reset subspan and complete A53 image-service time with actual
   per-session CNTFRQ and unchanged service boundaries.
6. Keep original B2.3, accepted B4.4.2 profiler, P03 shell, B2.4 assets,
   model and official TEST immutable.

The additional profile region `[0x42400000,0x42440000)` and immutable backup
range `[0x43000000,0x43D80000)` have unresolved runtime ownership. Audit
FSBL/boot firmware, TF-A, U-Boot, Linux, RPU, PL DMA and all other masters.
Static non-overlap is not enough. If ownership/protection cannot be proved,
stop and redesign. No B4.5 physical run is authorized by the earlier B4.4.2
approval.

### P08-B4.6 — repeated paired Track A/Track B system comparison

After B4.5 closes, conduct the previously proposed six independent physical
sessions in AB/BA/AB order, with the same frozen 1,024 TRAIN-derived images,
1,023 ordinary frames, trace ordinal 1023 isolated, complete matched
image-service boundaries, per-run A53 CNTFRQ, cold-boot/recovery accounting
and run-level uncertainty. Track A (42 neurons/26 dispatches) and Track B
(1,010 neurons/702 dispatches) are different workloads; this is a system/
workload comparison, not matched-complexity or pure FPGA speedup.

## 5. Immutable evidence and important local paths

Operator workstation is normally `~/Git/Thesis`, evidence root `~/Thesis_Evidence`, and Python environment `~/Git/Thesis/.venv-p08`.

Key original source/evidence paths used by the B4.4 runbook:

```bash
export P08_B4_SHARDS="$HOME/Thesis_Evidence/p08_b4_1_original_scalar_shards_20261102T060939Z"
export P08_B4_INGRESS="$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z"
export P08_B4_FIRST16="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"
export P08_B4_FULL_ORACLE="$HOME/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json"
export P08_B3_INDEPENDENT_REPORT="$HOME/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json"
export P08_B3_PILOT_STAGE="$HOME/Thesis_Evidence/p08_b3_pilot16_pc_stage_20261102T043729Z"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P08_B44_ORIGINAL_B4_PHYSICAL_REPORT="$HOME/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json"
export P08_B44_ORIGINAL_TIMING="$HOME/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json"
export P08_B44_PROFILE_BUILD="$HOME/Thesis_Evidence/p08_b44_reset_profile_retry_20261102T195900Z"
export P08_B44_PROFILE_ELF="$P08_B44_PROFILE_BUILD/vitis_workspace/p08_b44_reset_profile_1024.elf"
export P08_B44_PROFILE_MAP="$P08_B44_PROFILE_BUILD/vitis_workspace/p08_b44_reset_profile_1024.map"
export P08_B44_PROFILE_ELF_AUDIT="$P08_B44_PROFILE_BUILD/p08_b44_profile_elf_ptload_preflight.json"
export P08_B44_PROFILE_PHYSICAL="$HOME/Thesis_Evidence/p08_b44_profile1024_retry_20261103T061707Z"
export P08_B44_PROFILE_INDEPENDENT="$HOME/Thesis_Evidence/p08_b44_profile1024_independent_20261103T100712Z.json"
```

Original B2.3 production ELF SHA256:
`0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1`.
Original B2.3 production map SHA256:
`f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc`.

Do not overwrite/rebuild these original artifacts or replace the accepted P03 shell. If the original ELF/map are needed for a new audit, use exact SHA-verified copies under the required canonical original B4 filenames. The profile ELF/map are distinct and separately pinned.

**Important path gotcha from earlier terminal troubleshooting:** `P08_B44_PROFILE_PHYSICAL` must point to the **evidence directory**, not the `profile1024_a53_physical_run.log` file. A prior attempt exported the log filename into this variable, causing later code to look for `<logfile>/stage.txt`. The successful root is the directory ending `p08_b44_profile1024_retry_20261103T061707Z`. Never reuse a failed/successful evidence directory or overwrite an existing report.

## 6. Hardware monitoring and safety rules

- PC-only mailbox monitor (while a run is actively in progress) reads the existing owning XSDB process's cached mailbox file. It does **not** open a second JTAG owner, halt a CPU, write DDR or interrupt the FPGA:
  ```bash
  export P08_B44_MONITOR="$P08_B44_PROFILE_PHYSICAL"
  python scripts/p08_b4_2_monitor_mailbox_pc_only.py \
    --evidence "$P08_B44_MONITOR" \
    --capture-subdir profile1024_capture \
    --samples 2 --interval 20
  ```
  An unchanged completed-image count over 20 seconds is not automatically a hang; a missing/partial cached snapshot can occur while XSDB replaces the cache. Terminal acceptance still requires exact 1024 completion and independent scalar/physical verification. This monitor is not a substitute for independent post-run verification.
- `hw_server` endpoint used in the runbooks is `tcp:127.0.0.1:3121`; a read-only local check is `ss -ltn | grep ':3121'`. Required local executables for the physical runner are `xsdb` and `vivado`.
- A destructive JTAG session discards the running Linux/A53 context. After **any** destructive attempt, successful or failed, perform the required reboot/power-cycle and never resume the halted Linux session.
- Preserve all failed and successful evidence. No deleting/reusing evidence roots, no rerunning over an existing JSON, no repeated open-ended JTAG attempts.
- The original P07-B4i A53 stop gate admits only a genuine positive halt or its exact documented powered-down responses. “External debug access is disabled” is **not** proof that the core is powered down. Do not weaken that fail-closed gate or change debug/security settings based on guesswork.
- Do not perform destructive actions without fresh read-only preflight, explicit separate operator approvals, exact memory map, and recovery plan. The completed B4.4.2 run does not authorize B4.5 hardware work.

## 7. Development and evidence workflow

- Work in small submilestones with clear source/native/physical gates.
- Prefer PC-only source, parser, verifier, and synthetic-negative tests before Vitis or board actions.
- Freeze original source, trained assets, P03 bitstream/XSA, production ELF/map and accepted evidence. New instrumentation belongs in separately named source/build/report artifacts.
- Use absolute evidence paths outside the repository and no-overwrite creation. Before writing any new report/directory use `test ! -e "$PATH"`.
- Pin SHA256 for every ELF, map, input, report, bitstream/XSA and physical capture used in an acceptance.
- Clearly label every result as one of: modeled, synthetic/native, CI, operator-local, physical, independently verified, or user-accepted.
- Never infer physical acceptance from source code, a passing CI workflow, or a preflight marker.
- The assistant should supply exact `git fetch/pull` and regression commands after every substantive code change and wait for the user's output before advancing.
- Do not merge branches or open a later milestone's destructive hardware work without explicit user authorization.
- Keep root `LitReview.md` and the frozen original model/checkpoint/TEST protocol untouched unless the user explicitly authorizes a separate task.

## 8. Scientific and communication guardrails

1. Track A official TEST 94.56% and Track B TRAIN-derived validation 97.08% are different datasets/checkpoints and are not directly comparable test accuracies.
2. A 42-neuron one-core network and a 1,010-neuron 27-logical-core network are different workloads. Report full-system measurements with exact scope; do not claim pure PL speedup.
3. The 5.827-second reset measurement is A53 reset-service time dominated by SHA-256 integrity scans. It is not FPGA inference latency, PL compute, or the full B image service time.
4. The original B4.2 full image service (~13.034 s median) includes reset plus all 26 ticks and other phases. The new B4.4.2 reset profile is a distinct instrumented experiment. Do not subtract medians across these separate runs and call the result an optimization delta.
5. SHA verification protects the original immutable and restored mutable contexts. Any proposal to remove, sample, parallelize or cache integrity checks must explain how it preserves the same integrity guarantee and must be separately versioned and independently verified.
6. P08-A4 power/energy remains deferred/unmeasured. P08-B energy is not measured by the current evidence.
7. Track B official MNIST TEST remains SEALED_NOT_ACCESSED. Do not read it, tune on it, or claim its accuracy.
8. The FPGA architecture is Loihi-inspired and event-driven but uses synchronous ticks/global barriers and PS orchestration. Do not claim real asynchronous Loihi silicon equivalence.

## 9. First local pull and regression commands

The active development branch is stacked on the current PR #54 head. Pull it
without changing the parent PR branches:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch --track origin/agent/v3-p08-b45-reset-integrity 2>/dev/null || \
  git switch agent/v3-p08-b45-reset-integrity
git pull --ff-only origin agent/v3-p08-b45-reset-integrity
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# First close the inherited B4.4 local-verification gate.
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b44_profile_physical.py \
  tests/test_p08_b4_2_full1024_physical.py \
  tests/test_p08_b44_reset_profile_sidecar.py \
  tests/test_p08_b44_profile_elf_admission.py \
  tests/test_p08_b44_build_offline.py

# Then run the new B4.5 strict native reset-variant test.
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b45_reset_variants.py
```

These are PC-only tests. They do not contact the KV260, open XSDB, program
the PL or write physical DDR. Report the exact pytest summaries and commit
SHA. Do not claim a local pass until the user supplies the output.

The new B4.5 source files are:
- `software/p08/p08_b45_reset_variants.{h,c}`
- `tests/native/p08_b45_reset_variants_native.c`
- `tests/test_p08_b45_reset_variants.py`
- `.github/workflows/p08_b45_reset_variants_no_board.yml`
- `docs/P08_B4_5_RESET_INTEGRITY_OPTIMIZATION_PROTOCOL.md`

The portable source prototype is not yet integrated into either A53 main,
has no genuine Vitis ELF/map, and has not run on hardware. After local tests
pass, the next subtask is a PC-only review of the source-lock interface and
integration design. A physical implementation must provide a real platform
protection/ownership mechanism; a no-op callback is prohibited.

Do not merge PRs #52/#53/#54 or the new B4.5 branch without explicit user
authorization. Preserve the stack dependency order and verify each merge.
Official MNIST TEST remains sealed.

**End of handoff seed. The immediate task is local verification of the inherited B4.4 regression suite and new B4.5 native variant test; physical work remains blocked by DDR ownership/protection proof.**
