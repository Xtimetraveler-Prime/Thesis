# P08-B4.4.2 — NEW original full1024 reset-profile physical run

STATUS: NEW offline Vitis original B2.4 profile ELF/map/ELF-admission have
GENUINELY PASSED on operator PC. New JTAG source and independent
physical verifier native CI have passed ONLY on synthetic input; NO
NEW profile physical run has been performed or accepted. The original
B2.3 Vitis ELF and accepted B4.2 full1024 physical evidence remain
IMMUTABLE. Official MNIST TEST remains SEALED.

## Frozen provenance and new genuine operator build hashes

NEW profile ELF:
 /home/dna/Thesis_Evidence/p08_b44_reset_profile_retry_20261102T195900Z/vitis_workspace/p08_b44_reset_profile_1024.elf
 SHA256 bed1301c69594bf7ebeaa37765ad2cb3035aa0f6d5e9cb4d1fb4637042be3ab3

NEW profile map:
 /home/dna/Thesis_Evidence/p08_b44_reset_profile_retry_20261102T195900Z/vitis_workspace/p08_b44_reset_profile_1024.map
 SHA256 d94fa2695e82cc3a501442313bb77e89eb046f01450167108832a190fd9fd2c9

NEW Vitis profile offline ELF admission:
 /home/dna/Thesis_Evidence/p08_b44_reset_profile_retry_20261102T195900Z/p08_b44_profile_elf_ptload_preflight.json
 SHA256 7a5818dc5469ea288fefcefb87ebc4fd3ab1e5c7bdce0bbfda717a6f2787b129

Original accepted full1024 independent B4.2 physical numerical and
timing report SHA256
297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032.
Original accepted 1023 ordinary-image B4.4 timing report SHA256
4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81.
Original first16 independently signed B3 physical report SHA256
b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11.
Original accepted B4.1 64-shard scalar oracle SHA256
7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8.
Existing P03/27core original SHA and all original accepted
B2.4 frozen trained assets and original B2.3 ELF/map unchanged.

## Step 1 — PULL and TEST (PC only, no FPGA)

    cd ~/Git/Thesis
    git fetch origin
    git switch agent/v3-p08-b44-profiling
    git pull --ff-only origin agent/v3-p08-b44-profiling
    git status --short
    git rev-parse HEAD
    source ~/Git/Thesis/.venv-p08/bin/activate
    cd Loihi_Digital_Twin/v3

    PYTHONPATH="$PWD/src" python -m pytest -q -rs \
      tests/test_p08_b44_profile_physical.py \
      tests/test_p08_b4_2_full1024_physical.py \
      tests/test_p08_b44_reset_profile_sidecar.py \
      tests/test_p08_b44_profile_elf_admission.py \
      tests/test_p08_b44_build_offline.py

## Step 2 — Restore source arguments and original frozen original proof

    export P08_B4_SHARDS="$HOME/Thesis_Evidence/p08_b4_1_original_scalar_shards_20261102T060939Z"
    export P08_B4_INGRESS="$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z"
    export P08_B4_FIRST16="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_20261102T042201Z.json"
    export P08_B4_FULL_ORACLE="$HOME/Thesis_Evidence/p08_b4_1_full1024_scalar_20261102T143900Z.json"
    export P08_B3_INDEPENDENT_REPORT="$HOME/Thesis_Evidence/p08_b3_pilot16_independent_20261102T055256Z.json"
    export P08_B3_PILOT_STAGE="$HOME/Thesis_Evidence/p08_b3_pilot16_pc_stage_20261102T043729Z"
    export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
    export P08_B44_ORIGINAL_B4_PHYSICAL_REPORT="$HOME/Thesis_Evidence/p08_b4_2_independent1024_20261102T184928Z.json"
    export P08_B44_ORIGINAL_TIMING="$HOME/Thesis_Evidence/p08_b4_4_first1024_one_session_descriptive_20261102T191317Z.json"
    export P08_B44_PROFILE_BUILD="$HOME/Thesis_Evidence/p08_b44_reset_profile_retry_20261102T195900Z"
    export P08_B44_PROFILE_ELF="$P08_B44_PROFILE_BUILD/vitis_workspace/p08_b44_reset_profile_1024.elf"
    export P08_B44_PROFILE_MAP="$P08_B44_PROFILE_BUILD/vitis_workspace/p08_b44_reset_profile_1024.map"
    export P08_B44_PROFILE_ELF_AUDIT="$P08_B44_PROFILE_BUILD/p08_b44_profile_elf_ptload_preflight.json"

    sha256sum "$P08_B44_PROFILE_ELF" "$P08_B44_PROFILE_MAP" "$P08_B44_PROFILE_ELF_AUDIT"
    sha256sum "$P08_B4_FULL_ORACLE" "$P08_B3_INDEPENDENT_REPORT"
    sha256sum "$P08_B44_ORIGINAL_B4_PHYSICAL_REPORT" "$P08_B44_ORIGINAL_TIMING"

