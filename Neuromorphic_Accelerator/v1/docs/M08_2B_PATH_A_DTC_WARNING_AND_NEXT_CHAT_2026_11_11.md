# M08.2b — original UIO evidence, DTC diagnostic correction, next verification handoff
**Date:** 2026-11-11 America/Denver (owner UTC folder date 2026-11-12). **PR #83 DRAFT, UNMERGED.** All activity on the existing M08.2b branch.

## Uploaded original evidence (six files)

All four uploaded files covered by the two independent owner SHA ledgers match their listed digests. Both ledgers themselves were separately hashed, but neither is self-covered:

| Original file | Independently observed SHA256 |
|---|---|
| SSH 01_board_stdout.log | 97a6b860ae144e0ffa55bf28779f0f3ac1d434ca3a76e03886be9d9b1ac9d223 |
| SSH 04_evidence_sha256.txt | 65b515f72841b9ca9c8865e2b1a011cc817e291fb210ea40c2e09f6de6a261b6 |
| UIO 01_dtc_compile.log | f8d957ff6abd7436336753c408d45e536d00f302ee14226923eec90c4d51f471 |
| UIO 02_dtbo_decompiled.log | fa1e6494db51afe8e879fafbc731516937d051093f2582edf2ed0336aba68227 |
| UIO 03_review.json | ff677b160a00b88d1cbe79c71e98c5387ac6f5c9abfd9fd62b12eede724e555f |
| UIO 99_evidence_sha256.txt | 9ccf682d28ed49098aee962b7a4cf14f01955f9b8d36e8ffcc85ff2aaa405efa |

Original second-stage UIO review folder: /home/dna/Thesis_Evidence/M08/m08_2b_path_a_uio_overlay_REVIEW_ONLY_tuzu33oo . **Preserve it unchanged.** Its owner SHA ledger lists .bit.bin a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b, warning-bearing .dtbo 81045b1ff03514c4312b8340ecfbdfcd771cc5a9b7902a2a9e45324642f652a1, other source and shell.json; those unuploaded bytes have NOT been independently rehashed.

## Actual KV260 read-only result

Ubuntu 24.04.2 Linux 6.8.0-1036-xilinx; KV260 revB. Active dfx-mgr.service and fancontrol.service; FPGA-manager operating, and current PL overlay k26-starter-kits_image_1. Existing UIO0–3 are four axi-pmon performance-monitor devices, **not M08**.

Real /proc/device-tree labels: amba -> /axi, fpga_full -> /fpga-region, zynqmp_reset -> /firmware/zynqmp-firmware/reset-controller. Live /axi is compatible simple-bus with **#address-cells=2 and #size-cells=2** and zero-byte ranges (identity translation). uio_pdrv_genirq.of_id=generic-uio is on the actual kernel command line, the kernel UIO driver is loaded and registered. **No M08 Linux driver binding, PS-to-PL MMIO traffic, or fan continuity is established.**

## DTC correction required

Native DTC did compile the previous review overlay and produce the intended two 4 KiB generic-uio nodes:
- m08-identity: address 0xA0000000, length 4096.
- m08-page: address 0xA0001000, length 4096.

However the original compiler and decompiler emitted **reg_format** and **avoid_default_addr_size** warnings: the synthetic /fragment@1/__overlay__/ AMBA parent did not explicitly declare cell widths, so standalone dtc assumed 2/1 while the 16-byte reg values require **2/2**. Its prior success marker only meant a review candidate was produced; **DO NOT CALL THE OLD .dtbo WARNING-CLEAN OR DEPLOYABLE.** The separate decompiler-only resets_property warning is associated with unresolved symbolic zynqmp_reset phandle fixups in an unapplied overlay.

