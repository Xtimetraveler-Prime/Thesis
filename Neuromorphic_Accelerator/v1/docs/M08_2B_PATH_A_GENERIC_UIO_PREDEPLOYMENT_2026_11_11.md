# M08.2b Path A: native PL_FLAT staging accepted, dual-UIO OFFLINE candidate

2026-11-11 owner evidence, one consolidated M08.2b milestone. PR #83 DRAFT and unmerged. Absolutely no M08 physical programming, Linux firmware install, or PS AXI transfers.

## New genuine owner evidence received

The owner uploaded **six** separate originals: 02_bootgen_original.log, 05_package_review.json, 04_dtbo_roundtrip_original.log, 99_evidence_sha256.txt from the first-stage offline packaging evidence; and 01_board_stdout.log with its 04_evidence_sha256.txt from a new READ-ONLY Linux SSH capture.

The three supplied original package files, each independently hashed against the user's ORIGINAL 99_evidence_sha256.txt:
- 02_bootgen_original.log: f9709985b603aacc49960ae81b5cd1281782559be0355043feafbe961adae355
- 05_package_review.json: ba16a46c516f7dd626c3942013f9c9891dbb0d61ae8a6bf3d41d81c62cc3579b
- 04_dtbo_roundtrip_original.log: c4a6c2634777532b78e347ca955e62ce8c4bb4419af52f7c526b597bdffb6e2b

The package original ledger 99_evidence_sha256.txt SHA256 was independently measured as b69e8a463110fb69d2deb34adccd13a2e18d5261eba1a50ad9decd773282431f. The remaining ledger entries for other original files, including the binary converted .bit.bin and .dtbo, were owner-side recorded, NOT independently byte-rehashed because those files were not uploaded. Preserve all native original files on the PC.

Original Bootgen v2025.2 stdout confirms Bootimage generated successfully. The original first-stage review status is OFFLINE_PACKAGE_STAGED_NO_BOARD_NO_MMIO_ACCESS. Original fan-preserving input .bit SHA 2d749451f46fe0660a9e78081cb6c92920a608ba16c084f37d2e1ab32f3e8af8. Converted original .bit.bin file SHA a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b, size 7,797,692 bytes. Genuine dtc round trip original compiled DTBO SHA 2a3608d5c7f84f1c62e4324ca3b5538692b449a6b2b8a1a5a4a0399a5dd6fd4e. It contains FPGA-full target and the stock four reset IDs 0x74..0x77 with valid __fixups__ for fpga_full and zynqmp_reset. The decompiler printed one unresolved reset-phandle warning: those 0xffffffff values are SYMBOLIC fixup placeholders, not a genuine runtime error nor a verified Linux application. Do not try to hardcode the placeholders or call xmutil to test this now. The package shell_type is PL_FLAT, one slot; stock K26 Linux runs XRT_FLAT, one slot. The new package is review-only, no Linux MMIO devices included.

The new original PC SSH stdout 01_board_stdout.log SHA d59a2554acb027417f24e84ce093c5d79c6a0bf1e2f6f0766551ea2b15c8801b independently matches its owner 04_evidence_sha256.txt row; ledger own SHA 025f1596e6183c6b9cc3801d87630467613f46d0ed0a85e239aa4be0ba7b872e. Other ledger rows were NOT independently rehashed this turn. Genuine Ubuntu 24.04.2 kernel 6.8.0-1036-xilinx, KV260 revB, active fpga0 operating, dfx-mgr.service active, fancontrol.service active, live k26-starter-kits_image_1 overlay. Four UIO nodes uio0..uio3 are all axi-pmon, NOT M08.

**NEW CRITICAL DISCOVERY:** Linux kernel command line literally includes uio_pdrv_genirq.of_id=generic-uio; original live probe shows /sys/bus/platform/drivers/uio_pdrv_genirq PRESENT, kernel module uio_pdrv_genirq loaded (16384 bytes). Therefore generic-U​IO driver support is LIKELY available for two dynamically added platform device nodes. But there are currently NO M08 UIO bindings, so no MMIO permission or actual register access is proved. The original SSH file confirms only driver availability, not the live DT symbol amba or a ready new overlay. New source adds a read-only DT symbol/parent-bus investigation before constructing the candidate.

Upstream references:
- Linux kernel UIO docs: https://www.kernel.org/doc/html/latest/driver-api/uio-howto.html
- AMD FPGA region overlays and PS AMBA device nodes: https://xilinx-wiki.atlassian.net/wiki/pages/viewpage.action?pageId=2762965000
- AMD firmware manager PL_FLAT and XRT_FLAT: https://github.com/Xilinx/dfx-mgr
- AMD Ubuntu Kria package triplet: https://docs.amd.com/r/en-US/ug1630-kria-som-apps-developer-ubuntu/dfx-mgrd

## New SOURCE-ONLY owner-safe Linux UIO mapping candidate

- scripts/m08_path_a_stage_uio_overlay.py
- tests/test_m08_path_a_uio_overlay.py
- read-only extension scripts/m08_kv260_path_a_readonly.sh, m08_live_dt_amba_fpga_symbols.