Keep P07_B4L_REPORTS set to previously accepted genuine P03.2c
bitstream/LTX/XSA/post-route reports; do not substitute a new P03.

The ORIGINAL B4.2 Vitis ELF/map must be under canonical original
B4.2 filenames, and not the new profile names. If original
P08_B4_ELF and P08_B4_MAP remain set in shell, verify original SHA and
filenames first. Otherwise create fresh external COPIES from accepted
B2.3 Vitis originals, no overwrites/recompilation:

    export P08_B44_ORIGINAL_OLD_DIR="$HOME/Thesis_Evidence/p08_b44_original_source_copies_$(date -u +%Y%m%dT%H%M%SZ)"
    test ! -e "$P08_B44_ORIGINAL_OLD_DIR"
    mkdir -m 700 "$P08_B44_ORIGINAL_OLD_DIR"
    cp -- "$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf" "$P08_B44_ORIGINAL_OLD_DIR/p08_b4_original_full1024.elf"
    cp -- "$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.map" "$P08_B44_ORIGINAL_OLD_DIR/p08_b4_original_full1024.map"
    export P08_B4_ELF="$P08_B44_ORIGINAL_OLD_DIR/p08_b4_original_full1024.elf"
    export P08_B4_MAP="$P08_B44_ORIGINAL_OLD_DIR/p08_b4_original_full1024.map"
    sha256sum "$P08_B4_ELF" "$P08_B4_MAP"

Original B2.3 ELF expected SHA256:
0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1.
Original B2.3 map expected SHA256:
f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc.

## Step 3 — Mandatory new B4.4 READ-ONLY physical preflight

    PYTHONPATH="$PWD/src" python scripts/p08_b44_profile_physical_run.py \
      --mode preflight \
      --stage "$P08_B3_PILOT_STAGE" \
      --shards "$P08_B4_SHARDS" \
      --ingress "$P08_B4_INGRESS" \
      --oracle "$P08_B4_FULL_ORACLE" \
      --first16 "$P08_B4_FIRST16" \
      --b3-report "$P08_B3_INDEPENDENT_REPORT" \
      --elf "$P08_B4_ELF" \
      --linker-map "$P08_B4_MAP" \
      --reset-pins "$P08_B2_RESET_PINS" \
      --reports "$P07_B4L_REPORTS" \
      --b4-independent-report "$P08_B44_ORIGINAL_B4_PHYSICAL_REPORT" \
      --b44-timing-report "$P08_B44_ORIGINAL_TIMING" \
      --profile-elf "$P08_B44_PROFILE_ELF" \
      --profile-map "$P08_B44_PROFILE_MAP" \
      --profile-elf-audit "$P08_B44_PROFILE_ELF_AUDIT"

MANDATORY marker:
P08_B44_PROFILE1024_ORIGINAL_64_SHARD_SCALAR_AND_SEPARATE_REAL_ELF_PREFLIGHT_PASS=1
P08_B44_PROFILE1024_READONLY_BOARD_VISITED=0
P08_B44_PROFILE1024_DESTRUCTIVE_JTAG_NOT_AUTHORIZED_BY_PREFLIGHT=1

