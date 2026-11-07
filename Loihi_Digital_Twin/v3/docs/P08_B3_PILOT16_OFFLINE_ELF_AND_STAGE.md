# P08-B3.0 — Separate original B2.4 first16 pilot A53 ELF, offline original DDR staging

**Source development dated 2026-11-01; no KV260 hardware access.** After operator P08-B2.4 original scalar first16 PASS, the SHA-pinned **new** first16 numerical reference is `13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271`, external `/home/dna/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json`. Frozen original first3 original B2.3 signed witnesses reproduced. Physical parity, physical DDR ownership and hardware execution still unproven.

## Dedicated pilot firmware (NOT the 1024 image ELF)

New distinct `software/p08/p08_b3_pilot16_a53.c` is a bounded **16-image** source using the same original P07-B 27-core B2.4 P03 engine, 3 physical slots, 26 ticks, 702 hardware dispatches, trace hook, and per-image original 27x512KiB SHA reset and restore, original B1.3 ingress and same 256B journal/timing/mailbox ABI. Identifies itself as `P08_B3_ORIGINAL_27CORE_FIRST16_PILOT_A53_V1` and `P08_B3_PILOT16_TERMINAL_DONE=1`; **never** prints the old 1024-frame terminal receipt. Critical: it **still authenticates all 802,816 raw bytes for the original 1,024 matched held-out TRAIN source**, despite executing only ordinals 0..15. The per-image 16-ordinal sources therefore cannot change between original Track A and B pilot. No source here is user-accepted physical firmware until the genuine new ELF is separately built and examined.

New `software/p08/build_p08_b3_pilot16.py` creates an isolated Vitis 2025.2 standalone A53 component `p08_b3_original_pilot16` with a distinct generated ELF/map, with the original P07 modules, original B2.2 frozen 27core SHA header, and exact 10k source packet bindings set *only on newly copied build-stage source*. The prior P08-B2.3 1024-frame source/ELF/map are untouched. `scripts/build_p08_b3_pilot16.sh` is **host-only**, checks accepted P03 XSA and routed FPD128 width metadata, checks the original B2.2 SHA header+manifest, creates a NEW out-of-repo Vitis workspace, links exactly one new original B2.4 pilot ELF, emits program-header analysis and hashes, and runs new ELF+oracle admission. **No XSDB, Vivado programming, JTAG launch, DDR write or board contact.**

`scripts/p08_b3_pilot16_admission.py` requires a **real separately identified** first16 pilot ELF, separate map, correct original signed XSA `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`, original B2.2 27-per-core SHA header `5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171` and the actual operator first16 scalar oracle file SHA `13e3e679...`. Rejects any original P08-B2.3 1024-ELF or 1024 terminal marker, any missing pilot marker, wrong ELF64 AArch64 EXEC/PT_LOAD, overlap with planned 64MiB DDR, and missing linked numeric/reset/ingress/timer symbols in map. Emits an external no-overwrite JSON; these are **static necessary conditions, NOT physical ownership proof**.

## Independent, no-overwrite immutable source package for physical transfer (PC ONLY)

New `scripts/p08_b3_pilot16_stage_host.py` independently re-checks the *original frozen 33-file B2.4 source*, re-generates exactly 27 original P02 records bytewise, re-generates the original frozen B4l 16KiB core/axon binding descriptor, admits original B4M 896KiB input and 80KiB output routes and unchanged matched first1024 raw data + exact 1024-frame wire SHA ledger; requires genuine operator 16 scalar report hash. Creates **five ordinary files** in a NEW external immutable-reference directory, with six **PROPOSED ONLY** physical transfers (original 27-core bundle staged twice in two independent regions). Original existing model and stage files are read only; no JTAG or board actions:

| File | Proposed DDR start | End exclusive | Pinned original SHA256 |
| --- | --- | --- | --- |
| Original 27×512KiB P02 (mutable) | `0x40000000` | `0x40D80000` | `3733e1c2…f64e` |
| Original B4M input routes 896KiB | `0x41000000` | `0x410E0000` | `380268c5…74e8` |
| Matched 1024 raw uint8 pool 802,816B | `0x42100000` | `0x421C4000` | `739006f0…c06e` |
| Original B4l 16KiB axon binding | `0x43FC0000` | `0x43FC4000` | `2f0a5299…11eb` |
| Original B4M 80KiB output routes | `0x43FC4000` | `0x43FD8000` | `24052691…3103` |
| **Second** original 27×512KiB P02 **immutable backup** | `0x43000000` | `0x43D80000` | **same original 27-core bundle SHA** |

