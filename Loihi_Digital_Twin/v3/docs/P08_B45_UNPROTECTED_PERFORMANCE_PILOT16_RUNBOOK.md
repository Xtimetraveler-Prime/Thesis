# P08-B4.5 — reduced-integrity PERFORMANCE-ONLY KV260 16-image pilot

**Status:** Source and native/no-board CI prepared. Genuine new Vitis 2025.2
ELF/map builds, independent operator-local admission, and live 16-image
hardware execution **NOT YET RUN**. This is a new *research experiment*,
not a repair or weakening of original protected B4.5 A53 binaries.

Two separate, deliberately **UNPROTECTED** pilot16 A53 executables are
built from original frozen full27-core/26-tick/702-dispatch neural and
TRAIN-derived source. Original independent B3/P03/Track A/B4/B4.4
physical evidence, original 27 P02 contexts, original SHA header,
routed XSA, BIT/LTX, original A53 binaries, and the fail-closed
`p08_b45_a53_backup_guard.c` are **unchanged**.

**What we measure:** once: one-time 27 SHA-256 source validation at
session bind + per-image source/destination P02 header checks; unchecked:
no reset-content SHA or headers at bind or per-image. Both preserve
quiescence, actual 14,155,776-byte copy, cache/barrier, poison-on-error,
same full original neural inference, raw-pool source admission and
result/timing journals. No in-band XMPU callbacks exist in these distinct
performance-only builds, and sidecar word 19 MUST be zero. The source
pool still checks the original COMPLETE 1024x784 raw image SHA, but
executes **only first 16** original TRAIN-derived images in each pilot.
A separate `0x42400000` 4096-byte reset-only sidecar is captured.

**Reduced integrity guarantee:** Start-of-session A53 once validation
and host same-session signed source staging/readback, plus **all 27
post-run hardware backup readback byte equal to original frozen
contexts**. This is stronger evidence of ordinary numerical correctness
and stable endpoints than none, but cannot disprove transient backup
modification or assert a runtime protection mechanism. In particular,
the once variant is NOT secure immutable memory. The unchecked mode is a
performance lower bound, NOT a production configuration.

**Remaining physical hazard:** Original JTAG workflow halts Linux A53,
programs accepted P03 PL, writes original six DDR ranges and low-DDR
standalone ELF, and writes the 256B mailbox + 3x4096B journaling rows.
These operations can corrupt live Linux/boot/other-master memory without
a separately disposable dedicated session. The previously accepted
P07-B4i original A53 halt/FPD+LPD128 gate MUST PASS first. A failed
gate STOPS before any new PL/DDR/ELF operations; old A53 debug-disabled
does NOT mean "powered down." Accept known residual DDR early-boot/
DMA exclusive-ownership uncertainty explicitly, even without XMPU.
Have physical power-cycle/recovery available; NEVER resume halted Linux.
No boot media/QSPI/FSBL/security register/XMPU changes in this plan.

## 1. PC terminal: fetch and run inherited + new tests

Everything in this section is on your Ubuntu PC in VS Code. **NOT PuTTY.**

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b45-unprotected-pilot16
git pull --ff-only origin agent/v3-p08-b45-unprotected-pilot16
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b45_perf_pilot16.py \
  tests/test_p08_b45_reset_variants.py \
  tests/test_p08_b45_a53_build.py \
  tests/test_p08_b4_2_full1024_physical.py \
  tests/test_p08_b44_profile_physical.py
```

Native CI is no-board and is NOT actual Vitis evidence.

## 2. PC terminal: use accepted original frozen source paths

These are the **previously user-accepted, stored absolute paths** from
the original P08-B3/B4/B4.4/B4.5 operator runbooks. DO NOT regenerate
model/validation assets or choose a different B2 checkpoint. If a path
was relocated, use read-only `find` for the exact basename and
SHA-verify the discovered candidate before changing the export.

```bash
export P08_B45_ORIGINAL_ELF="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P08_B3_PILOT_STAGE="$HOME/Thesis_Evidence/p08_b3_pilot16_pc_stage_20261102T043729Z"
export P08_B4_FIRST16="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"
export P08_B3_INDEPENDENT_REPORT="$HOME/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json"

