# P07-B.5.3 — Exact physical neuron-trace capture: new firmware candidate

**Status (2026-11-01): IN DEVELOPMENT. B5.3.1 native bounded 840320B
C recorder, B5.3.2 isolated raw-bank7 integration, separate A53 main,
Vitis source/build path, strict PC-only ELF/XSA/source admission,
standalone hook and firmware syntax tests IMPLEMENTED / native CI PASS.
A genuine operator-built new Vitis B5 ELF/map has NOT been admitted yet.
Real sidecar+mailbox DDR ownership, distinct B5 physical JTAG launcher,
board readback, and raw physical byte-for-byte parity are NOT VERIFIED
OR AUTHORIZED.** P07-B.5 final
milestone remains OPEN, P07-B.6 and P08-B remain gated, and original
official MNIST TEST remains sealed.

## B5.3.2 operator Vitis build / first offline admission NO-GO (2026-11-01)

The operator's first independent Vitis 2025.2 build of
`P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1` **compiled and linked
successfully**, generating an actual ELF and GNU linker map in
`/home/dna/p07_b5_raw_trace_build_20261101T202750Z`.
The build deliberately printed
`P07_B5_RAW_REAL_BOARD_RUN_AUTHORIZED=0`,
`P07_B5_RAW_SIDECAR_DDR_OWNERSHIP_INDEPENDENTLY_PROVEN=0`, and
`P07_B5_RAW_LOW_DDR_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0`.

The strict PC-only offline check **correctly rejected** that first
genuine ELF with:
`P07_B5_NEW_RAW_OFFLINE_NO_GO=NO-GO: experimental B5 ELF polluted by original firmware identity`.

**Root cause CONFIRMED IN SOURCE:** The newly forked B5 A53 main
contained the correct distinct `elf_identity[]`, but its terminal
`xil_printf()` string still emitted
`P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3`. Consequently the old V3
runtime identity was *really present in the new ELF*. The offline
identity gate was behaving properly; the source was wrong.

**Fix:** Changed only `software/p07/p07_b5_full_board_raw_trace_v1.c`
diagnostic status format to
`P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1`.
Retained the strict binary scan in
`scripts/p07_b5_raw_trace_offline_admission.py` and improved its
diagnostic to name an offending old firmware token. Hardened
`scripts/build_p07_b5_raw_trace.sh` with *pre-build new C main
source* and *post-link ELF* legacy-identity NO-GO checks and native
negative regression tests in `tests/test_p07_b5_raw_trace_offline_admission.py`
and `tests/test_p07_b5_trace_integration.py`.

**Disposition:** Preserve the operator's old build directory, ELF/map
hash and failure result as historical diagnosis, **NOT accepted B5
physical firmware**. The operator must perform a NEW independent Vitis
build at a NEW external absolute directory using the corrected
committed source; the old artifact must not be patched, overwritten,
reused or programmed. Only run the separate PC-only offline source/ELF
admission after new real Vitis build succeeds. Source fixes, native
tests and genuine compiler success do not prove new B5 DDR ownership,
physical trace parity, or final P07-B.5 completion.

## B5.3.3 genuine separate Vitis A53 admission ACCEPTED; original-run physical capture tooling implemented PC-only

The operator's genuine separately rebuilt Vitis 2025.2 B5 RAW A53
ELF and GNU linker map now pass exact source/original B2.4/P03 route
and frozen 27core/XSA PC admission, after the earlier rejected stale
V3 diagnostic-print fix.

- Build directory: `/home/dna/p07_b5_raw_trace_build_20261101T204014Z`
- Source/ELF admission report:
  `/home/dna/Thesis_Evidence/p07_b5_raw_elf_offline_20261101T204303Z.json`
- Genuine B5 ELF SHA256:
  `0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf`
- Genuine GNU map SHA256:
  `1e6cf5d0a9744378fb0aebe2e6271da661b8739a2fb930e983342477fd0e78c8`
