# CURRENT RESEARCH HANDOFF — Loihi v3 FROZEN / Neuromorphic_Accelerator/v1 NEW (2026-11-07)

> **PROJECT NAMING AND LOCATION SUPERSESSION (2026-11-07):** The former proposal called *Loihi_Digital_Twin/v4* is now explicitly **`Neuromorphic_Accelerator/v1/`**, a fresh version sequence under the new top-level **`Neuromorphic_Accelerator/`** umbrella. This is **not** a new version of the Loihi twin. New project has only an initial README and open architecture trade-study questions under `Neuromorphic_Accelerator/v1/docs/ARCHITECTURE_DESIGN_QUESTIONS.md`; no selected microarchitecture, tested HLS/RTL engine, new KV260 test, or v1 performance claim. Former references to 'v4' below are **dated historical proposals**, superseded by this note. The preserved Loihi v1–v3 version roots and signed evidence MUST NOT be moved or modified. The new v1 discussion should distinguish *physical compute engines* (which YANA and HiAER-Spike still call cores) from *Loihi-style virtual logical cores*; choose state groups/cache boundaries for DDR locality rather than copying 27 old logical-core pages. **Next development sequence is documented in `Neuromorphic_Accelerator/v1/roadmap.md` (M01–M09; currently proposed and NOT STARTED):** candidate neuron/group/hybrid state placement, independent v1 neural software reference, traffic instrumentation, v3 HLS reuse audit, sparse PL event hardware, DDR residency, scheduler/cache controls, genuine KV260 trials, then quantitative thesis analysis. Reassess the LIF/reference and network/time semantics BEFORE v1 engine source. Source attribution and license review are milestone gate requirements.

**AUTHORITATIVE FIRST-READ CONTEXT; overrides all older active instructions below.** Following advisor discussion, the thesis is pivoting from Loihi-constrained architectural emulation toward an experimental **sparsity-aware, DDR-backed virtualized LIF SNN accelerator** (future v4). v4 will preserve independently verified neuron dynamics and virtualized logical compute while **not** treating Loihi sizes, access restrictions, or scheduler details as mandatory. Time-multiplexing/off-chip memory are established prior art: novelty must be based on the **measured interaction of DDR-backed virtualization, sparse/event-driven execution, active-context locality and working-set management**, possibly an activity-aware context scheduler. No v4 branch or RTL architecture has yet been selected; next step is design brainstorming, targeted literature, benchmark contract and experiment planning, **not code on v3**.

## Central research questions (working wording)

> How much performance must we sacrifice to virtualize a larger network, and how much of that cost can sparsity-aware execution recover?

> How do DDR-backed virtualization and event-driven sparsity interact to determine the performance, scalability, and hardware efficiency of FPGA-based spiking neural network accelerators?

Candidate contributions (research hypotheses, **not accepted results**): (1) controlled measurement/curves of virtualization cost versus network size, spike/connectivity sparsity, context locality and resident capacity; (2) design/test sparsity- or locality-aware DDR context scheduling/caching against simple policies; (3) independently neural-correct, demonstrably resource-constrained FPGA SNN acceleration on networks beyond resident memory, with fair local-memory controls and comparison to published accelerators **only** at disclosed equivalent workloads and timer boundaries. Use YANA, SENECA, HiAER-Spike, Ansari/Wielgosz and NIR in root `LitReview.md`. Four controlled small-network variants considered: timestep/on-chip, event/on-chip, timestep/DDR, event/DDR; large DDR-scale study separately where on-chip controls cannot fit. Exact v4 experiments TBD.

## v3 termination status (do not resume legacy physical test runbook)

- v3 **frozen research baseline**. Historical acceptance remains true; incomplete planned work remains incomplete, not silently completed. Previous single 27-core/1010-neuron B_AUTH_ONCE V2 full1024 independently accepted (1023-image median ~7225.137ms), separate 42-neuron A full1024 standalone accepted (median ~35.6969ms); unequal workloads and distinct timer work, so not matched acceleration. The exact original SHA, contexts, runbooks and test logs are preserved.
- The formerly planned **six independent coldboot A/B_AUTH_ONCE A B / B A / A B** physical study was **discontinued after one genuinely NEW accepted Session 01 A**, not completed. Original slot01 run `/home/dna/Thesis_Evidence/p08_b46_s01_A_20261106T052149Z/`, independent original all1024 neural + 26×42 trace/A53 PASS, CNTFRQ **99,999,001 Hz**, 1023-image ordinary A53 median **35.67722641549189 ms**. Report JSON and same-capture rereview SHA256 **`26e9cfbc9b6485313d89e72f80ec578498539c902838140940f1027da4038eb0`**; raw hash manifest SHA **`8c5e1b05775bbcaf087b55203569da949abfe16ebc3d46d0b98035002a3a6440`**. Operator PC slot01 ledger `/home/dna/Thesis_Evidence/p08_b46_s01_A_accepted_20261106T052707Z.json` SHA **`ceb17077b99bb5f4bfc346ad7147cb6df65aedd73f1940c25c32f3c8ce007bec`**, first slot accepted only. Fresh physical boot/power-cycle operator-attested, **not** electrical instrument proof. All five remaining 02:B/03:B/04:A/05:A/06:B are **CANCELED / NOT RUN**. No paired AB/BA/AB statistic accepted; do **not** run the stale Session02 command under historical sections below.
- Earlier original B_AUTH_ONCE V2 ELF SHA `a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85` remains verified **unprotected**. The separately rebuilt A2.1 new ELF SHA `fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793` does not replace lost historical original SHA `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`. No Loihi-bitwise silicon clone, secure XMPU/DDR backup hardware protection, energy/power measurement, pure PL acceleration, official MNIST TEST access, strict A/B physical service-work equivalence, or matched-network speedup.
- `LOIHI_TWIN_ROADMAP.md` has the **2026-11-07 authoritative v3 pivot/freeze banner**; old P04–P09 *remaining* milestones are canceled for v3 while accepted evidence remains; **P10** is the FINAL optional **DEFERRED bounded v3 optimization** (no work now). Future v3 optimizations require a new explicit user decision and timebox. V4 design can reuse source/oracles but no commits or hardware steps authorized yet.

## Repository, command, build and evidence workflow — keep for future chats

- Repo: `Xtimetraveler-Prime/Thesis`, active integration branch `main`; preserved Loihi twin version roots `Loihi_Digital_Twin/v1/` (verified old baseline), `v2/` (accepted Loihi manycore), `v3/` (frozen KV260 archive). **NEW program location:** `Neuromorphic_Accelerator/` with `Neuromorphic_Accelerator/v1/` for first-generation new accelerator/virtualization exploration (README and `docs/ARCHITECTURE_DESIGN_QUESTIONS.md` only, no source engine yet). Do **NOT** create a `Loihi_Digital_Twin/v4/`. Root `README.md` holds thesis questions; root `LitReview.md` holds original+new literature.
- v3 tree: `Loihi_Digital_Twin/v3/src/loihi_twin_v2/` (historical package name intentionally retained), `scripts/` (source/ELF admissions, PC independent verification, optional destructive hardware runners), `tests/` (native regression), `vivado/` (build, Tcl, bitstream/HDL), `hls/`, `rtl/`, `hardware/`, `docs/`, `artifacts/`, `LOIHI_TWIN_ROADMAP.md`. Source-backed claim scopes and file provenance live in exact historical docs below. Never silently migrate names or discard v1/v2/v3 evidence.
- Local PC shell (VS Code Ubuntu):

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b46_4b_six_session_plan.py \
  tests/test_p08_b46_4b_session_receipt.py \
  tests/test_p08_b45_perf_full1024_independent_cli.py
