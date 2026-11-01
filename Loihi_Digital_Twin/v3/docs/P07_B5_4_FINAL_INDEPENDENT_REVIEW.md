# P07-B.5.4 — Final original trained 27-core FPGA evidence and operator closeout

**Status (2026-11-01): P07-B.5.4 FORMALLY ACCEPTED; ALL B5 NUMERICAL/PHYSICAL
GATES PASSED AND OPERATOR COLD-REBOOT/JTAG ATTESTATION ACCEPTED.
P07-B.5 CLOSED WITH BOUNDED CLAIMS; P07-B.6 AND OVERALL P07-B REMAIN OPEN.**
No `main` merge. PR #49 and #50 stay draft. P07-B.6/P08-B gated.

## 2026-11-01: B5.4 FORMALLY ACCEPTED — five genuine physical sessions + operator cold-reboot attestation

The operator executed **`scripts/p07_b5_final_acceptance.py --mode accept`**
against the original four 0/1/2/0 V3 sessions, the fifth B5 RAW0
physical evidence directory, the unchanged frozen TRAIN sources and the
external operator five-session cold power-cycle/JTAG/recovery/risk attestation.
Real terminal markers:

```text
P07_B5_4_FIVE_PHYSICAL_SESSIONS_ORIGINAL_SIGNED_NUMERICAL_GATE_PASS=1
P07_B5_4_840320B_REAL_RAW_NEURON_PARITY_PASS=1
P07_B5_4_BOARD_CONTACT_THIS_AUDIT=0
P07_B5_4_OFFICIAL_MNIST_TEST_SEALED=1
P07_B5_4_FINAL_OPERATOR_ACCEPTANCE=1
```

**Final accepted report:**
`/home/dna/Thesis_Evidence/p07_b5_4_accepted_20261101T224134Z.json`;
**operator-attestation SHA256:**
`4dd6cf0d02c477a2992b55b8bc2454ee9800c94ccce78f6cee25a32f2dc7fa31`.

Actual accepted report contains
`P07_B5_final_acceptance=true`,
`operator_attested_cold_boot_and_recovery_all_five_sessions=true`,
`operator_explicit_final_B5_acceptance=true`,
`all_required_B5_numerical_gates_pass=true` and
`original_P03_PL_and_accepted_original_V3_ELF_modified=false`.
Physical and independent scalar 840320B neuron trace SHA256 remain
`7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`.
Original official TEST is SEALED. This **formally closes P07-B.5
within the previously defined numerical/physical validation scope**.

**Preserved explicit limits:** DDR/boot ownership exclusive use NOT
independently proven; cold reboots operator-attested, NOT independently
instrumented; packet routing **counts** checked, not every individual
packet-word trace. Acceptance does not establish wider Loihi architectural
feature coverage, official TEST accuracy, P07-B.6 final freeze/handoff
or full P07-B completion. [Final operator-attested B5.4 bounded acceptance
ledger](P07_B5_4_2026_11_01_FINAL_OPERATOR_ATTESTED_ACCEPTANCE.json).
Neither `main` nor the independent `main:LitReview.md` is modified;
draft PR #49/#50 must remain unmerged until P07-B.6 and whole P07-B
are separately accepted.

## 2026-11-01: Genuine operator B5.4 five-session review PASS (NUMERICAL ONLY)

The operator ran the real
`scripts/p07_b5_final_acceptance.py --mode review` against all five
original source-backed physical evidence directories. The resulting
**write-once operator PC report** is:

`/home/dna/Thesis_Evidence/p07_b5_4_final_numerical_review_20261101T220745Z.json`

The reported terminal markers were:

```text
P07_B5_4_FIVE_PHYSICAL_SESSIONS_ORIGINAL_SIGNED_NUMERICAL_GATE_PASS=1
P07_B5_4_840320B_REAL_RAW_NEURON_PARITY_PASS=1
P07_B5_4_BOARD_CONTACT_THIS_AUDIT=0
P07_B5_4_OFFICIAL_MNIST_TEST_SEALED=1
P07_B5_4_FINAL_OPERATOR_ACCEPTANCE=0
```

