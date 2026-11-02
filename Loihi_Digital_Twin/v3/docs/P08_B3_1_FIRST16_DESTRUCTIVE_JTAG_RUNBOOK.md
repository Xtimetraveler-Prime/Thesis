# P08-B3.1 — KV260 original B2.4 first16 physical JTAG: preflight and risk review

## 2026-11-02 first actual KV260 attempt — confirmed staging-only abort / corrected

The operator ran the dedicated first P08-B3.1 physical JTAG session at
`/home/dna/Thesis_Evidence/p08_b3_pilot16_physical_20261102T050721Z`.
Original accepted P03 shell programming passed, physical PSU target
reported. **All 27 mutable and all 27 independent backup frozen P02
512KiB core readbacks individually reported physical byte-exact PASS**
in the operator's genuine XSDB transcript. Subsequently Tcl emitted
`P08_B3_PILOT_STAGING_FAILED_REBOOT_REQUIRED=1` with
`can't read "name_BYTE_EXACT_PASS": no such variable`, in the
post-readback logging line for the first of the four other signed
source transfers. Root cause: Tcl `$name_BYTE_EXACT_PASS` parses
as an unbound *single* variable. It must be braced: 
`puts "P08_B3_PILOT_${name}_BYTE_EXACT_PASS=1"`.
This correction has **no A53 firmware change**; the operator's
existing signed pilot16 ELF SHA
`29482212c80fb9137b3c185b0cbcdf2000f41417e5af8d3c46b0cd39ecb74fd3`
and map SHA
`9d2106d82347385e936bb27176aa8f50a332beb3f13c3ca8e182890a689c674b`
remain accepted.

The new native regression test **fully executes the real staging Tcl**
inside `tclsh` with mock PSU `dow`/`mrd` and synthetic source hashes
and all six proposed transfers, including both 27core readbacks
and all four original peripheral payload readbacks/receipt names.
It also deliberately reinserts the original invalid variable to verify
the observed abort would reoccur. All native B3.1 and prior P08 CI
workflows pass. The fake-PSU test itself is **NOT physical evidence**.

**Mandatory:** Power-cycle/reboot the real board before any retry; never
resume the halted Linux. Do not use the former partial readback evidence
directory for a new run, do not skip staging, and don't infer all six
stages or first16 numerical/latency success from the genuine
54 P02 readback PASS markers. On a fresh run the accepted frozen PC
source package and accepted new pilot ELF/map may be reused unchanged.
An independent real six-transfer receipt followed by
a complete genuine 16/16 terminal is still required.

**Status dated 2026-11-01: NEW host runner + Tcl + independent physical verifier authored; zero board contact from this development environment; operator-local read-only preflight and a NEW, separately approved dedicated cold-boot run required.** No original P07-B3/B4m/B5, original B2.4 frozen P02 files, B2.3 1024-image ELF, P08-A six latency sessions, original P03 bit/XSA or root `LitReview.md` modified.

## Frozen user-confirmed inputs

* **Exact 16 original matched TRAIN-derived source scalar oracle** SHA `13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271`. Includes 16 individual classifications/output-count vectors, original 26×1,010 trace fingerprints and 3 separately signed frozen B2.3 numerical witnesses.
* **Exact genuine Vitis 2025.2 separately bounded FIRST16 A53 ELF** SHA `29482212c80fb9137b3c185b0cbcdf2000f41417e5af8d3c46b0cd39ecb74fd3`, MAP SHA `9d2106d82347385e936bb27176aa8f50a332beb3f13c3ca8e182890a689c674b`; `p08_b3_original_pilot16.elf`, distinct from original 1024 ELF and original P07-B V3/B5 ELF. Verified read-only pilot report `p08_b3_original_pilot16_elf_admission.json`; does **not** prove boot memory exclusivity.
* **Immutable original 27×512KiB trained P02 images, original 16KiB B4l metadata, original 896KiB input and 80KiB output route images, matched 802,816-byte raw first1024 Track A TRAIN-derived pixel pool**. Six proposed independent physical destinations, with **two distinct identical copies of frozen original model**:
  `[0x40000000,0x40D80000)` mutable;
  `[0x43000000,0x43D80000)` immutable backup;
  `[0x43FC0000,0x43FC4000)` descriptor;
  `[0x41000000,0x410E0000)` original input routes;
  `[0x43FC4000,0x43FD8000)` original output routes;
  `[0x42100000,0x421C4000)` original matched raw pool.
