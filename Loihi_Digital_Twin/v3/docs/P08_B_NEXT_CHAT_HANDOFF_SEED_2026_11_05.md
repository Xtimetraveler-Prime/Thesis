# P08-B — NEXT CHAT HANDOFF SEED (2026-11-05 UTC; B4.5.4.4 PC-only accepted)

> **LATEST USER RESEARCH DIRECTION AND ACTIVE BRANCH — 2026-11-05.**
> User explicitly chose to validate numerical prediction/FNV parity and
> reset latency using UNPROTECTED immutable source backups as a stated
> research limitation, rather than treating DDR XMPU as a prerequisite
> for B4.5 physical performance experiments. The prior XMPU/FSBL
> original source work remains accepted research history, but is
> not the next blocker. DO NOT change the originally accepted B4.5
> `p08_b45_a53_backup_guard.c` that returns -1; do not modify frozen
> P03/P07/P08 model, inputs or original accepted 1024 profile.
>
> **New active branch:** `agent/v3-p08-b45-unprotected-pilot16`
> stacked on draft PR #61; new draft PR should remain unmerged without
> explicit operator instruction. It adds separate explicit
> `p08_b45_perf_reset.c/.h`, NEW `once` and `unchecked` A53
> 16-frame entry points and Vitis 2025.2 build wrappers, new
> mode-unique SHA/ELF admission, original B3/P03 physical
> stage/readback+CPU takeover+FPD128 gated runner, 16-frame
> terminal/neural/FNV/full-service/4KiB-reset sidecar capture,
> 27x512KiB post-run immutable backup readback, and separate
> independent PC-only evidence review. Sidecar backup guard word 19
> MUST be 0; do not misrepresent content immutability.
>
> **Exact full commands:** read
> `docs/P08_B45_UNPROTECTED_PERFORMANCE_PILOT16_RUNBOOK.md`.
> First operator must build TWO new genuine mode-specific Vitis
> ELFs/maps and run both PC-only preflights. Only then can operator
> separately execute pilot16 physical modes with ten affirmative
> scoped risks and disposable CPU/JTAG session. Full 1024-image
> optimized benchmark is NOT yet implemented/approved. Reboot board
> after ANY JTAG attempt. No PuTTY scripting: short
> `sudo xmutil listapps`, conditionally `sudo xmutil unloadapp`;
> all heavy tools run on PC VS Code. Official MNIST TEST stays sealed.
>
---
> **LATEST GIT HISTORY / OPERATOR SOURCE RESULT — 2026-11-05 UTC.**
> P08-B4.5 original C-vs-Tcl source-gate report is **operator-reported
> PC-ONLY PASS**, physical NO-GO. Original external JSON
> `/home/dna/Thesis_Evidence/p08_b45_fsbl_c_tcl_20261105T071335Z.json`
> SHA-256 `61e4b668e08b760800e69b39fdb61c5382aa23c0df568a31c3a49beff6c16bde`.
> All six original DDR-XMPU helper bodies were 21 bytes and had
> zero obvious C writes, while the debugger Tcl referred to their
> names. No live FSBL/XMPU or ownership proof; candidate boot artifact
> array was empty because none were supplied.
> **Before repeating ANY board inspection**, read
> `docs/P08_B45_HISTORICAL_KV260_INSPECTION_REUSE_2026_11_05.md`:
> October 21 Ubuntu 24.04.2 / Image A BootFW screenshot, all 19
> Track A and seven P08-A width logs, Oct 22 Linux `devmem` vs XSDB
> inconsistent width readings and successful B4i CPU takeover,
> Nov 2–3 failed read-only A53 debug observations followed by
> Nov 3 **successful original 1024-image** B4.4 profiling.
> These are saved, NOT a reason for new serial/JTAG reads.
> Next work should start with **PC-only search of existing BOOT.BIN/
> BIF/FSBL image/build receipts**, not PuTTY.
> User cannot easily paste into PuTTY; if a new board snapshot later
> becomes necessary and separately approved, use only one short,
> easy-to-type read-only command at a time. No multiline loops,
> raw register reads/writes, XSDB, A53 takeovers or boot edits
> without a new narrowly scoped physical plan and approval.
> Draft PR #61 is current, stacked on #60; no merges authorized.
>
> **LATEST STATUS OVERRIDE — 2026-11-05 UTC, P08-B4.5 source-channel work package in progress.**
> This note supersedes older `NEXT ASSISTANT ACTION = B4.5.4.5` passages
> below; those remain historical only. Operator reported original B4.5.4.5
> source verification PASS from
> `/home/dna/Thesis_Evidence/p08_b4545_psu_source_20261105T065516Z.json`,
> SHA-256 `2d6f9e079b3bf9845ebd07d69b2de4611b90dc821341b0c9ada6458b2daa74a0`.
> See `docs/P08_B4_5_4_5_OPERATOR_REPORTED_GENERATED_PSU_ACCEPTANCE_2026_11_05.md`.
>
> **Current branch:** `agent/v3-p08-b45-physical-readiness-source-gate`,
> **draft PR #61**, stacked on `agent/v3-p08-b4545-generated-psu-audit`
> **draft PR #60**; ancestors #59 etc remain unmerged. DO NOT MERGE
> without the operator's explicit approval. New
> `scripts/p08_b45_fsbl_source_channel_gate.py` + native negative tests +
> no-board CI + exact operator runbook are in draft PR #61.
> Read `docs/P08_B45_FSBL_C_VS_TCL_PHYSICAL_READINESS_PC_ONLY_RUNBOOK.md`
> first. The original-source run has now been operator-reported PASS
> with the SHA and path pinned above; do not request a duplicate test.
> Its PC-only NO-GO status is unchanged.
>
> **Current scientific finding:** Generated C `psu_protection` reaches
> all six 21-byte DDR-XMPU C helper definitions, while Tcl has XMPU
> symbols. AMD PG201 distinguishes C as FSBL source from Tcl as debugger
> initialization, so Tcl does NOT establish active boot protection.
> 2025.2 FSBL default bypass remains only a source default. Current KV260
> BOOT.BIN, current FSBL compiler branch, 6-port XMPU security policy,
> original backup exclusive ownership, 512KiB extra cover, and trusted
> A53 guard are all **UNPROVEN**. Never enable protection blindly or
> run JTAG/DDR/MMIO/BOOT.BIN changes under a source-only task.
> Official Track B MNIST TEST remains sealed.
>
> **Numbering:** Previous B4.5.4.5 evidence is preserved as accepted;
> future P08-B4.5 work uses named packages/PRs, NOT B4.5.4.6.
> P08-B4.6 remains the separately gated paired A/B study.
>
---

