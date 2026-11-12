# M08.2b Path A — genuine owner fan .bit accepted; OFFLINE Linux package staging

**2026-11-11 (owner UTC evidence folder 2026-11-12). ONE consolidated M08.2b milestone. PR #83 draft and unmerged. The KV260 remains on its ACTIVE k26-starter-kits image; NO M08 physical PL programming, Linux MMIO, or state-page traffic.**

## Genuine owner bitstream release (offline-only acceptance)

The original owner release directory on PC is:

    /home/dna/Thesis_Evidence/M08/m08_2b_path_a_fan_bitstream_20261112T041544Z_d26c8d

Owner uploaded 8 files: 7 ledger-covered receipts/reports AND the newly generated actual 05_m08_path_a_fan_page.bit (7,797,831 bytes); all 8 uploaded covered-file digests independently match the original 08_evidence_sha256.txt. The ledger itself was independently hashed, not listed as its own entry.

- 05_m08_path_a_fan_page.bit SHA256: **2d749451f46fe0660a9e78081cb6c92920a608ba16c084f37d2e1ab32f3e8af8**
- 02_vivado_fan_bitstream.log SHA256: 500364fdc72e25b1ef2f6764e5053a2085ff46f0d080c667c13b640d84fbe1c9
- 04_fan_release_timing.rpt SHA256: 92ad2a49fb49e6e78edb34fd4899842f2d58d4c9813f10caccede7aad47f73e7
- 06_fan_bitstream_metrics.txt SHA256: e4dcb531eec6f40f82a23bdaff53a21e0be979e075d39b9446d2c5173517fe30
- 07_fan_bitstream_independent_audit.json SHA256: 553eed412cd17eac25b9027de3c42a135cc123effd63f645e51af174ad7fa900
- 01_original_route_preflight.json SHA256: b5cb7b27529418e8fa3508c653794a4eef152c7bb8580749534c0d934f8f95c2
- 03_source_sha256_after.txt SHA256: 568163f62f40df6f7457ecd018b518850e4783947f5afd84fb6de482df3876b5
- 08_evidence_sha256.txt SHA256 (self, not self-covered): e948e78921de950d40f0ba98b3aa45ad53ad19a4d8b1429bfa9e57c909c84ec3

Original route preflight status: K26_FAN_ROUTED_EVIDENCE_REVIEWED_RTSTAT10_DOCUMENTED_OFFLINE_ONLY. 3,367/3,367 routed nets; zero routing errors; setup WNS +5.355 ns; hold WHS +0.029 ns; 0 methodology violations and 0 unconstrained timing paths. Physical M08_FAN_PWM[0] routed to A12, LVCMOS33, OUTPUT, 4 mA SLOW. Only single SmartConnect internal reset RTSTAT-10 warning, documented NOT waived. The original DCP SHA from the owner preflight is aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e.

Native Vivado 2025.2 vendor log confirms actual 'write_bitstream completed successfully', rechecked DRC precondition reports 0 Errors, actual owner bitstream filename and 7,797,831-byte data. The new fan .bit is DIFFERENT from the old unfanned SHA 170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf. Original owner audit status: M08_K26_NEW_FAN_BITSTREAM_OFFLINE_ONLY_NO_LINUX_NO_BOARD.

**ACCEPTANCE: NEW K26 M08 FAN-PRESERVING OFFLINE BITSTREAM VERIFIED. NOT a Linux firmware package, NOT fan continuity, NOT physical FPGA programming or PS AXI.** Original owner evidence directory remains immutable.

## New first-party PC-only package staging candidate

- scripts/m08_path_a_stage_linux_package.py
- tests/test_m08_path_a_linux_package.py
- extension to scripts/m08_kv260_path_a_readonly.sh (observes UIO kernel driver readiness; no modprobe, no MMIO)