* **Dedicated P08 B3 result slots**, NEVER accepted P07-B original receipt locations:
  `[0x43FF0200,0x43FF0300)` 256-byte terminal mailbox;
  `[0x42200000,0x42201000)` 4,096-byte journal (16×256);
  `[0x42300000,0x42301000)` 4,096-byte timing sidecars (16×256).
  Standalone A53 ELF can write its actual loadable low-DDR PT_LOAD region; exact span must be independently read from the genuine ELF program headers, including allocated .stack/.heap and FSBL/TF-A/PS reservations.

## B3.1 pre-launch physical polling safeguard — after local preflight PASS

The original 16-image A53 application writes the 256B mailbox DONE sentinel
`0xC0DEF00D` for **startup and progress records**, not only terminal
records. The new independent `pilot_mailbox_classify` Tcl function was
added to `p08_b3_pilot16_run_and_capture.tcl`: it **never** halts A53
merely upon a DONE marker. It verifies exact magic/version, completed-image
count and status; continues through 0/16–16/16 progress, halts and
preserves evidence on explicit `0xDEAD0823` failure, and treats ONLY
`status=0x600D0823`, `frame=15`, `completed=16`,
`fault=0` and DONE as successful terminal. It refuses mismatched
progress indices and count regression; timeouts cannot be accepted.
Unit tests replay real 64×32-bit little-endian byte records into the
**actual Tcl classifier**, including start/progress/finish/failure
states. **The user-authenticated A53 ELF binary is unchanged**:
`29482212c80fb9137b3c185b0cbcdf2000f41417e5af8d3c46b0cd39ecb74fd3`.
Never reuse the earlier pre-fix Tcl version for a physical launch.

### Authorized separate operator execution (after successful local preflight)

User explicitly accepted current B3.1 destructive risks, including
discarding Linux, eight individual approval conditions and reboot.
Run in a dedicated recovery-ready cold-boot JTAG session with
`hw_server` locally available at `tcp:127.0.0.1:3121`.
Commands below are **intentionally destructive**; they are NOT part
of default preflight and cannot be run by GitHub CI.

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p08-b-scaled-latency
git pull --ff-only origin agent/v3-p08-b-scaled-latency
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

export P08_B3_PILOT_STAGE="/home/dna/Thesis_Evidence/p08_b3_pilot16_pc_stage_20261102T043729Z"
export P08_B3_PILOT_BUILD_DIR="/home/dna/Thesis_Evidence/p08_b3_pilot16_build_20261102T044104Z"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P08_B2_4_SCALAR_REPORT="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"
# Keep P07_B4L_REPORTS set to your PREVIOUSLY ACCEPTED original P03
# routed source directory (unchanged bit/XSA/LTX and metrics).
test -f "$P07_B4L_REPORTS/p03_2_ps_mmio.bit"

# Exact original source / genuine new ELF / scalar: NO BOARD
PYTHONPATH="$PWD/src" python scripts/p08_b3_pilot16_physical_run.py \
  --mode preflight --stage "$P08_B3_PILOT_STAGE" \
  --pilot-build "$P08_B3_PILOT_BUILD_DIR" \
  --reset-pins "$P08_B2_RESET_PINS" \
  --oracle "$P08_B2_4_SCALAR_REPORT" --reports "$P07_B4L_REPORTS"

export P08_B3_EVIDENCE="$HOME/Thesis_Evidence/p08_b3_pilot16_physical_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$P08_B3_EVIDENCE"
command -v xsdb
command -v vivado
ss -ltn '( sport = :3121 )'

# DESTRUCTIVE HARDWARE: original PS FPD128 Linux discard, P03 PL,
# all original P02 model/backup and frozen routes/input overwrite,
# low-DDR pilot A53 ELF and two new journals/mailbox.
PYTHONPATH="$PWD/src" python scripts/p08_b3_pilot16_physical_run.py \
  --mode execute \
  --stage "$P08_B3_PILOT_STAGE" \
  --pilot-build "$P08_B3_PILOT_BUILD_DIR" \
  --reset-pins "$P08_B2_RESET_PINS" \
  --oracle "$P08_B2_4_SCALAR_REPORT" \
  --reports "$P07_B4L_REPORTS" \
  --evidence "$P08_B3_EVIDENCE" \
  --dedicated-jtag-owner YES \
  --discard-linux-and-halt-all-a53-approved YES \
  --unproven-boot-ddr-dma-exclusivity-risk-accepted YES \
  --six-original-ddr-transfers-overwrite-approved YES \
  --original-p03-pl-programming-approved YES \
  --low-ddr-new-pilot-elf-overwrite-approved YES \
  --mailbox-and-two-journals-overwrite-approved YES \
  --reboot-and-recovery-approved YES
