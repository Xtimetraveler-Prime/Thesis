# P08-B2.3 — New image-only 1,024-image original-B2.4 A53 source + offline Vitis build

**2026-11-01 source candidate, Vitis build/user local validation pending.** This is the **first brand-new scaled A53 application source** for P08-B, not a modified P07-B V3/B5 ELF. The original P03.2 routed XSA, 27 logical original B2.4 contexts/three slots/26 ticks, original P07 B4m C11 engine, and original official MNIST TEST seal are unchanged.

## B2.1 C encoder root-cause remediation

The operator B2.1 genuine Track B input staging PASSED and B2.2 original 27-core SHA pins PASSED; later the independent native-C `--verify` **failed** `P08_B2_NATIVE_ORIGINAL_896K_ROUTE_SHA_NO_GO`. Source audit identified a hand-transcribed SHA256 literal in `software/p08/p08_b2_ingress.c`: the final 16 bytes were wrong. Replaced with the **previously accepted Python original 896KiB SHA** `380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8`. No original data, B2.4 model, P07 files, B2.1 stage, A3.2 stage or signed routes were changed. Added native exact C SHA pin equality to Python frozen source and full 1,024-frame C-vs-Python positive/negative fixture tests. Genuine local C parity **MUST BE RERUN** before trusting A53 ingress.

## New A53 architecture candidate

The distinct new `software/p08/p08_b2_3_image_only_a53.c`:
- Accepts PS FPD128 width, exact original SHA-pinned **802,816-byte** Track A first1024 raw pixel pool `[0x42100000,0x421C4000)`, original frozen B4M 896KiB route image, original 16KiB axon binding/80KiB route data, and genuine independently verified original 27-core SHA-pinned backup `[0x43000000,0x43D80000)`. It uses the generated B2.2 27×SHA256 C header staged from the original 33 frozen assets, not a substitute model.
- **Per image:** true CNTVCT service entry; 27×512KiB authenticated original-context restore with poison-on-failure; generate correct original P06B13I1 123,216-byte ingress using the pinned B4MING01 table; completely initialize the original registered P03 adapter/metadata/binding, fresh pager, scheduler, source-spike trace, P03 packets and 27-core routes; call unmodified original `p07_b4m_full_run` to process all 702 actual dispatches, 26 true barriers and full original 1,010-neuron trace reads at their original nested hook; validate 27-context reset and output receipt; physically flush a 256-byte image journal **within** the service timer; capture CNTVCT t6 after commit; store a distinct 256-byte timing sidecar **after** the service timer. Full A53 service includes reset, ingress, HLS polling/trace, route and result commit.
- Journal: 1,024 × 256-byte independently addressable rows from `0x42200000`, with image index, reset generation, classification, all 10 readout counts, physical source-spike FNV, dispatched/page-transfer receipts, raw/encoded SHA256, CRC32 and terminal marker. Timer sidecar: separate 1,024 × 256-byte rows at `0x42300000`, raw CNTVCT entry/commit, observed CNTFRQ, six nested-aware contiguous phase durations, CRC32 and terminal marker. Dedicated **new** 256-byte mailbox `0x43FF0200` does not overwrite accepted B4m V3/B5 mailboxes. **No JTAG execution was attempted.**
- Actual hardware trace-hook reads happen inside each dispatch; no fake isolated PL time or unrealistically separable per-tick trace-free interval. This first variant is **image-only**. The later B detailed-tick version needs separate safe instrumentation, and full selected raw 26×1,010 trace at frame 1023 remains to be implemented and accepted.

## Offline build candidate

`software/p08/build_p08_b2_3_image_only.py` uses the existing accepted Vitis 2025.2 standalone A53 platform API, but imports a fresh and exact P08 C/H source set, fresh app identity, original P07 modules intact, the external user-generated SHA header, and emits a **new** genuine ELF and GNU linker map. `scripts/build_p08_b2_3_image_only.sh` refuses an existing or in-repository build directory, checks unchanged accepted P03 XSA `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f` and accepted PS/PL 128-bit routed metrics, checks *operator-reported actual* B2.2 SHA header `5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171` and manifest `1d915c36eaf42740bac9e62afae58ffe80c94ae51cbf6c6c809d3fd6e626ce34`, copies accepted frozen P07 source read-only into a fresh source stage and applies the accepted P07 B4m **10K output route capacity solely in the new source copy**.