test -s "$P08_B45_ORIGINAL_ELF" &&
test -s "$P07_B4L_REPORTS/p03_2_ps_mmio.xsa" &&
test -s "$P08_B2_RESET_PINS/p08_b2_2_original_context_sha256.h" &&
test -s "$P08_B4_FIRST16" &&
test -s "$P08_B3_INDEPENDENT_REPORT" &&
test -s "$P08_B3_PILOT_STAGE/original_27core_backup_source_14155776.bin" &&
echo "P08_B45_PERF_ACCEPTED_PC_INPUTS_PRESENT=1"

sha256sum "$P08_B45_ORIGINAL_ELF" \
 "$P07_B4L_REPORTS/p03_2_ps_mmio.xsa" \
 "$P08_B2_RESET_PINS/p08_b2_2_original_context_sha256.h" \
 "$P08_B3_INDEPENDENT_REPORT"
```

Expected SHA order:
```text
0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1
52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171
b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11
```

NOTE: the correct accepted original B2.2 SHA header is
`5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171`.

## 3. PC terminal: build new, distinct genuine Vitis 2025.2 ELFs

```bash
source "$HOME/Vivado/2025.2/Vitis/settings64.sh"
command -v vitis
command -v aarch64-none-elf-readelf
command -v aarch64-none-elf-nm

export P08_B45_MODE=once
export P08_B45_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_perf_once_pilot16_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p08_b45_perf_pilot16.sh
export P08_B45_PERF_BUILD_ONCE="$P08_B45_BUILD_DIR"

export P08_B45_MODE=unchecked
export P08_B45_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_perf_unchecked_pilot16_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p08_b45_perf_pilot16.sh
export P08_B45_PERF_BUILD_UNCHECKED="$P08_B45_BUILD_DIR"
```

Each script fails closed unless the original canonical B2.3 ELF,
routed XSA/metrics, B2.2 SHA header+manifest, genuine
Vitis/AArch64 tools, exact freshly copied unique mode source,
new genuine ELF/map and new no-overwrite offline admission PASS.
Vitis runs exclusively on the PC.

Expected file examples:
```text
$P08_B45_PERF_BUILD_ONCE/vitis_workspace/p08_b45_perf_once_pilot16.elf
$P08_B45_PERF_BUILD_ONCE/vitis_workspace/p08_b45_perf_once_pilot16.map
$P08_B45_PERF_BUILD_ONCE/p08_b45_perf_once_pilot16_elf_admission.json
$P08_B45_PERF_BUILD_UNCHECKED/vitis_workspace/p08_b45_perf_unchecked_pilot16.elf
$P08_B45_PERF_BUILD_UNCHECKED/vitis_workspace/p08_b45_perf_unchecked_pilot16.map
$P08_B45_PERF_BUILD_UNCHECKED/p08_b45_perf_unchecked_pilot16_elf_admission.json
```

## 4. PC terminal: BOTH fully offline physical-source preflights

Only AFTER both authentic new real Vitis builds succeed:

```bash
P08_B45_COMMON=(
 --stage "$P08_B3_PILOT_STAGE"
 --first16 "$P08_B4_FIRST16"
 --b3-report "$P08_B3_INDEPENDENT_REPORT"
 --original-elf "$P08_B45_ORIGINAL_ELF"
 --reset-pins "$P08_B2_RESET_PINS"
 --reports "$P07_B4L_REPORTS"
)

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_pilot16_physical_run.py \
 --experiment once --build "$P08_B45_PERF_BUILD_ONCE" \
 "${P08_B45_COMMON[@]}" --mode preflight

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_pilot16_physical_run.py \
 --experiment unchecked --build "$P08_B45_PERF_BUILD_UNCHECKED" \
 "${P08_B45_COMMON[@]}" --mode preflight