The report independently confirmed 4 V3 0/1/2/0 sessions with complete
26-tick scalar fingerprint and counter equality, a fifth original B5 RAW0
physical session with all **26,260 neuron words**, **840,320 bytes**
byte-for-byte identical to frozen scalar, and exact physical SHA256
`7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`.
The earlier accepted original original-TRAIN0 repeat still matched, the
original frozen P03 PL/V3 ELF remained unchanged and official TEST SEALED.

The write-once report's self-contained SHA pin fields were:
original four-run report SHA256
`f1dc383f4f4e316fca4cb5c6175e129347dfeb3fa4f9982de2c4ada412cc1ada`;
genuine raw0 verification report SHA256
`0c37aee136c218216eb01926b8a50ad67fb81833d4aa2c6feb096be6aa68106c`.
[Bounded B5.4 five-physical-session numerical review ledger](P07_B5_4_2026_11_01_FIVE_SESSION_NUMERICAL_REVIEW_PASS_NOT_FINAL_ACCEPTANCE.json).

**Final approval is NOT established by this report.** It explicitly says
`P07_B5_final_acceptance=false`,
`operator_attested_cold_boot_and_recovery_all_five_sessions=false`,
`operator_explicit_final_B5_acceptance=false`,
`boot_firmware_and_other_DDR_owner_independently_proven=false`,
`independent_board_powercycle_instrumentation_proof=false`,
`P07_B6_started=false`, and `main_merged=false`.
No independent physical cycle record or actual operator-per-session
attestation has been received. User's conditional request to close B5
and merge is **not** a substitute for inventing those attestations.
No tests or hardware runs need to be repeated solely to document the
remaining facts.

**Main branch safety:** GitHub confirms a main-only commit adds
`LitReview.md`, blob SHA
`3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`.
The P07-B development line does not include that commit. Do **not**
force-push, reset, overwrite `main`, or use a snapshot replacement.
When full P07-B and the operator's requested signoff are satisfied,
integrate the draft PRs in dependency order **#49 → #50** using normal
Git merges; verify `LitReview.md` remains byte-identical on the resulting
`main`. No direct main edit or merge was performed at this checkpoint.

## Genuine physical B5.3 result

The operator supplied the **complete independently audited B5.3 RAW0
physical verification JSON** produced by
`scripts/p07_b5_raw_physical_verify.py`.
Actual source evidence resides on the operator PC:

`/home/dna/Thesis_Evidence/p07_b5_raw_train0_real_20261101T213638Z`

- Signed original TRAIN ordinal 0; canonical TRAIN index **37384**;
  classified **1**, 25 readout spikes to class 1.
- Original 27 physically staged contexts/routes/TRAIN0 bytewise readbacks:
  `same_session_original_27core_and_route_stage_verified=true`.
- **702 HLS dispatches**, **26 global barriers**, 702 page-ins,
  699 dirty + 3 final page-outs.
- Full original physical HLS debug-bank7 trace:
  **26 × 1,010 × 32 bytes = 840,320 bytes / 26,260 neuron records**.
- Independently regenerated scalar original signed B2.4 reference
  and genuine physical PSU readback both SHA256
  `7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`.
- Exact 26-tick FNV64 `0xB59CA8594D6E64AD` and all 26 independently
  checked tick FNV64 values.
- All seven independent original neural/input/spike/packet COUNT/readout
  numerical checks `true`.
- Original B5-specific 256B genuine physical terminal mailbox SHA256
  `435b1c903f3323b3bfd156eb271202d82c8738ebe2a7a8c489e6aab7fcdd4d6b`.
- Distinct genuine new B5 ELF SHA256
  `0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf`;
  GNU map SHA256
  `1e6cf5d0a9744378fb0aebe2e6271da661b8739a2fb930e983342477fd0e78c8`.
- `raw_neuron_original_26x1010_bytes_exactly_equal=true`,
  `original_signed_model_modified=false`,
  `original_V3_ELF_modified=false`,
  `original_official_MNIST_TEST=SEALED_NOT_ACCESSED`.

