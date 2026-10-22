# P07-B.4l — consolidated model deployment and hardware paging

**Created 2026-10-22.** Consolidates previous B4l.1 through B4l.4
planning into one substantial engineering milestone rather than incrementing
a separate name for every tool or experiment. **This document distinguishes
completed host work, implemented but not physically verified board work,
and remaining paging integration.**

## Physical and frozen-source acceptance entering B4l

- **B4k real standalone Cortex-A53:** user-reported genuine physical
  `P07_B4I_A53_DOWNLOADED=1`,
  `P07_B4I_MAILBOX_CAPTURED_64_BYTES=1`,
  `P07_B4I_PHYSICAL_READONLY_ADMISSION_PASS=1`,
  `P07_B4K_REAL_STANDALONE_A53_ADMISSION_PASS=1`. Zero trained
  inference, no 27-core page/dispatch measured.
- **B4l host-only model staging accepted by operator:** original frozen
  B2.4 33 files and **27 × 512 KiB** P02 contexts verified byte-for-byte;
  original B2.4 directory untouched, official MNIST TEST sealed.
  Bundle SHA256 **`3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e`**,
  length **14,155,776 B**, mapped
  `[0x40000000,0x40D80000)`. Source:
  `P07_B4L1_2026_10_22_REAL_FROZEN_STAGING_USER_ACCEPTANCE.json`.
  These are original frozen **trained** weights (not a new trained model).
  **Not physically staged on KV260** at the time of this acceptance.

The user-local frozen material lives at
`artifacts/p06_b24_frozen_1000`. The accepted host stage is
`$P07_B4L1_STAGE` with exactly two artifacts:
`p07_b4l1_original_27_p02_ddr.bin` and
`p07_b4l1_staging_index.json`. The artifacts themselves are intentionally
not uploaded into Git. The official MNIST TEST remains sealed.

The original P07-B3 paging interface requires **three resident physical
slots, one HLS engine, 27 logical cores and 26 ticks**. Full logical
schedule: **702 dispatches and 26 global barriers** per image. The P03/P05
page-in transfer size is **438,272** bytes per context, page-out dirty mutable
size **106,496** bytes; the full P02 backing record stride remains 524,288.

## Consolidated B4l development scope and gates

**Part A: already accepted PC-only original frozen 27-core package.**
Authenticates the genuine 33 original B2.4 assets and prepares indexed
canonical P02 DDR bytes. No physical FPGA action or numerical execution.

**Part B: implemented new full physical DDR staging and independent
readback.** On a new, dedicated disposable JTAG session, the new
`scripts/p07_b4l_physical_model_deploy.py` runner:

1. Validates **all 33 original B2.4 assets** via unchanged original
   verifier, exact accepted manifest, all 27 P02 header/payload checks,
   exact B4l.1 original bundle SHA, core ordering, physical bounds,
   and official TEST seal.
2. Requires fresh evidence directory, hardware tools and six explicit
   per-operation user approvals. **No operator note is required.**
3. **Before contacting hardware**, splits the verified 14MiB original
   B4l.1 image into 27 SHA-checked temporary 512KiB input images in
   the evidence directory, without modifying the B2.4 freeze.
4. Repeats the physically established B4i dedicated A53 halt/PS 128-bit
   gate (including powered-down secondary cores) and original B4j
   accepted P03 bitstream programming with VIO reset-release.
5. Calls new `vivado/p07_b4l_stage_27_ddr.tcl`. Selects **PSU/APU
   physical debug target only**, not translated A53; writes only the
   fixed `0x40000000+i*0x80000` original 512KiB P02 records,
   `i=0..26`, and `mrd -bin` reads each entire 512KiB back.
   The Tcl compares every byte and emits an exact marker per core.
6. The independent host Python verifier checks presence of all 27
   unique returned files, 512KiB length each, SHA256 of each readback
   against its B2.4 source, each exact byte against the ORIGINAL host
   bundle, and the complete 14MiB readback aggregate
   `3733e1c2…e238af64e`. Only then reports physical staging PASS.
