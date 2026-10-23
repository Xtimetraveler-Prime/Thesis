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

## Preflight import-path regression repaired (2026-10-22)

The operator built the genuine B4l paging-probe ELF successfully but the
subsequent PC-only preflight failed **before frozen-asset verification** with:

```text
ModuleNotFoundError: No module named 'loihi_twin_v2.p06_b24_freeze'
  at scripts/p07_b4l1_stage_frozen_27core.py, admit_freeze
```

**Root cause:** Running `python scripts/p07_b4l_physical_paging.py`
from the `v3` directory automatically places `v3/scripts` on
Python's module search path, not sibling `v3/src`. The earlier B4l.1
real verifier command included `PYTHONPATH="$PWD/src"`, but the
paging-preflight instructions omitted it. No evidence suggests Vitis
ELF invalidity; the runner stopped before reaching the ELF admission
check. Do not count this interrupted host preflight as a physical failure.

**Permanent fix:** `p07_b4l1_stage_frozen_27core.py` now installs
the canonical sibling `v3/src` directory at the *original genuine
B2.4 verifier import site*. It refuses an absent/symlink source tree,
does not stub, bypass, substitute or relax the original 33-asset
frozen verification, and benefits all callers (standalone stage,
model deploy, and integrated paging). A native regression subprocess
runs under isolated Python `-I` with `PYTHONPATH` unset and checks
that import resolution reaches the original canonical module location.

The user can either pull this commit then repeat the **exact same
documented** preflight, or run the previous revision with an explicit
single-command prefix:

```bash
PYTHONPATH="$PWD/src" python scripts/p07_b4l_physical_paging.py \
  --mode preflight \
  --frozen-dir "$P07_B4L1_FREEZE" \
  --staged-dir "$P07_B4L1_STAGE" \
  --reports "$P07_B4L_REPORTS" \
  --b4i-build "$P07_B4I_BUILD_DIR" \
  --elf "$P07_B4L_ELF" \
  --expected-elf-sha "$P07_B4L_ELF_SHA"
```

This does not modify the genuine accepted B2.4 original frozen assets,
the compiled A53 paging ELF or its SHA, Track A, P03, or official MNIST
TEST. **No KV260 board access until every remaining actual preflight
gate independently passes.** A later ELF-memory-layout failure (if
any) must be diagnosed separately from this import resolution fix.

## B4l paging ELF: user-reported real build and preflight PASS (2026-10-22)

The operator confirmed that the genuine Vitis paging ELF **was built
successfully** and the integrated PC-only
`scripts/p07_b4l_physical_paging.py --mode preflight` **passed** after
fixing the project's direct-script frozen-verifier import path. This
independently checks the same frozen 27-core B2.4 context bundle,
accepted P03 artifacts and the user-local new ELF entry/LOAD placement.
The actual ELF bytes, newly generated SHA256 and full preflight output
remain on the operator's PC; do not invent or pin values unavailable
in the conversation. No physical B4l PL paging was performed by this
report. The previous physical full 27-core DDR readback PASS remains
separate from upcoming page-in, mutable page-out and dirty restore.

The **next operational checkpoint** is the single existing
`scripts/p07_b4l_physical_paging.py --mode execute` workflow: freshly
rebooted, disposable KV260/Linux JTAG session; explicit operator flags;
real PS/FPD128 stop gate; original P03 accepted bitstream and VIO
reset release; complete 27×512KiB frozen DDR restaging and independent
readback; **same-session** standalone A53 ELF launch; bounded 256-byte
mailbox capture and strict independent paging verifier. The old DDR
contents must not be assumed to survive a reboot. This script is a
**destructive** low-DDR and P02 model-DDR experiment, not a live Linux
service. Low-DDR/firmware exclusivity has not been independently proven
by the takeover tests or approval flags. Do not bypass the gate. Reboot
after any attempt and preserve partial evidence. No handwritten note.

## Physically accepted 27-core three-slot paging (2026-10-23)