[Source-controlled bounded physical raw parity ledger](P07_B5_3_2026_11_01_REAL_ORIGINAL_TRAIN0_840320B_PHYSICAL_RAW_NEURON_PASS.json)
quotes operator-provided evidence; the assistant has NOT physically
read the operator's source binaries or contacted the board.

**Important scope:** The embedded reused older structural mailbox
field `independent_full_neuron_numerical_parity=false` does not
invalidate B5.3's stronger independently checked
`raw_neuron_original_26x1010_bytes_exactly_equal=true`. One proves
*structural mailbox* metadata; the other proves actual raw physical
neuron content equality to independent integer scalar oracle.
This is **not** full per-packet-byte route trace parity; original
P03/NEXT packet COUNTS were checked exactly.

## Historical B5.2 physical runs (independently verified in operator logs)

Four signed original V3 sessions, original TRAIN ordinals 0/1/2/0,
all 702 dispatches and 26 barriers, full scalar FNV and count parity:

1. `/home/dna/Thesis_Evidence/p07_b4m_diag_v3_real_20261101T041302Z`
2. `/home/dna/Thesis_Evidence/p07_b5_train1_real_20261101T045754Z`
3. `/home/dna/Thesis_Evidence/p07_b5_train2_real_20261101T192124Z`
4. `/home/dna/Thesis_Evidence/p07_b5_train0_reboot_repeat_real_20261101T193922Z`

Four-run report:
`/home/dna/Thesis_Evidence/p07_b5_fourrun_original_train_20261101T194900Z.json`.
Original TRAIN0 repeat fully reproduced original 256B physical mailbox
SHA256 `5a2d9c9645b79144ef20f5ed7f26e5ed1ad3745aaf929713cf89fcb7f8718eda`.
The report itself explicitly retained
`cold_reboot_between_runs_independently_proven=false`.

## New B5.4 independent PC-only numerical closeout

`scripts/p07_b5_final_acceptance.py --mode review` reopens and
**re-verifies directly from physical source files**, not merely
compares the two previously saved JSON summaries:

1. All **four** accepted original V3 full signed 27-core
   DDR/route/TRAIN physical staging and 256B terminal mailboxes,
   independently regenerated original scalar counters/FNV and
   exact TRAIN0 repeat equality. Requires 0/1/2/0 ordered
   *distinct* physical directories.
2. The distinct **fifth B5 RAW0 physical session**, with its exact
   signed new ELF/map, accepted original source and same-session
   physical readbacks, terminal B5 256B mailbox, 840,320 physical
   raw neuron bytes, all 26 tick fingerprints and bytewise original
   integer scalar trace comparison.
3. Both existing user-produced report JSONs must match
   freshly recomputed independent result structures exactly.
4. The output explicitly retains `P07_B5_final_acceptance=false`,
   `operator_attested_cold_boot_and_recovery_all_five_sessions=false`,
   `boot_firmware_and_other_DDR_owner_independently_proven=false`,
   `P07_B6_started=false` and `main_merged=false`.

**PC-only native tests**:
`tests/test_p07_b5_final_acceptance.py` prove that malformed,
reused, omitted or out-of-order session evidence, fake raw SHA,
changed historic reports, missing operator statement, omitted
actual per-session cold power cycles/recovery or a wrong explicit
acceptance token are *NO-GO*. Synthetic mock tests do not
represent physical evidence.

### Operator PC command — NEW final numerical review, no board contact