7. Preserves `stage.txt`, `ps_width.log`, `program.log`,
   `ddr_stage.log`, `manifest.json`, `transfer_inputs/`,
   `physical_readback/`, and `independent_receipt.json`
   if successful. **Reboot KV260 after any physical attempt.**

**B4l DDR physical PASS is now user-attested (2026-10-22).** The operator
reported the original B4l full XSDB staging and independent Python full
readback markers. The evidence ledger is
`P07_B4L_2026_10_22_REAL_27CORE_DDR_STAGE_PASS.json`. Physical **page-in,
page-out and inference remain unverified**; this acceptance covers DDR
provisioning and physical byte equality only.

**Part C: actual 3-slot resident page-in, dirty writeback, and
B3 acknowledgement-driven paging.** To implement after Part B is proven on
real DDR. Reuse original P03/P05 `page_in`, `page_out`, `quiescent`,
`dispatch` controls and original B3 C scheduler; prevent false success
based on memcpy/DDR readback alone. This cannot be declared complete
until independent physical slot image/state checks and page/dirty
traffic prove it. It is still part of **B4l**, not a new family
of tiny milestones.

**Next major milestone P07-B.4m: end-to-end 27-core inference and parity.**
Combine full B2a ingress, B2b NEXT packet/barrier routing, B3 pager and P03
HLS execution under standalone A53 firmware; prove real physical
26-tick frozen numerical equality against the three **predeclared
TRAIN-derived validation** frames, then latency/byte/power measurements
as warranted. Leave official MNIST TEST sealed until physical parity
is user-accepted. No rebuilt/trained weights allowed.

## Limits and hardware risk

This is a deliberately **destructive** standalone CPU/JTAG test. The memory
region `[0x40000000,0x40D80000)` appeared as System RAM under the
original Linux boot. `sudo xmutil unloadapp` does **not** release DDR.
The new experiment assumes an explicitly dedicated disposable session,
successful takeover and operator-accepted risk of displacing Linux/firmware
contents. CPU halts and flags do NOT independently prove exclusive firmware
DDR ownership. **Never run this against Linux you intend to preserve.**
No physical 3-slot page-in or neuron inference is performed by this
staging runner. Reboot/power-cycle to recover.

## PC-only local tests and preflight

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
  tests/test_p07_b4l1_stage_frozen_27core.py \
  tests/test_p07_b4l_physical_model_deploy.py

PYTHONPATH="$PWD/src" python scripts/p07_b4l_physical_model_deploy.py \
  --mode preflight \
  --frozen-dir "$P07_B4L1_FREEZE" \
  --staged-dir "$P07_B4L1_STAGE"
```

Expected PC-only markers:

```text
P07_B4L_REAL_27_CONTEXT_HOST_BUNDLE_PREFLIGHT_PASS=1
P07_B4L_OFFLINE_ONLY_NO_BOARD_ACCESS=1
P07_B4L_PHYSICAL_DDR_STAGED=0
P07_B4L_TRAINED_INFERENCE_EXECUTED=0
```

## Separately operator-approved physical DDR deployment

**ONLY after native + real package preflight passes and the operator
explicitly accepts destructively taking over a newly rebooted/disposable
KV260 Linux session.** Do not run on a previously halted session; first
reboot, use normal `sudo xmutil unloadapp` if appropriate, and save work.
Verify local Vitis tools and the previously accepted P03 report path.
Use a **new** absolute evidence directory (do not pre-create leaf):

```bash
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4I_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"

mkdir -p "$HOME/Thesis_Evidence"
export P07_B4L_EVIDENCE="$HOME/Thesis_Evidence/p07_b4l_physical_$(date -u +%Y%m%dT%H%M%SZ)"