The operator provided actual KV260 paging-ELF and independent verifier
results from
`/home/dna/Thesis_Evidence/p07_b4l_paging_20261023T004701Z`:

```text
P07_B4L_A53_PAGING_ELF_DOWNLOADED=1
P07_B4L_PAGE_PROBE_MAILBOX_CAPTURED_256_BYTES=1
P07_B4L_PHYSICAL_27_CORE_3_SLOT_PAGE_DIRTY_SAVE_VERIFIED=1
P07_B4L_REAL_A53_27_CORE_3_SLOT_PAGE_DIRTY_SAVE_PASS=1
P07_B4L_TRAINED_NEURAL_INFERENCE_EXECUTED=0
```

Exact readback values: **27** original logical-core IDs visited, **28**
physical page-ins, **1** mutable-only dirty page-out, **29** real page
completions, **15,136,542** aggregate reported page cycles, and
core-0 diagnostic STATE low-word **0x00000000 → 0x00000100** saved in
DDR and restored through subsequent PL reload. The stage file was
`REAL_A53_27_CORE_THREE_SLOT_PAGE_DIRTY_SAVE_PASS_REBOOT_REQUIRED`.
The real A53 reset emitted a reset-vector warning but the paging ELF
completed and the independent verifier passed; preserve that warning
rather than claiming general reset safety. **This physical paging
checkpoint is ACCEPTED**, distinct from B4l DDR staging and distinct
from **any trained HLS neural dispatch**. See
`P07_B4L_2026_10_23_REAL_3SLOT_PAGING_ACCEPTANCE.json`.

### Continuation within B4l — first scheduler-driven hardware epoch

New host-native integration files:

- `software/p07/include/p07_b4l_b3_epoch.h`
- `software/p07/p07_b4l_b3_epoch.c`
- `tests/native/p07_b4l_b3_epoch_harness.c`
- `tests/test_p07_b4l_b3_epoch.py`

The new C11 controller binds to the **unchanged accepted** `p07_b3c2_step`
B3a LRU / B3c2 physical P03 adapter, not the separate historical P03
round-robin scheduler. It runs exactly one tick-0 epoch using 27 logical
cores and 3 PL slots and requires real P03 page, dispatch, quiescence
and packet-bank readback ACKs before B3 acknowledgments. It captures
original 64-bit FPGA packet words into original B3c2 source-indexed
buffer views, checks all 27 source identities and counts, and calculates
a deterministic diagnostics-only FNV64 capture hash. **It stops with
one pending global B3 barrier; does NOT ACK the barrier, commit NEXT
packets, run tick 1, perform a full 26-tick inference or claim trained
numerical parity.** The output explicitly includes
`pending_barrier=1`, `barrier_acked=0` and zero independent B2b
NEXT acceptance. No original B2.4 frozen model, accepted P03/P05,
B3a/c2/c3 or official MNIST TEST files are modified.

A native C11 test reuses the full **unchanged original B3c23 test bus**
with source-indexed packet simulation and physically structured P03
page, 27 dispatch and packet-read ACKs. It asserts B3 LRU produces
27 page-ins, 24 dirty evictions, 27 completed dispatches and a pending
barrier with *zero barrier acknowledgments*; a failed dirty page-out
must sticky-fault the entire run and prohibit any later page-in or
barrier success. **This is host-native fake-bus acceptance only**. It
is not a new KV260 dispatch run, genuine board state/packet capture,
or physical numerical parity.

Remaining within B4l before any new destructive test: implement the
**separate standalone A53 scheduler integration ELF and genuine
metadata/axon graph registration from original frozen P02/B1.2**, capture
real emitted-neuron provenance, retain the original B2b/B3c3 hardware
NEXT event validation and commit as a separate barrier gate, and run
an independent ELF/linker/capacity/DDR admission. A complete zero-input
or one-tick hardware run still does not establish full trained B2
inference; numerical oracle comparison follows in consolidated B4m.
Reboot/power-cycle after all physical JTAG experiments. No handwritten
operator note is required.