- Accepted original P03 XSA SHA256:
  `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`
- Actual new A53 LOAD `[0x00000000,0x00107BC0)`,
  **1,080,256 bytes**, **different from original V3**.
- New trace candidate `[0x42000000,0x420CD280)`,
  **840,320 bytes**; new B5 mailbox
  `[0x43FF0100,0x43FF0200)`, **256 bytes**.
- The original TRAIN source remains sealed from official MNIST TEST,
  with 27 immutable records, 20,384 input routes, 1,000 output routes.
- The accepted new Vitis report explicitly says
  `P07_B5_GENUINE_RAW_CAPTURE_VITIS_SOURCE_ELF_OFFLINE_PREFLIGHT_PASS=1`,
  `P07_B5_SIDE_CAR_PHYSICAL_DDR_OWNERSHIP_PROVEN=0`,
  `P07_B5_REAL_PHYSICAL_LAUNCH_AUTHORIZED=0`,
  `P07_B5_BOARD_ACCESSED=0`,
  `P07_B5_B5_3_RAW_FPGA_TRACE_VERIFIED=0`.

The [operator evidence ledger](P07_B5_3_2026_11_01_REAL_VITIS_RAW_ELF_PC_ADMISSION.json)
preserves this exact new SHA-pinned ELF/map and the explicit
unproven physical DDR/firmware claims. This PC gate **does not**
mean physical model or raw capture was executed.

**B5.3.3 dedicated physical infrastructure now under test:**

1. `vivado/p07_b5_raw_trace_xsdb_run.tcl` is **not V3**:
   requires a different launch token, the operator-admitted
   exact new B5 ELF SHA, 256B independently readback-zeroed new
   mailbox, a real B5 terminal success/finished/26,260-record
   receipt, CPU halt, then segmented actual PSU physical
   readback of exactly 210,080 uint32 words (840,320 bytes).
   Every failed/partial attempt preserves a NO-GO and REBOOT warning.
2. `scripts/p07_b5_raw_physical_capture.py` defaults to
   `--mode preflight`, **read-only PC and no physical contact**.
   It reopens the genuine signed original frozen graph and real
   ELF/map, revalidates the operator offline report, original
   P02 source metadata, original B4l descriptor and original
   B4i shell, accepted XSA, all original TRAIN frames/routes.
   Real board `--mode execute` requires the 8 original session
   approvals plus **5 distinct new approvals** for B5 raw
   firmware, revised 1,080,256-byte low DDR span, unproven
   boot-firmware overlap risk, separately reserved 840,320-byte
   trace sidecar writes and B5 mailbox writes. It requires a
   fresh external evidence directory and independently staged
   and SHA-readback-verified original 27 DDR records / descriptors /
   both routing tables and original TRAIN input in the SAME
   dedicated XSDB session BEFORE new A53 download.
3. `scripts/p07_b5_raw_physical_verify.py` **PC-only**
   refuses unproven or synthetic evidence, regenerates the
   frozen TRAIN scalar reference, validates real XSDB log,
   original model/staging/readback SHA, exact distinct B5
   terminal 256B mailbox, all 27×26 dispatch counters,
   26,260 per-neuron 32B trace records, and per-tick / 26-tick
   FNV64, then determines first original tick/core/comp/neuron
   mismatch or exact *all-byte physical-vs-scalar equality*.
   A passing authentic full raw audit can demonstrate real
   direct per-neuron equality; it still does NOT imply boot
   firmware DDR ownership was independently proven, reboot
   attested, or P07-B.5 final acceptance.
4. `tests/test_p07_b5_raw_physical_safety.py` proves
   **host-only** B5 mailbox geometry, rejects legacy V3
   mailbox, missing/duplicate/corrupted raw receipts, 13
   explicit approvals, missing actual same-session original
   physical stage and disallows board contact during PC preflight.
   The full existing B4m/B5 CI suite is retained.