```

After any JTAG attempt, **reboot/power-cycle KV260; never resume the
halted Linux instance.** Preserve `$P08_B3_EVIDENCE` and use the
standalone PC-only independent physical-verifier:

```bash
export P08_B3_INDEPENDENT_REPORT="$HOME/Thesis_Evidence/p08_b3_pilot16_independent_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P08_B3_INDEPENDENT_REPORT"
PYTHONPATH="$PWD/src" python scripts/p08_b3_pilot16_independent_physical_verify.py \
  --evidence "$P08_B3_EVIDENCE" --stage "$P08_B3_PILOT_STAGE" \
  --oracle "$P08_B2_4_SCALAR_REPORT" \
  --pilot-build "$P08_B3_PILOT_BUILD_DIR" \
  --reports "$P07_B4L_REPORTS" \
  --reset-pins "$P08_B2_RESET_PINS" \
  --out "$P08_B3_INDEPENDENT_REPORT"
sha256sum "$P08_B3_INDEPENDENT_REPORT"
```

No 16-image result may be called accepted physical inference until
this independent same-session source, JTAG and scalar-reference verifier
passes. On any failure, **do not retry destructive JTAG without
diagnosing and rebooting**. Report the `stage.txt`, exact failing
`*.log` and the binary mailbox/sidecars, *not* just the exit code.
No accepted quantitative latency claim from the 16-image pilot.

## Physical risks that MUST be explicitly accepted before any JTAG action

**These are NOT proven safe by SHA256 or PT_LOAD.** The actual DDR controller may still be owned by Linux, U-Boot, TF-A/ATF, PMUFW, other A53 cores, RPU cores, CMA or PL/PS DMA masters. Halting A53 cores is necessary but does not prove these other masters are quiescent or memory spans are reserved. Boot firmware and the standalone ELF's low-DDR exception vectors, stack, heap and page tables may conflict. Programming the FPGA and downloading the ELF can destroy the existing Linux session or interrupt network/serial functions. The 28+MiB original P02 source+backup staging, 4 source route/input transfers, mailboxes and new ELF are **destructive physical writes**. Do NOT test while the board is needed for another workload. Work in a dedicated cold-boot JTAG lab session with serial console and known-good recovery boot media, independent stable power, and a plan to power-cycle/reboot after the run **even on failure**. Never try to resume the halted Linux session.

The historical P07-B JTAG pilots used explicit *accepted-risk* gates, not mathematically proven DDR ownership. For P08-B3 the runner records that the risk remains **UNPROVEN**, regardless of the operator's YES approval. A full independent DDR owner-map / firmware coexistence proof is still not available. Do not equate an accepted risk with owner proof.

## Source added: independently gated same-session run

`scripts/p08_b3_pilot16_physical_run.py`: **DEFAULT `--mode preflight`**, PC only. Revalidates the exact original five source SHA pins, six proposed (nonoverlapping) addresses, 16 scalar JSON accepted SHA, genuine separate new Vitis ELF/map, P03 original XSA/bit/LTX SHAs and routed FPD128 metrics. Regenerates the genuine original pilot ELF/oracle static report and requires byte-for-byte equality to previous admission JSON. Denies all destructive operations by default; `--mode execute` additionally requires **eight individually named `YES` consents** including explicit acceptance of UNPROVEN boot/DDR DMA ownership, discard-Linux, six physical writes, accepted PL programming, low-DDR ELF overwrite, two 4KiB journals+mailbox overwrite, and reboot recovery. Before invoking the hardware it creates a new outside-repo evidence directory recording accepted source SHA and risk.

The physical sequence, **only after explicit approval**:
1. Calls the unchanged accepted P07 `p07_b4i_stop_and_width_gate.tcl` to halt/account for all A53 cores and prove FPD/LPD 128-bit PS width, then programs original SHA-pinned P03.2 bitstream and VIO reset via `p03_2c_program_bitstream.tcl`. Both authentic logs must pass before any model overwrite.
2. NEW `vivado/p08_b3_pilot16_six_ddr_stage.tcl`: physically stages the immutable original 27×512KiB P02 from 27 fixed-size chunks, **twice** into mutable + immutable backup, and the other 4 original physical payloads; uses physical **PSU/APU target** (not A53 virtual address), reads every staged byte back, and stops on any mismatch. Python independently rechecks both 27×512KiB full SHA and every source file byte-for-byte against its original frozen host byte stream. No ELF download allowed before this gate.
3. NEW `vivado/p08_b3_pilot16_run_and_capture.tcl`: re-halts and processor-resets A53 #0 (after signed source readbacks), physically zeros and reads back dedicated terminal mailbox + both 4KiB sidecars, downloads *exact operator SHA pinned PILOT16 ELF*, launches, polls terminal for a bounded duration, re-halts A53 and captures exact 256B mailbox + 4096B neural journal + 4096B timing journal via physical PSU readback. It accepts only strict 16/16 PASS, never a timeout or partial sample.
4. Runner applies the **UNTRUSTED file syntax and original scalar** verifier as first-pass numerical gate and preserves all logs/readbacks/CRC evidence; independent physical acceptance must still re-read the evidence.
5. NEW `scripts/p08_b3_pilot16_independent_physical_verify.py` independently parses exact original physical stage/launch transcripts, accepted PS width & P03 programming, exact SHA-pinned original six readbacks, zeroed/result mailboxes and original scalar numeric data for all 16. It admits only those complete same-session hardware artifacts. Even a pass means actual first16 classifier/spike/trace-FNV parity, **NOT direct raw 26×1010 neuron-trace byte equality**, **NOT calibrated benchmark latency** and **NOT energy/speedup**. Physical provenance is based on attributable same-session XSDB logs and source readbacks, not cryptographic device attestation.

## Operator PC-only PRE-FLIGHT — safe now, no board touched

From the same `Loihi_Digital_Twin/v3` root on the exact branch:

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
  tests/test_p08_b3_pilot16.py \
  tests/test_p08_b3_pilot16_physical.py \
  tests/test_p08_b2_4_numerical.py

export P08_B3_PILOT_BUILD_DIR="$HOME/Thesis_Evidence/p08_b3_pilot16_build_20261102T044104Z"
export P08_B2_4_SCALAR_REPORT="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
# P08_B3_PILOT_STAGE is the NEW external dir from the previously passed
#   scripts/p08_b3_pilot16_stage_host.py command.
# P07_B4L_REPORTS = accepted original P03 routed XSA/bit/LTX directory.
test -d "$P08_B3_PILOT_STAGE"
test -d "$P07_B4L_REPORTS"
PYTHONPATH="$PWD/src" python scripts/p08_b3_pilot16_physical_run.py \
  --mode preflight \
  --stage "$P08_B3_PILOT_STAGE" \
  --pilot-build "$P08_B3_PILOT_BUILD_DIR" \
  --reset-pins "$P08_B2_RESET_PINS" \
  --oracle "$P08_B2_4_SCALAR_REPORT" \
  --reports "$P07_B4L_REPORTS"
```