Corrected first-party scripts/m08_path_a_stage_uio_overlay.py now adds #address-cells=<2> and #size-cells=<2> inside &amba; requires EMPTY native DTC compile diagnostics, allows ONLY the documented unresolved reset-phandle warning when decoding, validates both DT fragments explicitly declare the 2/2 bus cells, and otherwise rejects. tests/test_m08_path_a_uio_overlay.py covers old-warning rejection and wrong widths. Original warning-bearing owner artifacts are not modified.

## New no-MMIO UIO discovery source

scripts/m08_path_a_uio_sysfs_readonly.py and tests/test_m08_path_a_uio_sysfs.py inspect ONLY sysfs metadata. They find UIO by **name and exact map0 physical address/size**, not arbitrary /dev/uioX numbering; fail closed on ambiguity/overlap/duplicate; and record no device opens, register access, kernel driver changes, PL changes or fan operation. Pre-deployment expected state: M08 absent; four axi-pmon UIO devices remain. Later present state can validate metadata only after separately approved physical deployment.

## NEXT VERIFICATION (the new chat is responsible for operator commands)

The user explicitly requested that this current development chat **NOT give verification commands**. Next chat must:
1. Fetch current branch HEAD; give exact safe VS Code PC commands for git fetch/pull, SHA, compileall, focused test_m08_path_a_uio_overlay.py + test_m08_path_a_uio_sysfs.py, M08-targeted suite and full unittest suite.
2. Preserve existing first-stage owner package folder /home/dna/Thesis_Evidence/M08/m08_2b_path_a_linux_package_REVIEW_ONLY_bco0j53i and locate most recent successful read-only BOARD evidence folder matching SSH stdout digest 97a6b... . No need to repeat SSH baseline unless evidence is missing or stale.
3. Give PC-only native dtc re-run of corrected scripts/m08_path_a_stage_uio_overlay.py with original STAGED, BOARD and existing owner ~/Thesis_Evidence/M08 parent. A NEW sibling evidence folder MUST be created. Verify original SHA ledger, native compile log **empty of warnings** (reg_format, default_addr_size), decompiled 2/2 cells, phandle fixups, both exact 4 KiB device names, unchanged .bit.bin SHA and new SHA receipt. If no clean native result, preserve original new failure and debug; never silently waive warnings.
4. Optionally give a short PC-to-board SSH stdin-stream command for new sysfs-only inspector --expected absent (read-only, preserve original stdout/stderr/exit/hash). No PuTTY multiline commands; user cannot paste into PuTTY.
5. Ask user to return only actually generated outputs: original 01_dtc_compile.log, 02_dtbo_decompiled.log, 03_review.json, 99_evidence_sha256.txt and UIO metadata probe output, then continue development based on those results. **Do not unload, program or install the FPGA.**

## Research direction and remaining physical gates

Overall objective: a research-grade FPGA digital twin of Loihi-inspired event-driven neuromorphic hardware, with independently checked neural numerics, event/service timing, state residency/cache tradeoffs, and eventually real PS memory/DDR/DMA benchmark comparisons. The earlier Loihi_Digital_Twin/v2 signed24 work is separate from Neuromorphic_Accelerator/v1 signed16 paging work. M01–M07 completed their stated model/HLS/RTL/scoped experiments. M08.2b has a genuine offline K26 fan-preserving .bit (SHA 2d749451f46fe0660a9e78081cb6c92920a608ba16c084f37d2e1ab32f3e8af8, 7,797,831 bytes), but that shell exposes identity and a 256B state page only, **with neural compute DISPATCH disabled**. No physical M08 PL programming, kernel driver binding, PS AXI page readback, DDR/DMA, neural inference or real performance proof has occurred.

After corrected dtc signoff: build guarded kernel UIO ownership and PS userspace readback code, develop independent cooling/rollback safe for the PL reconfiguration *gap*, then only with owner explicit approval execute Linux-managed first deployment and physical identity/64-word write/read/COMMIT/dispatch-refusal checks. A fan pin present on a routed .bit **does not prove** uninterrupted cooling during reconfiguration. Keep the active k26-starter-kits and fancontrol running and PR #83 unmerged.
