# P07-B.6 — Original 27-core scaled physical inference freeze and P08-B handoff

**Status (2026-11-01): PREPARATION STARTED ONLY, NOT FINALLY ACCEPTED.**
New B6.1 read-only signed source/evidence freeze manifest implemented.
B5.4 has passed **five independently verified physical numerical sessions**,
including exact 840,320-byte 26×1010-neuron original signed scalar
parity, but the operator has *not yet supplied a genuine local*
`--mode accept` PASS JSON. User reports all fields in a separate
attestation file have been personally set to true. Do not substitute
that statement for a completed input-file verification.
B5 formal acceptance, B6 final freeze, P08-B, and PR merges remain gated.

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

### B6.2 — Final production freeze / reproducibility package (OPEN)

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

### B6.3 — Final independent acceptance and P08-B protocol handoff (OPEN)

B6 final acceptance remains dependent on user verification of the
B6.2 full hardware freeze and independent validation,
preserving signed original B2.4 model/TEST seal and accepted V3
results. P08-B scaling/timing runs cannot begin until a separate
explicit bounded benchmark protocol is agreed. No official TEST
unlock based on B5 numerical parity alone.

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

