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

**No B4l DDR physical PASS exists yet.** The Python and Tcl implementations
are host/CI-verified only until operator repeats them on the actual board.

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