**Operator action NOW (PC ONLY, DO NOT RUN BOARD EXECUTE):**

```bash
cd ~/Git/Thesis
git switch agent/v3-p07-b5-scaled-multiframe-validation
git pull --ff-only origin agent/v3-p07-b5-scaled-multiframe-validation
source ~/Git/Thesis/.venv-p08/bin/activate
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b5_raw_capture_native.py \
  tests/test_p07_b5_trace_integration.py \
  tests/test_p07_b5_raw_trace_offline_admission.py \
  tests/test_p07_b5_raw_firmware_c_syntax.py \
  tests/test_p07_b5_raw_physical_safety.py

export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4L1_STAGE="$HOME/Thesis_Evidence/p07_b4l1_original27_20261022T204013Z"
export P07_B4L_BINDINGS="$HOME/Thesis_Evidence/p07_b4l_b3_bindings_20261023T011829Z"
export P07_B4M_STAGE="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P07_B4I_BUILD_DIR="$HOME/p07_b4i_build_20261022T161058Z"
export P07_B5_RAW_BUILD_DIR="$HOME/p07_b5_raw_trace_build_20261101T204014Z"
export P07_B5_RAW_ELF="$P07_B5_RAW_BUILD_DIR/vitis_workspace/p07_b5_raw_trace_v1.elf"
export P07_B5_RAW_OFFLINE="$HOME/Thesis_Evidence/p07_b5_raw_elf_offline_20261101T204303Z.json"

PYTHONPATH="$PWD/src" python scripts/p07_b5_raw_physical_capture.py \
  --mode preflight \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --bindings-dir "$P07_B4L_BINDINGS" \
  --routes-dir "$P07_B4M_STAGE" \
  --offline-report "$P07_B5_RAW_OFFLINE" \
  --reports "$P07_B4L_REPORTS" \
  --b4i-build "$P07_B4I_BUILD_DIR" \
  --build-dir "$P07_B5_RAW_BUILD_DIR" \
  --elf "$P07_B5_RAW_ELF" \
  --validation-ordinal 0
```

Expected read-only status:
`P07_B5_NEW_RAW_GENUINE_A53_ELF_MAP_AND_ORIGINAL_TRAIN_HOST_PASS=1`,
`P07_B5_NEW_RAW_PC_ONLY_PREFLIGHT_PASS=1`,
`P07_B5_BOARD_CONTACT=0`,
`P07_B5_NEW_RAW_LAUNCH_AUTHORIZED_BY_PREFLIGHT=0`,
`P07_B5_NEW_RAW_840320B_DDR_OWNER_INDEPENDENTLY_PROVEN=0`.

**STOP after PC preflight.** No new physical B5 sidecar
run should be attempted until independently reviewing the
new trace mailbox DDR ownership and low-DDR firmware coexistence
risk, the dedicated XSDB launcher/reader semantics, and the
operator's distinct explicit approvals. The original previously
successful V3 physical runs, original accepted P03 shell,
V3 ELF and all original B2.4 frozen data remain untouched.
No merge of PRs #49 or #50 into `main` until the entire P07-B
work is accepted and the operator explicitly authorizes merge.

## B5.2 entry evidence / safe scope

The operator completed and independently reverified all four
**genuine physical** frozen TRAIN 27-core sessions (ordinals 0,1,2,0).
Every run reproduced all signed scalar aggregates and 26-tick
P03 bank7 trace FNV64. The original ordinal0 second attempt produced
the **same 256-byte physical mailbox SHA256** as the first:

`5a2d9c9645b79144ef20f5ed7f26e5ed1ad3745aaf929713cf89fcb7f8718eda`

Four-run report:
`/home/dna/Thesis_Evidence/p07_b5_fourrun_original_train_20261101T194900Z.json`;
[bounded B5.2 acceptance ledger](P07_B5_2_2026_11_01_REAL_FOUR_SESSION_FINGERPRINT_ACCEPTANCE.json).