```

- For future changes: create **new named branch from freshly pulled main**, implement one explicit scope/submilestone, native `python3 -m pytest -q -rs` with relevant regression suites, `python3 -m py_compile` for changed Python, `bash -n` for shell, original Vivado/Vitis/XSA/ELF SHA provenance if relevant; use no-board GitHub Actions, draft PR, obtain user PC native/physical evidence when needed, only merge after explicit user permission. The present user explicitly requested **one-time consolidation of the existing v3 stacked PRs into main**; this does not authorize later merges automatically.
- User PC immutable real evidence is outside checkout in `$HOME/Thesis_Evidence/` (not `/tmp`), with exact ELF/bitstream/route/report SHA checks; GitHub CI cannot rehash original private board captures. Keep raw logs, signed report and no-overwrite new evidence folders; no reinterpretation of rereviews as separate physical sessions, no fabricated observed CNTFRQ, throughput or energy. Official MNIST TEST remains sealed and is NOT an implicit prerequisite for v4.
- Physical safety for **future separately approved** KV260 work: `source "$HOME/Vivado/2025.2/Vitis/settings64.sh"`; single `hw_server` on TCP 3121 and no competing Vivado/XSDB clients; use PuTTY only for short read-only inspection (e.g. `sudo xmutil listapps`); any JTAG/DDR/PS halt/PL programming is potentially destructive, needs **session-specific explicit risk review**, known disposable Linux/JTAG ownership, fresh coldboot and **mandatory physical power-cycle after ANY JTAG attempt**; do not resume halted Linux. FSBL/PL/RPU/DMA DDR-ownership exclusion and XMPU unprotected backups remain **UNPROVEN**. **Do not launch any preserved old hardware runner merely because its commands are documented.**
- Source update links: [frozen v3 roadmap](../LOIHI_TWIN_ROADMAP.md), [first newly accepted A study slot](P08_B46_4B_SESSION01_REAL1024_A_FIRST_PAIR_OPERATOR_ACCEPTANCE_2026_11_05.md), [historic six-study runbook, now canceled](P08_B46_4B_SIX_NEW_AB_BA_AB_SESSION_RUNBOOK.md), [historic A/B source boundary audit](P08_B46_4A_AB_SERVICE_BOUNDARY_SOURCE_AUDIT_RUNBOOK.md), root [literature review](../../../LitReview.md), root [README](../../../README.md).

## Archived historical handoff below

Everything below this heading is preserved chronologically to retain provenance, CLI syntax, historical failure/acceptance boundaries and original one-at-a-time physical safety policy. Its old statements 'CURRENT', 'NEXT B', 'NOT RUN', 'PENDING', and 'NO MERGE' refer to their **original time** and do not override the new v3 freeze, canceled experiments, or the one-time user-approved integration request.

---

# ARCHIVED: AUTHORITATIVE CURRENT HANDOFF — START HERE (2026-11-05 local / 2026-11-06 UTC)


> **Read this block and the linked accepted evidence FIRST.** The 1,200+
> lines of historical dated notes below are an append-only research
> provenance record. Many say “A2.1 NOT RUN,” “old ELF missing,”
> “B4.5 pending,” etc.; those are **historically true but superseded**
> for the current experiment by this top block. Never undo historical
> acceptance, interpret historical NO-GO as current, or mark any
> future experiment accepted without a distinct new physical receipt.

## 0. AT-A-GLANCE VERIFIED PROJECT STATE

**Project:** Loihi-inspired K26/KV260 FPGA digital twin, GitHub
`Xtimetraveler-Prime/Thesis`, project root
`Loihi_Digital_Twin/v3`. Primary research objective:
**board-local** A53 scheduling/DDR virtualized contexts with PL
Loihi-like neural execution; frozen independent software oracle,
physical numeric equivalence, reproducible full-image A53
service latency, integrity risk strictly scoped.

**Most recent operator verification — B4.6 reconstructed A2.1:**
On November 5 local (November 6 UTC), operator physically
executed 1,024 original TRAIN-derived input images with
**new genuine rebuilt A2.1 standalone A53 ELF** SHA
`fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793`.
Original P07 packed software oracle, selected 26×42 trace
and 1,024 CRC/clock-checked A53 service records **PASS**;
physical JTAG runner printed final
`P08_B46_NEW_REBUILT_A21_ORIGINAL_1024_PHYSICAL_AND_INDEPENDENT_PASS=1`
and `script_exit_status=0`. Real A53 counter:
**99,999,001 Hz**. Median over 1,023 ordinary
images (selected trace ordinal 1023 excluded):
**35.696886611897256 ms**.

Actual physical run evidence:
`/home/dna/Thesis_Evidence/p08_b46_A21_rebuilt_real1024_20261106T033101Z/`.
First physically verified report
`p08_b46_rebuilt_A21_1024_independent.json`
SHA **`b57f20beb80943fb8d6b526a2e119cd12b17641db6fa7e55dbab8ca9f2f148a6`**.
Captured `physical_output_sha256.txt` SHA
**`7978b82ade256fc9e419510036131115e93a18b6b80e55048e3132904d223a7e`**.
Independent OFFLINE **rereview of the SAME original physical
capture** (not a second boot) produced
`/home/dna/Thesis_Evidence/p08_b46_rebuilt_A21_rereview_20261106T034152Z.json`,
same SHA
**`b57f20beb80943fb8d6b526a2e119cd12b17641db6fa7e55dbab8ca9f2f148a6`**.
User pasted terminal output and SHA values; GitHub connector
did **not** receive/download their raw PC private evidence.
See [accepted physical receipt](P08_B46_REBUILT_A21_REAL1024_ACCEPTANCE_AND_NEXT_STUDY_2026_11_05.md).

**Previous source gate:** Actual reconstructed-A2.1 vs selected
B_AUTH_ONCE same original TRAIN 1,024 image order/pixel SHA pass:
`/home/dna/Thesis_Evidence/p08_b46_Arebuild_vs_Bauthonce_source_20261106T025815Z.json`,
SHA `ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56`,
marker `P08_B46_SOURCE_GATE_PC_ONLY_PASS=1`.
This source report historically contains
`P08_B46_TRACK_A_REBUILT_CANDIDATE_PHYSICAL_REACCEPTED=0`:
it was finalized **BEFORE** the genuine A2.1 revalidation,
so **do not change its bytes**; the new accepted physical
report and this dated handoff supersede it for A2.1's
ONE independently accepted physical run.

**Historical A2.1 original ELF** SHA
`fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`
was originally built under
`/tmp/v3_p08_a2_build_20261018T193149Z`
and is now missing following PC reboot; **DO NOT claim
recreated byte-for-byte** or relax old historical A3.2
acceptance. Rebuilt A ELF is separately source-, XSA-,
and hardware-reaccepted. Frozen P03.2c XSA SHA
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
Real ELF directory:
`/home/dna/Thesis_Evidence/p08_a2_1_rebuild_20261106T023403Z/vitis_workspace/p08_a2_board.elf`.

**B4.5.5 CLOSED:** User independently completed REAL
1,024-image physical V2 authenticate-once and unchecked
trials, all predictions/spike vectors/full 26tick 1010-neuron
FNV and 27 post-run context backup endpoints exact.
Selected future B architecture is **auth-once V2**, NOT unchecked:
`B_AUTH_ONCE_UNPROTECTED_V2`, ELF SHA
`a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85`.
Accepted once independent original scalar/full1024 JSON:
`/home/dna/Thesis_Evidence/p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json`,
SHA `06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a`.
Unchecked independent SHA
`68655383c582577986d7bdd253b21ecf1c933d234136d51b7b5076591c63cf79`.
Final four-source B4.5.5 accepted synthesis:
`/home/dna/Thesis_Evidence/p08_b45_full1024_synthesis_20261106T011541Z.json`,
SHA `b04aa0ada133a61ce052ce40f7aa7dbf667da6958031cfdc63b99cc57354eff0`;
Markdown SHA
`8cd181ecedb407e04418ef5ab121e6560a8fef3a5908ac0ec39acfbdae41fef3`.
Original B4.4 complete-service median 13034.111501ms vs
auth-once 7225.137459ms; original separately instrumented
reset median 5826.767549ms vs auth-once 8.766998ms.
**Descriptive** cross-session ratios ~1.804× service and
664.63× reset; not a randomized paired speedup.
The remaining mixed 26-tick/702 dispatches/DDR pager/PS
routing phase has 6944.179ms median and **96.11% of summed
ordinary service ticks**; NOT pure PL neural arithmetic.
No original backup XMPU write protection was proven and
transient DDR corruption was NOT excluded; postrun 27-backup
equality is an endpoint-only integrity observation.
See [B4.5.5 final accepted report](P08_B45_5_FINAL_REAL_PHYSICAL_QUANTITATIVE_ACCEPTANCE_2026_11_05.md).

**Current B4.6 status:** A rebuilt original-source 42-neuron /
26-dispatch original TRAIN physical run **ACCEPTED**;
B selected original genuine V2 auth-once 1,010-neuron /
27 virtualized logical cores/702 dispatches has original
independent 1024 physical run **ACCEPTED for B4.5.5**.
**ZERO of SIX NEW B4.6 counterbalanced session runs completed.**
Signed A-vs-B identical full-service timing-scope comparison
is **NOT yet accepted**.
The A standalone validation and earlier B4.5 once physical
test are NOT B4.6 repeated paired study sessions.
Last output:
`P08_B46_NEW_A_B_SIX_REPEATED_PHYSICAL_SESSIONS_ACCEPTED=0`,
`P08_B46_A_B_TIMER_BOUNDARY_EQUIVALENCE_PROVEN=0`,
`P08_B46_6_SESSION_TRACK_A_VS_B_AUTH_ONCE_STUDY=NOT_RUN`.
Board printed mandatory “REBOOT KV260”; separate power-cycle
confirmation was **not supplied**. Confirm full power cycle
before any further JTAG.

## 1. DEVELOPER WORKFLOW AND ACCESS BOUNDARIES

**Repo:** `https://github.com/Xtimetraveler-Prime/Thesis`.
All new source/code changes on **feature branches** using the
GitHub connector, with native negative/contract tests and GitHub
Actions CI, then user pulls to Ubuntu VS Code and runs EXACTLY the
matching native test suite, Vitis builds and physical runs.
The assistant can read/update public GitHub source through
GitHub tools; it **cannot see** user-owned real
`/home/dna/Thesis_Evidence` files on their PC unless user
pastes/upload them. DO NOT claim board/JTAG test was run
by assistant or GitHub CI. Operator handles all KV260 hardware,
PuTTY, xsdb and physical approvals personally. All accepted
Git external raw files are operator-reported until actually
read/downloaded and rehashed. User wants copy/paste exact
VS Code terminal commands after every development + test change,
branch names, sha, CI and clear STOP/PASS markers.