Expected:
`P08_B3_PILOT16_ORIGINAL_SIGNED_SIX_SOURCE_ELF_ORACLE_PREFLIGHT_PASS=1`,
`P08_B3_PILOT16_PSU_DDR_BOOT_DMA_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0`,
`P08_B3_PILOT16_READ_ONLY_BOARD_VISITED=0`,
`P08_B3_PILOT16_EXECUTION_NOT_AUTHORIZED_BY_PREFLIGHT=1`.

No JTAG executable instructions run during preflight. If any source or pin differs, **STOP**, preserve original files and report exact error.

## Destructive step — separate user authorisation required AFTER risk review

Do not invoke `--mode execute` merely because `--mode preflight` passed. **Before any physical operation**, obtain a specific acknowledgement that the operator reviewed the exact proposed DDR spans, agrees to terminate/discard Linux and overwrite P03 PL, permits the low-DDR A53 download, accepts unproven other-PS/firmware/DMA ownership and has a recovery/reboot plan. The full execute command also requires eight independent explicit `--<risk> YES` flags. Evidence must go into a **NEW external directory**. This document intentionally omits the execute command until operator returns that risk acknowledgement; no background or remote hardware action will happen.

Upon a future operator-approved attempt, the independent verifier is run on the copied physical evidence; do not report accepted pilot inference until it passes. Original TEST sealed; accepted original frozen A/B physical evidence untouched; P09 deferred.