```bash
cd ~/Git/Thesis
git switch agent/v3-p07-b5-scaled-multiframe-validation
git pull --ff-only origin agent/v3-p07-b5-scaled-multiframe-validation
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
    tests/test_p07_b5_scaled_validation.py \
    tests/test_p07_b5_raw_physical_safety.py \
    tests/test_p07_b5_final_acceptance.py

export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4L1_STAGE="$HOME/Thesis_Evidence/p07_b4l1_original27_20261022T204013Z"
export P07_B4M_STAGE="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P07_B5_RAW_BUILD_DIR="$HOME/p07_b5_raw_trace_build_20261101T204014Z"
export P07_B5_RAW_OFFLINE="$HOME/Thesis_Evidence/p07_b5_raw_elf_offline_20261101T204303Z.json"

export P07_B5_RUN0="$HOME/Thesis_Evidence/p07_b4m_diag_v3_real_20261101T041302Z"
export P07_B5_RUN1="$HOME/Thesis_Evidence/p07_b5_train1_real_20261101T045754Z"
export P07_B5_RUN2="$HOME/Thesis_Evidence/p07_b5_train2_real_20261101T192124Z"
export P07_B5_RUN0_REPEAT="$HOME/Thesis_Evidence/p07_b5_train0_reboot_repeat_real_20261101T193922Z"
export P07_B5_RAW_RUN0="$HOME/Thesis_Evidence/p07_b5_raw_train0_real_20261101T213638Z"

export P07_B5_FOURRUN_REPORT="$HOME/Thesis_Evidence/p07_b5_fourrun_original_train_20261101T194900Z.json"
# Restore this to the ACTUAL previously generated raw verify JSON shown
# with cat "$P07_B5_RAW_VERIFY0" in the earlier operator session.
# If the shell variable was cleared, locate it using:
find "$HOME/Thesis_Evidence" -maxdepth 1 -name 'p07_b5_raw_verify_train0_*.json' -type f -print
: "${P07_B5_RAW_VERIFY0:?Set to your EXISTING B5 raw verify report; do not synthesize it}"

export P07_B5_4_REVIEW="$HOME/Thesis_Evidence/p07_b5_4_final_numerical_review_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P07_B5_4_REVIEW"
PYTHONPATH="$PWD/src" python scripts/p07_b5_final_acceptance.py \
  --mode review \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --routes-dir "$P07_B4M_STAGE" \
  --build-dir "$P07_B5_RAW_BUILD_DIR" \
  --reports "$P07_B4L_REPORTS" \
  --offline-report "$P07_B5_RAW_OFFLINE" \
  --fourrun-report "$P07_B5_FOURRUN_REPORT" \
  --run "0:$P07_B5_RUN0" \
  --run "1:$P07_B5_RUN1" \
  --run "2:$P07_B5_RUN2" \
  --run "0:$P07_B5_RUN0_REPEAT" \
  --raw-evidence "$P07_B5_RAW_RUN0" \
  --raw-report "$P07_B5_RAW_VERIFY0" \
  --out "$P07_B5_4_REVIEW"
cat "$P07_B5_4_REVIEW"
```

Expected review markers:
`P07_B5_4_FIVE_PHYSICAL_SESSIONS_ORIGINAL_SIGNED_NUMERICAL_GATE_PASS=1`,
`P07_B5_4_840320B_REAL_RAW_NEURON_PARITY_PASS=1`,
`P07_B5_4_FINAL_OPERATOR_ACCEPTANCE=0`,
`P07_B5_4_BOARD_CONTACT_THIS_AUDIT=0`.

## 2026-11-01 operator attestation prepared — PC acceptance result still required

After receiving the independently passing five-session numerical review,
the operator reported: **"I also created the template copy and set every
null value to true"** and explicitly requested completion of B5 and the
start of B6, while reconfirming that no P07 source should merge to `main`
until the whole P07 track is finished.

This is an **operator statement that the local external attestation JSON
was filled out**; it is not the actual signed JSON artifact, a physical
cold-reboot instrumentation record, or an executed
`p07_b5_final_acceptance.py --mode accept` PASS. The acceptance script
must itself open the exact local file, validate all five physical session
paths and every boolean, recheck all original source-backed evidence,
and emit a new **write-once accepted** JSON before the automation
may mark B5.4 formally closed. Do not infer the path or report SHA.

**Operator PC-only B5.4 final acceptance command** — after verifying
all five `true` fields are truthful and the original external attestation
file is still present:

```bash
# Run in Loihi_Digital_Twin/v3 after sourcing .venv-p08 and setting
# variables in the preceding "Operator PC command" block.
find "$HOME/Thesis_Evidence" -maxdepth 1 -type f \
  -name 'p07_b5_4_operator_attestation_*.json' -print
# Select the EXACT operator-created file displayed by find:
export P07_B5_ATTEST="/home/dna/Thesis_Evidence/<ACTUAL_ATTESTATION_FILENAME>.json"
test -s "$P07_B5_ATTEST" || { echo "Missing operator attestation" >&2; exit 1; }
export P07_B5_4_ACCEPT="$HOME/Thesis_Evidence/p07_b5_4_final_accepted_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P07_B5_4_ACCEPT" || { echo "Destination already exists" >&2; exit 1; }

PYTHONPATH="$PWD/src" python scripts/p07_b5_final_acceptance.py \
  --mode accept \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --routes-dir "$P07_B4M_STAGE" \
  --build-dir "$P07_B5_RAW_BUILD_DIR" \
  --reports "$P07_B4L_REPORTS" \
  --offline-report "$P07_B5_RAW_OFFLINE" \
  --fourrun-report "$P07_B5_FOURRUN_REPORT" \
  --run "0:$P07_B5_RUN0" \
  --run "1:$P07_B5_RUN1" \
  --run "2:$P07_B5_RUN2" \
  --run "0:$P07_B5_RUN0_REPEAT" \
  --raw-evidence "$P07_B5_RAW_RUN0" \
  --raw-report "$P07_B5_RAW_VERIFY0" \
  --attestation "$P07_B5_ATTEST" \
  --confirm-final-acceptance \
     ACCEPT_P07_B5_WITH_ATTESTED_COLD_BOOTS_AND_UNPROVEN_DDR_OWNERSHIP \
  --out "$P07_B5_4_ACCEPT"
cat "$P07_B5_4_ACCEPT"
```

Expected terminal status:
`P07_B5_4_FINAL_OPERATOR_ACCEPTANCE=1` with
`P07_B5_4_FIVE_PHYSICAL_SESSIONS_ORIGINAL_SIGNED_NUMERICAL_GATE_PASS=1`.
The accepted file must record both
`operator_attested_cold_boot_and_recovery_all_five_sessions=true`
and `P07_B5_final_acceptance=true`, while correctly retaining
`boot_firmware_and_other_DDR_owner_independently_proven=false`
and `independent_board_powercycle_instrumentation_proof=false`.
Do not invent or manually edit that report; preserve it for P07-B.6.
The script is **PC-only** and never programs the FPGA.

## B5.4 actual cold reboot/DDR residual risk / user final signoff gate

The physical verification reports explicitly retain **false** for
independent cold reboot and physical DDR ownership. They cannot
prove how the operator actually power-cycled between experiments.
Further hardware destruction is **not** required merely to review
these five good sessions.

Review and copy the deliberately **unattested/null**
[operator attestation template](P07_B5_4_OPERATOR_ATTESTATION_TEMPLATE.json)
to a **new external** path on the operator's PC, but ONLY fill out
an entry as `true` when it describes what really occurred for that
specific original physical session. There are five distinct entries:
four original V3 TRAIN runs plus separate B5 RAW0. Verify personally:

- A **fresh board cold power cycle BEFORE** every physical attempt.
- A physical **cold power cycle AFTER** every physical attempt
  including failure, and **no resumed halted Linux**.
- Dedicated JTAG control for each run.
- Explicit acknowledgment of STILL UNPROVEN boot-firmware/low
  DDR and new B5 trace/mailbox exclusive ownership.
- Independent inspection of numerical evidence, followed by
  explicit operator acceptance of the **bounded P07-B.5 numerical
  milestone**, not unclaimed full packet-by-packet trace parity.

The B5.4 `--mode accept` path is implemented but **DO NOT run until
you have independently reviewed the actual physical run history and
explicitly authorized final acceptance**. It strictly requires
the user-created external attestation JSON, separately passed
numerical source recheck, plus an explicit final acceptance token.
No automatic fake signing or fill-in of the `null` fields.
Even real operator attestation is not hardware instrumentation
proof of power-cycling; this limitation remains a visible field
in the final report.

**Passing B5.4 accepts only P07-B.5 within documented numerical
scope**. P07-B.6 freeze/handoff will then need its own final
verification and explicit operator signoff. Neither acceptance nor
any PR merge happens automatically. Do not unseal official TEST
or modify the frozen original model.
