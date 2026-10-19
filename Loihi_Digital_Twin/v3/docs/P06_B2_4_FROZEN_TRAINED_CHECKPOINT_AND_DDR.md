# P06-B2.4 — Frozen trained checkpoint, packed 27-core P02 images and TEST protocol

**Implementation status:** B2.4 host-only freeze source/tests/CLI **COMMITTED; native workstation validation PENDING**. B2.3 **USER-ATTESTED PASS** for trained dense 784→1000→10, 27 cores, 14,155,776 P02 backing bytes and full 26-tick numerical parity on *three* fixed TRAIN-derived validation images. **No scaled FPGA run, official MNIST TEST unseal, measured performance, or B2.4 user acceptance is claimed.**

Development branch `agent/v3-p06-b2-training-foundation`, stacked draft PR #47, dependent on still-unmerged B1 PR #46. Neither PR may be merged without explicit user authorization. Accepted Track A checkpoint and source stay read-only.

## Accepted user report and fixed identity

B2.2 best epoch **6**, original 10,000-image TRAIN-derived validation accuracy **0.9708**, **0** silent examples. The B2.2 candidate checkpoint is already on the user's PC at `artifacts/p06_b22_candidate_1000`; it is NOT on GitHub. The user supplied successful B2.3 real dense *structural and numerical* runs (ordinal 0 alone, then canonical validation ordinals **0,1,2**):

| Bound value | SHA256 |
|---|---|
| Trained B2.2 `weights_state_dict.pt` | `93e43915b38cf3c815a125bbab2788e45209f0ccd024d098b25b82a0a8cd0957` |
| Effective signed24 trained integer weights | `4a20357fc5e77465380c1600e7e82cda515bbafc233fb9e3a1205bca9d00d8b0` |
| Trained full dense NetworkSpec | `0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a` |
| 27-logical-core B1.2 compiled deployment | `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a` |
| B1.1 packed/P02 capacity audit | `82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498` |

The **27 full initial DDR contexts**, 512 KiB each, are host-side representations from the accepted P02 ABI. No dynamic runtime mutable DDR state or PL-borne bytes are captured.

Previously user-attested, frozen **TRAIN-derived VALIDATION**, not official TEST:

| Ordinal | Canonical original TRAIN IDX | Image SHA prefix | Predicted / true label | Traces |
|---|---:|---|---|---|
| 0 | 37384 | `5978f00e...` | 1 / 1 | monolithic `4bef8f76...`, partitioned `4afdce2b...` |
| 1 | 27347 | `3e3c39ef...` | 2 / 2 | monolithic `e62d9969...`, partitioned `1cb32f77...` |
| 2 | 20178 | `ecba50a2...` | 1 / 1 | monolithic `9cce27d0...`, partitioned `9c5766a6...` |

Their monolithic and partitioned SHA strings are *not supposed to be identical*: their trace schemas differ. **Neuron-state/input/spike/NEXT-route equality** across all 26 ticks is the actual verified parity test. User-reported exact full trace fingerprints are anchored in B2.4 source, and full numerical checks are rerun locally before snapshot output is created.

## Freeze layout, safety and provenance

New `src/loihi_twin_v2/p06_b24_freeze.py` + `scripts/p06_b24_freeze.py`:

- Refuse any pre-existing output directory; create a private sibling staging directory and move into the requested output path **only after writing/checking everything**. Do not alter or overwrite original B2.2 candidate or its TRAIN archives. Freeze is *tamper-evident with SHA256 and no-overwrite*, not cryptographically signed external custody, hardware WORM storage or immutable OS permissions. Retain top-level SHA outside the freeze directory for later chain-of-custody.
- Verify the genuine B2.2 candidate bytes, model dimensions, source provenance, best epoch/validation and signed int24 weight digest; require the **exact** user-reported source/deployment/capacity SHA and 3 originally checked selected validation ordinals, image indices/bytes and both original 26-tick trace SHAs.
- Generate full source graph and B1.2 serialized compiled mapping **from actual trained checkpoint**; recompute accepted P03 images/P02 initial 512KiB DDR record for each of the 27 logical cores using `export_paged_hardware_image` and `build_initial_ddr_context_record`. Check every record against B1.1's original initial full-file SHA, P02 header payload digest, zero event queues and fixed DDR base-offset accounting.
- Create a dedicated **predeclared official TEST protocol document** without reading the TEST archives: canonical complete 10,000 official TEST images, raw uint8 phase-17 quota encoding, 26 steps, same lowest-index argmax/tie, per-image reset, exactly one prediction/image including failures, top1/denominator/per-class/recall/confusion/silent/error reporting. Future TEST access requires user-accepted B2.4 frozen model **and** separately accepted actual P07-B scaled board ingress/paging/host-vs-board parity and pinned evaluation conditions. Do not use TEST for checkpoint selection.
- SHA-bind **every byte asset** in `frozen_manifest.json`; a separate read-only verification command checks manifest digest, all 33 asset checksums, exactly 27 fixed initial P02 records, zero runtime event banks, source original candidate manifest, 3 fixed B2.3 validation traces and unchanged predeclared TEST protocol. `--deep` additionally reconstructs the original NetworkSpec and B1.2 compiled deployment and independently regenerates all 27 P02 records without opening any dataset.

