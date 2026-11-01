# P07-B.4g — PS-Only Readback: Persistent 64-bit FPD and LPD (2026-10-21)

**Physical state: BLOCKED for P03 PL MMIO, A53 ELF download and P07-B inference.** User separately ran `vivado/p07_b4g_ps_width_only.tcl`. The script completed with `P07_B4G_PS_ONLY_TWO_PS_REGISTERS_READ=1` and `P07_B4G_PS_ONLY_DONE_NO_PL_READ=1` and printed NO inference / A53-download permission. The user did not explicitly attest in the pasted output whether a controlled reboot had occurred before this run; treat that timeline as **unconfirmed** until directly clarified.

## Observed (user provided XSDB console output)

- XSDB physical access target: **PSU**.
- FPD `afi_fs` `0xFD615000 = 0x00002560`, `[9:8]=1` => **64-bit M_AXI_HPM0_FPD**, vs accepted **128-bit**.
- LPD `afi_fs` `0xFF419000 = 0x00000512`, `[9:8]=1` => **64-bit M_AXI_HPM0_LPD**, vs earlier physical baseline **128-bit**.
- One earlier live B4g attempt read FPD=0x00002560, then first P03 PL MMIO `0xA4000000` read failed with an AP transaction timeout. **Do not repeat the timed-out PL access.**
- Existing P03.2c physical acceptance documented FPD=0x00000A00 and LPD=0x00000200 (both 128-bit) and a working FPD128 SmartConnect-to-32-bit-AXI-Lite shell. These PS register values differ from the current observed board state.
- The 64-bit width mismatch with the *accepted hardware contract* is established. **Whether the accepted P03 bitstream is currently loaded, PL clock/reset/isolation state, physical AXI route and cause of the previous timeout are UNKNOWN.** Do not claim 64-bit width alone caused the timeout.

## Next phase: BOOT/PL provenance inventory, read-only, no additional XSDB PL MMIO

First determine whether there was actually a **normal board reboot or power-cycle** between the timeout and PS-only read. Identify the exact current boot media/boot image (FSBL, TF-A, U-Boot, Linux) and whether the previous P03 PL bitstream was JTAG-loaded into volatile configuration or installed persistently into the board's boot path.

If the KV260 is accessible at a **Linux shell on the BOARD itself** (for example serial console/PuTTY; **not the PC's VS Code shell**), run ONLY these observational commands:

```bash
printf '\n== kernel and distro ==\n'
uname -a
cat /etc/os-release
printf '\n== boot command line ==\n'
cat /proc/cmdline
printf '\n== device-tree model ==\n'
tr -d '\\0' < /proc/device-tree/model; printf '\n'
printf '\n== fpga manager state, if exported ==\n'
for f in /sys/class/fpga_manager/fpga*/state; do
  if [ -r "$f" ]; then printf '%s: ' "$f"; cat "$f"; fi
done
printf '\n== boot files (metadata only) ==\n'
ls -lh /boot 2>/dev/null || true
```

Those commands do not program PL, change PS SLCR, modify Linux services or read the unsafe P03 MMIO aperture. If there's no Linux prompt, obtain **serial boot messages** without modifying U-Boot environment or FSBL settings, then report the last boot stage reached. For a currently running Linux instance, `/sys/class/fpga_manager/fpga0/state` may report `operating`, `unknown` or may be unavailable. `operating` alone **does not prove the loaded PL design matches the accepted P03 bitstream's SHA256**. The Linux sysfs FPGA-manager documentation defines `state` as a state-machine summary, not authenticated design identity.

Do not blindly reprogram the PL, perform a PS configuration write, halt running A53/Linux, or download the user-accepted A53 ELF with default physical entry point `0x0`. The accepted ELF has overlapping risk with the low DDR boot/OS owner, independent of these PS interface width issues.

## Decision branches, NOT actions to execute yet

**If boot image/FSBL differs from accepted 128-bit P03 setup:** reconcile the actual platform and its PS initialization with the accepted baseline. Review whether the old physical P03 tests depended on a different boot image or selected a special JTAG/XSA/PS init sequence. A matching known boot configuration under a planned controlled recovery is preferable to runtime `mwr` on the static `afi_fs` width fields.

**If the current boot path reliably initializes FPD=64 and cannot be changed:** only as a separately scoped new hardware branch consider a **64-bit FPD → SmartConnect → 32-bit AXI-Lite** P03-compatible routed candidate, preserving the original accepted FPD128 artifacts. This requires Vivado BD/route, real XSA and a new P03 read-only physical acceptance; never claim the old fixed XSA already matches this new design. FPD64 itself does not establish that the P03 shell is actually loaded or accessible.

**If PL is not configured/current loaded design unknown:** first establish PL image provenance and intended boot/programming policy, without retrying reads to `0xA4000000`.

**Even if later FPD128 and PL ID recover:** B.4g register observation still cannot authorize standalone A53 ELF download or P07-B inference. Low DDR ownership/MMU/cache, reserved P02 DDR, and CPU/Linux state are separate outstanding gates.

Reference: `docs/P03_2C_PS_HPM_WIDTH_BOOT_REMEDIATION.md`, `docs/P03_2C_ACCEPTANCE.md`, `docs/P07_B4G_FPD64_AP_TIMEOUT_RECOVERY_GATE.md`, `docs/P07_B4G_PS_ONLY_64BIT_RECHECK_LEDGER.json`.

Official: AMD UG1087 `afi_fs` FPD/LPD width encoding; Linux FPGA Manager sysfs state semantics https://cdn.kernel.org/doc/html/latest/driver-api/fpga/fpga-mgr.html.

**Project invariants:** accepted Track A/B/P03/P05 frozen; PR #49 draft and unmerged; B2 official MNIST TEST sealed.