PYTHONPATH="$PWD/src" python scripts/p07_b4l_physical_model_deploy.py \
  --mode execute \
  --frozen-dir "$P07_B4L1_FREEZE" \
  --staged-dir "$P07_B4L1_STAGE" \
  --reports "$P07_B4I_REPORTS" \
  --evidence "$P07_B4L_EVIDENCE" \
  --dedicated-jtag-owner YES \
  --cpu-takeover-approved YES \
  --ddr-27core-overwrite-approved YES \
  --firmware-coexistence-risk-acknowledged YES \
  --pl-program-approved YES \
  --reboot-recovery-approved YES
```

These explicit flags are approvals, not proof of memory isolation.
Expected on **actual hardware success, not as a predeclared claim**:

```text
P07_B4L_REAL_FPD128_LPD128_PASS=1
P07_B4L_ACCEPTED_P03_PROGRAM_VIO_RESET_PASS=1
P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1
P07_B4L_PHYSICAL_27_CORE_DDR_FULL_BYTE_EXACT_PASS=1
P07_B4L_PHYSICAL_PL_PAGE_IN_EXECUTED=0
P07_B4L_TRAINED_INFERENCE_EXECUTED=0
P07_B4L_REBOOT_REQUIRED=1
```

On failure preserve `$P07_B4L_EVIDENCE/stage.txt` and any logs.
Do NOT retry in the same halted Linux context. Always reboot, and
inspect the failed core/address before designing a revised attempt.

## CI and evidence rules

Native tests exercise source-bound preflight, strict approvals, actual
Tcl via `tclsh` with a simulated PSU memory target, 27 address/size
geometry, exact 14MiB row-by-row equality, early halt/PL failures, wrong
readback and missing/duplicate pass receipts. None accesses the KV260.
Document independent physical PASS only from actual user-provided board
logs and `independent_receipt.json` after running this new code locally.
PR #49 remains draft/unmerged pending operator acceptance.

## Physical DDR admission accepted; next same-milestone paging controller (2026-10-22)

The operator physically ran the B4l 27-core DDR provisioning workflow and
supplied:

```text
P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1
P07_B4L_DDR_STAGE_TCL_DONE_REBOOT_REQUIRED=1
P07_B4L_PHYSICAL_27_CORE_DDR_FULL_BYTE_EXACT_PASS=1
P07_B4L_PHYSICAL_PL_PAGE_IN_EXECUTED=0
P07_B4L_TRAINED_INFERENCE_EXECUTED=0
P07_B4L_REBOOT_REQUIRED=1
```

**Physical DDR provisioning and independent 27-record full-readback is a
user-attested PASS.** The original full readback files remain on the user's
PC. This does not prove physical slot residency, page-out persistence, or
trained inference. Do not retroactively count the staged page bytes as page
engine transfers.

**Continuation inside B4l, not another subphase:** Implemented new
`software/p07/p07_b4l_page_probe.c` and
`software/p07/p07_b4l_paging_probe_board.c`, using the *actual accepted*
`p03_hw_page`, `p03_hw_debug_word`, `p03_hw_xilinx_io` and P03
FPD128/shell identity controls. The new C11 controller performs **27
hardware full page-ins plus one re-page-in** across 3 slots, checks the
five independent resident static samples (CONFIG, AXON, SYNAPSE,
ROUTE DESCRIPTOR and ROUTE) against their original P02 DDR words after
each page-in, modifies a low STATE word in slot 0,
acknowledges **one genuine mutable-only dirty page-out** before evicting
core 0 for core 3, compares the saved DDR word, then reloads core 0
and verifies persistent state. Counters: **28 full page-ins; 1 mutable
page-out; all 27 logical cores checked; 0 neural dispatch**. This is a
bounded diagnostic mutation of the standalone DDR copy only; the frozen
B2.4 host snapshot and accepted host bundle remain immutable.

The board-side standalone C source publishes a separate **256-byte** mailbox
with physical page-completion counts, page cycles, dirty-state DDR and
resident readbacks and no-inference status. The independent Python verifier
`scripts/p07_b4l_verify_page_probe.py` checks every field including
reserved-zero words and prohibits a physical PASS based on synthetic
host-native tests. The new isolated Vitis build sources are
`software/p07/build_p07_b4l_page_probe.py` and
`scripts/build_p07_b4l_page_probe.sh`.

**This is NOT a physically tested A53 page probe or a user-built Vitis ELF
at the time of this commit.** It requires a real Vitis 2025.2 build,
independent ELF load/placement and XSA checks, an integrated same-session
DDR stage **plus** ELF download/capture runner, and actual KV260 results
before any hardware page-in/page-out success is declared. Any reboot
between DDR stage and A53 launch would invalidate the prepared DDR
contents. Retain the current physical ownership warnings and reboot
recovery rules. The official MNIST TEST remains sealed.

### Next PC development verification (no board access)

```bash
cd ~/Git/Thesis
 git status --short
 git fetch origin
 git switch agent/v3-p07-b-scaled-physical-inference
 git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4l_page_probe.py \
  tests/test_p07_b4l_physical_model_deploy.py
