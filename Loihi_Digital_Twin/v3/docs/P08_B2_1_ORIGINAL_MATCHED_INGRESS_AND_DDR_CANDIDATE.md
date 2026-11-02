# P08-B2.1 — Source-authenticated 1,024-image B2.4 ingress and DDR candidate

**Status: new PC-only implementation, operator validation pending, no new A53 ELF or physical KV260 run.** This milestone follows the accepted P08-B1 genuine stage report: `P08_B1_MATCHED_DATASET_OFFLINE_PASS=1`, `P08_B1_B_TRAIN_MEMBERSHIP_OVERLAP=0`, `P08_B1_1024_RAW_PIXEL_IDENTITIES=PASS`, and `P08_B1_PHYSICAL_KV260_RUN=NOT_RUN` in operator output saved as `/home/dna/Thesis_Evidence/p08_b1_matched_source_20261102T002231Z.json`. The assistant has not opened that local JSON and does not claim to have reverified its contents independently.

## B2.1 actual implementation

- `scripts/p08_b2_stage_1024_ingress.py` **re-runs** original B1 frozen-33-asset/dataset/ledger admission. It reads the historical accepted original B4m 896KiB input routes (SHA256 `380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8`), verifies B4MING01 header and exact route-table bytes against the actual B2.4 compiled `packed_deployment.json`, checks original A 1024 raw pixel concatenation and computes every B2.4 P06B13I1 frame SHA in same original frame order. For control ordinals **0,1,2,15,1023**, independently compares to the original `encode_ingress_frame`/decoder. It does not silently reuse A's 784→axon ingress wire.
- New **no-overwrite external** stage contains `p08_b2_original_track_a_raw1024_uint8.bin` (**802,816B**), `p08_b2_original_27core_1024_ingress_sha256_lines.txt` (1024 lines of 64-hex SHA256) and a JSON with original labels, source indices, both raw/encoded SHA per image, accepted route and stage SHA provenance, selected trace index 1023 and explicitly `KV260_physical_latency=NOT_RUN`. Produces no 126MB redundant frame directory and reads neither official TEST nor new training images.
- `software/p08/p08_b2_ingress.c/.h` is a **distinct portable real C11 original-route ingress builder** intended for a future B2 instrumented A53 application. Its `p08_b2_admit_routes` validates the entire original 896KiB signed route image SHA256 and exact B4MING01 header before binding routes. `p08_b2_encode_frame` constructs exactly **123,216B** original P06B13I1 wire with correct full payload/header CRC32, SHA and 25+1 tick fields. It is not an A53 executable and never starts the FPGA. The route image is caller-owned and must remain immutable across the run.
- `tests/native/p08_b2_ingress_native.c` is a **strict C11 executable verifier**: reject unauthenticated source route images in CI, or verify **all 1,024 C-encoded frames against independently computed Python original-B ingress SHA references** on the operator's existing real dataset/route files. No hardware access.
- `tests/test_p08_b2_ingress.py` covers deterministic framing parity, corrupted inputs, immutable route rejection, C11 strict native compilation and bounded static DDR regions. GitHub Actions is native/synthetic only; the genuine local 1,024-frame C parity gate needs operator's original route files.

## DDR candidate (NOT physical address admission)

All ranges are **half-open PS physical DDR addresses** within original P03 `[0x40000000,0x44000000)`. P08-B2.1 offline static non-overlap calculation includes: original 27 mutated core records `[0x40000000,0x40D80000)`, input route table `[0x41000000,0x410E0000)`, single B ingress buffer `[0x41100000,0x411E0000)`, original accepted B5 raw-trace area `[0x42000000,0x420CD280)` reserved to avoid, **new 802,816B raw-pool `[0x42100000,0x421C4000)`**, future neural journal `[0x42200000,0x42300000)`, image sidecar `[0x42300000,0x42400000)`, detailed ticks `[0x42400000,0x42800000)`, optional selected 840,320B raw trace `[0x42800000,0x428CD280)`, proposed **immutable original 27×512KiB backup `[0x43000000,0x43D80000)`**, original 16KiB/80KiB binding/route tables, historic V3/B5 mailboxes, proposed new B2 mailbox `[0x43FF0200,0x43FF0300)`. Exact range map is emitted in the generated JSON.