> **Read the CURRENT status first, not historical stale next-step
> instructions later in older stage documents.** Current development
> branch: `agent/v3-p08-b4544-fsbl-protection-review`; draft PR
> **#59**, stacked on draft #58 (B4.5.4.3), #57 (B4.5.4.2),
> #56 (B4.5.4.1), #55 (B4.5.3), #54/#53/#52 (earlier P08).
> All remain **UNMERGED** unless live GitHub says otherwise.
> **NEVER MERGE without express user instruction.** Do not switch
> to stale `main`; create next incremental branch from the
> **current** `agent/v3-p08-b4544-fsbl-protection-review` head.
>
> **Accepted source evidence, 2026-11-05 UTC:**
> The operator locally ran 16 B4.5.4.4 negative/source tests:
> `................ [100%]`. The source checker passed both real
> Vitis FSBL C-source branch parsing and original XSA vs
> P03-generated `psu_init.c` SHA comparison. Original file:
> `/home/dna/Thesis_Evidence/p08_b4544_fsbl_protection_branch_20261105T062334Z.json`.
> Report SHA-256:
> `e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9`.
> Decision: `FSBL_SOURCE_BYPASS_PATH_IDENTIFIED_REAL_BOOT_AND_XMPU_NO_GO`.
> See
> `docs/P08_B4_5_4_4_OPERATOR_FSBL_PROTECTION_SOURCE_ACCEPTANCE_2026_11_05.md`.
>
> **Major AMD/Xilinx source discovery (citations preserved below
> and in roadmap):** The installed Vitis 2025.2
> `xfsbl_hw.h` defaults to `XFSBL_PROT_BYPASS` unless
> `FSBL_PROT_BYPASS_EXCLUDE` is supplied to the compiler.
> The bypass branch runs `psu_apply_master_tz()` and
> `psu_ocm_protection()`, NOT full generated
> `psu_protection()` / `psu_protection_lock()`; the full
> branch invokes those two in order **before** ordinary
> `XFsbl_HookBeforeHandoff()`. The **active KV260
> BOOT.BIN/FSBL macro choice remains UNKNOWN**.
> Source availability is NOT physical XMPU configuration.
>
> **Critical next-source gap:** The operator's generated
> `psu_protection()` body is 130 source bytes;
> `psu_protection_lock()` only 43; the current limited
> direct-hex-address scan found no 0xFD00... DDR XMPU
> register literals. This **does not mean the XMPU config
> is empty**. Trace these wrappers to generated
> `psu_init.h`, `psu_init.tcl`, table entries,
> function calls, mask/write programs and HWH PS security
> metadata before concluding anything about real regions.
> No `FSBL_PROT_BYPASS_EXCLUDE` change or XMPU writes yet.
>
> **NEXT ASSISTANT ACTION = B4.5.4.5 (PC-only):**
> inspect the accepted generated P03 PS security/protection
> configuration and local pre-existing FSBL/BOOT.BIN/BIF
> source or build artifacts (only read-only host operations).
> First inspect the roadmap, this seed, real original SHA pins
> and source review runbooks; create a NEW feature branch
> derived from PR #59's current head, then add a strict,
> fail-closed source call-graph/table analyzer, native
> negative tests, no-board GitHub Actions and runbook with
> complete exports/find commands. Request operator's
> local native verification and report SHA before advancing.
> Do NOT run the KV260/XSDB/JTAG, write XMPU or DDR,
> enable A53 guard, build/rewrite active boot media or touch
> official MNIST TEST under this task.
>
> **Physical blocker:** Original 27x512KiB immutable
> backup `[0x43000000,0x43D80000)` (13.5 MiB) requires
> conservative 1MiB-aligned potential RO cover
> `[0x43000000,0x43E00000)`, including extra 512KiB
> `[0x43D80000,0x43E00000)`; actual FSBL/TF-A/Linux/
> APU/RPU/PL/DMA/JTAG DDR ownership, per-port AXI
> Master IDs, region slots and active lock remain unproven.
> The original A/B A53 backup-guard callbacks deliberately
> return failure and **MUST NOT be bypassed**.
> Any future hardware experiment requires a separately
> proven boot + DDR protection design, trusted continuing
> attestation, signed/admitted NEW firmware, recovery plan,
> read-only preflight and **new explicit operator approval**.
>
> **Workflow preferences — strictly follow:** work in
> small separate submilestones in feature branches;
> no merges without explicit user instruction; maintain
> original immutable source/models/binaries and evidence;
> include complete `export` commands and/or exact `find`
> commands for EVERY operator local test/build, plus
> `git fetch/switch/pull` and `PYTHONPATH` tests after
> each code change; run CI, negative tests, wait for
> operator verification before stage acceptance.
> Output external evidence under `$HOME/Thesis_Evidence`
> with fresh timestamped no-overwrite paths.
>