```

For a real **offline-only** Vitis build using the original accepted P03
FPD128 XSA, independently confirm the native gates first, then run:

```bash
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4L_BUILD_DIR="$HOME/p07_b4l_page_probe_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p07_b4l_page_probe.sh
```

Expected only after the user's actual Vitis build:
`P07_B4L_REAL_VITIS_ELF_AND_MAP_BUILT=1` and
`P07_B4L_PHYSICAL_BOARD_RUN_AUTHORIZED=0`. Verify real ELF symbol and
LOAD sections before any destructive `dow` attempt. No board execution
command is provided at this stage; the future physical pilot must re-stage
all 27 original records and start the new ELF in the **same disposable
JTAG session**.

## Integrated same-session paging probe and launch implementation (2026-10-22)

**Implemented, host-native CI PASSED, real Vitis build and new KV260
physical run NOT YET PERFORMED.** The assembled paging deliverable is still
part of the single **P07-B.4l** milestone, not an additional numbered phase.

New files:
- `vivado/p07_b4l_xsdb_page_probe_run.tcl` — idempotent already-stopped
  primary A53 handling, processor reset, exactly 256 zero mailbox bytes,
  distinct B4l ELF `dow`/continue, bounded physical PSU/APU mailbox
  polling and 256-byte capture. Never dispatches inference itself.
- `scripts/p07_b4l_physical_paging.py` — default offline, verifies original
  33-asset B2.4 freeze and accepted B4l.1 27×512KiB bundle, accepted
  P03 XSA/BIT/LTX and real Vitis ELF+map/physical PT_LOAD. Its optional
  destructive execute mode does the whole DDR stage **and** A53 launch in
  **one uninterrupted JTAG session**. It requires independent full
  physical 14MiB DDR readback before any A53 ELF download.
- `scripts/p07_b4l_verify_page_probe.py` — independently validates
  exactly 64 little-endian uint32 mailbox words (256 bytes): B4l unique
  identity; accepted FPD128; 27 distinct cores; 28 page-ins; exactly
  one mutable-only dirty page-out; the changed low STATE word in real
  DDR and reloaded URAM; nonzero PL page-cycle count; >=29 PL page
  completions; no inference; distinct completion cookie.
- `software/p07/build_p07_b4l_page_probe.py`,
  `scripts/build_p07_b4l_page_probe.sh` — separate Vitis 2025.2
  A53 ELF, only when invoked on user's AMD-tools PC. Reuses genuine
  accepted P03 routed XSA. Never modifies the physically accepted
  B4i ELF, B2.4 model, or original P03 RTL.
- `tests/test_p07_b4l_page_probe.py`,
  `tests/native/p07_b4l_page_probe_harness.c`, and
  `tests/test_p07_b4l_physical_paging.py` — strict native C11
  controller/dirty-save/failure tests, real Tcl simulated with tclsh,
  real ELF parser validation against mocked readelf, integrated
  stage/launch precondition and failure tests. These synthetic tests
  are explicitly **not** new physical PL paging evidence.

The paging controller checks five original static DDR banks per core:
CONFIG at 0x1000, AXON at 0x7000, SYNAPSE at 0xF000,
ROUTE DESCRIPTOR at 0x4F000, ROUTE at 0x50000. The original
DDR data is unchanged on the PC. The one deliberate test-only
STATE mutation is the low 32 bits of core0 STATE bank word0
(offset 0x5000, XOR 0x100), and it is persisted to the board's
working DDR copy through the actual P03 mutable-only page engine.
Do not use that mutated board DDR copy for numerical inference;
the frozen images must be restaged again for future experiments.

A standalone ELF PT_LOAD at physical address 0 is still an
intentional destructive JTAG experiment. The offline checker
requires entry 0, a single LOAD and a span contained within the
independently accepted historical Track A [0x0,0x29D80)
envelope; it rejects arbitrary memory placement. The ELF SHA
must be explicitly supplied from the user-local actual build.
The word `exclusive` in the Tcl approval label is a *human
authorization*, **not independent proof of low-DDR ownership**.
It is not appropriate for live-Linux JTAG injection.

### User PC check before the next board run

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
  tests/test_p07_b4l_page_probe.py \
  tests/test_p07_b4l_physical_paging.py \
  tests/test_p07_b4l_physical_model_deploy.py

source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4L_BUILD_DIR="$HOME/p07_b4l_page_probe_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p07_b4l_page_probe.sh
```