**CRITICAL:** The 27-core backup is **only a planned buffer**; preserving, SHA/readback-verifying, copying and reinitializing all 27 actual backing records at image-service start must be implemented/tested in B2.2. Old `p07_b3_init` does **not** restore neuron state. All addresses are static proposals: no Vitis `PT_LOAD`/stack/heap analysis and **no independent FSBL/TF-A/U-Boot/Linux/RPU/DMA DDR ownership**. B2.1 is not evidence of physical exclusivity. Image service must include per-image context restore, the original per-image B1.3 source encode, all 26 tick/702 dispatches, all 27-core trace reads/routes/26 barriers and final result commit. Detailed seven-boundary A2.2 timing needs a careful B-aware nested-trace policy because the accepted B trace hook fires *inside* the dispatch step; do not publish false separate dispatch/trace time.

**NOT DONE:** new signed instrumented B2 A53 ELF, genuine map/load/stack checks, XSDB runner or real 16-image pilot, clocked B sidecars, per-frame frozen monolithic 1,024 oracle, numerical full-trace capture, accepted P08-B physical timing. Original official MNIST TEST remains `SEALED_NOT_ACCESSED`. Power/energy remains deferred.

## Local operator source and native B2.1 gate — no JTAG

Use the pre-existing original B4m route stage `/home/dna/p07_b4m_frozen_inputs_20261023T034626Z` and original A first1024 source-stage. Do not edit, regenerate, or move those originals.

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p08-b-scaled-latency
git pull --ff-only origin agent/v3-p08-b-scaled-latency
git status --short
git rev-parse HEAD
git rev-parse 'HEAD:LitReview.md'
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b1_matched_source.py tests/test_p08_b2_ingress.py
PYTHONPATH="$PWD/src" python -m py_compile scripts/p08_b2_stage_1024_ingress.py

export P08_B1_STAGE="$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z"
export P08_B4M_ROUTES="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P08_B2_STAGE="$HOME/Thesis_Evidence/p08_b2_1_original1024_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B2_STAGE"
PYTHONPATH="$PWD/src" python scripts/p08_b2_stage_1024_ingress.py \
  --stage-dir "$P08_B1_STAGE" \
  --train-data-dir "$PWD/data/mnist_raw" \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --routes-dir "$P08_B4M_ROUTES" \
  --out "$P08_B2_STAGE"

export P08_B2_C11_EXE="$HOME/Thesis_Evidence/p08_b2_ingress_native_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B2_C11_EXE"
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
  -I software/p08 -I software/p07/include \
  software/p08/p08_b2_ingress.c \
  software/p07/p07_a2_sha256.c \
  tests/native/p08_b2_ingress_native.c \
  -o "$P08_B2_C11_EXE"
"$P08_B2_C11_EXE" --reject-zeros
"$P08_B2_C11_EXE" --verify \
  "$P08_B4M_ROUTES/p07_b4m_original_input_routes_896k.bin" \
  "$P08_B2_STAGE/p08_b2_original_track_a_raw1024_uint8.bin" \
  "$P08_B2_STAGE/p08_b2_original_27core_1024_ingress_sha256_lines.txt"

sha256sum "$P08_B2_STAGE/"*
```

Require `P08_B2_ORIGINAL_27CORE_1024_INGRESS_HOST_STAGE_PASS=1`, `P08_B2_NATIVE_SOURCE_AUTHENTICATED=1`, `P08_B2_NATIVE_ENCODED_FRAMES_EXACT=1024` and `P08_B2_HARDWARE_EXECUTED=0`. Share the full log and new report path before any further board build/proposed destructive 16-frame pilot.

## Next exact implementation work

**B2.2:** a brand-new timed A53 application, static 27-core context restore with readback and original-image backing, one-frame RAM/buffer input generation using the authenticated original route image; per-image strictly journaled full-service interval, per-tick B-aware phases with source/trace nested evidence, reliable full 1,024 loop and selected trace; native real C11 positive 2-image reset/nonce tests. **B2.3:** independently generated 1,024-frame B2.4 original scalar oracle receipts, CRC/overflow parsers and read-only source/ELF/map admission, then new Vitis 2025.2 ELF/map build. **B3:** only after independent offline gates and separate operator physical authorization, dedicated JTAG-only first16 original-order pilot, fresh cold boot before/after, exact numerical oracle before latency accepted.

No B2.1 source CI or local PC admission constitutes operator consent to run XSDB.