**These are strong fingerprint reproducibility results but NOT direct physical
bytewise validation of every hidden/readout membrane state.** The
original V3 physical terminal mailbox contains one cumulative FNV64
over 26 x 1,010 actual 256-bit HLS trace words, not their raw bytes.
The independent host can already serialize the exact expected
26 x 1,010 x 32B original integer-scalar trace using
`scripts/p07_b5_raw_trace_reference.py`.

## Candidate B5.3 experimental RAW sidecar geometry

**Candidate memory only, not independently authorized physical ownership:**

| Item | Exact value |
| --- | --- |
| HLS debug source | P03 bank 7, original 256-bit per-compartment raw trace |
| Companion check | P03 bank 1 committed after-state; original V3 hooks enforce this |
| Logical schedule | 26 ticks, each 27 cores in ascending order |
| Core counts | frozen 1,000 hidden + 10 readout = 1,010 compartments |
| Record size | 32 bytes = 8 little-endian uint32 words |
| Total records | 26,260 |
| Total raw trace | **840,320 bytes** = **210,080 uint32 words** |
| Proposed additional DDR base | `0x42000000` |
| Proposed additional DDR end EXCLUSIVE | `0x420CD280` |
| Extra reader | dedicated new B5 physical XSDB PSU readback, NOT implemented |
| Accepted production V3 firmware | unchanged, not reused for new B5 ELF |
| Root B2.4 model / P03 PL | unchanged |
| Official B2 TEST | SEALED |

The proposed sidecar does **not** overlap the original known P02
27×512KiB model span `[0x40000000,0x40D80000)`, the original
input routes `[0x41000000,0x410E0000)`, original ingress
`[0x41100000,0x411E0000)` (maximal reserved frame), original binding
descriptor `[0x43FC0000,0x43FC4000)`, original output routes
`[0x43FC4000,0x43FD8000)`, or accepted 256B mailbox
`[0x43FF0000,0x43FF0100)`.

**Disjointness does NOT prove the physical region is free** relative
to PS boot firmware, memory protection, Linux carve-outs, system
allocators, coherent masters, hardware address decoding, or other
software. It must be reviewed independently against the actual KV260
memory map/owners BEFORE any Vitis B5.3 firmware runs or DDR
overwrites. The existing V3 A53 low DDR
`[0x00000000,0x00106B00)` exclusivity is independently UNPROVEN
as well. Neither original twelve destructive approvals nor
software-only tests prove new sidecar ownership.

## B5.3.1 native-only completed implementation (NO BOARD CONTACT)

Two new **additive-only** files:

- `software/p07/include/p07_b5_raw_capture.h`
- `software/p07/p07_b5_raw_capture.c`

The C module accepts caller-owned, exactly 210,080-word sidecar
memory, validates all original 27 per-core compartment counts
(sum **exactly 1,010**; readout core 26 must contain 10), clears
exactly the provided buffer, then serializes original 8-word
P03 bank7 values **without recomputing them**. It enforces
**exactly** each `(tick, core, compartment)` in canonical order,
rejects duplicate/skipped/late/out-of-range neurons, rejects
nonzero bits in the reserved high trace word/spike flag, refuses
overrun, and finalizes only after all 26,260 records.

This is a **bare C serializer**. It is not yet hooked into the real
A53 dispatch callback, is not included in the accepted V3 ELF
build and has not physically written any board memory. A successful
native test does **not** demonstrate on-board capture.

Native unit tests `tests/test_p07_b5_raw_capture_native.py` compile
the actual new C implementation with host GCC and use ctypes to
test all 26×1,010 correctly ordered synthetic words, exact little-endian
840,320B serialization, physical-buffer canaries,
wrong metadata/capacity/alignment, duplicate/skipped records,
malformed reserved bits, and incomplete trace poison behavior.
These tests cannot be substituted for an XSDB physical readback.

## 2026-11-01 B5.3.2 development — separate B5 firmware wired, NO BOARD ACCESS