The updated SSH probe reads ONLY live kernel device-tree /proc/device-tree/__symbols__/amba, fpga_full, zynqmp_reset targets and any explicit parent address/size cell properties; it does NOT write new overlays, modprobe, map device memory, load firmware or touch fan PWM. New Python candidate REQUIRES original full first-stage SHA ledger and all original files, the pinned converted .bit.bin hash, original successful PL_FLAT manifest, **NEW read-only SSH evidence receipt**, live amba/fpga_full/zynqmp_reset symbol references, generic UIO boot argument, and current driver+fan+fpga_manager availability.

**HARD FAIL-CLOSED ADDITION:** The new read-only board probe must also read actual amba #address-cells and #size-cells as exactly TWO 32-bit big-endian cells each (hex 00000002), confirming that the four-cell 64-bit <address,size> reg in the proposed overlay matches the live bus schema. If either property is missing or differs, preserve genuine owner SSH evidence and DO NOT stage a 64-bit UIO mapping; investigate the actual live DT first. This is still not a guarantee that the new nodes would bind or function at runtime.

Only on those checks does it create a FRESH PC-only REVIEW folder and a second *separate* uniquely named static Linux package candidate. It copies the existing SHA-verified bit.bin, never regenerates or changes hardware. Its DTBO includes the original FPGA full firmware-name and four zynqmp_reset references, plus a separate &amba overlay fragment with exactly two non-overlapping resources:
- compatible = generic-uio; linux,uio-name = m08-identity; 64-bit reg = <0 0xA0000000 0 0x1000>.
- compatible = generic-uio; linux,uio-name = m08-page; 64-bit reg = <0 0xA0001000 0 0x1000>.

No IRQ, no DMA, no raw /dev/mem and no guessed /dev/uioX device-number assumption. The new source invokes genuine PC dtc -@ to compile and independently decode those intended DT properties and all external symbol fixups. It leaves the original successful first-stage package untouched and records source inputs, tool console logs, full SHA receipts and a manifest explicitly asserting that real kernel binding, physical cooling continuity, programmed PL and 256-byte MMIO are NOT verified.

**Status remains OFFLINE_DUAL_UIO_CANDIDATE_NOT_INSTALLED.** Even if native dtc passes, exact live kernel resource ownership and possible driver probe behavior are only verified after a separately authorized, fan-safe deployment with rollback. Physical FPGA programming is NOT authorized yet. Do not copy this candidate under /lib/firmware/xilinx, unload the running K26 base image, alter fancontrol, or manually invoke FPGA manager sysfs.

## Owner PC VS Code commands (NO long PuTTY typing)

    cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
    git rev-parse HEAD
    python3 -m compileall -q src scripts tests
    bash -n scripts/m08_kv260_path_a_readonly.sh
    python3 -m unittest discover -s tests -p 'test_m08_path_a_uio_overlay.py' -v
    python3 -m unittest discover -s tests -p 'test_m08*.py' -v
    python3 -m unittest discover -s tests -v

First run exactly the working PC SSH capture; the newly added read-only DT symbol probe will make a fresh owner evidence folder:

    bash scripts/run_m08_path_a_readonly_pc.sh ubuntu@10.42.0.135

Record the printed new M08_PATH_A_EVIDENCE_DIR as BOARD. Keep it unchanged. Next, on the PC, set the exact previous successful package-staging folder as STAGED (the one containing the original 99_evidence_sha256.txt and m08-v1-fan-page/ directory):

    BOARD="/EXACT/new/read-only/SSH/evidence/folder"
    STAGED="/EXACT/original/m08_2b_path_a_linux_package_REVIEW_ONLY_folder"
    python3 scripts/m08_path_a_stage_uio_overlay.py --staged-dir "$STAGED" --board-evidence-dir "$BOARD" --evidence-base "$HOME/Thesis_Evidence/M08"

If the live Linux DT lacks the amba label or any other required symbol, staging FAILS CLOSED and preserves read-only original evidence. Return original 01_board_stdout.log; do not hot-patch active base DT to force the script. If native dtc compiles successfully and the source-reviewed binary fixups match, stdout says:

    M08_PATH_A_DUAL_UIO_REVIEW_ONLY_DTBO_CREATED_NOT_INSTALLED

The source creates a new separate evidence folder named m08_2b_path_a_uio_overlay_REVIEW_ONLY_<unique>. Verify:

    CANDIDATE="/EXACT/printed/new/UIO/review/folder"
    (cd "$CANDIDATE" && sha256sum -c 99_evidence_sha256.txt)

Share original 01_dtc_compile.log, 02_dtbo_decompiled.log, 03_review.json, 99_evidence_sha256.txt and new SSH 01_board_stdout.log. Do NOT transfer the candidate to the board yet.

## Remaining gates

1. Native dtc generation plus original source SHA; verify actual Linux base AMBA bus DT symbol and 64-bit cell conventions, existing resource conflict and driver-binding intent. PL_FLAT runtime acceptance remains unproven.
2. Develop a source+test-verified PS userspace UIO identity/page verification harness that refuses any ambiguous/wrong UIO map and checks actual PS transaction responses. No physical MMIO before owner-approved safe load.
3. Provide independent cooling during PL reset/reconfiguration, authorized fan-safe transition/rollback, before actual Linux managed PL replacement; explicitly do not pretend A12 output is continuous during the gap.
4. Physical ID magic/version, full 64-word staged page readback/COMMIT and rejected DISPATCH only after proven Linux MMIO ownership. Neural inference, DDR/DMA and benchmarks remain open.

Single M08.2b milestone, PR #83 draft/unmerged.
