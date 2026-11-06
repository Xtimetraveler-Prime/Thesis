# P08-B4.6.4a — A-rebuilt versus B_AUTH_ONCE service timing boundaries (PC ONLY)

**STATUS: new source-only code and negative tests; independent operator-local PASS pending. No new KV260 execution, JTAG authorization or six-session paired A/B acceptance. Draft PR stack must remain unmerged.**

Read first: [current handoff](P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md), [accepted real rebuilt-A2.1 physical receipt](P08_B46_REBUILT_A21_REAL1024_ACCEPTANCE_AND_NEXT_STUDY_2026_11_05.md), [B4.6 source gate](P08_B46_SELECTED_AUTH_ONCE_PC_SOURCE_GATE_RUNBOOK.md), and [roadmap](../LOIHI_TWIN_ROADMAP.md). This work is a child of `agent/v3-p08-b46-a21-candidate-physical-validation`, draft PR #69, **not** the superseded pre-rebuild PR #67 head.

## Exact arms and already accepted evidence (immutable)

**Track A = separately accepted *rebuilt* A2.1** genuine Vitis A53 ELF SHA256 `fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793`, original 42 neurons/26 PL dispatches. The operator ran a genuine, independent original 1,024-image packed-neural/selected 26×42 trace and A53 timer validation in a SINGLE real KV260 session, report SHA256 `b57f20beb80943fb8d6b526a2e119cd12b17641db6fa7e55dbab8ca9f2f148a6`, real CNTFRQ 99,999,001Hz and 1023 ordinary-image median 35.696886611897256ms. Original historical A2.1 ELF SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0` is **STILL MISSING** and is NOT substituted for rebuilt A. The historical `scripts/run_p08_a3_2_1024.sh` remains permanently pinned to that historical SHA; the new legitimate physically used launcher is `scripts/run_p08_b46_rebuilt_a21_1024.sh`. Do not weaken either SHA pin.

**Track B = selected B_AUTH_ONCE_UNPROTECTED_V2** original 1010 neurons / 27 virtual cores / 702 dispatches genuine ELF SHA256 `a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85`, previous real B4.5 once full1024 acceptance SHA256 `06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a`. NOT B4.4 per-frame SHA, NOT unchecked, NOT memory-protected. Prior signed frozen A(rebuilt)/B 1024 TRAIN source report SHA256 `ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56` must remain unchanged. Both standalone prior A and B accepted experiments count as **ZERO** of the future proposed six NEW A/B sessions.

## Read-only frozen-source A53 boundary crosswalk

| Step | A original frozen C, deployed in separately rebuilt A2.1 ELF | B original authenticate-once V2 C | Significance |
| --- | --- | --- | --- |
| Clock | `read_ticks()` A53 CNTVCT_EL0; header `p08_clock_rate()` CNTFRQ_EL0 | `observed_counter()` / `observed_frequency()`; six-phase `p08_b2_meter` | Both A53 system clocks; use real **per-run** CNTFRQ; never convert PL cycles via CNTFRQ. |
| Start | `t.service_start=read_ticks(NULL)` at `execute_image` entry before `load_image_record(frame)` | Per-image `now=observed_counter()`, then `p08_b2_meter_start` **before** `p08_b45_perf_reset_image` | Comparable broad *before per-image work* concept, different first steps. |
| Reset/ingress | `load_image_record` validates encoded image, `p07_a2_run_frame` prepares/restores one-core master | `p08_b45_perf_reset_image` copies/clean/invalidate 27 mutable contexts; encode original 784B raw input; scheduler reinitialize | Distinct context copy, input mapping and scheduler timing. No matched reset microphase. |
| Neural | 26 A dispatches to P03/PL, original 42 neurons, plus A53 host orchestration | 26 ticks, **702** dispatches, virtualized DDR paging, routing and A53/PL mixed control | **Not** pure PL compute-only or equal neural work. |
| End | `commit_frame_result` writes/flushed original compact journal; selected trace flush before `t.after_commit=read_ticks(NULL)` | `commit_journal` flushes B journal, then `P08_B2_AFTER_JOURNAL_COMMIT`, `p08_b2_meter_finish` `cntvct[6]-cntvct[0]` | Both end immediately after neural journal commit at source level, but emitted data and preceding subwork differ. |
| Excluded overhead | A timing-sidecar record and P08 header write **after** stop time | B timing record, reset profile and progress mailbox write **after** meter final mark | Outside each ordinary timer but perturbs between-image cache/activity. A selected trace (ordinal1023) costs extra and is excluded from ordinary stats. |
| Session-only prior work | A descriptor/master integrity and startup **outside** image loop | Authenticate-once full source SHA bind **before** 1024-frame loop | Do not add once-only bind to B per-image service or claim backup XMPU protection. |

**Audit conclusion:** original source confirms both use the concept “A53 per-image entry through durable neural journal commit” but **does not establish physically equivalent boundaries or matched service internal work.** No automatic inference of B/A neural kernel speedup, throughput efficiency, significance or energy. Count **1023 ordinary frames** per genuine future run, validate all 1024 numerically, separately check selected trace ordinal1023. Original accepted A/B own neural oracle, full 26tick FNV, signed TRAIN pixel order and all27 postrun B backup endpoint equality remain separate mandatory evidence gates.

## Physical launcher and recovery boundary — NO-GO

- **A rebuilt genuine physical script:** `scripts/run_p08_b46_rebuilt_a21_1024.sh` independently checks rebuilt ELF SHA, original source report, source/ELF admission, P03.2c XSA, frozen original TRAIN stage, PS width, P07 staged 64MiB DDR physical `[0x40000000,0x44000000)` overwrite, original A sidecar, board recovery. Its `P08_B46_PREFLIGHT_ONLY=YES` has no board contact; do NOT use without a separate reviewed preflight even after user approvals.
- **B accepted historical standalone launcher:** `scripts/p08_b45_perf_full1024_physical_run.py` uses a different explicit *CPU halt before P03 programming* path, six original signed DDR transfers, 27×512KiB backup source+readbacks, B 1024 journal/timing/reset profile, B-specific V2 admission, ten risk approvals, reboot after any JTAG attempt. Historical Track A and B launcher variants **must not be directly concatenated** into a six-session experiment. Original JTAG/FPD+LPD128 ordering, low-DDR ELF, snapshot/resume behavior and nonexclusive Linux/FSBL/DMA/PL ownership need a separately signed per-arm run protocol.
- **Safety:** no new user authorization to issue **any** JTAG/XSDB/Vivado, DDR, boot image edits or new A53 build. Prior A2.1 JTAG console output demanded a KV260 power-cycle but its *actual completion was not separately confirmed*. Confirm physical reboot and environment before *any* subsequently independently approved board attempt. External evidence lives only under fresh `$HOME/Thesis_Evidence` directories and is never overwritten, including failed runs.

## Execute native/static validation in your VS Code Linux terminal (NO BOARD)

These commands explicitly use only the newly stacked child branch; keep existing work safe if `git status --short` shows uncommitted changes.

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b46-4a-service-boundary-audit
git pull --ff-only origin agent/v3-p08-b46-4a-service-boundary-audit

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b46_ab_service_boundary_audit.py \
  tests/test_p08_b46_auth_once_source_gate.py \
  tests/test_p08_b46_a21_rebuild_admission.py \
  tests/test_p08_b46_rebuilt_a21_first1024_physical.py \
  tests/test_p08_b45_full1024_latency_synthesis.py \
  tests/test_p08_b45_perf_full1024_independent_cli.py

python3 -m py_compile scripts/p08_b46_ab_service_boundary_audit.py
bash -n scripts/run_p08_a3_2_1024.sh scripts/run_p08_b46_rebuilt_a21_1024.sh
```

