# P08-B4.6.4b — SIX NEW A/B_AUTH_ONCE REAL KV260 SESSIONS, ONE AT A TIME

**Status:** implementation and no-board tests only. The NEW session 1 physical run has NOT happened. Initial B4.6.4a signed source-boundary gate is operator-reported PASS and the 2026-11-06 UTC SHA is pinned below. **Nothing here automatically authorizes any new JTAG operation; the operator must approve each destructive session separately. No merge permission.**

Current child branch `agent/v3-p08-b46-4b-six-session-physical-admission`, stacked on B4.6.4a PR #70 (which is stacked on A2.1 real physical acceptance PR #69). Read the current [handoff](P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md), [roadmap](../LOIHI_TWIN_ROADMAP.md), [B4.6.4a A/B timer findings](P08_B46_4A_AB_SERVICE_BOUNDARY_SOURCE_AUDIT_RUNBOOK.md), [rebuilt-A original KV260 runbook](P08_B46_REBUILT_A21_FIRST_1024_PHYSICAL_RUNBOOK.md), and [B V2 once physical full1024 runbook](P08_B45_UNPROTECTED_FULL1024_PHYSICAL_WITH_LIVE_MONITOR_RUNBOOK.md).

**Frozen scientific question:** Compare A53 **entry-to-committed-neural-journal system service**, not matched network, power, energy, PL-only arithmetic or memory protection. Different original architectures, A 42 neurons/26 dispatches, B 1010 neurons/702 dispatches. The source scope is comparable broadly but strictly identical physical timer work is **NOT proven**. B V2 authenticates original context SHA once at session bind OUTSIDE the measured per-image interval and is UNPROTECTED from transient DDR writes. The order is **A B / B A / A B**: three independent temporal pairs, SIX independently booted sessions. Each captures 1024 original TRAIN-derived images; verify all1024 neural/trace and A53 clock records; ordinary distributions have **1023 images** because special trace ordinal1023 is excluded. No re-training or sealed official MNIST TEST. Existing earlier one A and one B full1024 standalone sessions are **ZERO** of the new six.

## 0. Gate inherited from B4.6.4a (operator pasted; original saved)

- Static service-boundary PC report:
  `/home/dna/Thesis_Evidence/p08_b46_ab_boundary_source_audit_20261106T045251Z.json`
  SHA256 **`41ea9f2958e9e31aaa120d368b1f325f16bc51ed63834c2748b2dde38d6cb430`**.
- A rebuilt genuinely physically accepted ORIGINAL 1024 independent:
  `$HOME/Thesis_Evidence/p08_b46_A21_rebuilt_real1024_20261106T033101Z/p08_b46_rebuilt_A21_1024_independent.json`
  SHA `b57f20beb80943fb8d6b526a2e119cd12b17641db6fa7e55dbab8ca9f2f148a6`. NEW distinct A ELF SHA `fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793`; historical A SHA `fc44...` still missing and **never relabeled**. The user's historical independent rereview was on the same old evidence, not a second boot.
- B V2 genuinely physically accepted prior auth-once single:
  `$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json`
  SHA `06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a`. Original B V2 ELF SHA `a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85`. NOT B4.4 full-SHA original or unchecked.
- Original full1024 raw image index/pixel SHA matched-A/B TRAIN source:
  `$HOME/Thesis_Evidence/p08_b46_Arebuild_vs_Bauthonce_source_20261106T025815Z.json`
  SHA `ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56`.
- Prior A physical runner printed mandatory power cycle; **not independently confirmed** from the earlier user paste. Physically power-cycle BEFORE the first newly approved run, not just before the second.

The raw historical accepted PC evidence remains private to the user's PC. GitHub/CI **cannot independently rehash it**. Original operator SHA pins are input claims until independently reopened by this PC-only script. A SHA and successful report are evidence integrity, not digital signatures or proof of boot independence.

> **B4.6.4b original-data schema correction (2026-11-06 UTC):** The accepted B4.5 V2 *independent* reporter emits `whole_image_service_descriptive_1023.ordinary_frames=1023`, NOT `ordinary_frame_count`. The latter belongs to the earlier preliminary original report. The first version of `p08_b46_4b_six_session_plan.py` falsely rejected the SHA-correct old B independent acceptance with `NO-GO: B4.5 V2 original once standalone independent evidence invalid`; fixed BOTH the no-board preregistration and B session receipt checks, added regression tests, and preserved all genuine SHA pins. No prior original evidence was edited, and this is NOT evidence of a new physical A/B run. If plan generation fails, NEVER hash a nonexistent output or proceed to JTAG.