Directory generated on user's PC under **gitignored `artifacts/`**:

```text
artifacts/p06_b24_frozen_1000/
├── frozen_manifest.json                         # 33 assets + whole manifest SHA
├── checkpoint/
│   ├── weights_state_dict.pt                    # byte-for-byte ORIGINAL candidate
│   └── candidate_manifest.json                  # byte-for-byte original B2.2 metadata
├── network_source.json                          # signed24 full 794k original graph
├── packed_deployment.json                       # B1.2 serialized 27-core packed graph and audit
├── b23_validation_parity.json                    # full 3 validation result rows + trace hashes
├── predeclared_official_test_protocol.json      # written while official TEST remains SEALED
└── initial_ddr/
    ├── core_000_initial_p02_512k.bin
    ├── ...
    └── core_026_initial_p02_512k.bin
```

The full NetworkSpec and packed source JSON representations are **large**. Expect significant temporary disk/CPU/RAM during independent recomputation. Actual temporary/final file sizes are machine-dependent except 27 × 524,288 initial DDR bytes = **14,155,776** bytes. No training is performed in this freeze. No physical FPGA programming/DDR writes/JTAG are performed.

`frozen_manifest.json` sets `checkpoint_frozen=true` to indicate an output *materialized frozen snapshot*, but intentionally marks `user_native_B2_4_accepted=false`, `status=HOST_FROZEN_CANDIDATE_PENDING_NATIVE_ACCEPTANCE`, official TEST SEALED and physical KV260 NOT_TESTED until the separate user verification gate.

## PC native test commands: new B2.4 code, no full dense workload

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-b2-training-foundation
git pull --ff-only origin agent/v3-p06-b2-training-foundation
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b24_freeze.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b23_trained_audit.py tests/test_p06_b22_training.py \
  tests/test_p06_b21_training_foundation.py tests/test_p06_b15_paging.py \
  tests/test_p06_b14_differential.py tests/test_p06_b13_streaming.py \
  tests/test_p06_b12_partition.py tests/test_p06_b1_contract.py

PYTHONPATH="$PWD/src" python -m compileall -q \
  src/loihi_twin_v2/p06_b24_freeze.py \
  scripts/p06_b24_freeze.py tests/test_p06_b24_freeze.py
```

## Freeze *actual* trained checkpoint and three fixed validation witnesses

**Separate, opt-in CPU/RAM-intensive step**. These commands WILL build a complete 27-core host snapshot (but will NOT train/test official/flash FPGA). They re-run B2.3 dense numerical oracle on original canonical TRAIN-derived validation ordinals **0, 1, 2**, before materialization.

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
mkdir -p artifacts

# Do NOT pre-create artifacts/p06_b24_frozen_1000; script refuses overwrite.
PYTHONPATH="$PWD/src" python scripts/p06_b24_freeze.py \
  --freeze \
  --candidate-dir "$PWD/artifacts/p06_b22_candidate_1000" \
  --data-dir "$PWD/data/mnist_raw" \
  --output-dir "$PWD/artifacts/p06_b24_frozen_1000"
```

Expected *only after successful completion*: `P06_B24_HOST_FREEZE_MATERIALIZED_PASS=1`, and freeze report manifest SHA256 and all 27 initial DDR records.

Verify **without modifying checkpoint or output**:

```bash
PYTHONPATH="$PWD/src" python scripts/p06_b24_freeze.py \
  --verify --output-dir "$PWD/artifacts/p06_b24_frozen_1000"

# Stronger independent read-back; CPU/RAM/disk I/O intensive:
PYTHONPATH="$PWD/src" python scripts/p06_b24_freeze.py \
  --verify --deep \
  --output-dir "$PWD/artifacts/p06_b24_frozen_1000"

# Copy the reported manifest SHA to a separate personal evidence record:
sha256sum artifacts/p06_b24_frozen_1000/frozen_manifest.json
```

Expected markers: `P06_B24_FROZEN_INTEGRITY_PASS=1`, `P06_B24_OFFICIAL_TEST_STATUS=SEALED`, `P06_B24_PHYSICAL_KV260_STATUS=NOT_TESTED`.

Note that **SHA256 printed by the program as `manifest_sha256`** hashes the unsigned canonical JSON *contents* whereas `sha256sum frozen_manifest.json` hashes the actual pretty-printed file bytes; **these two values are legitimately different**. Preserve both in the acceptance record.

**B2.4 cannot be closed from source commit alone.** The user must report native B2.4 unit/regression gates, full materialization, ordinary and deep SHA/DDR verification, and both manifest hashes. No `t10k*` TEST file, physical KV260 scaled run or P08-B measurements are in scope. Next B2.5 only after this separate native gate.