User-native commands for the new B4l scheduler integration:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4l_b3_epoch.py \
  tests/test_p07_b3c23_hw_integration.py \
  tests/test_p07_b4l_page_probe.py
```

There is **no new paging/scheduler ELF to build or KV260 physical
execute command** for this host-native integration gate. The physically
accepted paging ELF remains separate and unchanged. First review the
new test results and keep the B2 TEST sealed.

## Original frozen core bindings and first-epoch A53 dispatch candidate (2026-10-23)

**Same consolidated B4l milestone, not a new numbered subphase.** Following
the operator's native acceptance of the 27-dispatch B3c2/P03 fake-bus gate,
implemented the next combined PC/offline deliverable:

**Immutable actual B2.4 binding descriptor**:
`scripts/p07_b4l_frozen_bindings.py` is a direct-command, no-board tool.
It first re-verifies the complete 33-file original frozen B2.4 package,
the exact operator-accepted 27×512KiB B4l DDR bundle
`3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e`,
and then **reconstructs the accepted B1.2 compiled graph directly
from the original SHA-indexed `packed_deployment.json`**. For each of
the 27 original core configs it determines the exact compartment count
and legal input-axon IDs, uses the original `export_one_core_image`
packer to cross-check the P03 axon words against the corresponding
immutable source P02 initial DDR record, and emits a 16KiB/27-entry
binary descriptor and a self-hashed JSON index. Every entry holds the
original P03 metadata `core_id | (compartment_count<<7)` plus a
4096-bit exact registered input-axon bitmap. SHA binds the descriptor
table, original trained source mapping, original accepted model DDR
bundle, zero padding and fixed core ordering. Source/output overwrite
and symlinks are refused. Original frozen weight bytes and official
MNIST TEST remain unchanged.

**Future descriptor physical placement**: `[0x43FC0000,0x43FC4000)`
inside the established P05 staging region, outside the 27 P02
DDR records and the existing `0x43FE0000` P05 header and
`0x43FF0000` result mailbox. This allocation is for the
standalone first-epoch probe **only**; ingress/bank buffers must
not overlap it when subsequent physical inference is developed.
The descriptor has not yet been staged to KV260.

**Original P03 C-level consumer**:
`software/p07/p07_b4l_b3_bindings.c` validates the complete binary
header, original hard-pinned B2.4 model/deployment SHAs, all 27
metadata/bitmap entries and zero padding. It uses the already accepted
`p07_a2_sha256.c` algorithm (unchanged in the repository) to hash the
table and calls the **original `p03_hw_register_core` and
`p03_hw_register_axon`**; there are no dummy/neatly numbered synthetic
registration bindings. Any malformed table fails *before* P03
registration; I/O registration errors are fatal and must not be
treated as partial success.

**New standalone A53 candidate**:
`software/p07/p07_b4l_b3_epoch_board.c` is distinct from the accepted
paging-only ELF. It verifies PS FPD128, original P03 identity,
authenticates the physically staged descriptor, registers all 27
original P02/B1.2 cores, initializes the accepted B3a LRU +
B3c2 P03 adapter, and calls `p07_b4l_b3_one_epoch` for
27 real page-ins, 24 dirty evictions and **27 genuine HLS dispatches**.
Crucially the implementation deliberately stops at the FIRST
PENDING B3 global barrier with zero NEXT-route commit and
**zero barrier acknowledgments**. The test starts from
empty initial CURRENT banks with **no external ingress**.
It captures the physical P03 64-bit packet words, but it
does **not** claim independently verified source-spike provenance,
valid B2b routed packet fanout, any later tick, or numerical parity.
The independent `scripts/p07_b4l_verify_b3_epoch.py` validates
all 256 mailbox bytes and enforces these zero/non-progress fields.
Native synthetic receipts and native fake-bus tests never authorize
real KV260 inference.

**Actual Vitis 2025.2 offline build implementation**:
`software/p07/build_p07_b4l_b3_epoch.py` and
`scripts/build_p07_b4l_b3_epoch.sh` compose the accepted original
P03 adapter, B3a, B3c2, B2b packet library and B3c3 code with the
new descriptor, epoch coordinator and standalone A53 firmware.
The SHA256 source is copied from the accepted P07 implementation;
the Vitis import requires a temporary flattened *include directive
only in the fresh staging copy*, never editing accepted original files.
This is a **new** A53 ELF, new SHA and linker map; the previous
successful paging-only ELF remains preserved and is not reusable
for this first-epoch dispatch. All host-native CI tests are separate
from Vitis output. The ELF may be larger than the previously
accepted physical `[0,0x29D80)` Track A envelope, so the actual
Vitis ELF LOAD/stack/heap ownership must be reviewed after building;
**do not assume that a successful link authorizes a `dow`.**

### PC-only next acceptance checkpoint

Run from the existing B4l branch in VS Code:

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
  tests/test_p07_b4l_b3_epoch.py \
  tests/test_p07_b4l_frozen_bindings.py \
  tests/test_p07_b4l_b3_board_candidate.py \
  tests/test_p07_b3c23_hw_integration.py
```