**Current actual branch:**
`agent/v3-p08-b46-a21-candidate-physical-validation`,
draft PR **#69**, stacked on unmerged draft #68
(rebuilt-A candidate admission), #67 (B4.6 A vs B_AUTH_ONCE
same-source), #66 (B4.5.5 quantitative closeout), #65
(B4.5 V2 reset-bind repair).
Latest snapshot after recorded physical acceptance has
docs-only updates. **NEVER merge into main or merge stacked
PRs unless user explicitly requests.** For next B4.6
work, create a NEW distinct branch from CURRENT #69 head
(e.g. `agent/v3-p08-b46-service-boundary-audit`), then
a draft PR stacked on #69. Don't modify protected
historical P07/P03/V2 B4.5 original source or
historical A3.2 runner/ELF SHA in place.
Record exact source/XSA/ELF SHA before building or JTAG.

### Standard user PC pull + regression test

Run in user's VS Code Ubuntu terminal (not assistant/cloud):

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b46-a21-candidate-physical-validation
git pull --ff-only origin agent/v3-p08-b46-a21-candidate-physical-validation

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
 tests/test_p08_b46_new_a21_physical_safety.py \
 tests/test_p08_b46_auth_once_source_gate.py \
 tests/test_p08_b45_full1024_latency_synthesis.py \
 tests/test_p08_b45_perf_full1024_independent_cli.py \
 tests/test_p08_b45_full1024_reset_bind_repair.py

bash -n scripts/run_p08_b46_rebuilt_a21_1024.sh
git status --short
~~~

Change `git switch` + `git pull` branch names only when
a new branch exists; use `--ff-only`, never force push,
reset --hard, discard uncommitted user edits, or merge without
approval. Tests run on host need original project imports
`PYTHONPATH="$PWD/scripts:$PWD/src"`; PC may require
`~/Git/Thesis/.venv-p08` for `torch` dependencies of
historical independent original P07 neural verifier.
Use Python 3.x interpreter from existing venv; don't silently
retrain or regenerate accepted original model/artifacts.

### Machine, directory and project layout — important

~~~text
/home/dna/
  Git/Thesis/                           git repository root
    .venv-p08/                          Python project virtual environment
    Loihi_Digital_Twin/v3/               ACTIVE v3 root
      LOIHI_TWIN_ROADMAP.md              chronological master roadmap
      docs/                              acceptance reports / runbooks / this handoff
      scripts/                           PC Python gates, physical shell runners
      tests/                             native offline regression tests
      src/loihi_twin_v2/                 frozen model/oracle Python
      software/p03/ p07/ p08/            frozen C + distinct A53 apps
      vivado/                             P03 XSA/bit, Tcl, original artifacts
      artifacts/                          original trained frozen source assets
      data/mnist_raw/                    canonical ORIGINAL TRAIN IDX dataset
  Thesis_Evidence/                       persistent OUT-OF-GIT source/evidence
    p08_a2_1_rebuild_20261106T023403Z/ genuine rebuilt A21 build/ELF/map
    p08_a3_2_stage1024_20261019T003150Z/ original accepted A 1024 stage
    p08_b46_Arebuild_vs_Bauthonce_source_20261106T025815Z.json
    p08_b46_A21_rebuilt_real1024_20261106T033101Z/ new real A capture
    p08_b46_rebuilt_A21_rereview_20261106T034152Z.json
    p08_b45_perf_once_full1024_V2_20261105T192804Z/
    p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json
    p08_b45_full1024_synthesis_20261106T011541Z.json
    ... other accepted P07/P08 pilot, original B4.4 and full1024 captures
  Vivado/2025.2/Vitis/settings64.sh       installed AMD Vitis/Vivado tools
~~~

P03 accepted route:
`$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports`
with `p03_2_ps_mmio.xsa/.bit/.ltx` and original metrics.
**Do not move/overwrite original route/XSA**. Normal
Vitis build command, when new rebuild explicitly approved:

~~~bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source "$HOME/Vivado/2025.2/Vitis/settings64.sh"
export P03_DIAG_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
# Choose NEW dated persistent P08_A2_BUILD_DIR under ~/Thesis_Evidence
# ONLY for a newly approved build, NEVER overwrite the accepted rebuilt ELF.
# bash scripts/build_p08_a2.sh
~~~

**CRITICAL NEVER use `/tmp`, `/var/tmp`, pytest directories,
`/dev/shm` or Git checkout as the SOLE copy** of an
accepted ELF, Vitis build/source, linker map, bitstream/XSA,
original model, oracle, JTAG evidence or report. A
restart erased/made unavailable historical A2.1 /tmp build;
pytest-discovered similarly named ELFs were **synthetic**
SHA `13d6152f339a100ace3c45f01e35d78e82009562ff99a299294be6ba6a75deb0`.
Always store dated unique persistent
`$HOME/Thesis_Evidence/<experiment>_<UTC>`
folders; preserve source, ELF/map, build_identity.txt,
Vitis logs, SHA manifest and hardware raw captures.
Make a separate SHA-verified off-machine backup.
User evidence files are not automatically in Git;
do not create fake sandbox links or pretend Git preserves them.

### Re-establish useful environment variables (PC)

~~~bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source ~/Git/Thesis/.venv-p08/bin/activate
export P03_DIAG_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"

