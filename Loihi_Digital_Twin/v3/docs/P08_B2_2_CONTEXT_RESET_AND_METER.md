# P08-B2.2 — Authenticated original 27-core reset and A53 service-meter source

**Candidate status (2026-11-01): native PC-only reset/timer, genuine host acceptance requires operator validation.** This adds fresh P08 modules; the accepted P07-B firmware, bitstream/XSA, B2.4 frozen 33 assets, original P08-A measurements, and root `LitReview.md` remain unchanged. The user reported genuine B2.1 1,024-frame ingress staging successful with evidence directory `/home/dna/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z` and file hashes **raw `739006f03b37c36d7aa11b6b68612338fc5249c7f48b9d854520ee7e3ea9c06e`, SHA list `5f21aa4e64f31918272b4d7ef84830bc309c6c205744f6735cec4bc69a1a719e`, manifest `996d48b1d4e83ec2433d445a4be37cff8ef50b599d07db23c165f1be10337e6e`**. These hashes are an operator report, not cloud-side physical or local-file readback.

## What is implemented

1. **Portable C11 authenticated 27×512KiB reset primitive:** `software/p08/p08_b2_context_reset.{h,c}`. All 27 original immutable backup SHA256s are bound against a trusted `original_sha256[27][32]` array and original P02 v1 headers in core ID order. A fresh image reset requires positive quiescence, re-hashes **all 27 original backup records before the first destructive write**, copies all 27 512KiB records to the original backing DDR range, cache-cleans/barriers/invalidates each destination, and verifies each complete original SHA256. One IO/hash/check error permanently poisons the session and blocks any retry; the receipt gives reset generation, 27 source/destination verifications, and exact 14,155,776 byte transfer. The module never calls MMIO or starts P03. Software reset of the accepted `p07_b3_pager` alone is **insufficient**. The future A53 app MUST also ensure P03 quiescence, rebind software metadata, rebuild P03 runtime/pager/scheduler/trace and reload all three PL slots from freshly restored P02 backing before every image. This reset primitive does not itself clear PL slots.
2. **Portable C11 A53 timer:** `software/p08/p08_b2_service_meter.{h,c}`. Seven contiguous monotone service timestamps `t0..t6` (entry; after 27-core restore; after B1.3 ingress; after scheduler re-init; after all 26 ticks; after accepted output receipt check; after journal commit) with exactly six nonoverlapping stage durations and **one full end-to-end time** `t6-t0` in raw A53 CNTVCT ticks. The firmware must read actual per-session CNTFRQ_EL0 (the accepted A deployments saw ≈99,999,001 Hz, *not* PL frequency). The 26-tick interval **includes physical page-ins/outs/702 dispatches/trace readback/NEXT routing/barriers**. The accepted P07-B trace hook reads P03 traces **inside each dispatch**, so these phase windows must never claim independent zero-cost trace or pretrace dispatch time.
3. **New authentic reset SHA pins:** `scripts/p08_b2_2_prepare_reset_pins.py` reads and verifies original frozen 33-file P06-B2.4, ordered 27 P02 source files, frozen stage SHA and full pinned aggregate original SHA256 `3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e`. Writes a **NEW outside-checkout output directory** containing generated 27×32-byte C SHA table and a 27-row JSON manifest, while labeling backup physical readback and ELF as NOT RUN. No board.
4. **Native full-memory regression:** `tests/native/p08_b2_reset_native.c` allocates actual 27×512KiB source/destination buffers, binds all 27 SHA256s, restores two separate images, corrupts the destination between images and verifies byte-exact restoration, corrupts the **last** backup record and verifies fail-before-any-write, and injects cache-clean/quiescence failures to verify permanent poisoning. Also exercises 7 explicit monotone timestamp boundaries and fails on timer backward jump. `tests/test_p08_b2_2_reset.py` compiles and runs with strict C11 -Werror and checks independent header pins negative cases.

## IMPORTANT: not ready for online deployment

- **B2.1 independent C encoder all-1024 local parity still NOT SHOWN:** user ran host staging and sha256sum only. Run existing C gate from the B2.1 document before claiming local source parity accepted.
- **B2.2 firmware integration still pending:** no new P08 A53 `main`, standalone firmware ELF/linker map, actual CNTVCT reads, image journal, 1024 consecutive real PL inference runs or 26-per-tick detailed timestamps. Software modules and native mocks are NOT a KV260 runtime and cannot prove PL reset or correct hardware behavior.
- **Original 27 backup physically sourced/verified?** NO. The `[0x43000000,0x43D80000)` candidate is still **not independently owned**; it cannot be written or relied on without separate destructive/JTAG permission, physical readback and ELF overlap audit. The reset primitive presumes exclusive control of source and destination, which must be established independently. The 14MiB backup cannot be assumed to survive Linux, FSBL/TF-A or warm reboot.
- **Original frozen model TEST** remains sealed, original B A53 V3/B5 evidence is read-only, and Track A six accepted sessions untouched. **No online deployment or performance claim yet.**

## Next offline operator commands (no board access)

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
  tests/test_p08_b2_2_reset.py
PYTHONPATH="$PWD/src" python -m py_compile \
  scripts/p08_b2_stage_1024_ingress.py \
  scripts/p08_b2_2_prepare_reset_pins.py

# Pin actual original 27-core SHA256 from unchanged 33-file freeze.
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B2_RESET_PINS"
PYTHONPATH="$PWD/src" python scripts/p08_b2_2_prepare_reset_pins.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --out "$P08_B2_RESET_PINS"
sha256sum "$P08_B2_RESET_PINS/"*

# If B2.1's independent C parity was not yet run, do it now.
export P08_B4M_ROUTES="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P08_B2_STAGE="$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z"
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
```

Required exact B2.2 sources `P08_B2_2_FROZEN_27_RESET_PINS_PASS=1`, original aggregate SHA `3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e`, all native tests PASS and B2.1 independently encoded 1,024 frames PASS. This remains a **local source checkpoint**, not authorization for live JTAG.

## Next build phases

B2.3: separate P08 A53 image-only and detailed-tick apps that glue original P07-B true 26tick execution to the above reset + SHA-pin/ingress + CNTVCT + journal, per-image numerical hooks and selected trace; strict new Vitis build and bounded DDR/ELF admission, new physical runner **NOT YET AUTHORIZED**. B3: approved 16-image pilot, numerical oracle before accepting any timing; B4: three paired runs each A/B mode for 1024-image full service, 1023 ordinary measurements. No P09 until physical acceptance.
