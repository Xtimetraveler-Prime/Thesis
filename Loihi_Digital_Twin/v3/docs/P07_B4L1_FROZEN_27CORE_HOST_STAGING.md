# P07-B.4l1 — canonical frozen 27-core host DDR staging (new milestone)

**Started 2026-10-22 after user-attested B4k physical standalone admission.**
This is a new, **PC-only**, host staging development checkpoint. It is not
physical scaling or 27-core neural inference. The accepted P03/P05/Track A,
original B2.4 frozen checkpoint, B3 pager and official MNIST TEST are untouched.
PR #49 remains DRAFT, not merged.

## B4k physical precedent, not inferred performance

The user posted real KV260/XSDB and independent B4i receipt markers:

```text
P07_B4I_A53_DOWNLOADED=1
P07_B4I_MAILBOX_CAPTURED_64_BYTES=1
P07_B4I_PHYSICAL_READONLY_ADMISSION_PASS=1
P07_B4K_REAL_STANDALONE_A53_ADMISSION_PASS=1
P07_B4K_TRAINED_27_CORE_INFERENCE_EXECUTED=0
```

Additionally, the post-capture A53 #0 stop succeeded. This closes **only**
P07-B.4k's real A53 boot/PL read-only admission/mailbox verification milestone.
The original raw board logs were not independently downloaded into Git.
The user-run had **no** trained B2 numerical inference. See
`P07_B4K_2026_10_22_PHYSICAL_STANDALONE_ACCEPTANCE_LEDGER.json`.

## B4l.1 exact source and memory geometry

Use the **original user-local frozen B2.4 snapshot** at
`artifacts/p06_b24_frozen_1000`, not an invented payload or regenerated
weights, and not P07-A4's different 512 KiB master. Original B2.4 native
acceptance previously passed 33 frozen assets and 27 full initial P02
context records. The output manifest of the original source intentionally
contains a historical user-acceptance=false value; never edit it.

- **Frozen full manifest bytes SHA256:**
  `d71e2827a81ab1f00ef1e89446540ac04b7d7b34d89b30d46cd6e4ff013c7a63`.
- **Canonical unsigned frozen content SHA256:**
  `d01ccd2d5a85b22f81580cd7800933642e19d1a43e8a2f38eac1f6c4d83cab90`.
- **Original source graph SHA:** `0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a`.
- **Original compiled 27-core B1.2 SHA:** `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`.
- **Original B1.1 capacity SHA:** `82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498`.

The accepted B3a pager uses **27 logical cores, three resident P05/P03
physical slots, one HLS engine**, and fixed backing record address:
`0x40000000 + core_id*0x80000`. The corresponding half-open DDR region
`[0x40000000,0x40D80000)` comprises **14,155,776 bytes** and ends well
before the B4i mailbox at `0x43FF0000`. Every logical record is 524,288
bytes. A future page-in transports **0x6B000 (438,272) bytes**, which
must NOT be confused with this 0x80000 per-core backing stride. A future
dirty page-out uses **0x1A000 (106,496) bytes**.

No memory permission for the 14 MiB DDR destination is granted by this
host packaging; the future standalone physical staging step needs its own
ownership/readback, reboot and cache/MMU admission.

## Implemented host staging deliverable

`scripts/p07_b4l1_stage_frozen_27core.py` supports two deliberate modes:

**`--mode prepare`:** demands the original B2.4 frozen file and canonical
manifest hashes; runs the **original unmodified B2.4
`verify_frozen_directory(..., deep=False)`** to check all 33 indexed files,
P02 per-core initial state, P02 header payload hashes, event/packet empty
banks, accepted validation provenance and untouched official TEST protocol.
Rejects symlink, absent, overwritten, out-of-order or SHA-mismatched frozen
records. Creates a **new** evidence directory outside Thesis and the original
freeze, then concatenates the original 27 records in canonical core-ID order
into a byte-exact contiguous 14 MiB binary. Writes an independently indexed,
self-hashed JSON manifest containing SHA256 of each record, physical DDR
base/offset/end, SHA of the whole bundle, 27 cores, 3 slots and 1 engine.
Uses a temporary directory until the entire image is written and verified;
does not modify, move or open official TEST source.

**`--mode verify`:** revalidates the **original complete freeze**, rejects
missing/extra output files, checks the index's SHA and authoritative source
SHA bindings, rehashes the whole 14 MiB binary and compares every record to
the exact original frozen file byte-for-byte. No Vitis/Vivado/XSDB or board
connection exists in either mode.

`tests/test_p07_b4l1_stage_frozen_27core.py` uses synthetic 27×512KiB
fixtures with the `admit_freeze` entrypoint **mocked explicitly**; no fake
weights can be accepted as the real frozen B2.4 snapshot. Native tests cover
geometry, missing/tampered source, cross-core swap, altered output bytes,
forged index, added files and attempted overwrite. Native synthetic tests
are **not a substitute for the user's real 33-file B2.4 verifier**.

## PC / VS Code native checkpoint

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4l1_stage_frozen_27core.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4k_standalone_admission.py
```

After native checks pass, the genuine stage can be prepared on the PC
without loading a board, opening MNIST TEST, retraining or rebuilding ELF:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
mkdir -p "$HOME/Thesis_Evidence"
export P07_B4L1_FREEZE="$PWD/artifacts/p06_b24_frozen_1000"
export P07_B4L1_STAGE="$HOME/Thesis_Evidence/p07_b4l1_original27_$(date -u +%Y%m%dT%H%M%SZ)"
# Do not pre-create this specific stage output directory.
PYTHONPATH="$PWD/src" python scripts/p07_b4l1_stage_frozen_27core.py \
  --mode prepare \
  --frozen-dir "$P07_B4L1_FREEZE" \
  --output-dir "$P07_B4L1_STAGE"

PYTHONPATH="$PWD/src" python scripts/p07_b4l1_stage_frozen_27core.py \
  --mode verify \
  --frozen-dir "$P07_B4L1_FREEZE" \
  --output-dir "$P07_B4L1_STAGE"
```

Expected only on **real B2.4 original files**:

```text
P07_B4L1_ALL_27_ORIGINAL_P02_RECORDS_BYTE_EXACT_PASS=1
P07_B4L1_FROZEN_B2_4_SOURCE_UNMODIFIED=1
P07_B4L1_PHYSICAL_DDR_STAGED=0
P07_B4L1_TRAINED_INFERENCE_EXECUTED=0
P07_B4L1_OFFICIAL_MNIST_TEST=SEALED
```

The output files are:
`p07_b4l1_original_27_p02_ddr.bin` (**exactly 14,155,776 B**),
`p07_b4l1_staging_index.json`. Their SHA values depend on the actual
original B2.4 record bytes and MUST NOT be fabricated by CI or documentation.

## Next physical and inference stages

B4l.2, after user verifies real B4l.1 staging: plan a dedicated JTAG-only
physical DDR stage+full readback with explicit `[0x40000000,0x40D80000)`
ownership, physical byte-equality and sample verified P02 core IDs. Reboot
after testing. The **B4k ELF by itself does not load or dispatch any of
these 27 cores**.

B4l.3 onward: integrate accepted B3 pager (702 logical dispatches, 26 global
barriers/image, three slots, mandatory dirty page-out/ACK), B2a ingress,
B2b packet/epoch semantics, actual P03 HLS page/dispatch and physical
host-vs-board 26-tick numeric parity on predeclared TRAIN-derived validation
witnesses. No official TEST unseal before separately accepted physical
numeric parity. No changed trained weights, Loihi claims, or speed/power
benchmarks can be inferred from these host staging receipts.