export P08_B46_REBUILT_A21_BUILD="$HOME/Thesis_Evidence/p08_a2_1_rebuild_20261106T023403Z"
export P08_B46_A_STAGE_DIR="$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z"
export P08_B46_SIGNED_SOURCE_REPORT="$HOME/Thesis_Evidence/p08_b46_Arebuild_vs_Bauthonce_source_20261106T025815Z.json"
export P08_B46_REBUILT_A21_RUN_DIR="$HOME/Thesis_Evidence/p08_b46_A21_rebuilt_real1024_20261106T033101Z"
export P08_B46_A_RECHECK_JSON="$HOME/Thesis_Evidence/p08_b46_rebuilt_A21_rereview_20261106T034152Z.json"

export B46_B_ONCE_ELF="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_20261105T192804Z/vitis_workspace/p08_b45_perf_once_full1024.elf"
export B46_B_ONCE_REPORT="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json"
export B46_B45_SYNTHESIS="$HOME/Thesis_Evidence/p08_b45_full1024_synthesis_20261106T011541Z.json"

sha256sum "$P08_B46_REBUILT_A21_BUILD/vitis_workspace/p08_a2_board.elf" \
 "$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa" \
 "$P08_B46_SIGNED_SOURCE_REPORT" \
 "$P08_B46_REBUILT_A21_RUN_DIR/p08_b46_rebuilt_A21_1024_independent.json" \
 "$P08_B46_A_RECHECK_JSON" \
 "$B46_B_ONCE_ELF" "$B46_B_ONCE_REPORT" "$B46_B45_SYNTHESIS"
~~~

Expected exact SHA pins from top paragraphs. The rebuilt-A
source-only admission JSON hash/path was NOT included in the
latest user logs; retrieve its actual original file via
`find "$HOME/Thesis_Evidence" -maxdepth 1 -name 'p08_b46_a21_rebuilt_source_admission_*.json' -print`
or read physical capture `physical_identity.txt` for its
signed SHA; do not invent filename or SHA.

**If first reviewing actual physical evidence on PC WITHOUT
new JTAG**, read these existing files:

~~~bash
cat "$P08_B46_REBUILT_A21_RUN_DIR/attempt_exit_status.txt"
cat "$P08_B46_REBUILT_A21_RUN_DIR/verify.log"
sha256sum \
 "$P08_B46_REBUILT_A21_RUN_DIR/p08_b46_rebuilt_A21_1024_independent.json" \
 "$P08_B46_REBUILT_A21_RUN_DIR/physical_output_sha256.txt" \
 "$P08_B46_A_RECHECK_JSON"
~~~

No further A-only physical revalidation is needed merely
to reproduce this verified report. Both accepted JSON
SHA values equal because they recomputed from same
stored evidence; do not count twice.

## 2. BOARD OWNERSHIP AND EVIDENCE RULES — NONNEGOTIABLE

**Hardware:** KV260/K26 Zynq UltraScale+ MPSoC.
PC Ubuntu + VS Code for development; PuTTY for board UART;
Vivado/Vitis **2025.2** for PC builds and JTAG; one
dedicated `hw_server -s tcp::3121` where required.
Never let assistant/cloud claim actual board tests without
operator receipts.

Track A (A2.1) historic JTAG runner overwrites
**64 MiB DDR [0x40000000, 0x44000000)**; PS FPD
HPM0 128-bit acceptance check, original static P03.2c
bitstream, physical source readbacks, reset/journal/trace
capture. Track B_AUTH_ONCE uses DIFFERENT original SIX
DDR source transfers, 27×512KiB mutable physical
contexts and unprotected original backup contexts, a
different JTAG launcher and exact genuine 1010-neuron
source. The two original launchers are NOT interchangeable.
Do not assume stopping Linux applications via
`sudo xmutil listapps` / `sudo xmutil unloadapp`
excludes boot DMA / DDR masters. Real memory
ownership/DMA exclusivity NOT proven by readback or
128bit PS interface checks. Earlier operator explicitly
accepted the reduced-integrity experimental constraint
for B4.5; a later run requires its **own** physical
approval. No hardware backup XMPU/protection equivalence.

**Every destructive JTAG attempt**: fresh disposable
KV260 Linux/JTAG session, dedicated USB/debug owner,
no competing XSDB/Vivado sessions, explicit range/source
risk consent, original signed sources and a NEW
`~/Thesis_Evidence` evidence dir, check output hashes,
then **POWER-CYCLE THE BOARD even if FAIL**. Never
resume halted Linux. Abort upon unexpected terminal,
timeouts, output mismatches or concurrent clients.
If user says only “REBOOT KV260” output printed,
do NOT assume the power-cycle physically happened.
Do not run a six-session batch in the background:
operator runs each session, verifies/records physical
results and reboot before next.

**No official MNIST TEST** (t10k) data opened, retrained,
or scored; `SEALED_NOT_ACCESSED`. All original
TRAIN-derived input population (1024 frozen indices/raw
784-byte pixel SHA) immutable; no secret retraining or
model edits; each arm has its OWN frozen neural oracle.
Different A vs B trained weights and number of neurons:
their predictions need not match each other.

## 3. EXACT NEXT B4.6 TASKS TO CLOSE THE STUDY

1. **CURRENT NEXT: PC-only A/B image-service boundary audit.**
   Source A
   `software/p08/p08_a2_board.c` `execute_image`:
   `t.service_start=read_ticks(NULL)` just BEFORE
   `load_image_record`; `t.after_commit=read_ticks(NULL)`
   just AFTER `commit_frame_result` (and optional selected
   trace flush). Source B selected
   `software/p08/p08_b45_perf_once_full1024_a53.c`:
   `p08_b2_meter_start(...,observed_counter())`
   before original 27-context reset; `AFTER_JOURNAL_COMMIT`
   captured after `commit_journal`. Both include mixed
   PS+PL work; image 1023 trace effects excluded from ordinary
   1023 medians. **Do not call scopes equivalent just
   because these look similar**—write precise source-level
   timer contract and read both original timing sidecar
   schemas and relevant `cntfrq_el0`/timestamp parsing.
   Check whether B per-image timer includes reset, A
   restore, scheduler setup, ingress and output commit,
   and whether trace/flush are outside ordinary measure.
   Produce a separately tested, no-board evidence report
   and approved comparison protocol BEFORE hardware study.
   A 35.6969ms single A and B4.5 7225ms single B
   are descriptive prior context only and must NOT be
   reported as B4.6 paired benchmark.
2. **Source-gate six truly new independent physical sessions.**
   Pre-register three counterbalanced temporal pairs
   **A B / B A / A B**; six fresh board boot sessions,
   THREE A and THREE selected B_AUTH_ONCE. A is the
   **rebuilt accepted new SHA** `fa9268...`; B is
   **the genuine B_AUTH_ONCE V2 accepted ELF** SHA
   `a19b50...`, NOT unchecked or original full-SHA B4.4.
   Require actual independent original P07 packed neural
   all1024/selected26×42 trace for each A; original
   1010-neuron scalar/FNV full26 tick+10 spike count and
   27 postrun backup readbacks for each B; stage/readback
   original TRAIN 1024 sources; capture A53 actual
   `CNTFRQ_EL0`; 1023 ordinary image latency rows
   (ordinal1023 isolated); signed original hardware and
   ELF, power-cycle proof after every physical attempt.
   Need new source/runner studies and distinct approval
   for each session. Preserve each aborted attempt; no
   posthoc silent replacement. Original older A-only
   recovery and B4.5 once single run are not study sessions.
3. **Independent paired-session analysis and scientific result.**
   Use each physical boot as experimental unit:
   within each accepted session report median, P95
   nearest rank, counts/trace, min/max, full image
   ordinal vector and source/hardware pins; within each
   temporal pair compute ratio **B session median / A
   session median** and difference in ms, note run order
   AB vs BA, then geometric mean of three paired ratios,
   spread/order effect; N=3 *pairs*, not 1023
   independent hardware trials. No stronger significance
   or confidence claim than three sessions support.
   This is **system/workload comparison** between 42
   and 1010 neuron original networks, not equal-complexity
   FPGA kernel throughput or energy improvement. Identify
   source/time/PS+PL/DDR and security limitations.
