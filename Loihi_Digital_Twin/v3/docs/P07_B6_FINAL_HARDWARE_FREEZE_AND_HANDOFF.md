# P07-B.6 — Original 27-core scaled physical inference freeze and P08-B handoff

**Status (2026-11-01): P07-B.5 FORMALLY CLOSED. B6.1 GENUINE
OPERATOR FREEZE SEAL PASSED (33 original frozen files, all five source
physical validation sessions, accepted B5.4 original operator report).
B6.2 complete external evidence packaging and independent archive
auditor IMPLEMENTED; operator copy and independent audit PENDING.
B6.3 bounded final operator handoff checker and P08-B boundary
IMPLEMENTED; final P07-B acceptance PENDING B6.2 physical source
copy and separate B6.3 operator signoff.**
All PRs #49/#50/#51 remain draft and unmerged. Official MNIST TEST SEALED.

## Why B6 is necessary

A physical numerically successful demonstration is not equivalent to
a reproducible frozen hardware/software result. B6 freezes exactly
which signed original B2.4 TRAIN-only 784→1000→10 network and 27
P02 DDR contexts were used, which accepted P03 FPGA shell/XSA was
programmed, which accepted original A53 V3 and separate raw A53
firmware hashes were executed, which independently authenticated
physical evidence directories support the result, and what is **not**
claimed. This creates a reproducible boundary before performance,
scaling and official benchmark protocols are opened.

### B6.1 — Read-only reproducibility inventory and candidate hardware freeze

`scripts/p07_b6_freeze_manifest.py` implements two distinct
PC-only operations; native regression
`tests/test_p07_b6_freeze_manifest.py` checks the freeze contract,
malformed signatures, symlink/mutated file rejection, and no board or
merge side effects.

**`--mode inventory` (safe now):**
- Runs the original accepted **33-file B2.4 frozen directory
  verifier**, not a synthetic graph or re-trained snapshot.
- Revalidates original **20,384 input/1,000 output registered route
  entries**, the exact three signed original TRAIN ingress files,
  and their unchanged manifest.
- Reopens the genuine operator original B5.4 five-session NUMERICAL
  report, requiring four distinct original V3 0/1/2/0 sessions plus
  a fifth 840,320B strict physical original TRAIN0 raw parity
  session with exact SHA and numerical checks.
- Re-runs separately admitted genuine original P03 routed
  `p03_2_ps_mmio.xsa`, Vitis-built distinct B5 ELF/map and
  original signed route/frozen source gates.
- Computes individual SHA256 for a safe explicit whitelist:
  `frozen_manifest.json`, `network_source.json`,
  `packed_deployment.json`, `b23_validation_parity.json`;
  signed original 3 TRAIN images, route tables and manifest; P03
  XSA; new accepted B5 A53 ELF and linker map.
- Pins the original physically accepted V3 A53 ELF/map SHA256
  from original V3 acceptance contract as separately signed
  historical evidence. This candidate inventory does **not**
  physically rehash the original V3 ELF bytes or modify them.
- Records that original TEST is **SEALED_NOT_ACCESSED**, that
  full per-packet-byte equality / physical exclusive DDR ownership
  / hardware-measured board power cycles remain **unproven**,
  that formal B5 acceptance is not yet verified, and that the
  file is NOT a final B6 seal.
- Preserves the expected exact `main:LitReview.md` Git blob
  `3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`.
  This script does not claim it checked the remote main branch or
  modify Git history.

**`--mode seal` (ONLY after B5.4 genuine `--mode accept` PASS):**
- Requires actual operator external **B5.4 ACCEPTED** JSON,
  original operator five-session attestation JSON, original
  V3 four-run physical evidence directory paths 0/1/2/0, the
  independent B5 RAW0 physical directory, and original signed
  frozen sources.
- Calls the actual B5.4 `closeout()` in `accept` mode to
  **re-open all five original physical evidence sessions and
  recompare raw neuron bytes to independently regenerated scalar**
  from frozen source. It then requires a complete field-by-field
  match against the actual operator-created B5.4 accepted JSON.