`scripts/p08_b2_3_elf_admission.py` rejects non-AArch64 little-endian ELF64 ET_EXEC, missing/multiple entry/invalid PT_LOAD, segments whose physical/virtual ranges overlap `[0x40000000,0x44000000)`, wrong original XSA SHA, wrong accepted B2.2 SHA header, wrong new ELF identity or non-genuine linker map. Emits no-overwrite external JSON with explicit **boot/stack/heap/DMA DDR exclusivity unproven**, no physical permission. Native synthetic tests independently test ELF rejects and syntax-check the new standalone C application using declaration-only host headers (not Vitis emulation). `PT_LOAD` isolation alone is NOT sufficient for standalone PS safety.

### Operator offline verification (NO XSDB)

First refresh source and **rerun corrected actual C 1,024 parity**:

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
  tests/test_p08_b1_matched_source.py \
  tests/test_p08_b2_ingress.py \
  tests/test_p08_b2_2_reset.py \
  tests/test_p08_b2_3_image_only.py

export P08_B4M_ROUTES="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P08_B2_STAGE="$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P08_B2_C11_EXE="$HOME/Thesis_Evidence/p08_b2_ingress_native_fixed_$(date -u +%Y%m%dT%H%M%SZ)"
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
```

Require `P08_B2_NATIVE_ENCODED_FRAMES_EXACT=1024` plus `P08_B2_NATIVE_SOURCE_AUTHENTICATED=1`. If it fails again, STOP: do not build or deploy.

To **build genuine new A53 image-only candidate in Vitis 2025.2**, source the same Vitis environment used for P07-B. Set `P07_B4L_REPORTS` to the existing accepted P03 routed report folder that contains `p03_2_ps_mmio.xsa` and `p03_2_post_route_metrics.txt`; do not create or regenerate the accepted routed XSA.

```bash
# In v3, with Vitis 2025.2 tools in PATH and exact accepted P03 report folder:
# export P07_B4L_REPORTS="/actual/accepted/p03/routed/reports"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P08_B23_BUILD_DIR="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B23_BUILD_DIR"
bash scripts/build_p08_b2_3_image_only.sh
```

Expected on successful real Vitis platform + app + readelf/map audit:
`P08_B2_3_NEW_IMAGE_ONLY_A53_ELF_AND_MAP_BUILT=1`,
`P08_B2_3_NEW_A53_GENUINE_LOW_DDR_PT_LOAD_OFFLINE_PASS=1`,
`P08_B2_3_PHYSICAL_KV260_RUN=NOT_RUN`,
`P08_B2_3_OPERATOR_NEW_DESTRUCTIVE_JTAG_PERMISSION=NOT_GRANTED`.
Provide `$P08_B23_BUILD_DIR/vitis_build.log` failure excerpt if Vitis reports genuine compile errors and the new build folder / ELF / map / PT_LOAD report SHA on success. No board contact.

## Not done (hard B3 pilot blocks)

No physical backup source/readback at `[0x43000000,0x43D80000)`; no new approved DDR ownership including FSBL, TF-A, Linux, A53 linker stack, RPU/PL DMA, shell unknown boot state; no 1024 host B scalar oracle reference or byte-verified actual B numerical parity; no selected 1023 original full raw trace capture; no detailed per-tick instrumented distinct ELF; no sidecar physical parser/CRC acceptance; no new explicit destructive JTAG operator approval. **Do not start XSDB.** When exact new ELF & map are available, next work is new approved JTAG cold-boot staging, signed actual original 27-context backup/raw pool/JTAG readback and short numerical pilot **only with operator's specific session authorization**. The accepted original P07-B hardware proof and Track A numbers are frozen; official TEST remains sealed; P09 deferred.
