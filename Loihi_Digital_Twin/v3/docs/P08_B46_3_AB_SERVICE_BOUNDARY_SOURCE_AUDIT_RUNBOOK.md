# P08-B4.6.3 — ORIGINAL Track A / B_AUTH_ONCE service boundary source audit (PC ONLY)

**Status: code and native test candidate for operator verification. No new KV260/JTAG/DDR/Vitis work authorized. Do not merge draft branches.** This is a static audit of *original Git-pinned C firmware and launchers*. It does **not** establish timer interchangeability from new real A/B measurements, admit the missing A2.1 ELF, or authorize six repetitions.

## Source-of-truth and selected arms

Read the [current 2026-11-05 B4.6 handoff](P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md), [B4.6 selected source gate](P08_B46_SELECTED_AUTH_ONCE_PC_SOURCE_GATE_RUNBOOK.md) and [roadmap](../LOIHI_TWIN_ROADMAP.md) before any later physical planning.

- **A**: frozen genuine P08-A2.1 image-timing Track A, 42 neurons / 26 dispatches; accepted ELF SHA256 \`fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0\`. **Historical original ELF currently MISSING**, previously held only under \`/tmp\`; synthetic pytest ELF and A2.2 **are not substitutes**.
- **B**: frozen original P08-B4.5 **V2 authenticate-once / UNPROTECTED** 1010 neurons / 27 virtual cores / 702 dispatches; accepted ELF SHA256 \`a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85\`. **Not** old B4.4 per-image-SHA original nor unchecked; original 1024-frame independent physical report SHA \`06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a\`.

## A/B actual source boundary crosswalk

| Scope | A2.1 original C | B_AUTH_ONCE V2 original C | Interpretation |
| --- | --- | --- | --- |
| Observed A53 clock | \`p08_clock_rate()\` / \`read_ticks()\` read \`CNTFRQ_EL0/CNTVCT_EL0\` | \`observed_frequency()/observed_counter()\` read same A53 registers; six-phase \`p08_b2_meter\` | Convert each session using its **actual** reported CNTFRQ; no PL clock inference. |
| Service entry | \`t.service_start=read_ticks(NULL)\` at start of \`execute_image\`, before \`load_image_record(frame)\` | \`now=observed_counter()\`; \`p08_b2_meter_start\` before \`p08_b45_perf_reset_image\` | Both start before per-image ingress/reset work; exact instructions and prior state differ. |
| First part | Validate pre-staged encoded image and frozen A deployment; \`p07_a2_run_frame\` performs A single-core preparation and per-frame master copy | Copy/clean/invalidate **27** contexts from frozen backup; encode 784B raw pixels to B1.3 ingress, then rebuild virtual scheduler | **Not identical reset or ingress workloads.** Do not call these matched phases. |
| Neural + commit | 26 A dispatches; \`commit_frame_result\` writes/flushed compact original journal; selected trace flush before end | 26 B ticks and 702 dispatches incl. A53/PL paging/routing; receipt validation; \`commit_journal\` writes/flushed B journal | Same broad neural-to-journal-commit endpoint type, DIFFERENT operations, output sizes and architecture. |
| Service end | \`t.after_commit=read_ticks(NULL)\` after journal flush; then write A timing record and progress header **outside** interval | mark \`P08_B2_AFTER_JOURNAL_COMMIT\`; \`p08_b2_meter_finish\` uses counter[6]−counter[0]; then B timing record, reset profile and progress mailbox **outside** interval | Original timestamp is after commit in both; instrumentation/counter capture and between-image work differ. |
| Session-only work | A dataset/master SHA validation, startup and initial outputs precede repeated image path | V2 \`p08_b45_perf_reset_bind\` authenticates once **before** image loop (not in each 1023 ordinary frame) | Do not add B bind time to per-image service or hide a claim of equal security. |
| Outlier | Selected original trace ordinal **1023** | Selected original trace ordinal **1023** | Validate all 1024 frames numerically; compare **1023 ordinary** timer rows only. |

**Finding:** frozen source provides a *comparable broad A53 per-image service concept*, entry-before-work through committed neural journal, but **not evidence of byte-for-byte identical boundaries or matched service work**. The original B reset subphase excludes one-time source authentication, A reset/ingress differs, and the two launchers have distinct startup and sidecar overhead. An A/B numerical rate would describe **different systems and different workloads**, not a neural PL kernel speedup. Exact cross-arm boundary equivalence remains **UNPROVEN** pending a separate reviewed physical study design. Do **not** modify accepted A2.1/B V2 firmware merely to force matching: a new timer probe requires new immutable arm and independent admissions.

## Launcher and memory ownership NO-GO

Historical A launcher \`scripts/run_p08_a3_2_1024.sh\` uses A2.1 variant, preflight vs destructive paths, a 64MiB \`0x40000000..0x43FFFFFF\` reserved DDR staging/overwrite envelope, P07 provisioning, A sidecar and XSDB/P03 programming order. B runner \`scripts/p08_b45_perf_full1024_physical_run.py\` separately performs explicit A53 takeover/PS128 gate, P03 programming, six signed DDR transfers with 27 original 512KiB backup contexts, reset/timer/neural journals, B-side postrun readback and independent verification. A's earlier preparation/PS width sequence is not identical to B's **halt-before-programming** workflow. **Neither historical launcher is automatically approved for a new combined AB/BA/AB orchestration.**

Required before any later physical design admission: identify and independently verify all original DDR addresses, JTAG host ownership and Linux/A53 halt ordering for BOTH arms; confirm backups and sidecars cannot collide across sessions, define cold-boot/reboot/recovery and append-only failed attempts, and accept remaining unproven firmware/DMA DDR ownership risks **separately**. Every physical run needs fresh explicit user authorization and its own source/ELF/bitstream/OS state receipt. The user's unprotected performance research choice does not constitute hardware memory protection or ownership proof. Existing real 16/1024 B4.5 runs should **not** be repeated for this audit.

## PC-only operator native verification (VS Code terminal)

All commands are **host-only**, no Vivado/Vitis requirement and no JTAG calls. Preserve existing evidence, and keep the current draft stack unmerged.

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b46-ab-service-boundary-audit
git pull --ff-only origin agent/v3-p08-b46-ab-service-boundary-audit
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b46_ab_service_boundary_audit.py \
  tests/test_p08_b46_auth_once_source_gate.py \
  tests/test_p08_b45_full1024_latency_synthesis.py \
  tests/test_p08_b45_perf_full1024_independent_cli.py
python3 -m py_compile scripts/p08_b46_ab_service_boundary_audit.py
bash -n scripts/run_p08_a3_2_1024.sh
~~~

Write a **fresh and durable source audit JSON outside Git**, never under \`/tmp\` or \`/var/tmp\`. This step does not require the missing A2.1 ELF: its physical source gate remains BLOCKED.

~~~bash
mkdir -p "$HOME/Thesis_Evidence"
export B46_AB_BOUNDARY_REPORT="$HOME/Thesis_Evidence/p08_b46_ab_boundary_source_audit_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$B46_AB_BOUNDARY_REPORT" || { echo "NO-GO: existing output"; exit 1; }
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
  scripts/p08_b46_ab_service_boundary_audit.py \
  --v3-root "$PWD" --out "$B46_AB_BOUNDARY_REPORT"
python3 -m json.tool "$B46_AB_BOUNDARY_REPORT"
sha256sum "$B46_AB_BOUNDARY_REPORT"
~~~

Expected flags (assuming the original source snapshot has not drifted):

~~~text
P08_B46_AB_FROZEN_SERVICE_BOUNDARY_SOURCE_AUDIT_PASS=1
P08_B46_AB_PHYSICAL_BOUNDARY_EQUIVALENCE_PROVEN=0
P08_B46_AB_A21_ELF_SOURCE_ADMITTED=0
P08_B46_AB_NEW_HARDWARE_AUTHORIZED=0
~~~

Return the native test summary, exact audit JSON path and SHA256, and any static NO-GO output. This is **not** permission to run the historical shell runner or B Python runner in \`execute\` mode.

## Separate A2.1 source blocker (not solved here)

Read-only inspect the saved historical A3.1 TAR *without* extracting into accepted evidence:

~~~bash
tar -tzf "$HOME/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z.tar.gz" \
  | grep -Ei 'p08_a2_board[.]elf|p08_a2_2_board[.]elf|build_identity|[.]elf$' || true
find "$HOME/Thesis_Evidence" -type f -name 'p08_a2_board.elf' -print
~~~

A3.1 is documented to have used **A2.2**, not A2.1. If the exact genuine A2.1 SHA cannot be found, an original-source Vitis 2025.2 rebuild must use an entirely NEW durable build directory and must be labeled *reconstructed candidate* if its SHA changes. It cannot pass the original A2.1 SHA gate by relabeling or swapping the accepted pin. Do not ask for any board run until a separate fresh numerical/source/hardware admission plan is reviewed. See the [selected B4.6 source gate runbook](P08_B46_SELECTED_AUTH_ONCE_PC_SOURCE_GATE_RUNBOOK.md) for the original SHA and recovery procedure.

**Next gate:** after offline operator PASS and review, design a new source-gated per-session numerical/admission/recovery adapter and independent analysis receipts; no six-session A/B physical run or PR merge is approved yet. Official MNIST TEST remains sealed.
