# P07-B.4k — actual standalone Cortex-A53 shell-admission physical pilot

**Development date:** 2026-10-22. **State:** physical launch runner prepared,
not executed against the KV260. PR #49 remains draft/unmerged. Original P03,
Track A, accepted B2 numerics and official MNIST TEST remain unchanged.

## What is physically established

The operator independently reported passing the genuine P07-B.4i JTAG
4-core gate with Cortex-A53 #0/#1 successfully halted, #2/#3 powered down,
PSU FPD `0x00000A00` (128-bit) and LPD `0x00000200` (128-bit).
The subsequent P07-B.4j full physical shell-only program completed:

```text
PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released
P07_B4J_PHYSICAL_SHELL_PROGRAM_VIO_RESET_PASS=1
P07_B4J_A53_ELF_DOWNLOADED=0
P07_B4J_DDR_MAILBOX_TOUCHED=0
P07_B4J_TRAINED_INFERENCE_RUN=0
P07_B4J_REBOOT_REQUIRED=1
```

This *accepts B4j bitstream programming and VIO reset-release*, not A53
execution, DDR ownership, or trained B2 inference. The posted Vivado tail
provides direct P03 programming evidence; the complete per-run artifact/width
logs remain local to the operator. See the exact user-reported acceptance
ledger `P07_B4J_2026_10_22_PHYSICAL_SHELL_PROGRAM_ACCEPTANCE.json`.

## Verified standalone candidate and historical comparison

User's local Vitis 2025.2 B4i ELF:
`/home/dna/p07_b4i_build_20261022T161058Z/vitis_workspace/p07_b4i_mailbox_probe.elf`,
SHA256 `5fcdb0586564f3abef477804a54e0a87163c74654f9d15d1f9600ab2cb85e807`.
Genuine map SHA256
`4deb41d9f47bd397ced6a15027b83b74f1d689f25220088bce62e5d2363551ad`.
Single PT_LOAD `[0x0,0x23A40)`, entry `0x0`.
The independently SHA-confirmed accepted Track A P07-A4 ELF had the same
entry and physical LOAD start with a *larger* segment `[0x0,0x29D80)`.
The accepted P03 XSA SHA256 is
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
The B4i preflight additionally pins BIT/LTX against the routed report set.

This physical layout match and the previous Track A board success show that
the A53 standalone linker/boot convention was physically viable **in that
earlier experiment**. They do NOT independently measure Linux/TF-A/PMU
ownership of low DDR today. The new B4k test is explicitly a destructive
experiment intended to replace a disposable Linux execution environment,
not a live-Linux ELF injection.

## What the B4k runner actually does

`scripts/p07_b4k_standalone_admission.py`, default `--mode preflight`:

1. Reuse actual B4i artifact/source/route preflight and verify **exact**
   independent B4i ELF/map hashes, physical PT_LOAD and mailbox geometry.
2. In a **fresh** dedicated JTAG boot/session, using the previously
   physically successful B4i Tcl, require A53 #0 halted, secondary cores
   either halted or explicitly powered down, and both real PS widths 128-bit.
3. Repeat **the physically successful B4j programming** procedure to load
   exact accepted P03 BIT+LTX and verify VIO reset-release.
4. Overwrite exactly **64 bytes at physical `0x43FF0000`** with zero,
   verify readback, reset A53 #0 and XSDB `dow` the SHA-matched ELF at
   `[0x0,0x23A40)`, then `con` and poll for a complete mailbox.
   This step **does overwrite the low-DDR ELF span** and destroys the old
   Linux context, unlike B4j.
5. Independently run the original strict 16-word
   `scripts/p07_b4i_verify_mailbox.py`; require actual shell
   ID/version/capabilities, idle state, zero pending and no inference.
6. Preserve `ps_width.log`, `program.log`, `a53_run.log`,
   `p07_b4k_mailbox_64.bin`, `verify.log`, `manifest.json`,
   `stage.txt`. **Reboot the KV260 after any physical attempt**.

**No handwritten operator note** is required. The physical runner
still requires seven separate explicit flags: dedicated JTAG board owner,
CPU takeover, intentional destructive low-DDR overwrite, acceptance of
unverified firmware/low-DDR coexistence risk, mailbox overwrite,
PL programming, and reboot recovery. These indicate explicit operator
consent, **not factual proof of DDR exclusivity**. If the risks of
displacing a live bootloader/firmware or Linux are not acceptable, do
not execute; prefer alternate exclusively reserved DDR with relink and
independent platform validation.

B4k intentionally executes **read-only MMIO shell admission**, not the
frozen 27-core neural model. It never loads TEST data or dispatches HLS
inference.

## PC-only native and artifact checkpoint

From VS Code terminal on PC (NO board operations):

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
  tests/test_p07_b4i_physical_pilot.py \
  tests/test_p07_b4j_shell_program_pilot.py \
  tests/test_p07_b4k_standalone_admission.py

source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4I_BUILD_DIR="/home/dna/p07_b4i_build_20261022T161058Z"
export P07_B4I_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
python scripts/p07_b4k_standalone_admission.py \
  --mode preflight --build "$P07_B4I_BUILD_DIR" \
  --reports "$P07_B4I_REPORTS"