## 0. Immediate instructions to the next assistant

The thesis is a **Loihi-inspired synchronous/event-driven
neuromorphic digital twin** using an AMD KV260/K26 Zynq
UltraScale+ PS+PL architecture. Repository:
`https://github.com/Xtimetraveler-Prime/Thesis`, source root
`Loihi_Digital_Twin/v3/`.

### Fresh-chat process (current gate)

1. Read `LOIHI_TWIN_ROADMAP.md` (the P08-B4.5.4.1–.4
   subsections), this seed, then
   `docs/P08_B4_5_4_4_OPERATOR_FSBL_PROTECTION_SOURCE_ACCEPTANCE_2026_11_05.md`,
   `docs/P08_B4_5_4_4_FSBL_PROTECTION_BRANCH_AND_PHYSICAL_READINESS_RUNBOOK.md`,
   `docs/P08_B4_5_4_3_OPERATOR_FSBL_XSA_SOURCE_ACCEPTANCE_2026_11_05.md`,
   `docs/P08_B4_5_4_2_OPERATOR_SYMBOLIC_XMPU_POLICY_ACCEPTANCE_2026_11_05.md`,
   and the original `docs/P08_B4_5_RESET_INTEGRITY_OPTIMIZATION_PROTOCOL.md`.
   For historical ground truth read
   `docs/P08_B4_4_2_RESET_PROFILE_PHYSICAL_RESULTS.md`.
