# P07-B.4g — Track A 19-run retrospective and current Kria overlay evidence (2026-10-21)

**Status:** analytical checkpoint only, no KV260 register writes, no Vivado programming, no A53 ELF download; P07-B live shell still NO-GO. User reported all Track A historical `ps_width.log` measurements and screenshot of current KV260 Bash. Never mistake text logs for direct tool access to live hardware.

## User independent retrospective

User listed and read **19** historical `/tmp/v3_p07_*/*/ps_width.log` files from successful Track A experiments on 2026-10-17 (A2 first, A3 validation, 10 A3.3 primary/repeat batches, A4 ramp, 128/1024 primary and reboot-repeat, fail-closed, official 10000). **All 19** printed:

```text
P03_2C_PS_FPD_HPM0_WIDTH_BITS=128
P03_2C_PS_LPD_HPM0_WIDTH_BITS=128
```

Three individually inspected logs—A2 `/tmp/v3_p07_a2_physical_20261017T130533`, A4 validation1024 primary `/tmp/v3_p07_a4_val1024_primary_20261017T200134`, official full10000 `/tmp/v3_p07_a4_official_full10000_20261017T204944`—each also showed exact raw PS values `FPD=0x00000A00`, `LPD=0x00000200`, and `PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released`.

All three **independently dated original physical_identity.txt evidence logs** matched:
- Routed **XSA** `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
- Routed **BIT** `beb7324decacf1c39d1cda97b6f13f347ecb1901a9670e75479f27a669d988a4`.
- Routed **LTX** `31f5771432ffb8c72b35a55e1ef7e88e9d96d406fe8cb306733df474df360238`.

**Provenance clarification:** This promotes the BIT digest from merely user-observed current file into **matching prior successful Track A physical identity receipts**, substantially stronger accepted host-artifact provenance for B.4e/B.4f. It is **NOT proof that this accepted .bit is currently configured on the live KV260**, and the B.4f JSON produced earlier with `--bit-provenance observed` remains an immutable historical record—not silently rewritten.

## New KV260 screenshot and missing evidence

KV260 PuTTY screenshot of current `cat /proc/cmdline` reported Ubuntu boot command line and `root=LABEL=... `. Attempted multiline Bash `for f in /sys/class/fpga_manager/fpga*/state; do ...` ended in `syntax error near unexpected token 'fi'` (typing issue); therefore **fpga-manager `state` was NOT obtained**. Screenshot of `ls -la /sys/kernel/config/device-tree/overlays/` showed **`k26-starter-kits_image_1`** directory present on October 21, 2026.

AMD Kria docs describe default k26-starter-kits bitstream/DT overlay managed by dfx-mgr, and `xmutil unloadapp` unloading active accelerator. A surviving configfs overlay *may* mean it remains applied or that DFX manager and kernel states disagree; directory alone **does not prove active loaded FPGA image**. Earlier screenshot of `xmutil listapps` suggested active_slot `-1` for listed accelerators; must separately resolve with exact read-only app/overlay status.

The user says copy/paste in PuTTY is impractical. **Prefer one-line commands**:

```bash
cat /sys/class/fpga_manager/fpga0/state
cat /sys/kernel/config/device-tree/overlays/k26-starter-kits_image_1/status
hostname -I
```

If SSH network access exists, user can issue `ssh ubuntu@<board-ip>` from VS Code terminal after inspecting `hostname -I`, enabling ordinary paste/log capture. This does not change boot, PL or PS width. No network capability must be assumed.

## Conclusion

- **All 19** Track A historical physical runs required **128-bit** both PS HPM0 widths. Current measured PS selectors FPD `0x00002560` and LPD `0x00000512` both **64-bit**. Boot-time source of difference has not been proven. Neither `xmutil unloadapp` nor writing to static SLCR is an established fix.
- Track A guarded scripts check width **BEFORE** programming accepted P03 bitstream. Do **not** try current FPD128 PL programming on the FPD64 boot to fix PS static width, and do **not** access `0xA4000000` again until live PL and PS safety are separately recovered.
- Current `k26-starter-kits_image_1` overlay after user-reported unload is an important new **state-consistency question**, not proof of root cause.
- Need actual kernel FPGA-manager state, overlay status, and whether the user ran normal reboot + unload after last timeout. Retain project P03/P05/Track A frozen; B2 official MNIST TEST sealed; PR #49 remains draft/unmerged.

Vendor context: https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/1641152513/Kria%2BSOMs%2BStarter%2BKits , https://xilinx.github.io/kria-apps-docs/dfx/build/html/docs/run_application_on_target.html .