## 1. PC-only: pull, native tests and create SHA-pinned six-session study sheet

Run on the PC VS Code terminal, no board tools needed; protect uncommitted work shown by `git status`.

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b46-4b-six-session-physical-admission
git pull --ff-only origin agent/v3-p08-b46-4b-six-session-physical-admission

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b46_4b_six_session_plan.py \
  tests/test_p08_b46_4b_session_receipt.py \
  tests/test_p08_b46_ab_service_boundary_audit.py \
  tests/test_p08_b46_auth_once_source_gate.py \
  tests/test_p08_b46_new_a21_physical_safety.py \
  tests/test_p08_b45_perf_full1024_independent_cli.py

python3 -m py_compile \
  scripts/p08_b46_4b_six_session_plan.py \
  scripts/p08_b46_4b_session_receipt.py
bash -n scripts/run_p08_b46_rebuilt_a21_1024.sh
~~~

Export REAL original inputs exactly; do not replace with synthetic test fixtures. Both ELFs must already exist under **persistent** `$HOME/Thesis_Evidence`. No need to rebuild or repeat accepted standalone A/B experiments now.

~~~bash
export B46_BOUNDARY="$HOME/Thesis_Evidence/p08_b46_ab_boundary_source_audit_20261106T045251Z.json"
export B46_MATCHED_SOURCE="$HOME/Thesis_Evidence/p08_b46_Arebuild_vs_Bauthonce_source_20261106T025815Z.json"
export B46_A_PRIOR="$HOME/Thesis_Evidence/p08_b46_A21_rebuilt_real1024_20261106T033101Z/p08_b46_rebuilt_A21_1024_independent.json"
export B46_B_PRIOR="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_verified_20261106T005213Z.json"
export B46_A_ELF="$HOME/Thesis_Evidence/p08_a2_1_rebuild_20261106T023403Z/vitis_workspace/p08_a2_board.elf"
export B46_B_ELF="$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_20261105T192804Z/vitis_workspace/p08_b45_perf_once_full1024.elf"

for f in "$B46_BOUNDARY" "$B46_MATCHED_SOURCE" "$B46_A_PRIOR" \
 "$B46_B_PRIOR" "$B46_A_ELF" "$B46_B_ELF"; do
  test -s "$f" || { echo "STOP: missing $f"; break; }
done
sha256sum "$B46_BOUNDARY" "$B46_MATCHED_SOURCE" "$B46_A_PRIOR" \
 "$B46_B_PRIOR" "$B46_A_ELF" "$B46_B_ELF"
~~~

Require exact original accepted hashes listed above. Generate an external no-overwrite plan; do not pre-authorize JTAG.

~~~bash
export B46_STUDY_PLAN="$HOME/Thesis_Evidence/p08_b46_six_NEW_ABBAAB_study_plan_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$B46_STUDY_PLAN" || { echo "STOP: existing plan"; exit 1; }

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
  scripts/p08_b46_4b_six_session_plan.py \
  --boundary "$B46_BOUNDARY" \
  --matched-source "$B46_MATCHED_SOURCE" \
  --a-prior "$B46_A_PRIOR" \
  --b-prior "$B46_B_PRIOR" \
  --a-elf "$B46_A_ELF" \
  --b-elf "$B46_B_ELF" \
  --out "$B46_STUDY_PLAN"

test -s "$B46_STUDY_PLAN" || { echo "STOP: preregistration did not create a valid study plan"; exit 1; }
export B46_STUDY_PLAN_SHA="$(sha256sum "$B46_STUDY_PLAN" | awk '{print $1}')"
printf 'B46_STUDY_PLAN=%s\nB46_STUDY_PLAN_SHA=%s\n' \
 "$B46_STUDY_PLAN" "$B46_STUDY_PLAN_SHA"
python3 -m json.tool "$B46_STUDY_PLAN"
~~~

Expected:

~~~text
P08_B46_SIX_SESSION_PRE_REGISTERED_SOURCE_EVIDENCE_PASS=1
P08_B46_STANDALONE_PREVIOUS_PHYSICAL_RUNS_COUNTED_AS_NEW=0
P08_B46_FIRST_SCHEDULED_ARM=A_REBUILT_A2_1
P08_B46_SIX_NEW_SESSION_JTAG_AUTHORIZED=0
P08_B46_NEW_AB_BA_AB_PHYSICAL_SESSIONS_PERFORMED=0
~~~

**STOP if any of these steps fail.** No fake SHA overwrites, no report edits, no old accepted directory reused. Return the plan SHA and test summary as the first operator preflight evidence. The plan does NOT itself admit actual hardware execution.

## 2. Session 01 = A rebuilt A2.1 (first NEW physical boot) — PC offline preflight

The previous single accepted A rebuilt session remains untouched. This test must use **new** `p08_b46_s01_A_<UTC>` output, not the October original A firmware or the previous November A physical run.

~~~bash
export P08_B46_REBUILT_A21_BUILD="$HOME/Thesis_Evidence/p08_a2_1_rebuild_20261106T023403Z"
export P08_B46_A_STAGE_DIR="$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z"
export P03_DIAG_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P08_B46_SIGNED_SOURCE_REPORT="$B46_MATCHED_SOURCE"

# SELECT the ORIGINAL genuine A21 source-admission JSON on this PC;
# the filename is operator-specific and must NOT be guessed.
find "$HOME/Thesis_Evidence" -maxdepth 1 -type f \
 -name 'p08_b46_a21_rebuilt_source_admission_*.json' -print

# Set to ONE EXACT file returned by find (edit only this assignment):
export P08_B46_SIGNED_A_ADMISSION="$HOME/Thesis_Evidence/<EXACT_GENUINE_A21_ADMISSION>.json"
test -s "$P08_B46_SIGNED_A_ADMISSION" || {
  echo "STOP: original rebuilt A21 independent source admission missing"
  exit 1
}

export P08_B46_REBUILT_A21_RUN_DIR="$HOME/Thesis_Evidence/p08_b46_s01_A_$(date -u +%Y%m%dT%H%M%SZ)"
export B46_SLOT1_A_PREFLIGHT="$HOME/Thesis_Evidence/p08_b46_s01_A_pc_preflight_$(date -u +%Y%m%dT%H%M%SZ).log"

test ! -e "$P08_B46_REBUILT_A21_RUN_DIR" || { echo "STOP: used JTAG run path"; exit 1; }
test ! -e "$B46_SLOT1_A_PREFLIGHT" || { echo "STOP: used preflight log"; exit 1; }

export P08_B46_PREFLIGHT_ONLY=YES
set -o pipefail
bash scripts/run_p08_b46_rebuilt_a21_1024.sh \
  2>&1 | tee "$B46_SLOT1_A_PREFLIGHT"
sha256sum "$B46_SLOT1_A_PREFLIGHT"
~~~

Expect:
`P08_B46_SIGNED_REBUILT_A21_ELF_AND_ORIGINAL_1024_SOURCE_PREFLIGHT_PASS=1`,
`P08_B46_REBUILT_A21_ORIGINAL_1024_OFFLINE_PREFLIGHT_PASS=1`,
`P08_B46_PREFLIGHT_AUTHORIZES_PHYSICAL_JTAG=0`.
**No Vivado, XSDB, DDR access or evidence run directory is created in preflight.**

## 3. Session 01 actual hardware risk review and separately approved execution

**DO NOT EXECUTE merely because offline tests pass.** The person operating the KV260 must separately review and explicitly consent to this one particular destructive session. The script will overwrite the reserved DDR **[0x40000000,0x44000000)** (64MiB) and program original P03 PL logic, stop A53/Linux, and replace bare-metal code. FSBL/Linux/RPU/PL/DMA exclusive DDR ownership remains **UNPROVEN**; the selected B unprotected integrity tradeoff does NOT prove it safe. Power-cycle after any JTAG attempt, PASS or FAIL, and NEVER resume halted Linux.

Before authorization: physically power-cycle the board since the previously recorded A2.1 JTAG operation; choose a dedicated disposable JTAG-owned Linux boot with no active application or DMA, no other XSDB or Vivado debugging client, and clear recovery plan. Through PuTTY, at most short inspection `sudo xmutil listapps`, conditional `sudo xmutil unloadapp` for a known loaded app. Closing a Linux app is not proof of DDR ownership.

