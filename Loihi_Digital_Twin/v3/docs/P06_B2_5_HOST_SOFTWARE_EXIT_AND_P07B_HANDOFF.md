# P06-B2.5 — Host-software acceptance and explicit P07-B hardware-readiness handoff

**Status on 2026-10-19: B2.1–B2.5 USER-ATTESTED HOST-SOFTWARE PASS; AUTHORISED TO MERGE PR #46 THEN #47.** No scaled KV260 inference, new A53 firmware, physical paging/latency/energy measurement, official MNIST TEST unseal or B2.5 acceptance has occurred.

Development remains on `agent/v3-p06-b2-training-foundation`. Draft PR #47 is **stacked onto the accepted-but-unmerged B1 draft PR #46**. User specifically requested verification **before** merge; neither PR may be merged until the user later explicitly authorizes that action. Preserved Track A baseline/checkpoints/evidence are not modified.

## B2 scientific outcome, honestly scoped

The independent project-trained dense 784→1000→10 signed-24-bit LIF model (794,000 original connections) used the accepted original MNIST 60k TRAIN-only IDX source, its frozen 50k TRAIN / 10k **train-derived validation** split and the accepted 25+1 tick input/state/readout semantics. The user supplied actual B2.2 SHA-verified candidate checkpoint: epoch 6 and **97.08% TRAIN-derived validation accuracy, 0 silent of 10,000**. This is **not** the official held-out MNIST TEST score.

B2.3 independently verified all trained integer connections against the **real B1.2 packed compiler**: **27 logical cores**, 512 KiB initial P02 context each = **14,155,776 initial DDR bytes**, max CURRENT events/core **1,000**, max logical synapse bytes/core below 128 KiB. Three **fixed, preselected TRAIN-derived validation ordinals** 0, 1, 2 (canonical original TRAIN indices 37384, 27347, 20178) each passed **all 26 ticks** of source scalar integer oracle / partitioned logical core and PyTorch readout numerical parity. Do **not** extrapolate the three-frame full-neuron parity into a 10,000-frame packed numerical sweep or a physical accelerator measurement.

B2.4 user-supplied `--verify` and `--verify --deep` both returned `P06_B24_FROZEN_INTEGRITY_PASS=1`, checking **all 33 frozen assets** and independently regenerating the **27 original P02 static 512KiB DDR records**. The native B2.4 freeze manifest has **two intentionally distinct SHA domains**:
- Canonical-content unsigned-manifest digest: `d01ccd2d5a85b22f81580cd7800933642e19d1a43e8a2f38eac1f6c4d83cab90`.
- SHA256 of the full on-disk pretty-printed `frozen_manifest.json` file bytes: `d71e2827a81ab1f00ef1e89446540ac04b7d7b34d89b30d46cd6e4ff013c7a63`.

Original trained checkpoint bytes SHA: `93e43915b38cf3c815a125bbab2788e45209f0ccd024d098b25b82a0a8cd0957`; effective signed24 integer tensor SHA: `4a20357fc5e77465380c1600e7e82cda515bbafc233fb9e3a1205bca9d00d8b0`; signed source SHA: `0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a`; compiled B1.2 SHA: `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`; packed P02/B1.1 audit SHA: `82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498`.

