# M08.2b Path A — Linux-managed KV260 deployment: board evidence and safe discovery

**2026-11-11, same consolidated M08.2b milestone. PR #83 DRAFT/UNMERGED. NO physical M08 FPGA programming or PS AXI readback.**

## Owner's original live Linux evidence

- Ubuntu 24.04.2 LTS, kernel 6.8.0-1035-xilinx, aarch64; Linux boot is working.
- Genuine sudo xmutil listapps: k26-starter-kits XRT_FLAT **active slot 0->0,**; k24-starter-kits available/inactive (-1). This is the current PL firmware, **not M08**.
- Fancontrol systemd service: active; physical fans spinning. This proves only CURRENT cooling.
- systemctl is-active dfx-mgrd: inactive. That is NOT proof the manager is unavailable: the documented systemd unit is **dfx-mgr.service** and the process is named dfx-mgrd. On-target xmutil listapps succeeded.
- Owner independently verified original offline M08 05_m08_safe_page.bit 7,797,831 bytes against SHA256 170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf on PC. This was owner evidence, not off-machine bitstream byte verification.
- Local tests owner-reported PASS. Eight M01–M08 CI workflows SUCCESS on earlier HEAD 372410b424a03d8c10f3ccb225dc24ad285d9349; re-check all eight on later HEAD.

## Critical risk: existing M08 bitstream has no documented fan route

AMD's K26 starter-kit base PL image provides a TTC0-Clk2 -> EMIO -> HDA20 -> PACKAGE_PIN A12 path needed for active fan PWM. Without equivalent wiring, removing k26-starter-kits may disable active cooling. The original M08 Vivado BD script builds PS FPD HPM0 -> identity + signed16 page, clock and reset, **but no explicit validated TTC0-Clk2 fan path or fan output constraints**. Its offline success does not qualify it as a hot-swappable Linux image.

**STOP: No xmutil unloadapp, loadapp, JTAG program_hw_devices, FPGA-manager writes, fancontrol stop, firmware/BOOT.BIN/QSPI writes, devmem, or /dev/mem.** Don't treat Path B as safer while Linux owns PL/fan.

Official sources:
- AMD Kria fan warning: https://xilinx-wiki.atlassian.net/wiki/plugins/viewsource/viewpagesrc.action?pageId=2471788698
- AMD Linux firmware manager: https://docs.amd.com/r/en-US/ug1630-kria-som-apps-developer-ubuntu/dfx-mgrd
- AMD app package layout: https://docs.amd.com/r/en-US/ug1630-kria-som-apps-developer-ubuntu/Package-File-System-Unpacking
- AMD dfx-mgr service name: https://xilinx.github.io/kria-apps-docs/faq/build/html/docs/faq.html

**OWNER ORIGINAL SSH RESULT NOW RECEIVED (2026-11-11):** PC SSH ubuntu@10.42.0.135 worked. Original uploaded evidence has fpga0 operating, dfx-mgr.service ACTIVE, fancontrol ACTIVE, active overlay k26-starter-kits_image_1, K26 bit.bin/dtbo/shell.json catalog, and uio0..3 all axi-pmon, none M08. Ubuntu kernel on SSH is 6.8.0-1036-xilinx (newer than earlier serial). Owner receipt and actual rehashed files are documented at [M08.2b accepted Path A platform evidence and new fan BD source](M08_2B_PATH_A_OWNER_EVIDENCE_AND_FAN_BD_2026_11_11.md). The read-only inventory script now includes a focused installed shell.json and PWM/package probe. Source-only fan-preserving Vivado 2025.2 TTC0 wave-out channel2 to EMIO HDA20/A12 two-slave candidate also exists (native OWNER offline run pending). Do not unload current K26 starter-kit base.


## Immediate Path A discovery from the PC

Only one SHORT PuTTY command is necessary to get the current board address:

    hostname -I

If SSH to that address is reachable, perform all detailed read-only inventory from the Linux development PC's VS Code terminal:

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
bash -n scripts/m08_kv260_path_a_readonly.sh
bash -n scripts/run_m08_path_a_readonly_pc.sh
python3 -m unittest discover -s tests -p 'test_m08_path_a_readonly.py' -v
bash scripts/run_m08_path_a_readonly_pc.sh ubuntu@BOARD_IP
~~~

Substitute BOARD_IP with the actual address shown by hostname -I; do not type angle brackets. The PC wrapper streams the READ-ONLY board probe to bash over SSH standard input, creates no board files, copies all original stdout/stderr/exit status and first-party script into a fresh exclusive PC-side evidence directory and writes independent SHA256 hashes. Onboard sudo -n xmutil listapps may report unavailable due password prompt, without negating the original PuTTY listapps evidence. SSH may request a password/host key in VS Code terminal.

The script reads only: model/OS/cmdline, service dfx-mgr AND dfx-mgrd and fancontrol, actual FPGA-manager state, overlay directory names, Linux firmware catalog, daemon.conf, fan/temp sysfs sensors, /proc/iomem and registered UIO resources. It issues NO loading, unloading, PS register reads or fan writes. Owner should share 01_board_stdout.log, 02_ssh_stderr.log, 03_exit_status.txt and 04_evidence_sha256.txt. SSH failure is a preserved test outcome, NOT proof board is unbootable. These reports are readiness discovery, not authorization.

If SSH is unavailable, use two individually typed SHORT PuTTY commands, and preserve outputs:

    systemctl is-active dfx-mgr
    cat /sys/class/fpga_manager/fpga0/state

Do not install/start SSH merely to satisfy this step.

## Managed deployment design contract (future hardware revisions, no claims now)

1. Confirm installed firmware-manager package schema, actual k26-starter-kits shell.json and DT overlay, kernel driver/bindings and fan state from original board evidence. In this OS both k24 and k26 firmware catalog entries exist, but only K26 slot 0 is loaded.
2. Create an **M08 fan-preserving new hardware build** with genuine PS TTC0-Clk2 to EMIO and carrier HDA20 A12 route and approved I/O standard. Retain first-party PS HPM0 to 4KiB identity and 4KiB signed16 page; preserve compute DISABLED. Validate full clock/reset, Vivado 2025.2 native BD/route/timing/DRC and new immutable .bit SHA. Do NOT mutate accepted original .bit or Loihi evidence. Exact pin configuration must be derived from genuine K26 board XDC/reference, never invented.
3. Package the NEW bitstream (not current original) as matching .bit.bin + .dtbo + shell.json in a new uniquely named /lib/firmware/xilinx/<app> after compatible host build. Optional XRT xclbin only if actually required. Inspect installed firmware format before generating metadata or overlay.
4. Device tree must expose separate real PS address ranges: 0xA0000000/4KiB identity, 0xA0001000/4KiB page, without conflicting existing ownership; verify kernel driver or explicit UIO mapping and permissions. No /dev/mem or unconfirmed /dev/uio0 guesses. Verified PS clocks/HPM0/overlay binds precede access.
5. Only after owner has approved actual safe fan continuity and Linux manager transition, run a one-shot managed load with rollback evidence. Test identity magic 0x4D303831 and page magic 0x4D303850 on actual hardware, then full 64x32-bit page write/read/C​OMMIT and rejected DISPATCH. Capture original vendor/Linux/access evidence before physical acceptance.

If Path A is blocked by fan or compatible DT/driver work, document the blocker. Path B is still subject to cooling and active Linux-PL ownership safety, not an automatic immediate fallback.