On PC, source AMD Vivado/Vitis 2025.2, verify one existing `hw_server` or start one in a **different dedicated terminal only if none is running**; never run competing hardware debuggers.

~~~bash
source "$HOME/Vivado/2025.2/Vitis/settings64.sh"
command -v xsdb
command -v vivado
command -v hw_server
pgrep -af 'hw_server|xsdb|vivado' || true
~~~

**Only after individually approving EACH of these six risks for Session 01**, execute below. Do **not** put the block into an automated six-session loop. The human must enter authorizations on their own PC.

~~~bash
unset P08_B46_PREFLIGHT_ONLY
export P08_B46_CONFIRM_DISPOSABLE_LINUX_JTAG_ONLY=YES
export P08_B46_CONFIRM_OVERWRITE_ORIGINAL_64M_DDR=YES
export P08_B46_CONFIRM_ORIGINAL_TRAIN_ONLY=YES
export P08_B46_CONFIRM_UNPROVEN_BOOT_DDR_DMA_RISK=YES
export P08_B46_CONFIRM_PWR_CYCLE_AFTER_ANY_ATTEMPT=YES
export P08_B46_CONFIRM_NEW_CANDIDATE_ELF=YES

set -o pipefail
bash scripts/run_p08_b46_rebuilt_a21_1024.sh
~~~

If any real JTAG attempt begins, physically **POWER-CYCLE the KV260** afterward even if the command fails. Preserve failure capture and diagnostics untouched; DO NOT immediately run B or retry A. Expected original A per-image terminal alone is NOT enough; the original A physical runner's own independent 1024 neural/26×42 trace/A53 proof must PASS. Capture the exact `script_exit_status=0`, independent marker `P08_B46_REBUILT_A21_INDEPENDENT_ORIGINAL_ALL1024_PACKED_NEURAL_AND_TIMING_PASS=1`, and final run marker `P08_B46_NEW_REBUILT_A21_ORIGINAL_1024_PHYSICAL_AND_INDEPENDENT_PASS=1`.

## 4. PC-only rereview of the NEW Session 01 capture (after mandatory board power-cycle)

~~~bash
export B46_SLOT1_A_REVIEW="$HOME/Thesis_Evidence/p08_b46_s01_A_rereview_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$B46_SLOT1_A_REVIEW" || { echo "STOP: existing independent report"; exit 1; }

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b46_a21_rebuilt_independent_physical_verify.py \
 --build "$P08_B46_REBUILT_A21_BUILD" \
 --xsa "$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa" \
 --source-report "$P08_B46_SIGNED_SOURCE_REPORT" \
 --candidate-report "$P08_B46_SIGNED_A_ADMISSION" \
 --stage "$P08_B46_A_STAGE_DIR" \
 --evidence "$P08_B46_REBUILT_A21_RUN_DIR" \
 --out "$B46_SLOT1_A_REVIEW"

sha256sum "$B46_SLOT1_A_REVIEW"
~~~

Expected `P08_B46_REBUILT_A21_INDEPENDENT_ORIGINAL_ALL1024_PACKED_NEURAL_AND_TIMING_PASS=1`. This rereview is **same physical run**, not a second boot. The run must be physically distinct from previous standalone A and from all future B4.6 sessions.

Only after confirming a **physical cold boot BEFORE this session** and **actual post-JTAG board power-cycle AFTER this session** (operator attestations, not independent instrument recordings), record the first new hash-linked session:

~~~bash
export B46_SLOT1_A_LEDGER="$HOME/Thesis_Evidence/p08_b46_s01_A_accepted_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$B46_SLOT1_A_LEDGER" || { echo "STOP: previous ledger exists"; exit 1; }

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b46_4b_session_receipt.py \
 --plan "$B46_STUDY_PLAN" \
 --plan-sha256 "$B46_STUDY_PLAN_SHA" \
 --slot 1 \
 --evidence "$P08_B46_REBUILT_A21_RUN_DIR" \
 --independent "$B46_SLOT1_A_REVIEW" \
 --preflight "$B46_SLOT1_A_PREFLIGHT" \
 --operator-new-coldboot OPERATOR_CONFIRMED_NEW_INDEPENDENT_COLD_BOOT \
 --operator-after-jtag-power-cycle OPERATOR_CONFIRMED_POWER_CYCLE_AFTER_ANY_JTAG \
 --out "$B46_SLOT1_A_LEDGER"