Use the existing original frozen model and previously physically accepted
host DDR stage. Output must be NEW, absolute, outside the repository:

```bash
export P07_B4L1_FREEZE="$PWD/artifacts/p06_b24_frozen_1000"
: "${P07_B4L1_STAGE:?Set existing real accepted B4l1 stage directory}"
mkdir -p "$HOME/Thesis_Evidence"
export P07_B4L_BINDINGS="$HOME/Thesis_Evidence/p07_b4l_b3_bindings_$(date -u +%Y%m%dT%H%M%SZ)"
python scripts/p07_b4l_frozen_bindings.py --mode prepare \
  --frozen-dir "$P07_B4L1_FREEZE" \
  --staged-dir "$P07_B4L1_STAGE" \
  --output-dir "$P07_B4L_BINDINGS"
python scripts/p07_b4l_frozen_bindings.py --mode verify \
  --frozen-dir "$P07_B4L1_FREEZE" \
  --staged-dir "$P07_B4L1_STAGE" \
  --output-dir "$P07_B4L_BINDINGS"
```

Expected **only if the true original signed B2.4 deployment, original
packed P03 axons, all 27 P02 records and bundle match**:
`P07_B4L_REAL_B24_27CORE_METADATA_AND_AXONS_VERIFIED=1`,
`P07_B4L_FROZEN_MODEL_UNMODIFIED=1`,
`P07_B4L_PHYSICAL_SCHEDULER_DISPATCH_EXECUTED=0`.

Optionally build the new genuine A53 first-epoch candidate, also PC-only:

```bash
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4L_B3_BUILD_DIR="$HOME/p07_b4l_b3_first_epoch_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p07_b4l_b3_epoch.sh

export P07_B4L_B3_ELF="$P07_B4L_B3_BUILD_DIR/vitis_workspace/p07_b4l_b3_first_epoch.elf"
aarch64-none-elf-readelf -W -h -l "$P07_B4L_B3_ELF"
sha256sum "$P07_B4L_B3_ELF"
```

Expected only after a genuine successful local build:
`P07_B4L_REAL_B3_ONE_EPOCH_VITIS_ELF_AND_MAP_BUILT=1` and
`P07_B4L_B3_ONE_EPOCH_PHYSICAL_BOARD_RUN_AUTHORIZED=0`.

**STOP after this PC-only checkpoint and inspect the real descriptor
identity, actual ELF LOAD ranges, link map, stack, and heap.**
There is intentionally **no physical --execute command** for this
new A53 one-epoch ELF yet. Before any separate destructive JTAG
session the future runner must re-stage all original 27 P02 records
**AND** 16KiB descriptor, independently read both back, then
launch the freshly reviewed ELF in the same session, capture the
256B mailbox and independently verify it. Do not assume that
previous DDR content survived reboot, or that Linux/firmware
physical memory exclusivity was proven. Never resume halted Linux.
No handwritten operator note is required.
