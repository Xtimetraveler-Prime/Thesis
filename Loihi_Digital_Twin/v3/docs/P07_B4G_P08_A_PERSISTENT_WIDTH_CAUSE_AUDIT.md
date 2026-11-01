# P07-B.4g — P08-A Physical Runner Audit after Persistent FPD64 (2026-10-21)

**Question:** Could the six P08-A paired physical latency tests have permanently changed the KV260 PS FPD/LPD HPM0 widths and caused P07-B MMIO AP timeouts?

**Answer from repository source and user logs:** No direct evidence. The P08-A physical runners **required FPD128 as a hard prerequisite**, reused accepted P03.2c FPD128 bitstream, and did **not** include `mwr` to `0xFD615000` or `0xFF419000`, `psu_init`, `xmutil bootfw_update`, boot firmware flashing, or direct static PS width changes. The P08-A A53 launchers **did halt/reset A53 processors and download standalone ELF**, and both physical runners staged/write/readback dedicated `0x40000000–0x43FFFFFF` DDR. They required reboot after every attempt. These actions temporarily replace Linux/A53 execution and PL images and may leave a bad board state **until properly rebooted**, but are not a documented persistence mechanism for the PS static width selectors.

## Original script proof

- `scripts/run_p08_a3_1_pilot.sh` around lines 242–263: `xsdb vivado/p03_2c_xsdb_ps_axi_width_diag.tcl` → `grep -Fxq 'P03_2C_PS_FPD_HPM0_WIDTH_BITS=128'` → `xsdb vivado/p07_a4_xsdb_prepare.tcl` (dedicated DDR) → `vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl` → P08-A2.2 XSDB A53 launcher.
- `scripts/run_p08_a3_2_1024.sh` around lines 250–262: **same read-only FPD128 check before any P03 bit programming**, original P07 DDR staging, FPGA programming then A53 execution. User-attested **six independent P08-A3.2 sessions** on 2026-10-18/19 passed neural and latency gates. This strongly implies at least FPD128 at each session's admission; verify original archived `ps_width.log` rather than inferring every LPD result from the FPD-only runner check.
- `vivado/p08_a2_xsdb_run.tcl` and `p08_a2_2_xsdb_run.tcl`: CPU `catch {stop}`, `catch {rst -processor}`, `dow`, and mailbox reads from staged DDR. **No PS SLCR width register write**.
- `vivado/p03_2c_program_bitstream.tcl`: `program_hw_devices` + VIO PL reset; programs PL, **not documented as PS boot-fw image updater or FPD_SLCR width configurator**.
- Separately inspected legacy P08.4.3b bitstream flow is an FPGA program/JTAG hardware-conformance step, not a PS width update.
- `scripts/p08_a5_cpu_benchmark.py` runs host CPU reference and does not drive JTAG/PS registers.

## User new before/after `xmutil unloadapp` experiment

On 2026-10-21 the user rebooted and observed, both **before AND after** successful `sudo xmutil unloadapp` (`remove from slot 0 returns: 0 (Ok)`):

```text
FPD_SLCR.afi_fs @ 0xFD615000 = 0x00002560 => [9:8] = 1 => 64-bit
LPD_SLCR.afi_fs @ 0xFF419000 = 0x00000512 => [9:8] = 1 => 64-bit
```

So **`xmutil unloadapp` did not restore either width**. This distinguishes PL application unloading from PS static width setup. The earlier first P07-B `mrd 0xA4000000` failed with AXI AP timeout **while the P03 bitstream had not yet been programmed** after the new boot/unload state. Missing P03 PL slave is a plausible independent explanation for timeout; width mismatch is separately real. Do not claim either proves the other.

On Oct 17, **19 distinct P07 Track A archived width logs** all reported **128-bit FPD + 128-bit LPD**, including three explicitly compared accepted XSA/BIT/LTX identity log sets. The BIT SHA `beb7324decacf1c39d1cda97b6f13f347ecb1901a9670e75479f27a669d988a4` matched independent Track A physical evidence. Those successes predate the Oct 18–19 P08-A experimental sessions.

## NEXT low-risk check: original P08-A PS width logs, on the **PC**

```bash
find "$HOME/Thesis_Evidence" -type f -name ps_width.log -print0 2>/dev/null |
while IFS= read -r -d '' f; do
  case "$f" in
    *p08*|*P08*)
      printf '\n%s\n' "$f"
      grep -E 'P03_2C_PS_(FPD|LPD)_(AXIFS_RAW|HPM0_WIDTH_BITS)=' "$f" || true
      ;;
  esac
done
```

Also inspect whether P08 physical output includes a file describing boot environment or PS hardware. **Do not** rerun the prior P08 physical runners: they reset cores, change PL, and overwrite DDR. If no logs remain, the P08 gate's FPD128 enforced source plus accepted user results suffice for a **strong inference**, but not an independently reread historic PS width.

If P08 original Oct 19 raw logs also show **FPD128/LPD128**, then the divergence was **after those recorded runs** (possibly changed boot image, PS initialization, cold versus warm boot, independently applied Linux/firmware update, or other boot/loader differences). P08 software itself is not shown to have rewritten those static fields. No known Oct 17/19 FSBL image digests or boot-fw slot hashes are available to compare with current `xmutil bootfw_status`, so do not invent proof of a boot change.

**Safety:** No runtime `mwr` to static FPD/LPD, no P03 MMIO retry with absent PL, no accepted FPD128 PL deployment when PS currently 64-bit, no A53 ELF download (entry 0 low-DDR ownership unknown), no P08 physical rerun. Draft PR #49 stays unmerged, B2 official MNIST TEST sealed, Track A/P03/P05 frozen.

References: AMD UG1087 `FPD_SLCR afi_fs` and `LPD_SLCR afi_fs` static configuration documentation; AMD UG1137 system initialization via FSBL psu-init.