The new source is a strictly **REVIEW-ONLY**, source-tested OFFLINE converter. It refuses a missing/altered original release SHA ledger, unknown or old unfanned .bit, incorrect original independent audit or vendor exit, or untrusted output parent. It never writes firmware on the board. After validation it uses genuine AMD bootgen for ZynqMP .bit -> .bit.bin and genuine dtc for a symbolic Linux fpga_full overlay (genuine phandle fixups &fpga_full and &zynqmp_reset; the same four 0x74-0x77 reset IDs observed in the stock owner's DTBO). It creates a uniquely named PC staging folder with a new app subdirectory containing exactly:
- m08-v1-fan-page.bit.bin
- m08-v1-fan-page.dtbo
- shell.json

**Important deliberate distinction:** The installed K26 starter-kit shell.json reported XRT_FLAT and one slot. The new identity+state-page M08 design has NO XRT xclbin. We stage shell_type **PL_FLAT** (with num_slots "1") for the non-XRT static design. This is supported as a type in AMD's dfx-mgr documentation, but the actual installed Ubuntu daemon's acceptance of this choice must be reviewed before installation. Staging it offline is NOT proof of runtime acceptance.

**Deliberately NO M08 AXI DT resources in this initial overlay**: the live Linux UIO driver/module binding and current DT owner have not been validated. A dtbo can configure PL while userspace still has NO right to map 0xA0000000 or 0xA0001000. The new script checks stock-like fpga_full firmware-name/reset symbol fixups and refuses to imply generic-uio or device memory authorization. Do NOT add unvalidated UIO nodes, use /dev/mem, or assume /dev/uio0-3. The new read-only SSH probe captures uio_pdrv_genirq/generic-uio driver availability and existing AXI performance monitor UIO nodes to inform the next development.

AMD references:
- https://docs.amd.com/r/en-US/ug1630-kria-som-apps-developer-ubuntu/dfx-mgrd
- https://docs.amd.com/r/en-US/ug1630-kria-som-apps-developer-ubuntu/Package-File-System-Unpacking
- https://xilinx.github.io/kria-apps-docs/creating_applications/2022.1/build/html/docs/Generate_vivado_project_from_boardfile.html
- https://github.com/Xilinx/dfx-mgr (PL_FLAT / XRT_FLAT details).

## Exact Linux PC commands (VS Code terminal ONLY, no PuTTY paste)

    cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
    git rev-parse HEAD
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m08_path_a_linux_package.py' -v
    python3 -m unittest discover -s tests -p 'test_m08*.py' -v
    python3 -m unittest discover -s tests -v
    source /home/dna/Vivado/2025.2/Vivado/settings64.sh
    command -v bootgen
    command -v dtc
    RELEASE="$HOME/Thesis_Evidence/M08/m08_2b_path_a_fan_bitstream_20261112T041544Z_d26c8d"
    python3 scripts/m08_path_a_stage_linux_package.py --release-dir "$RELEASE" --evidence-base "$HOME/Thesis_Evidence/M08"

When vendor conversion and the source-created offline review pass, stdout includes:

    M08_PATH_A_LINUX_REVIEW_ONLY_PACKAGE_STAGED_NOT_INSTALLED
    M08_PATH_A_LINUX_PACKAGE_EVIDENCE_DIR=<new-original-owner-folder>

The fresh folder includes app triplet, original BIF, native bootgen and dtc logs, source+input receipt, decoded DTBO, manifest with explicitly NOT VERIFIED physical/MMIO flags, and 99_evidence_sha256.txt. Preserve full original folder. Verify from your PC:

    STAGED="/exact/new/folder/printed/above"
    (cd "$STAGED" && sha256sum -c 99_evidence_sha256.txt)

If bootgen/dtc fails, the owner should preserve the ORIGINAL tool stderr captured inside the new evidence folder. Do not copy the app folder to /lib/firmware/xilinx or call xmutil loadapp/unloadapp. No other OS, fan, boot firmware, QSPI/SD or JTAG changes are requested.

### Optional new read-only SSH kernel binding inventory from PC

    bash scripts/run_m08_path_a_readonly_pc.sh ubuntu@10.42.0.135

Return new 01_board_stdout.log and 04_evidence_sha256.txt. The added read-only section m08_kernel_mmio_binding_readiness reports available UIO binding/driver hints. It is ONLY discovery and does not authorize mmap or choose a UIO number.

## Next M08.2b gates (OPEN)

1. Verify native owner bootgen/dtc outputs, DTBO fixups, PL_FLAT compatibility with exact Ubuntu 24.04.2 image and true kernel driver ownership for separate M08 AXI 4KiB windows.
2. Build a safely bound M08 driver/UIO interface, DT resource declaration after conflict check, and a PS-side deterministic 64x32-bit write/read/COMMIT test **through an approved interface**.
3. Before any live Linux-managed PL replacement, separately establish fan cooling during the **reconfiguration gap** and recovery/rollback using genuine board thermal evidence and explicit operator approval. A routed A12 fan signal in a new bitstream does not guarantee fan PWM during unload/load.
4. Only after those conditions permit hardware deployment and the first genuine identity/page readback. Compute dispatch stays disabled. No DDR/DMA/inference acceptance yet.

PR #83 stays draft and unmerged pending owner approval.