- Produces a new write-once B6 SHA freeze report whose
  `B5_formal_operator_acceptance_verified=true` means
  the genuine local accepted report was independently rechecked.
  It continues to state `B6_final_hardware_freeze_accepted=false`,
  `P07_B_complete=false`, `P08_B_started=false`,
  `main_merged=false`, and the actual ownership/reboot
  limitations. Merely running `seal` does not freeze final B6.

### B6.2 — Full original source, firmware and real physical evidence reproducibility package (IMPLEMENTED / OPERATOR COPY PENDING)

New `scripts/p07_b6_reproducibility_bundle.py` requires genuine,
independently sealed B6.1 original signed source/hardware and B5.4
final operator evidence, the original physically accepted V3 ELF/map
(actual bytes, rehashed against the two independently accepted
historical SHA256s), the original B5 Vitis A53 ELF/map, P03 XSA,
all 34 B2.4 frozen manifest and asset files, original TRAIN routes,
all **five real physical session evidence trees**, and a fresh
read-only `origin/main:LitReview.md` original Git blob check.

The source list is rehashed BEFORE copying and all output bytes
are independently SHA-verified AFTER writing into a NEW external
directory. No mutable source, symlink, unexpected directory placement
or physical TEST file is implicitly trusted. Output includes
`handoff_manifest.json` with a SHA256 + byte count for every
copied source/physical file. B6.2 package remains
**PENDING OPERATOR-INDEPENDENT COPY AND VALIDATION** until this is
run successfully; no acceptance can be asserted from the code alone.

Operator must locate original physically accepted V3 ELF and GNU
map files from its original genuine Vitis workspace; the current
B5 artifacts are separate. From the B6 branch after a passing B6.1 seal:

```bash
# Locate original V3 assets without guessing their directories:
find "$HOME" -type f \
  \( -name 'p07_b4m_diag_v3_26tick.elf' -o \
     -name 'p07_b4m_diag_v3_26tick.map' \) -print
# Export exact genuine original V3 ELF/map paths after inspecting find:
# export P07_B4M_V3_ELF="/home/dna/.../p07_b4m_diag_v3_26tick.elf"
# export P07_B4M_V3_MAP="/home/dna/.../p07_b4m_diag_v3_26tick.map"
# Confirm the SHA256 pins before the copy:
# V3 ELF 66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904
# V3 MAP 148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede

git -C "$HOME/Git/Thesis" fetch origin main
export P07_B6_PACKAGE="$HOME/Thesis_Evidence/p07_b6_full_reproducibility_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P07_B6_PACKAGE"
PYTHONPATH="$PWD/src" python scripts/p07_b6_reproducibility_bundle.py \
  --seal "$P07_B6_SEAL" \
  --accept "$P07_B5_4_ACCEPT" \
  --attest "$P07_B5_ATTEST" \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --routes-dir "$P07_B4M_STAGE" \
  --reports "$P07_B4L_REPORTS" \
  --build-dir "$P07_B5_RAW_BUILD_DIR" \
  --v3-elf "$P07_B4M_V3_ELF" \
  --v3-map "$P07_B4M_V3_MAP" \
  --out-dir "$P07_B6_PACKAGE"
cat "$P07_B6_PACKAGE/handoff_manifest.json"
```

Expected flags `P07_B6_2_COMPLETE_ORIGINAL_SOURCE_AND_5_PHYSICAL_SESSION_COPY_SHA_PASS=1`,
`P07_B6_2_ACCEPTED_ORIGINAL_V3_AND_B5_A53_FIRMWARE_COPY_PASS=1`,
`P07_B6_2_MAIN_LITREVIEW_ORIGINAL_GIT_BLOB_PASS=1`, and
`P07_B6_2_FINAL_ACCEPTANCE=0`.
No Vitis rebuild, PL programming, filesystem replacement, hardware
power-cycle or official TEST access is authorized by B6.2.

Prepare a reproducible operator handoff with explicit:
- Freezed source and original signed DDR/route/current-spike/fanout ABI,
  accepted P03 fixed FPD128 PS/PL physical topology and exact XSA;