The operator's original TRAIN0 frozen scalar reference produced **exactly
840,320B** at
`/home/dna/Thesis_Evidence/p07_b5_train0_expected_raw_20261101T200800Z.bin`;
the operator independently confirmed actual file SHA256
`7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`,
reference FNV64 `0xB59CA8594D6E64AD`, and original frozen
monolithic trace SHA256
`4bef8f76965d4080a7c4ec2f3feab7c805e636d6397afb80a4a09f07733aea35`.
The [operator source-only raw reference ledger](P07_B5_3_TRAIN0_SCALAR_RAW_ORACLE_USER_ACCEPTANCE.json)
does **not** count this as an FPGA raw trace.

**B5.3.2 additional implementation completed on draft PR #50:**

- `software/p07/p07_b5_spike_trace.c` is a distinct B5-only replacement
  for the *original V3 compiled trace-hook source*, preserving original
  trace interface names for the accepted 26-tick scheduler. It reads
  the **actual P03 debug bank7** and independently checks the
  committed bank1 after-state exactly once per compartment, then
  appends those already validated eight raw words to the B5-only
  sidecar **before** the physical slot can be evicted. Any missing,
  skipped, extra, malformed or out-of-order record fails the run.
  The original accepted `p07_b4m_spike_trace.c` remains unchanged.
- `software/p07/include/p07_b5_trace_hook.h` declares mandatory,
  validated recorder binding; the replacement hook checks the original
  P03 registered per-core compartment counts and ascending prefixes
  against the B5 capture metadata **before** accepting inference.
- `software/p07/p07_b5_full_board_raw_trace_v1.c` is a new A53
  entry point with unique identity
  `P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1`. It preserves the
  original V3 trained 26-tick control path and requires
  `p07_b5_capture_begin`, `p07_b5_trace_attach`,
  `p07_b5_capture_finalize`, all 26,260 records, zero capture
  faults and an exact 840,320-byte A53 cache flush before reporting
  its **new** B5-specific 256B mailbox PASS. The **candidate** B5
  mailbox is at `[0x43FF0100,0x43FF0200)`, distinct from V3's
  `[0x43FF0000,0x43FF0100)`. That mailbox ownership, too,
  needs separate physical approval. The original V3 ELF has not
  been modified, recompiled or replaced.
- `software/p07/build_p07_b5_raw_trace.py` and
  `scripts/build_p07_b5_raw_trace.sh` stage a new distinct
  Vitis 2025.2 A53 application and linker-emitted GNU map in a
  **NEW external build directory**. They reuse the exact accepted
  P03 XSA and original source ABIs. The only staging transformations
  are the previously accepted flat SHA include and B4m-specific
  10,000 route binding ceiling; no alterations to original
  `P03` adapter/RTL/frozen training bytes.
- `scripts/p07_b5_raw_trace_offline_admission.py` is a strict
  **PC-only** verifier for actual staged new source SHA fingerprints,
  frozen 27-core and original 20,384/1,000 route identity,
  original accepted routed P03 XSA/settings, a **genuine** new Vitis
  ELF + GNU linker map, candidate sidecar geometry and exact
  new firmware identity. Its report **always** records
  `actual_B5_physical_launch_authorized=false`,
  `independent_actual_B5_DDR_owners_verified=false`,
  `actual_raw_840320B_FPGA_captured=false`, and
  `board_accessed=false`, regardless of offline success.
- Native tests
  `tests/test_p07_b5_trace_integration.py` and
  `tests/native/p07_b5_raw_trace_hook_harness.c` compile the
  **actual new C recorder and hook together**. The fake P03
  fixture simulates all 26 × 1010 separate bank7/1 reads and checks
  exact 840,320-byte serialized output, valid full-count finish,
  genuine ordering, live metadata mismatch rejection and
  corruption abort. These are **host-only synthetic P03 tests**.
  Additional native tests in
  `tests/test_p07_b5_raw_trace_offline_admission.py` mutate staged
  source to ensure strict rejection of missing, extra or altered
  files, accepted adapter modifications, and future physical
  DDR assumptions.