4. **Beyond B4.6:** review the ROADMAP, then propose
   bounded separate research milestones for detailed
   paging/routing/MMIO and 702-dispatch A53/PL
   attribution (B4.5 phase is **96.11%** mixed service
   share), real steady-state throughput, board-level
   power/energy with defined boundaries, DDR owner/
   XMPU integrity proof if pursued, stronger prospective
   neural benchmark/source provenance, and later
   deferred multi-physical HLS compute engines only
   if resident-context memory port arbitration is
   redesigned. Do not invent an already approved
   `B4.7` milestone. Keep TEST seal and prior original
   protected vs unprotected variant distinctions.

**Immediate code starting point:** new draft branch
`agent/v3-p08-b46-service-boundary-audit` based on
`agent/v3-p08-b46-a21-candidate-physical-validation`
when user asks to continue. Work PC-only first, add native
negative tests, CI, documentation and commands; then
bring the owner-controlled KV260 study to operator
in explicitly gated sequential sessions. NEVER start
destructive JTAG solely because previous single A and
single B separately passed. Current PR #69 not merged.

## 4. DOCUMENT INDEX AND CURRENT SOURCE OF TRUTH

1. [New accepted B4.6 reconstructed A2.1 real physical receipt](P08_B46_REBUILT_A21_REAL1024_ACCEPTANCE_AND_NEXT_STUDY_2026_11_05.md)
2. [B4.6 first-physical original runbook; already executed successfully](P08_B46_REBUILT_A21_FIRST_1024_PHYSICAL_RUNBOOK.md)
3. [B4.6 user-selected authenticate-once source gate runbook](P08_B46_SELECTED_AUTH_ONCE_PC_SOURCE_GATE_RUNBOOK.md)
4. [B4.6 new A2.1 rebuilt C/ELF original-source admission](P08_B46_REBUILT_A21_DISTINCT_ELF_PC_ADMISSION_2026_11_05.md)
5. [B4.5.5 accepted final 1024 physical quantitative phase closeout](P08_B45_5_FINAL_REAL_PHYSICAL_QUANTITATIVE_ACCEPTANCE_2026_11_05.md)
6. [B4.6 draft preregistered counterbalanced protocol — earliest B arm selection superseded by auth-once](P08_B46_1_PC_ONLY_COUNTERBALANCED_TRACK_A_B_PROTOCOL.md)
7. `LOIHI_TWIN_ROADMAP.md` in v3 root, authoritative dated longitudinal roadmap, chronological history below.

**Never mistake historical headings below, which precede this update,
for the current milestone state.**

---

## HISTORICAL HANDOFF NOTES — PRESERVED FOR PROVENANCE; SUPERSEDED WHERE ABOVE


> **LATEST B4.6 SOURCE PASSED; DISTINCT REBUILT A2.1 REAL HARDWARE VALIDATION RUNNER READY / NOT RUN (NOV 6 UTC).**
> Operator ran NEW B4.6 original 1024 frozen TRAIN-index/pixel
> matched A candidate vs selected authentic-once B gate:
> `P08_B46_REBUILT_A21_VS_AUTH_ONCE_FROZEN_1024_TRAIN_POPULATION_PASS=1`,
> `P08_B46_SOURCE_GATE_PC_ONLY_PASS=1`. Real new source report:
> `/home/dna/Thesis_Evidence/p08_b46_Arebuild_vs_Bauthonce_source_20261106T025815Z.json`,
> SHA `ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56`.
> New A2.1 historical-source rebuilt A53 ELF exact SHA
> `fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793`;
> historical 2026-10-18 A2.1 ELF SHA
> `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`
> NOT reproduced, and old accepted A3.2 physical results
> remain tied to historical ELF. Distinct new PC A2.1
> actual Vitis source/ELF admission file SHA not supplied
> in this turn; runner requires the existing real file
> and compares every staged and imported C/header, XSA,
> ELF and build receipt anew.
>
> **CURRENT ACTIVE STACKED BRANCH**
> `agent/v3-p08-b46-a21-candidate-physical-validation`,
> built on unmerged #68, adds NEW
> `scripts/run_p08_b46_rebuilt_a21_1024.sh`
> and `scripts/p08_b46_a21_rebuilt_independent_physical_verify.py`,
> standalone original NEW-SHA rebuilt A21 1024 TRAIN numerical
> recovery. The new physical runner retains original P03.2c
> XSDB FPD 128-bit, 64MiB DDR overwrite, 6-source
> physical readbacks, original P03 bitstream, isolated new
> A53 ELF and original P07 packed software neural oracle
> + selected 26x42 trace, 1024 CRC-checked A53 service
> receipts. Both original JTAG/FPGA source and old original
> physical runner are frozen. `P08_B46_PREFLIGHT_ONLY=YES`
> runs source/SHA/geometry gates and NEVER contacts board.
> Physical execute requires 6 explicit owner/memory/risk/
> reboot/TEST/new candidate approvals; user performs hardware
> only in fresh disposable Linux/JTAG session with no conflicting
> DDR/DMA owners; mandatory board power cycle after ANY
> JTAG attempt. New independent report proves A21 neural
> reacceptance for THIS original 1024 run only, NOT
> six coldboot A-vs-B_AUTH_ONCE comparison, same
> time boundary, hardware XMPU or electrical efficiency.
> No new board operations performed by assistant.
>
> **Operator current exact VS Code and KV260 instructions:**
> `docs/P08_B46_REBUILT_A21_FIRST_1024_PHYSICAL_RUNBOOK.md`.
> Ask for new real A2.1 terminal and independent report SHA,
> after reboot. Then review A/B common A53 timing boundaries
> and stage six new separately authorized A B/B A/A B
> sessions with original frozen TRAIN image population and
> each arm's OWN independently authenticated scalar oracle.
> DO NOT launch six experiments from only the source PASS;
> prior B4.5 once physical run is not a new B4.6 repeat.
> Preserve historical original ELF original TEST seal,
> PC-only source reports, and all physical data outside /tmp.
>

