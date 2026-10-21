# P07-B.4g — Track A Reconciliation: `xmutil unloadapp`, PS Width and Missing P03 PL Shell

**Date:** 2026-10-21. **Decision:** no FPGA/ELF rebuild or PL access until the current board-side boot/app/PS provenance is known. No execution or measurement has been performed by this document. Draft P07-B branch only; frozen original Track A/P03/P05 unchanged, B2 official MNIST TEST SEALED.

## New operator detail (October 21)

User clarified that both accepted Track A and current Track B board prep began: **reboot KV260 → login on Linux → `sudo xmutil unloadapp`**. The last P07-B actual XSDB observations after that operator pattern were: FPD `afi_fs=0x00002560` (64-bit), LPD `afi_fs=0x00000512` (64-bit). First attempt to read `0xA4000000` returned an AP transaction timeout; the subsequent PS-only probe made exactly two valid PS reads and **NO** PL MMIO access.

**Critical Track A finding:** `scripts/run_p07_a2_physical.sh` and `scripts/run_p07_a4_physical.sh` tested the **live FPD HPM0 width for 128 bits and abort on mismatch BEFORE programming PL**. They then program the accepted routed `p03_2_ps_mmio.bit` using `vivado/p03_2c_program_bitstream.tcl` (which also releases the VIO-controlled PL reset) and start standalone A53 code. The accepted XSA SHA remains `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`. Track A physical success did **not** follow from `xmutil unloadapp` alone: the successful run required both **FPD128 at runtime** and **explicit programming of the project P03 bitstream**.

**AMD Kria semantics:** `xmutil unloadapp` removes the active FPGA accelerator application/DT overlay via Kria's dfx-manager, freeing the PL for another configuration. It **does not load the custom P03 design** and is not documented as a way to set the PS static FPD HPM0 width to 128. Therefore if Track B has not subsequently programmed P03, the absent AXI-Lite slave is a **plausible independent reason for the first `0xA4000000` AP timeout**, but we have **NOT** confirmed actual FPGA fabric state; a PS/PL width mismatch may also contribute. The **source of 64-bit PS boot state is still unknown**. We must not attribute either symptom to the other as proven.

The earlier P03.2c `docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md` documented FPD `0x00000A00`, LPD `0x00000200` (**128 bits**) from the booted system and physically accepted `M_AXI_HPM0_FPD 128-bit → SmartConnect → 32-bit AXI-Lite`. That earlier remedy was to **match the PL design to a PS already configured 128-bit**, not to change PS static SLCR width registers at runtime. The Track A accepted `docs/P07_A2_FINAL_ACCEPTANCE.md` and `docs/P07_A4_2B_2C_PERSISTENT_GATE.md` rely on that exact platform.

## Non-invasive next step: read current state *on the KV260 Linux shell* ONLY

```bash
printf '\n=== Kria active accelerators ===\n'
sudo xmutil listapps
printf '\n=== Boot firmware slot and version ===\n'
sudo xmutil bootfw_status
printf '\n=== Kernel ===\n'
uname -a
printf '\n=== OS ===\n'
cat /etc/os-release
printf '\n=== Kernel cmdline ===\n'
cat /proc/cmdline
printf '\n=== FPGA manager state (NOT bitstream SHA identity) ===\n'
for f in /sys/class/fpga_manager/fpga*/state; do
  if [ -r "$f" ]; then printf '%s: ' "$f"; cat "$f"; fi
done
printf '\n=== Current boot log PL references (read-only) ===\n'
dmesg 2>/dev/null | grep -Ei 'fpga|dfx|firmware|overlay' | tail -n 35 || true
```

These commands are **read-only** and do not invoke `loadapp`, `unloadapp`, XSDB, `mwr`, Vivado or any A53/DDR writes. On OS versions requiring privilege for `dmesg`, omitting that optional output is OK. If `xmutil bootfw_status` is unsupported, record its error rather than attempting a firmware update.

On development PC, use the prior original Track A `ps_width.log` **if still preserved**:

```bash
find /tmp "$HOME" -type f -name ps_width.log -print 2>/dev/null | head -n 30
# For any candidate run log, inspect ONLY text:
grep -H -E 'PS_FPD_HPM0_WIDTH_BITS|PS_LPD_HPM0_WIDTH_BITS|PS_FPD_AXIFS_RAW|PS_LPD_AXIFS_RAW' /ABSOLUTE/OLD/TRACK_A/EVIDENCE/ps_width.log
```

Do not assume old `/tmp/` files survive reboot. Original Track A acceptance docs already record FPD/LPD128. No original bootfw slot/version/FSBL digest was recorded with those reports; if the current boot version differs from a still-available prior system log, that may explain why current width is 64 but cannot be taken as a proven cause without more evidence.

## Safe diagnosis matrix

| Observation | Interpretation | Allowed next step |
|---|---|---|
| Kria FPGA app inactive (after `unloadapp`) | No validated project P03 slave active | Do **not** re-read `0xA4000000` until a P03 configuration is deliberately established |
| FPD64 (already proven) | Mismatched to accepted routed FPD128 design | **Do not** run old P07-A2/A4 physical launcher (preflight should reject it); reconcile boot/FSBL/PS init |
| PS later verified FPD128 under accepted boot | Consistent with original P03 route but **not** proof of configured PL | With separate operator consent, controlled programming of accepted bitstream and VIO reset can be planned; never an automatic consequence of this read-only inventory |
| FPGA manager `operating` | Manager state; exact FPGA image unknown | Need separate PL provenance and no active app conflict |
| FPD64 reliably persists across normal boot with `xmutil unloadapp` | Boot configuration differs from accepted Track A condition | Investigate boot firmware/FSBL; optional NEW 64-bit FPD bridge only after separate scoped approval, route/XSA/physical retest |

**Do NOT:** issue a runtime SLCR `mwr`; treat `xmutil unloadapp` as PS reinitialization; run P03 physical scripts that halt A53 while Linux/DDR ownership unknown; program the existing FPD128 bitstream when live FPD remains 64 and expect old acceptance; retry timed-out PL MMIO; download the real B.4c A53 ELF with entry 0/low DDR LOAD; or unseal B2 official TEST.

## Original evidence and AMD references

- `Loihi_Digital_Twin/v3/scripts/run_p07_a2_physical.sh`: original Track A width-first → DDR staging → program accepted P03 bitstream → A53 launch, verified.
- `Loihi_Digital_Twin/v3/scripts/run_p07_a4_physical.sh`: same FPD128-first guarded approach.
- `Loihi_Digital_Twin/v3/docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md`: verified interface-width mismatch and boot-matched SmartConnect fix.
- `Loihi_Digital_Twin/v3/docs/P07_A2_FINAL_ACCEPTANCE.md`: successful real Track A accepted XSA and physical results.
- AMD KV260 user guide: https://docs.amd.com/r/en-US/ug1089-kv260-starter-kit/Accelerated-Application-Package-Selection
- AMD/Xilinx xmutil implementation: https://github.com/Xilinx/xmutil and https://github.com/Xilinx/xmutil/blob/master/README