**What remains of B5.3:** The *new* Vitis candidate still must be
built on the operator's actual Vitis 2025.2 toolchain and pass
the independent offline report before any further engineering
work. No new dedicated B5 physical JTAG launcher, real sidecar
DDR-owner admission, 840,320B PSU readback or authenticated
full-neuron physical comparison exists yet. **Do NOT call the
original B4m V3 physical runner with this B5 ELF**: its hashes,
firmware identity and 256B terminal mailbox ABI are different.
The original physical successes remain accepted, untouched.

### Operator checkpoint 1 — native C and offline gate (PC ONLY)

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p07-b5-scaled-multiframe-validation
git pull --ff-only origin agent/v3-p07-b5-scaled-multiframe-validation
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b5_raw_capture_native.py \
  tests/test_p07_b5_trace_integration.py \
  tests/test_p07_b5_raw_trace_offline_admission.py \
  tests/test_p07_b5_scaled_validation.py \
  tests/test_p07_b5_raw_trace_reference.py
```

### Operator checkpoint 2 — NEW real Vitis build and PC-only admission

ONLY after native tests pass and the accepted
`vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports`
still contain the genuine SHA-pinned original XSA:

```bash
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B5_RAW_BUILD_DIR="$HOME/p07_b5_raw_trace_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p07_b5_raw_trace.sh
```

A genuine successful operator build prints
`P07_B5_RAW_A53_ELF_AND_MAP_BUILT=1` and
`P07_B5_RAW_REAL_BOARD_RUN_AUTHORIZED=0`.
A build failure means **no candidate accepted**. On success:
verify the exact real ELF/map hashes and sections in
`$P07_B5_RAW_BUILD_DIR/artifact_sha256.txt` and
`$P07_B5_RAW_BUILD_DIR/readelf_layout.txt`.

```bash
export P07_B5_RAW_OFFLINE="$HOME/Thesis_Evidence/p07_b5_raw_elf_offline_$(date -u +%Y%m%dT%H%M%SZ).json"
export P07_B4M_STAGE="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
PYTHONPATH="$PWD/src" python scripts/p07_b5_raw_trace_offline_admission.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --routes-dir "$P07_B4M_STAGE" \
  --build-dir "$P07_B5_RAW_BUILD_DIR" \
  --reports "$P07_B4L_REPORTS" \
  --out "$P07_B5_RAW_OFFLINE"
