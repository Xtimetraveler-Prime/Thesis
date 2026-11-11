# M08.2b — guarded K26 programming and physical PS access gate

**2026-11-11. ONE consolidated M08.2b milestone. PR #83 remains DRAFT/UNMERGED. Source-only development; NO NEW physical FPGA programming has occurred.**

## Accepted boundaries and current safety STOP

The owner already proved exactly ONE Vivado 2025.2 hardware target localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA and devices FPGA xck26_0|xck26 plus arm_dap_1|arm_dap. Do not repeat drivers, cable installation or read-only JTAG enumeration. Original JTAG inventory SHA256 c0ef6b6d1e5dd6f58fd042ddd630e86eeae6f3814b083558171530ff9badf4f9; JTAG console SHA256 1ead36f4d22dd80e369b09495afd9eb6a77df373fe14f23a6679bd4273ac7a1a.

The genuine owner offline 05_m08_safe_page.bit is 7,797,831 bytes, recorded SHA256 170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf. The original .bit binary was not uploaded off-PC; it must be rehashed locally. Real offline route WNS +5.469 ns, WHS +0.015 ns, and one reviewed-but-not-waived SmartConnect RTSTAT-10 DRC warning. Neither M08 FPGA programming nor physical PS AXI access is proven.

**Current board Linux/boot, loaded PL application, device-tree/dfx-mgr ownership and fan-control wiring are UNKNOWN.** A Kria base image can route fan control via the PL; M08 bitstream has not proved compatible fan wiring. Blind JTAG overwrite is prohibited. The scripts below are not authorization.

## Implemented M08-specific one-shot loader (source-only)

- scripts/m08_kv260_program_oneshot.tcl reuses the proven Loihi P08.4.3b Vivado Hardware Manager sequence: open_hw_manager, connect_hw_server localhost:3121, exactly one exact-name target, open_hw_target, enumerate devices, choose only xck26_0 with K26 part (never ARM DAP), current_hw_device, refresh_hw_device -update_hw_probes false, set_property PROGRAM.FILE, one program_hw_devices, refresh_hw_device. Fail-closed exact original bitstream byte count and SHA256 are validated INSIDE Tcl before connecting. No Loihi .ltx/VIO, firmware/flash, OS PL app, PS reset or AXI memory access.
- scripts/run_m08_kv260_program_oneshot.sh runs only on the Linux PC terminal. It validates exact original filename, length, SHA, true Vivado 2025.2, explicit owner safety decision and approved isolated-JTAG mode BEFORE invoking Vivado. It creates a fresh exclusive evidence folder containing original bit path/SHA, copied owner-review record, raw vendor log, exit status, resulting vendor statement if successful, post-attempt SHA and SHA ledger. Original owner M08/Loihi archives are left untouched. No automatic retry.
- Direct Tcl invocation ALSO requires safety approval and the reviewed file; bypassing the wrapper does not skip checks. This file is a manually supported operator review, NOT independent proof that the board is actually safe. Recheck live cooling/ownership before creating it.

Only when the **actual** board evidence proves an isolated development state with no active Linux-owned PL, verified independent cooling, and owner approval, create a truthful plain-text review including these exact lines, each once, with explanatory evidence references:

~~~text
mode=ISOLATED_JTAG
linux_pl_ownership=NONE_CONFIRMED
fan_cooling=INDEPENDENT_VERIFIED
active_pl_replacement=APPROVED
operator_authorization=YES
~~~

Do NOT assert NONE_CONFIRMED from a stalled Linux prompt alone. Do NOT assert INDEPENDENT_VERIFIED from mere fan appearance or previous project use. If Linux is running with a PL firmware manager, use a later reviewed managed DT/overlay integration, not this isolated JTAG loader.