```

Each must print:
```text
P08_B45_PERF_PILOT16_ORIGINAL_SOURCES_AND_REAL_ELF_OFFLINE_PASS=1
P08_B45_PERF_BACKUP_HARDWARE_PROTECTED=0
P08_B45_PERF_UNPROVEN_BOOT_DMA_DDR_OWNERSHIP_EXPLICIT=1
P08_B45_PERF_BOARD_VISITED=0
P08_B45_PERF_DESTRUCTIVE_JTAG_NOT_AUTHORIZED_BY_PREFLIGHT=1
```

These only prove source/ELF admission; NONE touch KV260.

## 5. FIRST physical pilot (16 frames, ONCE) — operator approved

**Prerequisite, do not skip:** Successful offline section 4;
KV260 normally booted and reachable on PuTTY, fresh dedicated
disposable A53/JTAG session (discard its Linux instance); known
recovery/power-cycle method; PC `hw_server` already started and no
other active XSDB/Vivado client. Board remains live Linux until the
old strict stop/PS width gate takes ownership; it must PASS before
any PL, DDR, or ELF step.

**PuTTY:** these are separate short commands, not multi-line shell.
To inspect whether a default FPGA app is currently active:

```bash
sudo xmutil listapps
```

Only if an accelerated application is active and the operator is
ready to free its PL under the original accepted sequence:

```bash
sudo xmutil unloadapp
```

No other PuTTY command is required for the pilot. Do not issue
`devmem`, `mwr`, `loadapp`, QSPI or FSBL commands. The remaining
commands are all in the **PC's VS Code terminal**, which supports
multi-line paste.

**Physical execution is destructive.** The following command includes
TEN explicit, separate affirmative risk approvals. Execute only if
you have accepted all ten scope-specific actions, understand
that memory ownership beyond this disposable JTAG session is not
independently established, and can physically power-cycle afterwards.

```bash
export P08_B45_PERF_PHYSICAL_ONCE="$HOME/Thesis_Evidence/p08_b45_perf_once_pilot16_physical_$(date -u +%Y%m%dT%H%M%SZ)"

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_pilot16_physical_run.py \
 --experiment once --build "$P08_B45_PERF_BUILD_ONCE" \
 "${P08_B45_COMMON[@]}" \
 --mode execute \
 --evidence "$P08_B45_PERF_PHYSICAL_ONCE" \
 --dedicated-jtag-owner YES \
 --discard-linux-and-halt-all-a53-approved YES \
 --unproven-boot-ddr-dma-exclusivity-risk-accepted YES \
 --six-original-ddr-transfers-overwrite-approved YES \
 --original-p03-pl-programming-approved YES \
 --low-ddr-new-performance-elf-overwrite-approved YES \
 --mailbox-and-three-journals-overwrite-approved YES \
 --unprotected-backup-integrity-tradeoff-accepted YES \
 --post-run-backup-readback-approved YES \
 --reboot-and-recovery-approved YES
```

After ANY attempt (PASS or FAIL), **POWER CYCLE / REBOOT THE KV260**
before returning to normal Linux operation or starting another
JTAG session. In the old JTAG takeover, Linux-owned A53 cores have
been stopped; do **not** attempt to resume that Linux instance.

An accepted preliminary marker is:
`P08_B45_PERF_PILOT16_SAME_SESSION_JTAG_SCALAR_FNV_AND_BACKUP_PASS=1`.
This demands same-session original six DDR source readbacks,
16 exact scalar neural/FNV results, 16 intact timing and reset rows,
and 27 out-of-band postrun backup physical readbacks identical to
original source. It does NOT prove backup's security.

## 6. Independent PC-only acceptance of first pilot (after reboot)

```bash
export P08_B45_PERF_ONCE_INDEPENDENT="$HOME/Thesis_Evidence/p08_b45_perf_once_pilot16_independent_$(date -u +%Y%m%dT%H%M%SZ).json"

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_pilot16_independent_verify.py \
 --experiment once --build "$P08_B45_PERF_BUILD_ONCE" \
 "${P08_B45_COMMON[@]}" \
 --evidence "$P08_B45_PERF_PHYSICAL_ONCE" \
 --out "$P08_B45_PERF_ONCE_INDEPENDENT"