```

Expected offline output:
`P07_B4K_REAL_ELF_MAP_P03_OFFLINE_PREFLIGHT_PASS=1`,
`P07_B4K_ELF_PT_LOAD=[(0, 145984)]`,
`P07_B4K_OFFLINE_ONLY_NO_HARDWARE_ACCESS=1`,
`P07_B4K_PHYSICAL_LAUNCH_AUTHORIZED=0`.

## Separately controlled first physical execution

**Not a command to run on the existing halted board.** Power-cycle/reboot
the KV260 first, confirm a recoverable disposable Linux/JTAG session and
repeat `sudo xmutil unloadapp` (as in accepted P03/Track A). The
operator must personally assess risk, back up any volatile information,
and confirm no other person/process expects the Linux instance or DDR to
survive. Prepare a new evidence path (do NOT `mkdir` it ahead of time):

```bash
mkdir -p "$HOME/Thesis_Evidence"
export P07_B4K_EVIDENCE="$HOME/Thesis_Evidence/p07_b4k_a53_$(date -u +%Y%m%dT%H%M%SZ)"

python scripts/p07_b4k_standalone_admission.py \
  --mode execute \
  --build "$P07_B4I_BUILD_DIR" \
  --reports "$P07_B4I_REPORTS" \
  --evidence "$P07_B4K_EVIDENCE" \
  --dedicated-jtag-owner YES \
  --cpu-takeover-approved YES \
  --low-ddr-destructive-overwrite-approved YES \
  --firmware-coexistence-risk-acknowledged YES \
  --mailbox-overwrite-approved YES \
  --pl-program-approved YES \
  --reboot-recovery-approved YES
```

No `--recovery-note` option exists. Never bypass the flags if the
destructive conditions are not personally accepted. The runner prints
`P07_B4K_LOW_DDR_EXCLUSIVE_OWNERSHIP_PROVEN=0` as an intentional truth
statement, even on a successful run.

Success requires **actual** bounded XSDB mailbox completion and the
independent strict mailbox PASS from user-local bytes:

```text
P07_B4K_REAL_PS_FPD128_LPD128_PASS=1
P07_B4K_REAL_ACCEPTED_P03_PROGRAM_VIO_RESET_PASS=1
P07_B4I_A53_DOWNLOADED=1
P07_B4I_MAILBOX_CAPTURED_64_BYTES=1
P07_B4I_PHYSICAL_READONLY_ADMISSION_PASS=1
P07_B4K_REAL_STANDALONE_A53_ADMISSION_PASS=1
P07_B4K_TRAINED_27_CORE_INFERENCE_EXECUTED=0
P07_B4K_REBOOT_REQUIRED=1
```

On failure, preserve all evidence, including `stage.txt` and the partial
logs; **do not rerun against a halted Linux instance**. Reboot or power-cycle
before any further board operations. Physical success has not happened as
of this document's initial commit and must not be predeclared.

## Next step after real B4k pass

Only after operator verifies real A53 admission/mailbox should the team
build B4l's 27-core context staging, paging, autonomous dispatch, and
frozen B2 reference parity. A successful shell-only read proves
transport/CPU startup, not trained inference.

## First B4k physical run — XSDB `Already stopped` (2026-10-22)

The operator executed the B4k physical runner and supplied its local
`stage.txt` and final `a53_run.log` excerpts from evidence directory
`/home/dna/Thesis_Evidence/p07_b4k_a53_20261022T201543Z`:

```text
PL_PROGRAM_PASS_A53_ELF_PENDING_REBOOT_REQUIRED
P07_B4I_BOARD_ATTEMPT_FAIL_REBOOT_REQUIRED=1
P07-B.4i: Already stopped
```

The `verify.log` file was absent. **This attempt is a failed A53 launch
checkpoint, not a successful physical admission.** The stage proves that
B4k passed the real PS takeover and physically programmed the accepted P03
PL shell and verified VIO reset release. No A53 ELF download marker,
DDR mailbox completion, or independent verifier PASS was supplied. The
explicit physical A53 launch script failed instead.

### Root cause and narrow remedy

Prior B4i/B4j/B4k hardware stages successfully halt A53 #0, but
`vivado/p07_b4i_xsdb_run.tcl` unconditionally issued a **second** `stop`
when selecting A53 #0 immediately before `rst -processor`. AMD's XSDB
`stop` command explicitly raises an error for an already-stopped target
(UG1725). This is consistent with the observed `Already stopped` message.
The user posted the last lines of the log rather than full XSDB command
tracing, so the error's precise instruction location is inferred from the
known original script. No change in DDR ownership or FPGA behavior is
inferred.

A B4k-targeted, backwards-compatible correction to the reusable
`p07_b4i_xsdb_run.tcl` replaces the two A53 #0 `stop` sites
(before reset and after capture) with a `b4i_require_a53_halted`
helper. It accepts **only** the exact `Already stopped` XSDB response,
logging `P07_B4I_A53_0_PRE_RESET_ALREADY_STOPPED_CONFIRMED=1` when
observed. A successful fresh stop logs a different PASS marker. Any other
error, including `The core is powered down`, a JTAG timeout, or a broader
message that merely contains `Already stopped`, remains fatal **before
reset, mailbox write, or ELF download**. Its post-capture stop is
similarly fail-closed. No `dow`, `mrd`, `con`, address, ELF source,
bitstream or previously accepted P03/Track A implementation was changed.

The next host-native tests now execute this exact XSDB Tcl in a fake `tclsh`
with isolated fake `targets`, `stop`, `rst`, `dow`, `mrd` and `con`
commands. The positive paths require all markers, the mailbox output,
and successful continuation; negative paths require that an unexpected
halt error never reaches reset or ELF transfer. GitHub CI tests run with
**no board access** and do not count as new physical acceptance.

**Recovery:** the first failed session halted Linux/A53. Reboot or power
cycle the KV260; never resume that OS instance. Keep the old evidence folder
unchanged. Following the new native and preflight verifications, a separately
operator-approved destructive B4k rerun must use a fresh evidence directory.
All seven explicit approval flags are retained; **no operator note** is
required. The same low-DDR/firmware ownership risks remain unresolved and
must not be presented as proven safe by either the physical PL PASS or
these simulated Tcl tests.