- SHA-pinned genuine original V3 and optional separate B5 RAW
  A53 ELF/map, memory spans, 27 logical cores/3 physical slots,
  one HLS engine, original 26-tick/702-dispatch/26-barrier contract;
- A fresh simple operator hardware programming/replay protocol that
  **never** silently changes boot firmware, PL static widths,
  original model, signed TRAIN frames or sealed official TEST;
- Full original signed 4×V3 plus 1×RAW0 physical provenance
  and explicit model-vs-hardware/packet-count/trace scope;
- Actual operator power-cycle/recovery/JTAG attestation,
  new DDR ownership uncertainties and destructive-run safety;
- Robust local reproduction commands and evidence backup manifest
  with source-specific artifact SHA integrity.

### B6.3 — Final independent acceptance and P08-B protocol handoff (IMPLEMENTED; source-backed operator PASS pending)

New PC-only `scripts/p07_b6_final_handoff.py` independently
reopens the original five-session B6.2 copied physical evidence archive,
requires a fresh full B6.2 verifier result identical to the operator's
original independent archived audit, binds the B6.1 actual signed seal
and B5.4 accepted user-attestation source SHA256s, and verifies the
original `origin/main:LitReview.md` Git blob. `--mode review` never
accepts P07-B or changes main. `--mode accept` requires a **separate
explicit original trained 27core final operator handoff token**, still
without hardware contact, official TEST unlock or GitHub merge.
[Full B6.3 acceptance protocol, actual original V3 paths and
P08-B timing/benchmark handoff boundary](P07_B6_3_FINAL_HANDOFF_P08_BOUNDARY.md).

B6.3 final acceptance is conditional on the user actually creating
and independently verifying the full B6.2 physical evidence copy,
then running both review and explicit acceptance. P08-B scaling/timing
measurements cannot begin until the full P07-B source freeze is
accepted and a separate bounded benchmark protocol agreed.
No official TEST unlock based on B5 TRAIN parity.

## Operator commands, checkpoint A — independent B5.4 formal acceptance

From the project V3 folder, in the existing .venv-p08, use the same
original source variables as the successful B5.4 review.
**No board contact**.