The original freeze manifest retains `user_native_B2_4_accepted=false` as a **historical generation-time status field**. We record subsequent real user native verification *externally*, not by tampering with the frozen directory (which would break both SHA values). Source-of-truth for the user-attested values: `docs/P06_B2_5_USER_EVIDENCE_LEDGER.json`. Model bytes and 27 DDR images are **local under ignored artifacts/**, not GitHub; no raw local snapshot was uploaded to this branch.

## B2.5 new deliverables

`src/loihi_twin_v2/p06_b25_acceptance.py` and `scripts/p06_b25_acceptance.py` implement a **READ-ONLY** final local handoff assessment:
- Reuse the real B2.4 integrity verifier for every frozen file and each P02 record, optionally `--deep` to independently regenerate all 27 DDR contexts.
- Require the two **exact user-observed manifest SHA values**, precise B2.2 original checkpoint/integer identities, B2.3 source/compiler/packing digests, the original 26-tick three-frame validation witnesses, and intact predeclared original sealed-TEST protocol.
- Read the signed serialized B1.2 mapping and P02 B1.1 capacity records, check all 27 unique logical core IDs and per-core initial P02 SHA, exact DDR strides, logical synapse bound <=131,072 bytes, CURRENT event cap <=4096, 3 P05 physical resident slots and 1 P05 physical HLS engine.
- Report software readiness separately from **seven P07-B implementation and physical acceptance blockers**, including real `P06B13I1/P06B13R1` A53 firmware ingestion, page ownership/eviction/dirty writebacks, tick barriers and cross-image reset, board-vs-host parity and independent measured latency/bytes/power.
- Explicit flags `host_go_for_p07b_design_and_planning=true`, `go_for_p07b_scaled_physical_execution=false`, `go_for_official_mnist_test_unseal=false`. No hidden `--flash`, TEST loader, download, checkpoint rewrite or FPGA access. A `--report NEW_PATH` may write a standalone B2.5 summary **only outside the sealed B2.4 33-asset directory**; it never overwrites.

`tests/test_p06_b25_acceptance.py` contains **synthetic metadata-only** unit tests for double-hash interpretation, 27-core resource identities, trace tampering, numerical-frame scope, OFFICIAL TEST seal and physical NO-GO, false claims, and no freeze edits. These unit tests do not stand in for the user's genuine snapshot assessment.

## Formal B2 software exit decision

**Host-software GO / B2.5 user-attested PC acceptance:**
- Candidate is independent of Track A; physical P07/P08-A 784→32→10 artifact remains unchanged.
- Real trained checkpoint passed user-supplied SHA+validation integrity and original B1.2 exact packed capacity.
- Full per-neuron 26-tick equivalence was established for 3 predeclared TRAIN-derived validation frames.
- 33 materialized B2.4 files including all 27 initial DDR images passed user-supplied normal and deep byte regeneration verification.
- Sealed, prespecified official TEST protocol was already included before any TEST access.

**P07-B DESIGN / PLANNING GO (B2.5 user verification attested):**
The separate engineering phase should deliver, in order, a frozen PS/PL memory and DDR owner map with validated reset, real HLS engine and 3 resident contexts, deployed 27-core A53 streaming ingress and NEXT route ABI, dirty context writeback, fail-closed packet limits/epoch barriers, physical host-vs-board integer trace equality, and physically measured PL page bytes, throughput/latency and power/energy. This is **not** plug-and-play hardware because B1.3/B1.5 were host protocol and paging models, not physical scaled firmware. Plan a separately user-verified P07-B branch and versioned acceptance criteria before programming hardware.

**P07-B EXECUTION NO-GO today.** No flashed/accepted scaled 27-core A53/PL implementation, live paging telemetry, physical correctness or DDR owner/isolation/atomic reset assurance has been produced. The accepted P05 diagnostic only supports a distinct single-axon ingress ABI; never represent it as scaled network runtime.

**Official MNIST TEST UNSEAL NO-GO today.** Remains sealed until B2.4/B2.5 evidence is frozen, physical P07-B board-versus-host parity is user accepted and official protocol/run identifiers are fixed. One full official 10,000-image evaluation after that gate; no test-driven epoch/hyperparameter/model selection. The reported **97.08% is validation**, not an official benchmark.

## PC / VS Code acceptance commands (read-only, no FPGA, no MNIST dataset I/O)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-b2-training-foundation
git pull --ff-only origin agent/v3-p06-b2-training-foundation
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# B2.5 acceptance logic and corruption/capacity/source negative tests
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b25_acceptance.py

# B2.4/B2.3/B2.2/B2.1/B1 previous host regression suite
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b24_freeze.py tests/test_p06_b23_trained_audit.py \
  tests/test_p06_b22_training.py tests/test_p06_b21_training_foundation.py \
  tests/test_p06_b15_paging.py tests/test_p06_b14_differential.py \
  tests/test_p06_b13_streaming.py tests/test_p06_b12_partition.py \
  tests/test_p06_b1_contract.py

PYTHONPATH="$PWD/src" python -m compileall -q \
  src/loihi_twin_v2/p06_b25_acceptance.py \
  scripts/p06_b25_acceptance.py tests/test_p06_b25_acceptance.py

# Real original checkpoint/27 context package; read-only, no dataset:
PYTHONPATH="$PWD/src" python scripts/p06_b25_acceptance.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000"

# Optional more expensive independent 27-core reconstruction:
PYTHONPATH="$PWD/src" python scripts/p06_b25_acceptance.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" --deep

# Optional standalone new evidence JSON; OUTSIDE the frozen 33-asset set.
# Do NOT pre-create this file; if it already exists, choose a new filename.
PYTHONPATH="$PWD/src" python scripts/p06_b25_acceptance.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --report "$PWD/artifacts/p06_b25_host_handoff.json"
```

Expected flags on success: `P06_B25_HOST_SOFTWARE_HANDOFF_PASS=1`, `P06_B25_SCALED_FPGA_EXECUTION_GO=0`, `P06_B25_OFFICIAL_TEST_UNSEAL_GO=0`, `P06_B25_FREEZE_UNMODIFIED=1`. `B2_5_native_user_accepted=false` stays *historical code/manifest-time status* and is superseded by user's external reported run when provided; never edit the B2.4 frozen source just to flip a boolean.

**Subsequent user acceptance (2026-10-19):** the user reports that all B2.5 tests and handoff commands passed and explicitly authorized the ordered merges. Only this general user attestation was provided; exact B2.5 stdout, test count and optional report-file SHA were not supplied, so none are fabricated. The source-authoring assistant has not independently run native pytest or the user's SHA-indexed local freeze. Merge B1 PR #46 to `main` first, retarget B2 PR #47 to `main` after the B1 merge, check the resulting diff/integrity, and merge B2. Actual integration status is recorded separately after GitHub confirms it. The local freeze's historical status field must remain unchanged.