sha256sum "$B46_SLOT1_A_LEDGER"
~~~

Expected: `P08_B46_NEW_ABBAAB_SESSION_ORIGINAL_NEURAL_AND_A53_RECEIPT_PASS=1`, `P08_B46_CURRENT_NEW_SESSION_ACCEPTED_SLOT=1`, `P08_B46_ABBAAB_NEW_HARDWARE_SESSION_COUNT=1`, `P08_B46_SIX_RUN_STUDY_STATISTICS_ACCEPTED=0`. If the actual before/after power-cycles did **not** happen, DO NOT attest YES, and do not use this record to proceed. A successful source preflight, physical run, rereview and ledger together still provide only ONE of six new independent physical sessions.

**STOP HERE for operator review and exchange the local tests, six-session plan SHA, first A physical source/independent report SHA, first ledger SHA, and reboot confirmation before the second physical run.**

## 5. NEXT session 02 = B_AUTH_ONCE V2, then repeated B/A/A/B

The next order is **02:B, 03:B, 04:A, 05:A, 06:B**. Every slot must use a brand NEW physical boot and unique `p08_b46_sNN_<arm>_<UTC>` evidence directory, full PC source preflight before real board access, explicit risk approvals for THAT session, independent full1024 oracle/FNV/timer/backup rereview, mandatory power-cycle, and an incremental ledger referencing the previous accepted ledger; never concatenate different run scripts or silently reuse a B4.5 prior physical capture.

The actual original B V2 full1024 hardware command with all original source exports and ten individual operator confirmations is preserved in [B-auth-once 1024 runbook, sections B/D/E/F](P08_B45_UNPROTECTED_FULL1024_PHYSICAL_WITH_LIVE_MONITOR_RUNBOOK.md). Use ONLY `--experiment once`, `--mode preflight` first, and **only after new explicit individual authorization** `--mode execute` with a fresh `--evidence "$HOME/Thesis_Evidence/p08_b46_s02_B_<UTC>"`. Use exact existing V2 build root `$HOME/Thesis_Evidence/p08_b45_perf_once_full1024_V2_20261105T192804Z`; original V2 sha `a19b50...`, no rebuild, no unchecked. B independent verifier must pass original 1024 FNV, timing and all27 backup endpoint equality. B4.5 full1024 original real runs are not any of the six study slots.

To link second B receipt after its *own* independently successful physical capture, power-cycle and PC rereview:

~~~bash
export B46_SLOT2_B_LEDGER="$HOME/Thesis_Evidence/p08_b46_s02_B_accepted_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b46_4b_session_receipt.py \
 --plan "$B46_STUDY_PLAN" --plan-sha256 "$B46_STUDY_PLAN_SHA" \
 --slot 2 --previous-ledger "$B46_SLOT1_A_LEDGER" \
 --evidence "$P08_B45_FULL_ONCE_PHYSICAL" \
 --independent "$P08_B45_FULL_ONCE_INDEPENDENT" \
 --preflight "$B46_SLOT2_B_PREFLIGHT" \
 --operator-new-coldboot OPERATOR_CONFIRMED_NEW_INDEPENDENT_COLD_BOOT \
 --operator-after-jtag-power-cycle OPERATOR_CONFIRMED_POWER_CYCLE_AFTER_ANY_JTAG \
 --out "$B46_SLOT2_B_LEDGER"
sha256sum "$B46_SLOT2_B_LEDGER"
~~~

The receipt program checks the B JTAG capture (original neural/timer/reset and six-source receipt), selected once ELF, 1023 ordinary service median, previous exact A slot ledger, nonreuse of past captures, and the operator recovery attestations. It is PC-only: it cannot itself prove electrical reboot, guard DDR from boot/DMA activity, or establish statistical significance.

After SIX separately accepted slots, run a **separate** descriptive N=3 paired analysis submilestone; individual 1023 image records are not 1023 independent coldboots. Never claim power, energy, matched-complexity or secure XMPU. Existing historical evidence, all new failed runs, raw capture originals, original TEST seal and Git PR stack remain immutable and unmerged.