Issue ONE fresh, immutable **PC-only** static audit receipt; it needs NO ELF, no compiled artifact and no hardware.

```bash
mkdir -p "$HOME/Thesis_Evidence"
export B46_AB_BOUNDARY_REPORT="$HOME/Thesis_Evidence/p08_b46_ab_boundary_source_audit_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$B46_AB_BOUNDARY_REPORT" || { echo "NO-GO: existing evidence"; exit 1; }

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
  scripts/p08_b46_ab_service_boundary_audit.py \
  --v3-root "$PWD" --out "$B46_AB_BOUNDARY_REPORT"

python3 -m json.tool "$B46_AB_BOUNDARY_REPORT"
sha256sum "$B46_AB_BOUNDARY_REPORT"
```

Expected outputs *after native tests pass*:

```text
P08_B46_AB_FROZEN_SERVICE_BOUNDARY_SOURCE_AUDIT_PASS=1
P08_B46_AB_PHYSICAL_BOUNDARY_EQUIVALENCE_PROVEN=0
P08_B46_AB_ELF_OR_PHYSICAL_ADMISSION_PERFORMED_BY_STATIC_AUDIT=0
P08_B46_AB_NEW_HARDWARE_AUTHORIZED=0
```

This *static* flag stating it did not perform an ELF/physical admission **does not rescind** the already independently accepted distinct rebuilt A2.1 standalone real physical run. Return native test summary, the new JSON path/SHA256 and any NO-GO. **Do not execute either historical A or B hardware runner for this task.** Official MNIST TEST sealed.

## Next submilestone after local review

Design and independently test six NEW, signed no-overwrite *per-session* protocol/admission records. Require separately explicit human authorization for **each** JTAG session and new coldboot; pre-register exact A B / B A / A B order. Preserve all retries/failures. Validate independent original A/B neuron/spike/trace and timers for each; study-level unit is one physical boot per arm in each of **3** matched pairs, not 1023 independent replicates. Only then consider descriptive paired session-median differences/ratios, order effects, uncertainty and signed closeout. No merge until user explicitly authorizes it.