If NO-GO, STOP. Preflight does NOT authorize destructive JTAG.

## Step 4 — Explicitly NEW destructive physical experiment

This experiment interrupts Linux, physically programs P03 PL and
overwrites original frozen P02 context/routing/1024 raw source DDR,
original 256B terminal mailbox at 0x43FF0200, original 2 x
1024x256B neural/timing output regions at 0x42200000/0x42300000,
PLUS new original full1024 experimental RESET profile region
[0x42400000,0x42440000) = 262144B. Its independent PS/FSBL/RPU/
firmware/DMA DDR ownership is STILL UNPROVEN and no speedup/energy
result follows automatically. Do not execute unless the correct
KV260 physical targets, serial/recovery, stable power and dedicated
JTAG coldboot owner are confirmed and operator personally accepts
the additional DDR destructive risk.

Run ONLY after fresh B4.4 read-only preflight PASS and new operator
approval of all nine distinct YES flags. Ensure hw_server listening
at tcp:127.0.0.1:3121. Use a FRESH evidence directory, never old B4.

    export P08_B44_PROFILE_PHYSICAL="$HOME/Thesis_Evidence/p08_b44_profile1024_physical_$(date -u +%Y%m%dT%H%M%SZ)"
    test ! -e "$P08_B44_PROFILE_PHYSICAL"
    command -v xsdb
    command -v vivado
    ss -ltn | grep ':3121'

    PYTHONPATH="$PWD/src" python scripts/p08_b44_profile_physical_run.py \
      --mode execute \
      --stage "$P08_B3_PILOT_STAGE" \
      --shards "$P08_B4_SHARDS" \
      --ingress "$P08_B4_INGRESS" \
      --oracle "$P08_B4_FULL_ORACLE" \
      --first16 "$P08_B4_FIRST16" \
      --b3-report "$P08_B3_INDEPENDENT_REPORT" \
      --elf "$P08_B4_ELF" \
      --linker-map "$P08_B4_MAP" \
      --reset-pins "$P08_B2_RESET_PINS" \
      --reports "$P07_B4L_REPORTS" \
      --b4-independent-report "$P08_B44_ORIGINAL_B4_PHYSICAL_REPORT" \
      --b44-timing-report "$P08_B44_ORIGINAL_TIMING" \
      --profile-elf "$P08_B44_PROFILE_ELF" \
      --profile-map "$P08_B44_PROFILE_MAP" \
      --profile-elf-audit "$P08_B44_PROFILE_ELF_AUDIT" \
      --evidence "$P08_B44_PROFILE_PHYSICAL" \
      --dedicated-jtag-owner YES \
      --discard-linux-and-halt-all-a53-approved YES \
      --unproven-boot-ddr-dma-exclusivity-risk-accepted YES \
      --six-original-ddr-transfers-overwrite-approved YES \
      --original-p03-pl-programming-approved YES \
      --low-ddr-full1024-elf-overwrite-approved YES \
      --mailbox-and-full1024-journals-overwrite-approved YES \
      --extra-profile-ddr-region-overwrite-approved YES \
      --reboot-and-recovery-approved YES

The new source-authenticated Tcl has an automatic 3600-poll no-new
completed-image watchdog, 172800 global poll bound, exact terminal
ordinal1023/1024 success gate, 4th zero+readback region and 1024x256B
reset-profile physical capture. It intentionally reuses original
27core source/readback and accepted P03 shell from B4.2, but NEVER
downloads the original accepted B2.3 ELF in this new experiment.

Preliminary success markers (NOT independent physical acceptance):
P08_B44_PROFILE1024_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1
P08_B44_PROFILE1024_EXPERIMENTAL_DDR_0x42400000_ZERO_READBACK_PASS=1
P08_B44_PROFILE1024_REAL_1024_RESET_PROFILE_SIDECAR_PHYSICAL_CAPTURED=1
P08_B44_PROFILE1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1
P08_B44_PROFILE1024_ORIGINAL_1024_NEURAL_FNV_SCALAR_PRECHECK_PASS=1
P08_B44_PROFILE1024_1024_RESET_SHA_MEMCPY_CACHE_STRUCTURAL_PRECHECK_PASS=1
P08_B44_PROFILE1024_INDEPENDENT_PHYSICAL_PROVENANCE_PENDING=1

