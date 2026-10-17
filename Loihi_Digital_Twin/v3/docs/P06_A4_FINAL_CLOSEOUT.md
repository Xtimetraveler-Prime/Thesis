# P06-A4 — Track A compact benchmark closeout / static DDR entry gate

**Recorded:** 2026-10-17
**Branch for closeout:** `agent/v3-p06-lif-feasibility`
**Merge target:** `main` (user explicitly authorized).
**Acceptance scope: P06-A4 COMPLETE / USER-ACCEPTED (2026-10-17).**
The trained Track A host software P03 benchmark and separately generated
P02.1 **512 KiB initial static DDR context** both passed the user's native
verification. The 512 KiB record's full-file SHA256 was not pasted and
must be recorded from the existing local artifact before P07 loads it.
**This milestone does not establish FPGA MNIST inference or official-test accuracy.**

## Verified user-supplied evidence (not assistant's independent board run)

The user reported `P06_A4_SOFTWARE_SNAPSHOT_PASS=1` after invoking
`scripts/p06_a4_snapshot.py` on the exact saved checkpoint. That
routine executes `load_candidate` and `require_pinned_training_candidate`
before compilation; its success therefore implies successful checkpoint
byte SHA256 validation, state_dict reload and integer weight digest
checking **within that run**, even though the separate
`P06_A3_CANDIDATE_INTEGRITY_PASS=1` printout was not pasted.

Real trained one-core P03 image:
- core 0; 42 compartments; 816 axon bindings;
- 25,408 packed synapse words; 32 route descriptor words;
- 32 output route words.
- exact model: signed24 fixed LIF, fixed 25+1 input/drain,
  one-tick delayed hidden routing, zero state between images.
- Four software paths: independent dense signed integer oracle,
  integer-forward PyTorch model, independent packed-word replay,
  accepted `LogicalChip`. **Five images × 26 ticks each EXACT**.
- User-supplied `P06_A4_PARITY.status`: `ALL_TRACES_EXACTLY_EQUAL`.
- `P06_A4_OFFICIAL_TEST_STATUS=SEALED` and
  `P06_A4_FPGA_STATUS=NO_PHYSICAL_RUN_NO_DDR_PAGE_IMAGE`.

Byte hashes of all six packed streams reported by the user are pinned
in `P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json` and checked byte-for-byte
by the new `p06_a4_freeze.py` audit. The key P03 synapse stream is
203,264 bytes, SHA256
`d83b4e401cae33f92a2cba7c53f2f681453f88395b65d503c2c590f6c60e31d7`.

The authentic project-trained checkpoint is pinned to file SHA256
`0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88`
and quantized integer tensor SHA256
`1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`.

**Validation:** 50k train-derived training images and 10k held-out
validation images, best epoch 8/8, reported train 95.34%, validation
**94.39%**; exceeds predeclared 60% validation GO floor; validation
all-silent only 2/10k. These are NOT official test-set or KV260
accuracy claims.

The accepted source-level freeze also includes
`P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md` and
`P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`.

## Final P06-A4.2 static DDR context utility

`src/loihi_twin_v2/p06_a4_freeze.py` and
`scripts/p06_a4_freeze.py` now:

1. Verify exactly the six user-reported P03 packed-file lengths and
   SHA256 hashes, snapshot source/validation/encoder/packet metadata,
   and five full 26-tick trace JSON records/trace SHA256.
2. Reload the accepted `.pt` weights and compare exact signed integer
   hashes, source split and compiler/network fingerprints.
3. Use **existing P02.1** `build_initial_ddr_context_record` to
   build a complete 524,288-byte `LTV3CTX1` core-0 record;
   parse its header and embedded payload digest; compare dense and
   sparse P03 banks word-for-word, and require empty mutable
   event0/event1/trace/packet banks.
4. Record the resulting full-byte SHA256 in the generated
   `p06_a4_static_ddr_freeze_manifest.json`.
5. Refuse overwriting any pre-existing freeze directory.

**Updated user evidence 2026-10-17:** After the A4.2 command was supplied,
the user stated **"nice, the DDR validation passed"** and instructed
P06-A4 closure and merge. Record this as **user-attested native PASS**
for A4.2, without inventing a test count or printed marker. The explicit
full-file SHA256 and stdout were not pasted. The existing local record
must be preserved and its digest captured before P07 deployment.

## Accepted final A4.2 native gate — reproduction and SHA capture

After the authorized merge to `main`, from user's VS Code terminal:

```bash
cd ~/Git/Thesis
git fetch origin
git switch main
git pull --ff-only origin main
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
set -o pipefail

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_a4_freeze.py \
  tests/test_p06_a4_snapshot.py \
  2>&1 | tee /tmp/v3_p06_a4_closeout_native.log

PYTHONPATH="$PWD/src" python scripts/p06_a4_freeze.py \
  --candidate-dir artifacts/p06_a3_candidate_seed20261013 \
  --snapshot-dir artifacts/p06_a4_trained_word_snapshot_seed20261013 \
  --output-dir artifacts/p06_a4_static_ddr_seed20261013 \
  2>&1 | tee /tmp/v3_p06_a4_final_ddr_freeze.log
```

The user now confirms this A4.2 gate passed; these commands are retained
for reproduction **in a fresh output directory** only. **Do not rerun
the generator using an existing output directory: it intentionally
refuses to overwrite.** To capture the digest of the already generated
file without modifying it, run:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
sha256sum artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin
python -m json.tool artifacts/p06_a4_static_ddr_seed20261013/p06_a4_static_ddr_freeze_manifest.json
```

Expected original generation markers: `P06_A4_STATIC_DDR_FREEZE_PASS=1`,
`P06_A4_OFFICIAL_TEST_STATUS=SEALED`,
`P06_A4_P07_A53_INPUT_STREAMING=NOT_IMPLEMENTED`.
The current source manifest deliberately stores `sha256: null` until the
user provides the actual recorded digest. This is **artifact provenance
follow-up**, not an unaccepted computational milestone. Do not retrain,
change frozen model arithmetic or access official MNIST test data.

**Do not replace this with a P05 diagnostic core table/header**:
that old P05 ABI's external-input restrictions do not support
all 784 MNIST input axons. The static P02 record is a memory backing
artifact, not a runnable A53/PL MNIST application.

## P07-A objective after P06-A4 completion

In a NEW development branch from the merged `main`, design and test
a **versioned, many-axon A53 FPGA inference ABI** to consume the frozen
core0 512KiB record, encode 784 pixel input channels into events for
t=0..24, process t=25 drain, maintain NEXT-bank barrier semantics, reset
between frames, retrieve ten output counts, and match the frozen four-
path oracle on synthetic and selected validation frames. Only after
the board first-mismatch gate and frozen official test protocol are
accepted should the sealed test archive be accessed.
No physical P07 test, benchmark accuracy, power or latency data yet.