cat "$P07_B5_RAW_OFFLINE"
```

Success: `P07_B5_GENUINE_RAW_CAPTURE_VITIS_SOURCE_ELF_OFFLINE_PREFLIGHT_PASS=1`,
`P07_B5_REAL_PHYSICAL_LAUNCH_AUTHORIZED=0`,
`P07_B5_SIDE_CAR_PHYSICAL_DDR_OWNERSHIP_PROVEN=0`,
and `P07_B5_BOARD_ACCESSED=0`. This explicitly does **not**
authorize a real KV260 physical run.

## B5.3.2 work still needed (NEW FIRMWARE AND SHA GATES)

1. **Independent physical DDR and boot ownership review first.**
   Prove or separately accept the specific sidecar address risk
   without weakening the low-DDR risk recorded for V3.
2. Construct a separately named
   `P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1` standalone A53 ELF
   using an isolated **new** Vitis build and GNU linker map; NEVER
   overwrite accepted `p07_b4m_diag_v3_26tick.elf` or its map.
3. Add the new capture call **only** to a separately staged B5
   copy of the existing
   `p07_b4m_spike_trace.c` callback, immediately after the
   physical P03 bank7 and independently cross-checked bank1
   reads and **before** HLS slot eviction. This avoids doubling
   debug MMIO reads or using software-reconstructed trace bytes.
   Do not modify the repository's accepted B4m hook.
4. Add a dedicated B5 main/registration path to bind the approved
   sidecar, clear it **before** first HLS dispatch, require 26,260
   ordered updates, call `p07_b5_capture_finalize()`, flush exactly
   the new sidecar from A53 DCache, and expose an independent
   **B5-specific** terminal mailbox. A B4m V3 mailbox must not be
   repurposed or falsely stamped as a B5 trace receipt.
5. Independent PC-only source/ELF/physical range / XSA/route
   admission with distinct hashes; new physical launcher must
   refuse synthetic/mock trace artifacts and missing external
   run approvals. Source staging, Vitis build and offline checks
   cannot themselves authorize or claim a new board run.
6. In one separately authorized fresh JTAG physical session,
   stage and **physically read back** all original 27 P02 records,
   bindings/routes/one fixed original TRAIN input; run accepted
   P03 bitstream with new signed B5 ELF; capture the distinct
   B5 mailbox; physically read back **all 840,320 bytes** from
   the reserved B5 sidecar using the PSU debug target. Preserve
   readback and source hashes outside the repository.
7. Recompute original frozen scalar reference using
   `scripts/p07_b5_raw_trace_reference.py`; independently compare
   all bytes and report first
   `tick/core/compartment/population/neuron-index/field`
   mismatch. Require exact physical provenance and fresh mailbox
   before reporting `full_raw_neuron_trace_equal=true`.
   The existing `--mode compare-unverified` intentionally
   labels even an equal binary as unauthenticated; it is not a
   genuine hardware-acceptance route by itself.
8. Record a separate actual power-cycle/recovery attestation
   for P07-B.5.2 sessions (not derivable from mailboxes), and
   only after all remaining physical gates pass request explicit
   operator signoff for final P07-B.5/P07-B.6 transition.

**No B5.3 real hardware launch is implemented, claimed or authorized.**
Do not run older V3 launchers with a mismatched ELF or try to
patch accepted frozen binary/weights to bypass SHA admission.

## Operator PC-only development checks (safe today)

```bash
cd ~/Git/Thesis
git switch agent/v3-p07-b5-scaled-multiframe-validation
git pull --ff-only origin agent/v3-p07-b5-scaled-multiframe-validation
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b5_scaled_validation.py \
  tests/test_p07_b5_raw_trace_reference.py \
  tests/test_p07_b5_raw_capture_native.py
```

Regenerate the signed scalar raw transcript for the original fixed
TRAIN0 witness; this is still HOST-ONLY, no new real KV260 data:

```bash
export P07_B4L1_STAGE="$HOME/Thesis_Evidence/p07_b4l1_original27_20261022T204013Z"
export P07_B4M_STAGE="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P07_B5_RAW_REF="$HOME/Thesis_Evidence/p07_b5_train0_expected_raw_$(date -u +%Y%m%dT%H%M%SZ).bin"
export P07_B5_RAW_REF_JSON="$HOME/Thesis_Evidence/p07_b5_train0_expected_raw_$(date -u +%Y%m%dT%H%M%SZ).json"

PYTHONPATH="$PWD/src" python scripts/p07_b5_raw_trace_reference.py \
  --mode reference --ordinal 0 \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" --routes-dir "$P07_B4M_STAGE" \
  --expected-raw "$P07_B5_RAW_REF" --out "$P07_B5_RAW_REF_JSON"
stat -c '%n %s bytes' "$P07_B5_RAW_REF"
sha256sum "$P07_B5_RAW_REF"
cat "$P07_B5_RAW_REF_JSON"
```

Expected if the real frozen scalar oracle and raw FNV embedding agree:
`P07_B5_RAW_SCALAR_REFERENCE_REPORT=...`,
`P07_B5_FULL_RAW_PHYSICAL_TRACE_AUTHENTICATED=0`, and a real output
file of exactly 840,320 bytes. **This raw scalar success is NOT
physical B5.3 acceptance.**