2. Check CURRENT branch/PR heads and existing CI:
   #52→#53→#54→#55→#56→#57→#58→#59.
   **Current: `agent/v3-p08-b4544-fsbl-protection-review`**,
   draft PR #59 onto `agent/v3-p08-b4543-fsbl-boot-inventory`
   (draft #58). These are stacked, not merged. NO
   speculative rebase/merge to stale `main`.
3. Treat B4.5.4.4 original operator-local evidence as ACCEPTED
   **PC-only source** (report SHA pinned in current top block),
   not real FSBL boot or XMPU hardware proof. Do NOT rerun
   B4.5.3 authentic/unchecked Vitis apps just because
   a source audit completed; their full offline admission
   has already been independently accepted.
4. Implement **B4.5.4.5 source-only generated PSU security
   call-graph/boot-artifact provenance** on a **new feature
   branch from latest PR #59 head**, not inside an old
   B4.5.4.1–.4 branch. Keep each deliverable small,
   tests/CI passing and source/no-go outputs explicit.
   Update roadmap with authoritative AMD citations,
   plan/known gaps and new runbook, open stacked draft PR.
   Then provide the user FULL local commands with
   all exports/find alternatives and await local results.
5. Only AFTER the user verifies B4.5.4.5 may the next
   controlled submilestone assess actual boot-image
   provenance, per-port AXI reader IDs/slot permissions,
   14MiB backup/extra-half-MiB owner, and low-DDR A53
   owners. No board modifications or XSDB without
   a **separate explicit authorization and recovery plan**.

### Environment, working style, and actual output location

- Host: Linux terminal `dna@PC`; repo:
  `/home/dna/Git/Thesis`, current v3 tree:
  `/home/dna/Git/Thesis/Loihi_Digital_Twin/v3`.
- Python venv:
  `source ~/Git/Thesis/.venv-p08/bin/activate`.
  Use `PYTHONPATH="$PWD/scripts:$PWD/src" python3
  -m pytest -q -rs tests/test_...py` from `v3`.
- AMD Vitis installation `$HOME/Vivado/2025.2`.
  Installed public FSBL source:
  `$HOME/Vivado/2025.2/data/embeddedsw/lib/sw_apps/zynqmp_fsbl/src/`.
  Typical `xfsbl_handoff.c`, `xfsbl_hooks.c`,
  `xfsbl_hw.h` there; installed source does NOT
  prove it was used to build the active board FSBL.
- ORIGINAL Vivado routed P03 build is
  `v3/vivado/build/p03_2c_fpd128_route_20261011T225538Z/`.
  P03 routed XSA: `reports/p03_2_ps_mmio.xsa`
  SHA-256 `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
  Original matching generated PS init C is under
  `project/loihi_twin_v3_p03_mmio_impl.gen/sources_1/bd/
  loihi_twin_v3_p03_mmio_impl/ip/
  loihi_twin_v3_p03_mmio_impl_zynq_ultra_ps_e_0_0/psu_init.c`
  SHA `049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679`.
  Its original XSA ZIP root member has the SAME SHA.
- Evidence outside repo only:
  `$HOME/Thesis_Evidence`. Every script report
  gets a **NEW** `..._$(date -u +%Y%m%dT%H%M%SZ).json`.
  Use `test ! -e "$NEW_REPORT"`. Never delete/reuse
  operator successful or failed attempts.
- Do not copy/replace upstream AMD protected code
  without attribution. Keep references to tagged AMD/Xilinx
  2025.2 `xfsbl_hw.h`, `xfsbl_handoff.c` and AMD UG1085
  in roadmap and final thesis methods. These are
  vendor protection mechanisms, not new thesis inventions.

### GitHub development tools and gating

GitHub connector is available through `functions.exec` via
`tools.mcp__GitHub__fetch_file/create_file/update_file/
create_branch/create_pull_request/get_pr_info/fetch`.
Use `ALL_TOOLS` metadata discovery and actual action schemas.
A GitHub source commit or CI PASS is **not** equivalent to
an operator's actual Vitis build or physical KV260 evidence.
Use new branch; record full paths/SHAs; implement negative tests
for malformed C, missing generated XMPU config, false physical
claims and swapped original hashes; run no-board CI; wait for
operator local verification before completing a submilestone.

### Accepted phase evidence sequence (all from user's PC)

| Phase | Verification scope | Original external JSON SHA-256 |
| --- | --- | --- |
| B4.5.3 | Genuine distinct authentic-once and unchecked A53 ELF/map/report static paired recheck | `03b433527901a9d51dfb8a8ca99c0321d81335859d1be14505eb6a7be9369ec1` |
| B4.5.4.1 | Original source DDR geometry/ownership gap (physical NO-GO) | `7a1d87cf3278245a4a5ed612773ac228097e506f464861c3e1b69856f6ba56f2` |
| B4.5.4.2 | 6-port symbolic XMPU, 147456 transactions, reader list disabled | `ba89166f826425bcd69c86ee7b249f70cd39f359382fa69bd331a366678899f2` |
| B4.5.4.3 | Original XSA and installed FSBL source identity / call order | `9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5` |
| B4.5.4.4 | Local Vitis FSBL compile-time bypass/full-protection paths (16 tests PASS) | `e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9` |

Exact original JSON filenames/paths and more details are in
the next section 9. Preserve them as existing source evidence,
not proof of real boot XMPU permissions.

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

## 4. Ongoing P08-B4.5 reset-integrity experiment and future P08-B4.6

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

**Both original A53 variants were genuinely built under Vitis 2025.2
and independently accepted for OFFLINE static admission (B4.5.3).
B4.5.4.1–.4 PC-only ownership/source studies are also accepted.
No physical B4.5 inference has run, and the original guard fails
closed.** Follow
`docs/P08_B4_5_3_TWO_A53_VITIS_OFFLINE_BUILD_RUNBOOK.md`.
The original protection adapter still refuses to lock/verify the backup,
so original A/B ELFs are **for accepted offline static admission only**. There
is no B4.5 new board inference evidence.

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

## 9. Practical operator commands and the NEXT source-only phase

**B4.5.3 authentic-once and unchecked A53 apps were ALREADY genuinely
built in Vitis 2025.2, independently PC-audited, and accepted.**
**B4.5.4.1–.4 were ALREADY locally completed and accepted
PC-only; do NOT repeat them as though pending.**
Next task is B4.5.4.5 generated security data/call-graph/boot
provenance source audit. If the user explicitly says "continue",
create a NEW descendant branch from #59 head and implement
a host-only `psu_protection` dependency/table analyzer with
negative tests, CI and an operator runbook. **No physical
programming or Vitis boot-image build is authorized.**

### Fresh checkout and complete accepted source exports

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b4544-fsbl-protection-review
git pull --ff-only origin agent/v3-p08-b4544-fsbl-protection-review
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# Accepted B4.5.3 two genuine A53 Vitis build roots (read-only):
export P08_B45_ONCE_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_once_build_20261105T041935Z"
export P08_B45_UNCHECKED_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_unchecked_build_20261105T042140Z"

# Accepted independent 2-ELF evidence and subsequent audits:
export P08_B454_ACCEPTED_PAIR="$HOME/Thesis_Evidence/p08_b45_pair_independent_20261105T045733Z.json"
export P08_B454_GAP_REPORT="$HOME/Thesis_Evidence/p08_b454_ddr_owner_gap_20261105T051850Z.json"
export P08_B4542_POLICY_REPORT="$HOME/Thesis_Evidence/p08_b4542_xmpu_policy_pc_20261105T054738Z.json"
export P08_B4543_SOURCE_REPORT="$HOME/Thesis_Evidence/p08_b4543_fsbl_xsa_inventory_20261105T060831Z.json"
export P08_B4544_SOURCE_REPORT="$HOME/Thesis_Evidence/p08_b4544_fsbl_protection_branch_20261105T062334Z.json"

# Original P03 routed build and exact accepted hardware XSA:
export P08_B4545_P03_BUILD="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z"
export P08_B4545_XSA="$P08_B4545_P03_BUILD/reports/p03_2_ps_mmio.xsa"

# Installed Vitis 2025.2 FSBL source; not proof of active boot:
export P08_B4545_FSBL_ROOT="$HOME/Vivado/2025.2/data/embeddedsw/lib/sw_apps/zynqmp_fsbl/src"
export P08_B4545_FSBL_HANDOFF="$P08_B4545_FSBL_ROOT/xfsbl_handoff.c"
export P08_B4545_FSBL_HW_HEADER="$P08_B4545_FSBL_ROOT/xfsbl_hw.h"
export P08_B4545_FSBL_HOOKS="$P08_B4545_FSBL_ROOT/xfsbl_hooks.c"

# Exact previous P03-generated and XSA-matching psu_init.c:
export P08_B4545_PSU_GEN="$P08_B4545_P03_BUILD/project/loihi_twin_v3_p03_mmio_impl.gen/sources_1/bd/loihi_twin_v3_p03_mmio_impl/ip/loihi_twin_v3_p03_mmio_impl_zynq_ultra_ps_e_0_0"
export P08_B4545_PSU_INIT="$P08_B4545_PSU_GEN/psu_init.c"

# Optional header/Tcl to discover: DO NOT fake their existence:
export P08_B4545_PSU_HEADER=""
export P08_B4545_PSU_TCL=""
export P08_B4545_ACTIVE_BOOT_BIF=""
export P08_B4545_ACTIVE_BOOT_ELF=""
export P08_B4545_ACTIVE_BOOT_BIN=""

# New host-only result: fresh external NO-OVERWRITE file:
export P08_B4545_SOURCE_REPORT="$HOME/Thesis_Evidence/p08_b4545_psu_config_source_$(date -u +%Y%m%dT%H%M%SZ).json"
```

The **new** B4.5.4.5 implementation has not yet been created:
the path above is a naming suggestion, not an existing script.
After the next assistant implements it, tests/arguments must
match the actual committed code and runbook rather than being
invented in advance.

### Read-only exact path discovery, hashes, and source details

```bash
find "$P08_B4545_PSU_GEN" -maxdepth 2 -type f \
  \( -name 'psu_init.h' -o -name 'psu_init.tcl' \
     -o -name 'psu_init_gpl.c' -o -name 'psu_init_gpl.h' \) \
  -print 2>/dev/null

find "$P08_B4545_P03_BUILD" -type f \
  \( -name 'psu_init.h' -o -name 'psu_init.tcl' \
     -o -name 'psu_protection.c' \) -print 2>/dev/null

# Acceptable to inspect these 4 verified XSA ROOT MEMBERS
# without writing/extracting; inspect exact ZIP entries in Python:
python3 - <<'PY'
import zipfile, hashlib, os
from pathlib import Path
xsa = Path(os.environ["P08_B4545_XSA"])
with zipfile.ZipFile(xsa) as zf:
    for name in ("psu_init.c", "psu_init.h",
                 "psu_init.tcl", "psu_init_gpl.c"):
        if name in zf.namelist():
            info = zf.getinfo(name)
            if info.file_size > 2*1024*1024:
                print("SKIP OVERSIZE:", name, info.file_size)
                continue
            raw = zf.read(info)
            print(name, len(raw), hashlib.sha256(raw).hexdigest())
        else:
            print("MISSING:", name)
PY

# Read-only grep for generated security call graph:
grep -n -E 'psu_protection\(|psu_protection_lock\(|psu_protection_data\(|psu_mask_write\(' \
  "$P08_B4545_PSU_INIT" | head -90

# Investigate what filesystem contains; NO assumption
# that a found BOOT.BIN/BIF/ELF is actually booted:
find "$HOME/Thesis_Evidence" "$PWD" "$HOME/Vivado/2025.2" \
  -type f \( -name 'BOOT.BIN' -o -name '*.bif' \
     -o -iname '*fsbl*.elf' -o -name 'compile_commands.json' \) \
  -print 2>/dev/null | head -100

# Known original exact fingerprint integrity checks:
sha256sum "$P08_B4544_SOURCE_REPORT" "$P08_B4543_SOURCE_REPORT" \
  "$P08_B4545_FSBL_HANDOFF" "$P08_B4545_FSBL_HW_HEADER" \
  "$P08_B4545_PSU_INIT" "$P08_B4545_XSA"
```

**Expected hashes for the six lines just above:**

```text
e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9
9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5
161ffc06037594fd14be856dce29ec6643eb97c8dcbe2872abc414b8c4d5d80a
f8dc576e02f3f8678600e210eda7ee7b7a6713c15b112078da88036d6cb5d1f7
049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679
52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
```

If a path is missing, use actual `find` results and the
**accepted expected SHA** to select the true original source.
For source not found (e.g. active BOOT.BIN) mark UNKNOWN rather
than substituting another board's example. **Never modify**
the installed FSBL, generated Vivado P03 output, original
accepted ELF/bitstream or BOOT.BIN during investigation.

### New development/testing commands (next instance to tailor)

```bash
# After the new branch/source/tests have been created via GitHub:
cd ~/Git/Thesis
git status --short
git fetch origin
# Replace BRANCH_NAME with the ACTUAL newly created feature branch:
# git switch BRANCH_NAME
# git pull --ff-only origin BRANCH_NAME
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# Run tests for each code milestone; actual test filename from commit:
# PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
#   tests/test_p08_b4545_<actual_name>.py

# Always set every script input and NEW external out export, then
# run the exact command saved in its corresponding new runbook.
```

**No real board actions are approved.** A future real KV260
pilot is a separate, gated task only after boot provenance,
genuine DDR/XMPU ownership, validated PS+PL reader exceptions,
backup write denial, trusted guard attestation, a new admitted
ELF, reversible boot media and fresh explicit consent.

### Historical physics and frozen scientific context

P08-B4.4.2 physically accepted ~5826.77 ms A53 reset
median (~2908.6 ms SHA source + ~2908.6 ms SHA destination,
~7.0 ms total memcpy), so the B4.5 authenticated-once
hypothesis aims to remove per-image SHA overhead without
weakening source immutability. Prior uninstrumented
~13,034.1 ms whole-image median was from a **different**
session; these medians cannot be subtracted as if paired.
B4.5.2 unchecked mode is an intentional integrity-free
diagnostic lower bound, NOT a safe protected variant.

The official Track B MNIST TEST remains
`SEALED_NOT_ACCESSED`. No new physical KV260 B4.5.1
or B4.5.2 inference session is admitted or authorized.
PR #52 through #59 remain stacked and unmerged unless
the user specifically approves a merge.

**END: Next task is B4.5.4.5 read-only generated PSU/FSBL
XMPU configuration source tracing; not a repeat A53 build
and not a KV260 board pilot.**