The **future conditional** PC-only command, ONLY after full safety evidence and authorization, is:

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
BIT="$HOME/Thesis_Evidence/M08/m08_2b_bitstream_20261111T200505Z_nnHihq/05_m08_safe_page.bit"
sha256sum "$BIT"
M08_ALLOW_PROGRAM=YES M08_APPROVED_MODE=ISOLATED_JTAG \
M08_BOARD_REVIEW_FILE="/absolute/path/to/owner_review.txt" \
bash scripts/run_m08_kv260_program_oneshot.sh "$BIT"
~~~

**Do not run this command at the present unknown board state.** Target identity mismatch or an unapproved mode is a STOP requiring owner review, not an invitation to bypass the guard.

## Immediate missing physical evidence from the owner

Enable PuTTY Session > Logging > All session output on the PC. If and ONLY if the board has a Linux shell, manually type these **short commands one per line**:

~~~text
uname -a
cat /etc/os-release
xmutil listapps
~~~

Then share the **raw serial log** and the observed fan operation. If the third command is unavailable, report its original error; absence does not prove no PL owner. Later, if useful, a short command is systemctl is-active dfx-mgrd. If Linux never reaches a prompt, share the complete power-on raw serial log ending at the real stall, **do not** enter Linux commands in FSBL/BL31/U-Boot. No boot/flash modifications requested.

## Physical PS to PL readback acceptance: not yet ready

The original BD maps identity at 0xA0000000/4KiB and page at 0xA0001000/4KiB. A Vivado segment is NOT a Linux ownership/driver grant. M08 contains no VIO probe or JTAG AXI master. Programming the current .bit alone cannot read those registers. A real initiator with verified FPD HPM0 clock/reset and a **legal, owned** user/kernel interface is mandatory.

If Linux boots, review actual active DT, /proc/iomem, firmware overlays, UIO or kernel driver resource binding; NEVER guess /dev/uio0 or use raw /dev/mem. If no Linux, investigate proven PS initialization and supported XSCT/debug access only after current board evidence; no guessed mrd/mwr. If there is no valid PS/debug initiator, a new M08-specific JTAG AXI debug bridge is a SEPARATE bitstream revision, not a feature of the current .bit.

When an accessor is VALIDATED, preserve raw bus status and provenance and test in this order:

1. Identity offset 0x000 = 0x4D303831 and +0x004 = 0x00010000. Independently, page offset 0x000 = 0x4D303850 and +0x004 = 0x00020002, capability +0x008 = 1; verify two distinct windows, no aliasing.
2. The AXI page adapter permits page reads/writes ONLY in LOADING/READY/DIRTY, not EMPTY. Write logical ID at page +0x010 and BEGIN (1) to command +0x014. Perform EXACTLY 64 deterministic FULL-WSTRB 32-bit writes to +0x100 through +0x1FC followed by 64 fresh physically returned reads through the same approved AXI initiator. Compare every returned 32-bit word byte-for-byte. Require loaded bytes +0x01C = 256.
3. Only after the software comparison, COMMIT (2) at +0x014; status lower 3 bits must become READY (2), resident logical ID +0x018 must match. With compute disabled, DISPATCH (4) at +0x014 must return AXI SLVERR, and state must stay READY.
4. A timeout, unexpected response, unproven mapping, data mismatch, missing word, unsafe thermal/PL ownership or unexplained reset is a STOP, not a partial PASS. Retain original vendor/program/OS/AXI logs and independent SHA evidence. A one-word identity read is not 256-byte conformance.

No neural inference, Linux DDR, DMA, RTL neural computation, PS clock proof or physical signed16 update can be claimed from the source-only work.

## Verification source scope

tests/test_m08_physical_programming.py includes Bash grammar/missing approval and pure Tcl mocks for exact one K26, wrong SHA, changed or multiple cable, ARM DAP only, duplicate K26 and denied approval. Mocks can check guards but cannot constitute actual Vivado/board PASS. Verify all eight M01–M08 workflows on the exact final branch HEAD before considering physical acceptance.