These are candidate addresses from accepted B2.1 static non-overlap analysis. In particular **they are NOT reserved against PS Linux, FSBL/TF-A, U-Boot, existing kernel/CMA, another DMA master, A53 runtime memory, PMU, firmware or any active PL engines**. A new destructive cold-boot JTAG takeover must obtain operator approval with explicit reboot recovery and independent same-session verification of both 27core regions before any pilot ELF download. The package is NOT a JTAG transfer program and contains NO permission to proceed.

## Operator-local offline checks and build

Pull branch then run full P08 tests including new pilot:

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
 tests/test_p08_b2_3_image_only.py \
 tests/test_p08_b2_4_numerical.py \
 tests/test_p08_b3_pilot16.py

export P08_B2_4_SCALAR_REPORT="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"
sha256sum "$P08_B2_4_SCALAR_REPORT" # require 13e3e6791100...06d3b271

export P08_B3_PILOT_STAGE="$HOME/Thesis_Evidence/p08_b3_pilot16_pc_stage_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B3_PILOT_STAGE"
PYTHONPATH="$PWD/src" python scripts/p08_b3_pilot16_stage_host.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --routes-dir "$HOME/p07_b4m_frozen_inputs_20261023T034626Z" \
  --ingress-dir "$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z" \
  --oracle "$P08_B2_4_SCALAR_REPORT" \
  --out "$P08_B3_PILOT_STAGE"
sha256sum "$P08_B3_PILOT_STAGE/"*
```

Expected `P08_B3_PILOT16_PC_ONLY_ORIGINAL_DDR_STAGE_PASS=1`, `P08_B3_PILOT16_STAGE_FILES=5`, `P08_B3_PILOT16_PROPOSED_WRITES=6`, `P08_B3_PILOT16_PHYSICAL_JTAG_BYTES_WRITTEN=0` and `P08_B3_PILOT16_PHYSICAL_DDR_OWNER_PROVEN=0`.

**Separately build genuine pilot Vitis ELF** (2025.2 loaded, existing verified original P03 routed reports folder `P07_B4L_REPORTS` set as with your already successful B2.3 build):

```bash
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P08_B3_PILOT16_BUILD_DIR="$HOME/Thesis_Evidence/p08_b3_pilot16_build_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B3_PILOT16_BUILD_DIR"
bash scripts/build_p08_b3_pilot16.sh
```

Expected `P08_B3_PILOT16_REAL_A53_ELF_AND_ORACLE_OFFLINE_PASS=1`, `P08_B3_NEW_PILOT16_A53_ELF_AND_MAP_BUILT=1`, `P08_B3_PILOT16_DDR_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0`, `P08_B3_PILOT16_JTAG_AUTHORIZED=0`. Save generated separate pilot ELF, linker map, fresh SHA list and external admission JSON; **do not download to KV260**. If Vitis fails, report compile trace; modify only new P08 pilot source/build stage on this unmerged branch.

## Still mandatory before physical approval

1. Independent physical DDR owner proof / new QSPI/boot/RPU/PL DMA hazard review. P08-B2.3 `PT_LOAD` non-overlap and this P08-B3 new ELF check do **not** prove A53 stack, heap, exception vectors, bootloader/kernel, SDRAM content, or standalone firmware coexistence safety.
2. New independent same-session JTAG 6-source-transfer receipt, both original 27-core region readbacks, independently verified same-session binding+routes+raw SHA256 readbacks, and signed pilot ELF/map/download/terminal journal/timing/mailbox. Reboot is mandatory after destructive attempt. Physical script NOT PROVIDED yet; no operator approval.
3. Same-session 16-image hardware journal/sidecar and (separate) raw 26×1010 neural trace parity with original scalar oracle. The P08-B2.4 untrusted file verifier is NOT a physical authenticity verifier; don't confuse results. No accepted pilot latency until independent 16-image numeric equality.
4. Only then start original full 1,024 matched B physical cold-boot sessions, detailed-tick variant, selected original full frame1023 trace and paired Track A comparison. **P09 and original B2.4 official MNIST TEST remain deferred/sealed.**

Accepted original P07-B V3/B5 ELF+proof, P03 bitstream/XSA, original frozen 33 B2.4 assets, P08-A six sessions, root `LitReview.md` remain unchanged. Draft PR #52 remains unmerged pending explicit user approval.