A successful genuine Vitis build should produce ELF and linker map under
`$P07_B4L_BUILD_DIR/vitis_workspace/p07_b4l_paging_probe.{elf,map}`.
The output `P07_B4L_REAL_VITIS_ELF_AND_MAP_BUILT=1` is a **build**
acceptance only. It is not yet physically executable until the
offline inspector and the operator's real physical-session conditions
are satisfied. After the real build, run **PC-only** preflight:

```bash
export P07_B4L_ELF="$P07_B4L_BUILD_DIR/vitis_workspace/p07_b4l_paging_probe.elf"
export P07_B4L_ELF_SHA="$(sha256sum "$P07_B4L_ELF" | awk '{print $1}')"
export P07_B4I_BUILD_DIR="/home/dna/p07_b4i_build_20261022T161058Z"
export P07_B4L1_FREEZE="$PWD/artifacts/p06_b24_frozen_1000"
python scripts/p07_b4l_physical_paging.py \
  --mode preflight \
  --frozen-dir "$P07_B4L1_FREEZE" \
  --staged-dir "$P07_B4L1_STAGE" \
  --reports "$P07_B4L_REPORTS" \
  --b4i-build "$P07_B4I_BUILD_DIR" \
  --elf "$P07_B4L_ELF" \
  --expected-elf-sha "$P07_B4L_ELF_SHA"
```

Expected **only on real identity-valid host artifacts**:
`P07_B4L_REAL_PAGING_ELF_SOURCE_DDR_P03_OFFLINE_PREFLIGHT_PASS=1`,
`P07_B4L_PAGE_PROBE_OFFLINE_ONLY_NO_BOARD_ACCESS=1`,
`P07_B4L_PHYSICAL_PAGING_EXECUTED=0`.

The future physical B4l paging run must stage original contexts again
**inside the same dedicated disposable JTAG session**. **Do not run
`--mode execute` until the actual new ELF/map and complete offline
safety preflight have passed on the operator's PC.** On success, the
independent verifier should prove actual P03 page-engine transfers,
not mere XSDB DDR copy. As before, the board must be rebooted after any
physical attempt. No handwritten operator note is required.