```bash
cd ~/Git/Thesis
git switch agent/v3-p07-b5-scaled-multiframe-validation
git pull --ff-only origin agent/v3-p07-b5-scaled-multiframe-validation
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

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
export P07_B5_4_REVIEW="$HOME/Thesis_Evidence/p07_b5_4_final_numerical_review_20261101T220745Z.json"

# Restore the already existing original RAW verifier report and the
# exact separately edited operator attestation file; do NOT synthesize.
find "$HOME/Thesis_Evidence" -maxdepth 1 -type f \
  -name 'p07_b5_raw_verify_train0_*.json' -print
find "$HOME/Thesis_Evidence" -maxdepth 1 -type f \
  -name 'p07_b5_4_operator_attestation_*.json' -print

# Assign the TWO existing files listed by find, exactly:
export P07_B5_RAW_VERIFY0="/home/dna/Thesis_Evidence/<ACTUAL_RAW_VERIFY_FILE>.json"
export P07_B5_ATTEST="/home/dna/Thesis_Evidence/<ACTUAL_ATTESTATION_FILE>.json"
test -s "$P07_B5_RAW_VERIFY0" && test -s "$P07_B5_ATTEST"

export P07_B5_4_ACCEPT="$HOME/Thesis_Evidence/p07_b5_4_accepted_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P07_B5_4_ACCEPT"

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

Expected `P07_B5_4_FINAL_OPERATOR_ACCEPTANCE=1` and exact
`P07_B5_final_acceptance=true`. This is user-attested, **not**
independently measured cold-boot proof and does not establish
DDR exclusivity. If the script fails, B5 acceptance and B6
sealing remain OPEN.

## 2026-11-01 actual B5.4 operator ACCEPTED, and B6.1 inventory PASS

The operator supplied the real separate local `--mode accept`
report after accepting the exact five-session cold-powercycle/JTAG
operator-attestation file. Real stdout ended with
`P07_B5_4_FINAL_OPERATOR_ACCEPTANCE=1`, with all five signed physical
and 840,320B raw neuron-scalar numerical checks PASS.
Accepted operator report:

`/home/dna/Thesis_Evidence/p07_b5_4_accepted_20261101T224134Z.json`

Attestation SHA256:

`4dd6cf0d02c477a2992b55b8bc2454ee9800c94ccce78f6cee25a32f2dc7fa31`.

[Signed B5.4 final bounded operator acceptance ledger](P07_B5_4_2026_11_01_FINAL_OPERATOR_ATTESTED_ACCEPTANCE.json)
preserves the accepted numerical/physical findings, disclosure of
UNPROVEN DDR boot/user ownership, operator-attested rather than
instrumented power cycles, original official TEST SEALED.

The user also ran `scripts/p07_b6_freeze_manifest.py --mode inventory`
with successfully admitted frozen source and ELF evidence and obtained
`P07_B6_ORIGINAL_27CORE_SIGNED_SOURCE_ARTIFACT_FREEZE_INVENTORY_PASS=1`,
`P07_B6_B5_FORMAL_ACCEPTANCE_INDEPENDENTLY_RECHECKED=0`, and
`P07_B6_FINAL_ACCEPTANCE=0`.
That `0` was CORRECT for `--mode inventory`: this mode is not
allowed to use signed B5 approval as a substitute for independently
verifying the operator's actual acceptance report.

**B6.1 accuracy improvement after the initial operator run:**
`--mode inventory` now includes SHA256 for **ALL 33 original
manifest-signed B2.4 artifacts**, including every original
27×512KiB P02 context, the original frozen network, original
checkpoint weights, original compiler deployment, and other
original freeze files, plus the manifest itself, all three
TRAIN images, route tables, XSA, and B5 ELF/map. The user must
pull latest B6 branch and re-run a **NEW** inventory to get
this extended source coverage. Historical candidate manifest is
preserved without modification.

### B6.1 sealing against REAL user-approved B5.4 accepted report — PC ONLY

After source/evidence variables from B5.4 and B6.1 setup,
run the B6.1 seal *without* repeating any KV260 board experiment.
A separate output directory/file is mandatory:

```bash
export P07_B5_4_ACCEPT="$HOME/Thesis_Evidence/p07_b5_4_accepted_20261101T224134Z.json"
export P07_B5_ATTEST="$HOME/Thesis_Evidence/p07_b5_4_operator_attestation_20261101T222117Z.json"
export P07_B5_RAW_VERIFY0="$HOME/Thesis_Evidence/p07_b5_raw_verify_train0_20261101T215124Z.json"
export P07_B6_SEAL="$HOME/Thesis_Evidence/p07_b6_original_freeze_seal_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P07_B6_SEAL"
PYTHONPATH="$PWD/src" python scripts/p07_b6_freeze_manifest.py \
  --mode seal \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --routes-dir "$P07_B4M_STAGE" \
  --build-dir "$P07_B5_RAW_BUILD_DIR" \
  --reports "$P07_B4L_REPORTS" \
  --offline-report "$P07_B5_RAW_OFFLINE" \
  --b5-review "$P07_B5_4_REVIEW" \
  --b5-acceptance "$P07_B5_4_ACCEPT" \
  --attestation "$P07_B5_ATTEST" \
  --staged-dir "$P07_B4L1_STAGE" \
  --fourrun-report "$P07_B5_FOURRUN_REPORT" \
  --run "0:$P07_B5_RUN0" \
  --run "1:$P07_B5_RUN1" \
  --run "2:$P07_B5_RUN2" \
  --run "0:$P07_B5_RUN0_REPEAT" \
  --raw-evidence "$P07_B5_RAW_RUN0" \
  --raw-report "$P07_B5_RAW_VERIFY0" \
  --out "$P07_B6_SEAL"