sha256sum "$P08_B45_PERF_ONCE_INDEPENDENT"
```

Only if the **separate independent audit PASS** should we accept
the once first16 performance and neural correctness result.
Report full actual report SHA and reset-median/P95,
and any true operator-observed failed JTAG stage. A reset
within phase0, same-session 16 images and all 27 postbackup SHA
matches are necessary; they do **not** make per-image source SHA
verification equivalently secure.

## 7. SECOND physical pilot (16 frames, unchecked) — AFTER first accepted

Repeat the **same PuTTY one-line preparation** under a fresh
cold boot, dedicated JTAG session and separately accepted
risk flags. The original P03 width-first gate is repeated because
every real hardware run is a new session. Keep the once evidence
immutable; use an entirely new evidence root:

```bash
export P08_B45_PERF_PHYSICAL_UNCHECKED="$HOME/Thesis_Evidence/p08_b45_perf_unchecked_pilot16_physical_$(date -u +%Y%m%dT%H%M%SZ)"

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_pilot16_physical_run.py \
 --experiment unchecked --build "$P08_B45_PERF_BUILD_UNCHECKED" \
 "${P08_B45_COMMON[@]}" \
 --mode execute \
 --evidence "$P08_B45_PERF_PHYSICAL_UNCHECKED" \
 --dedicated-jtag-owner YES \
 --discard-linux-and-halt-all-a53-approved YES \
 --unproven-boot-ddr-dma-exclusivity-risk-accepted YES \
 --six-original-ddr-transfers-overwrite-approved YES \
 --original-p03-pl-programming-approved YES \
 --low-ddr-new-performance-elf-overwrite-approved YES \
 --mailbox-and-three-journals-overwrite-approved YES \
 --unprotected-backup-integrity-tradeoff-accepted YES \
 --post-run-backup-readback-approved YES \
 --reboot-and-recovery-approved YES
```

Power-cycle the board again immediately after the JTAG attempt,
whether it succeeds or fails.

```bash
export P08_B45_PERF_UNCHECKED_INDEPENDENT="$HOME/Thesis_Evidence/p08_b45_perf_unchecked_pilot16_independent_$(date -u +%Y%m%dT%H%M%SZ).json"

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
 scripts/p08_b45_perf_pilot16_independent_verify.py \
 --experiment unchecked --build "$P08_B45_PERF_BUILD_UNCHECKED" \
 "${P08_B45_COMMON[@]}" \
 --evidence "$P08_B45_PERF_PHYSICAL_UNCHECKED" \
 --out "$P08_B45_PERF_UNCHECKED_INDEPENDENT"

sha256sum "$P08_B45_PERF_UNCHECKED_INDEPENDENT"
```

**STOP if any stage fails**, preserve all evidence and reboot.
Do not automatically retry or weaken existing B4i debug/PS width
safety gate. An unsuccessful or missing 27-backup postrun capture
is not physical pass.

## 8. Pilot interpretation, next full1024 work

A 16-frame pilot is an initial numerical, instrumentation and
pipeline-ownership feasibility test, **not** a statistically complete
full1024 performance comparison or a protected one-time-authenticated
system. Its expected lower reset-service time is a hypothesis based
on the accepted original B4.4 full-SHA reset component timing, not
a claimed result until genuine measurements are captured.

After both pilot independent receipts pass and the operator reviews
real latency and protection limitations, **separate new work** must
produce distinct 1024-image binaries, same-width original JTAG
staging/capture, pair-appropriate offline admission, 1024 oracle
and independent 1,023 ordinary-frame timing analysis. Never
merely increase `B23_FRAMES` in a local source file or relax the
pilot's independent SHA. Keep original accepted P03 and B4.4
baseline unchanged. Official Track B MNIST TEST remains SEALED.