## During long run — proven NON-INTRUSIVE PC-only mailbox monitoring

In a SECOND terminal use the existing PC-side cached mailbox.
No additional JTAG owner, XSDB, CPU halt, board interrupt or writes.

    export P08_B44_MONITOR="$P08_B44_PROFILE_PHYSICAL"
    python scripts/p08_b4_2_monitor_mailbox_pc_only.py \
      --evidence "$P08_B44_MONITOR" \
      --capture-subdir profile1024_capture \
      --samples 2 --interval 20

The monitor reads the original owning XSDB's 256B mailbox_poll.tmp
PC cached file. An unchanged image count over 20 seconds is not a
hang. If XSDB temporarily removes/replaces cache, missing/partial
snapshot is normal. Terminal SUCCESS requires exact 1024/1024 and
its independent original frozen scalar proof still must PASS.

## Step 5 — REBOOT after any JTAG attempt, then separate PC-only physical verification

Power-cycle/reboot KV260 after any destructive attempt, successful
or failed; NEVER resume halted Linux. Preserve the full evidence root,
all XSDB/Vivado logs, original six original frozen source receipts,
1024 neural+timing journals, 1024 reset profiles and true terminal.

    export P08_B44_PROFILE_INDEPENDENT="$HOME/Thesis_Evidence/p08_b44_profile1024_independent_$(date -u +%Y%m%dT%H%M%SZ).json"
    test ! -e "$P08_B44_PROFILE_INDEPENDENT"

    PYTHONPATH="$PWD/src" python \
      scripts/p08_b44_profile_independent_physical_verify.py \
      --evidence "$P08_B44_PROFILE_PHYSICAL" \
      --stage "$P08_B3_PILOT_STAGE" \
      --shards "$P08_B4_SHARDS" \
      --ingress "$P08_B4_INGRESS" \
      --oracle "$P08_B4_FULL_ORACLE" \
      --first16 "$P08_B4_FIRST16" \
      --b3-report "$P08_B3_INDEPENDENT_REPORT" \
      --elf "$P08_B4_ELF" \
      --linker-map "$P08_B4_MAP" \
      --reset-pins "$P08_B2_RESET_PINS" \
      --reports "$P07_B4L_REPORTS" \
      --b4-independent-report "$P08_B44_ORIGINAL_B4_PHYSICAL_REPORT" \
      --b44-timing-report "$P08_B44_ORIGINAL_TIMING" \
      --profile-elf "$P08_B44_PROFILE_ELF" \
      --profile-map "$P08_B44_PROFILE_MAP" \
      --profile-elf-audit "$P08_B44_PROFILE_ELF_AUDIT" \
      --out "$P08_B44_PROFILE_INDEPENDENT"

    sha256sum "$P08_B44_PROFILE_INDEPENDENT"

Final genuine independent acceptance requires:
P08_B44_NEW_RESET_PROFILE1024_INDEPENDENT_SAME_SESSION_JTAG_PROVENANCE_PASS=1
P08_B44_NEW_RESET_PROFILE1024_ORIGINAL_1024_NEURAL_FNV_SPIKE_PARITY_PASS=1
P08_B44_NEW_RESET_PROFILE1024_ALL_1024_REAL_SHA_COPY_CACHE_SUBSPAN_COUNTERS_PASS=1
P08_B44_NEW_RESET_PROFILE1024_NEW_PAIRED_AB_BA_AB_BENCHMARK_ACCEPTED=0

This is a new instrumented single-session A53 reset bottleneck
description, NOT the original uninstrumented B4.2 service baseline,
nor a benchmark of calibrated PL-only compute, system energy
or repeated A-vs-B latency (still separate P08-B closeout gates).
No direct all-neuron raw trace capture, no independently proved
PS/firmware/RPU/PL-DMA DDR exclusivity, no official MNIST TEST.