cat "$P07_B6_SEAL"
```

Expected real PC-only `P07_B6_B5_FORMAL_ACCEPTANCE_INDEPENDENTLY_RECHECKED=1`;
`P07_B6_FINAL_ACCEPTANCE=0` is still REQUIRED.
The seal re-opens all five source-backed physical sessions rather than
trusting a manually edited PASS boolean. This independent seal is
B6.1's acceptance checkpoint, **not B6.3 final P07-B acceptance**.

## Operator commands, checkpoint B — new B6.1 candidate inventory

Pull new B6 branch **after** the above accepted result is saved
(only to maintain the operational dependency; candidate inventory
itself is PC-only and can run without an accepted B5 report).

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p07-b6-final-freeze-handoff
git pull --ff-only origin agent/v3-p07-b6-final-freeze-handoff
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b5_final_acceptance.py \
  tests/test_p07_b6_freeze_manifest.py

export P07_B6_INVENTORY="$HOME/Thesis_Evidence/p07_b6_original_freeze_inventory_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P07_B6_INVENTORY"

PYTHONPATH="$PWD/src" python scripts/p07_b6_freeze_manifest.py \
  --mode inventory \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --routes-dir "$P07_B4M_STAGE" \
  --build-dir "$P07_B5_RAW_BUILD_DIR" \
  --reports "$P07_B4L_REPORTS" \
  --offline-report "$P07_B5_RAW_OFFLINE" \
  --b5-review "$P07_B5_4_REVIEW" \
  --out "$P07_B6_INVENTORY"
cat "$P07_B6_INVENTORY"
```

Expected PC-only candidate:
`P07_B6_ORIGINAL_27CORE_SIGNED_SOURCE_ARTIFACT_FREEZE_INVENTORY_PASS=1`,
`P07_B6_B5_FORMAL_ACCEPTANCE_INDEPENDENTLY_RECHECKED=0`,
`P07_B6_KV260_BOARD_CONTACT=0`,
`P07_B6_MAIN_MERGE_PERFORMED=0`,
`P07_B6_FINAL_ACCEPTANCE=0`.

**Do NOT enter B6 `--mode seal` until the actual user-created B5.4
accepted source report exists and passes its own independent
`--mode accept` command. No B6 acceptance or merge is automatic.**

## Operator commands, checkpoint C — main-only literature-review preservation

The new `scripts/p07_b6_literature_merge_guard.py` is a
separate **read-only Git tree/commit integrity check**. It compares
the actual fetched `origin/main:LitReview.md` Git blob object ID
(not a file SHA256) against the original independent main
Git *blob* `3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`.
It rejects a missing file, changed contents, renaming or symlink,
and never changes either branch or executes hardware.

```bash
cd ~/Git/Thesis
git fetch origin main
git rev-parse 'origin/main:LitReview.md'
# Must print 3c45d0a0d0b55378d3564d8f82282803a8eb1a3e

cd Loihi_Digital_Twin/v3
export P07_B6_LITREVIEW_AUDIT="$HOME/Thesis_Evidence/p07_b6_main_litreview_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P07_B6_LITREVIEW_AUDIT"
PYTHONPATH="$PWD/src" python scripts/p07_b6_literature_merge_guard.py \
  --repo "$HOME/Git/Thesis" \
  --ref origin/main \
  --out "$P07_B6_LITREVIEW_AUDIT"
cat "$P07_B6_LITREVIEW_AUDIT"
```

Expected `P07_B6_MAIN_LITREVIEW_ORIGINAL_BLOB_IDENTICAL_PASS=1`.
After all P07-B milestones are accepted and the operator explicitly
authorizes merging, **re-run against `--ref main` after GitHub
merge and after updating local main**, using a NEW output report.
The same exact blob SHA must persist. Never use a force push,
reset or snapshot overwrite as a substitute for a merge.

## Git branches and literature-review preservation

Draft dependency chain (leave all unmerged):
- `main`: contains `LitReview.md`, exact Git blob
  `3c45d0a0d0b55378d3564d8f82282803a8eb1a3e`;
- PR #49: `agent/v3-p07-b-scaled-physical-inference`, base `main`;
- PR #50: `agent/v3-p07-b5-scaled-multiframe-validation`, base PR #49;
- B6 development branch:
  `agent/v3-p07-b6-final-freeze-handoff`, base PR #50.

Once the **entire P07-B** track is separately user-accepted,
normal merge by dependency order 49→50→B6 (not overwrite
or force-push), and compare `main:LitReview.md` blob SHA
after merging. No changes to main at B6.1.