> **LATEST USER A2.1 REBUILD COMPLETED; DISTINCT SHA, B4.6.2R PC-ONLY ADMISSION NEXT (OVERRIDES ALL BELOW).**
> User successfully rebuilt original Track A2.1 A53 firmware
> under persistent
> `/home/dna/Thesis_Evidence/p08_a2_1_rebuild_20261106T023403Z`.
> GENUINE new A2.1 ELF SHA
> `fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793`;
> original XSA SHA
> `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
> Vitis original builder pass, DDR PT_LOAD isolation pass,
> and `P08_A2_1_KV260_LATENCY=NOT_RUN`.
> OLD historical A2.1 ELF SHA
> `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`
> WAS NOT reproduced (`ORIGINAL_A21_BINARY_REPRODUCED=0`).
> The original accepted A2.1/A2.2 1024 physical results
> are historical and attached only to original accepted A
> SHA. NEVER change old original pin or pretend new ELF
> has already passed real board oracle.
>
> **NEW CURRENT ACTIVE BRANCH**
> `agent/v3-p08-b46-a21-rebuild-admission`, stacked on draft
> #67, not merged. New `scripts/p08_b46_a21_rebuild_admission.py`
> checks separate new A2.1 actual SHA, real original P03
> XSA, Vitis receipt/build identity, complete original A2.1/P07/P03
> staged C+headers hash to Git, real AArch64 ELF header and
> load segments disjoint from 0x40000000–0x44000000, rejects
> tmp as sole authoritative build, emits fresh source admission
> with no false physical neural acceptance. Existing
> `scripts/p08_b46_auth_once_source_gate.py` original SHA
> default remains FAIL-CLOSED. New two explicit optional
> `--a-rebuilt-admission` + `--a-rebuilt-xsa`
> independently re-audit rebuilt actual candidate before
> B1 strict original 1024 TRAIN source IDs and raw pixel SHA
> against original genuine B4.5 once/64-shard oracle.
> Output B4.6 manifest flags NEW A2.1 CANDIDATE,
> old historical binary NOT recovered, per-session
> physical JTAG NOT authorized, new A neural parity/TIMER
> hardware acceptance still FALSE. No KV260 touched.
>
> **NEXT USER ACTION** PC-only commands and safeguards:
> `docs/P08_B46_REBUILT_A21_DISTINCT_ELF_PC_ADMISSION_2026_11_05.md`.
> Run new native host tests, new A source/ELF admission,
> then A candidate vs original B_AUTH_ONCE 1024 shared TRAIN
> source gate. Share both new JSON SHA and any NO-GO. Only
> after both PC gates pass do we design new distinct
> user-authorized A candidate 1024 physical revalidation runner
> + independent P07 packed oracle and A53 timer evaluation.
> Do NOT invoke historical A3.2 physical runner against a
> binary with different SHA, or waive original XSA/DDR/FPD
> gates. NO six paired study runs yet. Keep original TEST
> SEALED and build/evidence off /tmp with backup.
>

> **LATEST A2.1 ARCHIVE SEARCH AND CONTROLLED PC-ONLY REBUILD PATH.**
> User found only `/home/dna/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z.tar.gz`
> using their broad home/archive search. Original Git
> `docs/P08_A3_1_PHYSICAL_ACCEPTANCE.md` establishes that
> A3.1 pilot used **A2.2 detailed per-tick ELF** SHA
> `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`,
> not A2.1 image-only. The tar contents have NOT yet been
> listed; verify read-only with
> `tar -tzf "$HOME/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z.tar.gz" | grep -Ei 'p08_a2_board[.]elf|p08_a2_2_board[.]elf|build_identity|[.]elf$'`.
> If a genuine A2.1 ELF is inside, extract separately OUTSIDE
> existing accepted evidence and check original SHA
> `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`.
> Otherwise use the original historical script
> `scripts/build_p08_a2.sh` with
> `P08_A2_BUILD_DIR="$HOME/Thesis_Evidence/p08_a2_1_rebuild_<UTC>"`,
> `P03_DIAG_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"`
> (only if actual accepted routed XSA SHA
> `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`),
> after sourcing Vitis 2025.2. This build stage only,
> no board. Compare the new ELF SHA to accepted A2.1.
> If different, DO NOT spoof original SHA or change
> original accepted B4.6 gate: treat it as NEW candidate
> pending separately reviewed static, numerical and
> physical reacceptance. Archive build sources, ELF/map,
> build_identity and Vitis build log persistently and
> SHA-verify independent backup.
>

> **CRITICAL ARTIFACT RETENTION / B4.6 BLOCKER — 2026-11-05 local.**
> The historical genuine accepted Track A A2.1 Vitis standalone
> ELF SHA `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`
> was compiled at
> `/tmp/v3_p08_a2_build_20261018T193149Z/vitis_workspace/p08_a2_board.elf`
> per `docs/P08_A3_2_2_PHYSICAL_CAPTURE_PROTOCOL.md` and
> `docs/P08_A3_2_3_REPEATED_LATENCY_PROTOCOL.md`.
> Operator later rebooted their Linux PC; that original /tmp build
> directory is missing. All discovered `/tmp/pytest-of-dna/`
> `p08_a2_board.elf` files are TEST-ONLY synthetic fixtures
> SHA `13d6152f339a100ace3c45f01e35d78e82009562ff99a299294be6ba6a75deb0`
> and MUST NEVER be used as genuine Track A firmware.
> Original A2.1 ELF recovery remains UNRESOLVED;
> B4.6 source gate cannot PASS until exact original genuine ELF
> is found or a distinctly identified reconstructed ELF is
> separately admitted and revalidated. DO NOT weaken pinned SHA
> or pretend a reconstructed ELF is the historical accepted binary.
>
> **PERSISTENT STORAGE RULE FOR ALL FUTURE CHATS:** NEVER
> place sole/authoritative Vitis builds, genuine ELFs and linker
> maps, XSAs, bitstreams, original input sources, host snapshots,
> test evidence, baseline reports, original SHA pins or run
> manifests under `/tmp`, `/var/tmp`, system cache or pytest
> working dirs. These are disposable and can be purged across
> boots/automatic cleanup. Use dated, dedicated durable
> `$HOME/Thesis_Evidence/<unique_build_or_run>` directories
> OUTSIDE the Git checkout, verify their original SHA256,
> retain `build_identity.txt`, ELF, map, staged source pins,
> reports, exact toolchain/XSA identity and accepted run receipts;
> make a separate off-machine backup before destructive
> work and check archived SHA after copying.
> A Git source file or Markdown path DOES NOT back up a
> user-local compiled ELF. Do not modify historically accepted
> evidence in place. Stop on missing artifact before any
> physical operation. No new KV260 authorization here.
>

> **LATEST 2026-11-05 LOCAL / 2026-11-06 UTC B4.5.5 CLOSED AND B4.6 AUTHENTICATE-ONCE SELECTED (OVERRIDES ALL BELOW).**
> User supplied genuine four-report B4.5.5 original/optimized
> source-pinned, all1024 A53 physical service+reset
> sidecar re-audit Markdown and hash. Final
> `/home/dna/Thesis_Evidence/p08_b45_full1024_synthesis_20261106T011541Z.json`
> SHA `b04aa0ada133a61ce052ce40f7aa7dbf667da6958031cfdc63b99cc57354eff0`;
> Markdown SHA `8cd181ecedb407e04418ef5ab121e6560a8fef3a5908ac0ec39acfbdae41fef3`.
> Both V2 modes fully accepted independent real 1024
> original neural/FNV/spike and 27 final DDR context
> equality; original full service median 13034.1115ms,
> optimized once 7225.137459ms / unchecked
> 7222.415632ms; original instrumented reset median
> 5826.767549ms, once 8.766998ms / unchecked
> 8.732007ms. Same selected last trace ordinal1023
> excluded. Four sessions/distinct profiled ELF;
> descriptive cross-session ratios only.
> **Important confirmed NEW PHASE result:** authentic once
> all 26 ticks/702 virtualized dispatches+DDR paging+
> routing mixed A53/PL phase median `6944.179ms`,
> **96.11% of sum of ordinary image-service timer
> ticks**, versus context reset 0.12%. Unchecked
> same mixed neural stage median `6941.350ms`,
> also 96.11%. This is NOT PL neural compute-only.
> Do not repeat accepted 16/1024 hardware tests.
>
> **USER SELECTED B4.6 PRIMARY ARCHITECTURE**
> `B_AUTH_ONCE_UNPROTECTED_V2`. A = frozen original
> Track A A2.1, 42 neurons / 26 dispatch, original
> exact ELF SHA
> `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`.
> B = **frozen original V2 authenticate-once** 1010
> neurons / 27 virtual cores / 702 dispatch, original
> exact ELF SHA
> `a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85`.
> **NOT** old B4.4 full per-image SHA arm, and NOT
> unchecked. No false memory protection security equivalence,
> matched network complexity, PL-only speedup or energy claim.
> Each arm independently validates OWN oracle, same
> original 1024 TRAIN-derived source IDs + 784B pixel
> SHA and selected trace 1023.
>
> **NEW ACTIVE DESCENDANT**
> `agent/v3-p08-b46-auth-once-comparator-gate`,
> stacked on unmerged B4.5.5 PR #66. New
> `scripts/p08_b46_auth_once_source_gate.py`
> and native synthetic tests, source-only
> A old ELF and B_AUTH_ONCE V2 ELF / original B4.5
> independent/SHA-pinned synthesis, complete canonical
> original P08-A3.2 stage + strict original TRAIN dataset
> and 33 B2.4 frozen source assets,
> and 1024 exact raw image source index/pixel SHA
> comparison against original B scalar oracle. Outputs
> NEW no-overwrite outside-checkout six-session
> proposed `AB/BA/AB` JSON with all hardware
> authorizations FALSE, A/B timer equivalence FALSE
> (needs review), owner proof FALSE, full repeated
> physical benchmark NOT ACCEPTED. No JTAG/board
> writes performed. No new A/B physical sessions
> authorized by original user direction.
>
> **Operator exact PC instructions and source selection:**
> `docs/P08_B46_SELECTED_AUTH_ONCE_PC_SOURCE_GATE_RUNBOOK.md`.
> Locate original Track A2.1 ELF on local PC,
> check SHA, run PC-only native tests and original
> full TRAIN-source gate, return source admission JSON SHA,
> then review A/B service boundaries and historical
> different DDR/JTAG launchers before any new physical
> approvals. B4.5.5 real acceptance document:
> `docs/P08_B45_5_FINAL_REAL_PHYSICAL_QUANTITATIVE_ACCEPTANCE_2026_11_05.md`.
> Both old source artifacts and Test seal preserved;
> do not merge draft stack without explicit authorization.
>
> **LATEST REAL P08-B4.5 BOTH PHYSICAL FULL1024 INDEPENDENT ACCEPTANCES (OVERRIDES ALL LOWER STATUS).**
> 2026-11-05 (local; JSON timestamp Nov 6 UTC): new original
> V2 `once` independent FULL1024 real JTAG original frozen scalar,
> 10 spikes + 26tick trace FNV, original source, 27 final DDR backup
> and timing/reset report PASS; JSON
> `/home/dna/Thesis_Evidence/p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json`,
> SHA `06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a`.
> New V2 `unchecked` also independently PASS same original
> 1024-frame numerical/reset/backup criteria;
> `/home/dna/Thesis_Evidence/p08_b45_perf_unchecked_full1024_V2_verified_20261106T005240Z.json`,
> SHA `68655383c582577986d7bdd253b21ecf1c933d234136d51b7b5076591c63cf79`.
> Original B4.4.2 separately instrumented reset
> median 5826.767549ms, V2 once 8.766998ms / unchecked 8.732007ms:
> descriptive 664.6x / 667.3x ratio of separate medians.
> Original B4.4 whole service median 13034.111501ms,
> once 7225.137459ms / unchecked 7222.415632ms:
> descriptive ~1.804x whole-image speed ratio.
> Both selected trace ordinal 1023 excluded, 1023 ordinary frames.
> Do NOT claim repeated counterbalanced statistical significance,
> pure PL neural speedup, identical reset instrumentation,
> memory write protection, transient DDR exclusion or energy.
> The previously recorded V1 failed bind and preserved
> signed raw evidence remain valid historical artifacts;
> source of observed failure is solved sufficiently by genuine
> V2 result, no repeat first16/full1024 physical runs needed.
>
> **ACTIVE** `agent/v3-p08-b45-comparison-and-b46-handoff`,
> descendant of unmerged PR #65. Implements B4.5.5 **PC-only
> physical quantitative synthesis**:
> `scripts/p08_b45_full1024_latency_synthesis.py`
> accepts FOUR SHA-pinned independent original B4.4 service,
> B4.4.2 profiled reset, new V2 once/unchecked physical
> reports; separately verifies both NEW raw original 1024x256B
> A53 timing+reset physical captures and six CRC-additive
> clock-phase counters with actual per-session CNTFRQ.
> Emits new no-overwrite JSON+Markdown, all 1023 ordinary
> phase medians and share-of-sum percentages (identifies
> next paging/dispatch 26tick mixed A53/PL bottleneck).
> Native synthetic tests/CI PC only. Operator still needs
> to run this script against genuine local evidence, share
> source/report SHA and six phase breakdown before closing
> B4.5.5. No new Vitis build/FPGA/JTAG/PuTTY currently needed.
>
> **B4.6.1 PC-only design draft now exists:**
> `docs/P08_B46_1_PC_ONLY_COUNTERBALANCED_TRACK_A_B_PROTOCOL.md`.
> It explicitly defines original frozen A-vs-original frozen B
> six independent coldboot sessions AB/BA/AB, 1023 ordinary
> original TRAIN-source frames, actual A53 CNTFRQ, all
> neural/FNV provenance, pre-registered pairing across 3
> sessions (NOT treating 1023 images as independent boots),
> workload-size mismatch and reduced-integrity optimized B
> labeling restrictions. NO new physical authorization.
>
> **Exact commands and accepted paths**:
> `docs/P08_B45_FULL1024_QUANTITATIVE_CLOSEOUT_AND_B46_HANDOFF_2026_11_05.md`.
> After report PASS, B4.6 original roadmap next step is the
> PC-only protocol for six truly independent counterbalanced
> Track A-vs-Track B sessions AB/BA/AB with matched complete
> service start/stop, 1023 ordinary frames, per-run A53 frequency,
> independent coldboot/recovery and neural FNV, and study-level
> uncertainty. Track A 42 neurons/26 dispatch vs B 1010/702:
> system/workload not complexity-matched pure FPGA speedup.
> DO NOT silently treat B4.5 unprotected optimized
> configuration as original secure B4.4 Track B.
> Never merge draft stack without explicit user authorization.
>
> **LATEST OPERATOR V2 physical once preliminary PASS + independent CLI fix (OVERRIDES LOWER).**
> New V2 `once` genuine full1024 physical runner reports six original
> physical DDR readbacks PASS, SHA-pinned V2 ELF, strict 1024 terminal,
> 1024 neural/timing/reset sidecar captures, all 27 backup context
> after-run readbacks, and original frozen 1024 scalar/FNV+backup
> `P08_B45_PERF_FULL1024_SAME_SESSION_JTAG_SCALAR_FNV_AND_BACKUP_PASS=1`.
> Separate PC-only independent verifier **failed to begin** because
> `p08_b45_perf_full1024_independent_verify.py` had omitted the
> required `--pilot-once-report`/`--pilot-unchecked-report` flags
> from argparse despite invoking `bench.admission(args)` which
> requires both. Fixed them as REQUIRED arguments; new regression
> tests simulate `once` AND `unchecked` with the exact existing
> `P08_B45_FULL_COMMON`, fail closed if pilot files omitted.
> No ELF, XSDB or original scalar changes. The saved once
> physical evidence is valid; operator must run independent review
> after pulling latest branch, **NO JTAG re-run** for this CLI mistake.
> The operator reported the new V2 unchecked physical run currently
> IN PROGRESS; no result yet. **Do not edit/pull running checkout,
> open another hardware debugger, or restart KV260 until current
> experiment exits.** Then physically power-cycle KV260 before
> any further PC work as prescribed and run independent reviewer
> separately for both saved captures. Never claim final full1024
> parity or performance acceptance without independent PASS/JSON SHA.
> Active branch remains `agent/v3-p08-b45-full1024-reset-bind-repair`
> (stacked draft PR #65); no merge. See latest
> `docs/P08_B45_FULL1024_V2_RESET_BIND_REPAIR_AND_PC_BUILD_RUNBOOK.md`.
>
> **LATEST REAL FAULT 105 DIAGNOSIS + FULL1024 V2 BOTH-MODE FIX (OVERRIDES LOWER WORK).**
> Operator actually ran PC-only original failure decoder on
> `/home/dna/Thesis_Evidence/p08_b45_perf_once_full1024_physical_20261105T172141Z`.
> Original independent postmortem JSON
> `/home/dna/Thesis_Evidence/p08_b45_failure_diagnostic_20261105T174301Z.json`
> SHA `e500d8a6507ff4319216fc9e6a3ca1b7fce8a46e6d58d333f9e73b86a3324fb3`,
> saved failure mailbox SHA
> `8b7aa5810c9bf5977218936a0314a1fcfac3b07073b6dd8d4da625e9147e7231`.
> Physical mailbox FAIL `0xDEAD0823`,
> ordinal `0xFFFFFFFF` **PRE-IMAGE-0**, fault 105,
> `-bind_result=1` means underlying `P08_B45_RESET_INVALID=-1`;
> NOT one completed frame. 1024 ALL ZERO journal,
> timing, reset-only rows, zero numerical inferences completed.
> Preloop `pager.counters.dispatches=702` and `pager.counters.barriers=26`
> reflect likely STALE A53 global/BSS data: original A53
> page scheduler `p07_b3_init` runs only inside per-image
> loop that was never entered. Stale `reset_state.magic`
> was NOT recorded in V1, so do not claim an exact invalid branch.
>
> **NEW ACTIVE BRANCH**
> `agent/v3-p08-b45-full1024-reset-bind-repair`, draft stacked
> atop failure triage PR #64 (NO MERGES).
> Two distinct full1024 original `once` and `unchecked`
> A53 mains now use a one-time startup BSS workspace zero
> before P03/inference and new `p08_b45_perf_startup.c/.h`
> to check original backing/backup/sha-pointer disjoint
> geometry/callbacks/mode, then clear only the isolated
> reset state ONCE before its existing fail-closed
> `p08_b45_perf_reset_bind()`. Failure-only mailbox
> V2 fields record exact bootstrap reason code and
> old reset state magic/generation/poison and pager
> dispatch/barrier counts. PC-only V1/V2 postmortem
> decoder extended. GENUINE A53 Vitis images now require
> `P08_B45_PERF_[AUTH_ONCE|UNCHECKED]_ORIGINAL_27CORE_1024_A53_V2`
> identity and new sources; old V1 binaries FAIL gate.
> All accepted original MODEL/26tick/702 dispatch,
> baseline, both real successful pilot16 binaries,
> protected fail-closed guard, 1024 oracle/FNV/
> postrun 27 backup contract UNCHANGED. No
> hardware-backup/XMPU security claim.
>
> **Exact PC-only operator commands** in
> `docs/P08_B45_FULL1024_V2_RESET_BIND_REPAIR_AND_PC_BUILD_RUNBOOK.md`:
> pull new branch, run all native regression tests, then build
> **two NEW genuinely Vitis 2025.2 V2 ELFs/maps in separate fresh
> output dirs**, check both new genuine SHA/identity and both
> whole original 64-scalar shards/pilot source preflights.
> Only after offline PASS separately discuss/approve
> destructive dedicated JTAG rerun using same two-terminal
> nonintrusive host-side monitor; board reboot after any
> attempt. Original V1 failure evidence remains immutable.
> No new V2 physical run, no full1024 speedup accepted.
> No board-side or PuTTY diagnostics currently required;
> if V2 returns fault 105, its added reason code
> determines next targeted fix. Official TEST sealed.
>
> **LATEST NEW ORIGINAL FULL1024 PHYSICAL FAILURE (OVERRIDES LOWER PLANS).**
> 2026-11-05 operator attempted unprotected B4.5 `once`
> FULL1024 genuine A53 physical inference. Six original DDR readbacks,
> original P03/FPD+LPD128, full sidecar zero readbacks,
> genuine SHA-pinned A53 ELF download and terminal mailbox/
> journal/timing/reset-profile captures PASS. A53 **reported a
> real TERMINAL FAILURE**; XSDB printed
> `P08_B45_PERF1024_JTAG_ATTEMPT_FAILED_REBOOT_REQUIRED=1`
> and runner aborted, preserving originals in
> `/home/dna/Thesis_Evidence/p08_b45_perf_once_full1024_physical_20261105T172141Z`.
> NO actual terminal 1024/1024 numerical PASS, NO postrun 27 backup
> readback and NO full performance speedup accepted. Fault/index
> unknown until saved mailbox decoded. DO NOT infer root cause from
> reset warning; appeared in previously successful physical pilots.
> Operator MUST physically REBOOT after failed JTAG. DO NOT run
> unchecked full1024 or repeat any physical run now.
>
> **ACTIVE** `agent/v3-p08-b45-full1024-failure-triage` stacked
> on draft PR #63. It adds **PC-only, read-only**
> `scripts/p08_b45_full1024_failed_run_postmortem.py`,
> synthetic native tests, new incident docs and roadmap NO-GO.
> Reads saved 256B FAIL mailbox (real fault, exact index/count),
> three 256KiB original journals/timing/reset profiles, CRC
> and ORIGINAL frozen full1024 scalar/FNV oracle: fail-closed
> evidence of all completed frames, never claim complete run
> or postrun backup security. No board/serial/JTAG contact
> or new ELF build. See
> `docs/P08_B45_FULL1024_AUTH_ONCE_FAILED_JTAG_POSTMORTEM_2026_11_05.md`
> for exact VS Code terminal commands; user provides report
> SHA and actual fault marker. Only after diagnosis decide
> whether new code changes/tests and genuinely NEW ELF
> would be justified. Successful 16-frame once+unchecked
> independent physical receipts remain accepted and unmodified.
> No merges without explicit approval.
>
> **LATEST ACCEPTED 2026-11-05 PHYSICAL PILOT RESULTS AND NEW FULL1024 WORK (OVERRIDES ALL LOWER STATUS).**
> Both actual unprotected performance-only once and unchecked first16
> KV260 A53 pilots passed B4i CPU halt/FPD+LPD128 gate, original P03 shell,
> six original signed DDR transfer/readbacks, strict terminal neural
> completion, 27 postrun DDR backup records, and separately executed
> independent original first16 scalar+FNV+backup PASS.
> Operator-report original JSON/sha:
> once `/home/dna/Thesis_Evidence/p08_b45_perf_once_independent_20261105T154923Z.json`
> SHA `7ab975d3c062df2606357080c1eeda0904ea8aaba0aed4c02fda8ce1140ecdca`;
> unchecked `/home/dna/Thesis_Evidence/p08_b45_perf_unchecked_independent_20261105T160411Z.json`
> SHA `5f29cda8661cad64fe39231d42a84c3293bef96af6c7fe74c9c74b466a2195aa`.
> Source: pasted 488-line terminal transcript; raw JSON and DDR binary not
> uploaded. Both genuine pilot ELF source digests and reset warnings recorded
> in docs/P08_B45_OPERATOR_REPORTED_REAL_UNPROTECTED_PILOT16_ACCEPTANCE_2026_11_05.md.
> DO NOT ask user to repeat either successful 16-image physical run.
>
> **ACTIVE DESCENDANT BRANCH** `agent/v3-p08-b45-unprotected-full1024-progress`
> DRAFT PR #63 stacked on unmerged draft PR #62. Two DISTINCT full1024 A53 sources,
> builder+original SHA gates, original full 64 scalar shard re-check,
> accepted B4.2/B4.4 original physical baseline SHA,
> BOTH accepted real pilot16 JSON pins, strict 1024 single-session
> dedicated JTAG runner and all27 backup after capture, separate
> independent full1024 verifier. Live progress in SECOND PC VS Code
> terminal ONLY via host-side atomic progress_state.txt snapshots
> authored by the SAME XSDB mailbox polling process; no competing JTAG.
> No real new full1024 Vitis ELF nor physical execution yet. Never
> claim true speedup until all1024 original prediction/FNV receipts,
> 1024 valid reset+service timers, and independent 27 backup postrun
> byte equality pass. Exclude final special trace ordinal 1023 from
> 1023 ordinary latency medians. A single run per mode is descriptive,
> not a paired AB/BA repeated statistical estimate.
>
> **Runbook and operator exact commands:**
> `docs/P08_B45_UNPROTECTED_FULL1024_PHYSICAL_WITH_LIVE_MONITOR_RUNBOOK.md`.
> All complex commands in PC VS Code. PuTTY only short
> `sudo xmutil listapps`, conditional `sudo xmutil unloadapp`.
> Destructive execute requires ten explicit scoped YES risk flags,
> original CPU stop/PS128 first, and physical reboot after every
> JTAG attempt. Leave original protected B4.5 fail-closed guard,
> original accepted P03/P07/TEST and prior pilot/benchmark receipts
> unmodified. No PR merge without explicit operator approval.
>
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
