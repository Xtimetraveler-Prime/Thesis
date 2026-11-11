# M08.2b — physical KV260 safe-page bring-up (one consolidated milestone)

**Status 2026-11-11:** Real Vivado 2025.2 first-party **OFFLINE .bit GENERATED AND SHA-AUDITED**. The next operator action is **READ-ONLY LIVE BOARD/JTAG INVENTORY**. **No physical KV260 program, Linux MMIO, signed16 compute, DDR or DMA operation is yet evidenced.** Keep the owner original routed project, checkpoint and bitstream release directories immutable.

> **LATEST OPERATOR RESULT — 2026-11-11 13:29 local:** The requested PC-side **physical JTAG inventory was already performed and PASSED**. Original user files `03_jtag_inventory.txt` and `04_jtag_console.log` show a single Vivado 2025.2 hardware target `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`, programmable FPGA **`xck26_0|xck26`** and a separate **`arm_dap_1|arm_dap`**. Only benign `open_hw`/`close_hw` deprecations; no programming. **DO NOT REPEAT the JTAG inventory steps appearing below**, unless the cable/board changes. Do not redo driver installation or Vivado hw_server troubleshooting. The operator **cannot copy/paste into PuTTY**: Linux serial commands must be short and entered one at a time; long scripts/sha checks belong on the PC. **Authoritative immediate plan and next-chat handoff:** [reuse accepted Loihi loader + missing board/fan gate](M08_2B_PHYSICAL_DEPLOYMENT_PLAN_LOIHI_REUSE_2026_11_11.md) and [M08 next-chat seed](M08_NEXT_CHAT_HANDOFF_2026_11_11.md). The original next-step *JTAG* block below is retained as a historical reproducibility recipe, **not a request for another run**.

## Original offline bitstream acceptance — owner-generated, independently cross-checked

Original owner offline release folder:
`/home/dna/Thesis_Evidence/M08/m08_2b_bitstream_20261111T200505Z_nnHihq`.

User uploaded eight original files: `result.txt`, `01_release_preflight.json`, `02_vivado_bitstream.log`, `03_rechecked_drc.rpt`, `04_rechecked_timing.rpt`, `06_bitstream_native_metrics.txt`, `07_m08_bitstream_independent_audit.json`, `08_evidence_sha256.txt`. Six original files referenced in the owner's SHA ledger were **independently byte-for-byte rehashed and MATCHED**; `08_evidence_sha256.txt` is the ledger, so is not itself ledger-covered, and `result.txt` is also outside ledger. Source manifests and the original `05_m08_safe_page.bit` bytes were **NOT uploaded**, so the independent validator has no off-machine SHA proof of those files—owner original audit records the bitstream digest, and the operator should now hash it on the PC before connecting to hardware.

| Verified owner original | Evidence |
| --- | --- |
| Original Vivado result | `exit_status=0` |
| Genuine tool/target | Vivado 2025.2 `xck26-sfvc784-2LV-c`, bitgen `Completed Successfully` |
| Correct restored top | `TOP=m08_page_ps_wrapper`; design display name `checkpoint_10_m08_page_post_route` |
| Already-routed DCP input SHA | `516ded0b2b19352952810b8f2a82f15b9eca02b4757cf53c187d179d051c8673` |
| Real PS PL0 design clock | Originally 99,999,001 Hz |
| Routed/rechecked WNS/WHS | **+5.469 ns / +0.015 ns**; 0 failing setup/hold endpoints, no unconstrained internal endpoints |
| Native DRC | Exactly 1 **WARNING RTSTAT-10**, 15 SmartConnect reset-pipeline nets (14 displayed), no DRC errors. Still not a DRC-clean claim |
| Bitstream | `05_m08_safe_page.bit`, **7,797,831 bytes** |
| Original vendor/auditor digest | **`170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf`** |
| Auditor status | `M08_ORIGINAL_K26_SAFE_PAGE_BITSTREAM_GENERATED_NOT_PROGRAMMED` |
| No physical or compute claims | `physical_board_programmed=false`, `compute_engine_connected=false`, `linux_mmio_accessed=false`, `physical_ddr_accessed=false` |

Owner original `write_bitstream` itself reported `0 Errors` and **0 bitgen warnings**; the separate full native `report_drc` still records RTSTAT-10. This is an expected distinction, not a suppressed/waived DRC issue.

## BOARD SAFETY: determine live fan and loaded-image ownership before any PL swap

**Important Kria-specific constraint:** AMD's [K26 SOM documentation](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/1641152513/Kria%2BSOMs%2BStar) and [fan-control reference](https://xilinx-wiki.atlassian.net/wiki/plugins/viewsource/viewpagesrc.action?pageId=2471788698) explain that some Kria base PL images route carrier-board fan control through PS TTC/EMIO to a PL pin. A *different custom PL image* may omit this wiring and disable software fan control. The currently generated M08 page bitstream has **not been proven to preserve the active board image's fan path**. It also has no Linux device-tree overlay/driver binding, and direct Vivado JTAG programming of a platform managed by `dfx-mgrd` may leave Linux believing an old application is loaded.

For now **do not execute** `program_hw_devices`, `xmutil unloadapp`/`loadapp`, raw `/dev/mem` / `devmem`, write to `/sys/class/fpga_manager`, alter active fan wiring, power-cycle an active Linux filesystem, flash QSPI, write `BOOT.BIN`, or try unknown PS/PL reset sequences. This is a safety/provenance gate, **not** an indication that the accepted .bit or route has failed. The correct integration can be JTAG on a deliberately prepared development image, or (if Linux manages PL) a vetted `bit.bin` + compatible device tree overlay via the Kria firmware manager. Choose only after reading the live board inventory.

### First actual PHYSICAL run — read-only PC evidence, PC with USB JTAG attached

Run this from the **PC** VS Code terminal in `~/Git/Thesis/Neuromorphic_Accelerator/v1` after verifying the latest source commit:

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
BIT="$HOME/Thesis_Evidence/M08/m08_2b_bitstream_20261111T200505Z_nnHihq/05_m08_safe_page.bit"
test -f "$BIT"
echo "170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf  $BIT" | sha256sum -c -
sha256sum -c "$HOME/Thesis_Evidence/M08/m08_2b_bitstream_20261111T200505Z_nnHihq/08_evidence_sha256.txt"
mkdir -p "$HOME/Thesis_Evidence/M08"
D="$(mktemp -d "$HOME/Thesis_Evidence/M08/m08_2b_physical_inventory_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
echo "M08_PC_PHYSICAL_INVENTORY_DIR=$D"
lsusb >"$D/01_pc_lsusb.txt"
ls -l /dev/serial/by-id >"$D/02_pc_serial_links.txt" 2>&1 || true
set +e
vivado -mode batch -nojournal -nolog \
    -source scripts/m08_kv260_jtag_readonly_inventory.tcl \
    -tclargs "$D/03_jtag_target_readback.txt" \
    >"$D/04_vivado_jtag_inventory.log" 2>&1
JTAG_EXIT=$?
set -e
echo "M08_JTAG_READONLY_EXIT=$JTAG_EXIT"
cat "$D/03_jtag_target_readback.txt"
grep -nE 'M08_|ERROR:|CRITICAL WARNING:|JTAG_' "$D/04_vivado_jtag_inventory.log" || true
(cd "$D" && sha256sum ./*.txt ./*.log > 05_original_sha256.txt)
~~~

The new `m08_kv260_jtag_readonly_inventory.tcl` **never** calls `program_hw_devices` or changes firmware; it only connects Hardware Manager and reads target/device names. If multiple targets appear, it **stops rather than choosing a device**. If a target is missing or mismatched, retain the report and diagnose cables/hw_server/USB permissions; **do not blindly reprogram**. A JTAG connection does **not** establish Linux boot, PS clock/reset readiness or AXI MMIO permissions.

### First actual PHYSICAL run — read-only Linux/serial inventory on the KV260 itself

If the KV260 **boots Linux and a shell is accessible**, run from the **on-board Linux shell**, not from the development PC:

~~~bash
uname -a
cat /etc/os-release
tr '\000' '\n' < /proc/device-tree/model
cat /proc/cmdline
if command -v xmutil >/dev/null 2>&1; then xmutil listapps; fi
for p in /sys/class/fpga_manager/*/state; do
    if [ -r "$p" ]; then printf "%s " "$p"; cat "$p"; fi
done
if command -v systemctl >/dev/null 2>&1; then
    systemctl --no-pager is-active dfx-mgrd fancontrol || true
fi
for p in /sys/class/hwmon/hwmon*/fan*_input; do
    if [ -r "$p" ]; then printf "%s " "$p"; cat "$p"; fi
done
~~~

Optionally copy `scripts/m08_kv260_linux_readonly_inventory.sh` (an existing first-party file) to the KV260 and run with an existing board-local evidence parent `mkdir -p "$HOME/M08_Physical_Evidence"` then `bash m08_kv260_linux_readonly_inventory.sh "$HOME/M08_Physical_Evidence"`. The script writes **only new evidence files**; it does not modify FPGA configuration or MMIO. The board console may be serial, USB or SSH depending on actual current boot. If the board is still stuck in its previously observed FSBL/BL31 boot path, provide the raw serial boot output and JTAG report; **no speculative PS-to-PL memory read is possible from an unproven OS**.

### Return original evidence, then perform controlled board programming

Return from PC:
- `03_jtag_target_readback.txt`, `04_vivado_jtag_inventory.log`, bitstream `sha256sum` success, serial port/USB identification.
- KV260 original read-only Linux/serial transcript or the board inventory directory text files.
- State whether the board is currently booting an active Linux application and how it is cooled (fan operation/alternative active cooling).

**After those readouts**, select an operator-approved path: if a proven safe JTAG development configuration with independent cooling and no active Linux PL owner exists, execute a separate **single-device, explicit-target** Vivado programming operation, preserving the resulting original log; otherwise integrate with the actual Linux `dfx-mgr` and compatible DT overlay and thermal controls first. **Do not run an unverified Linux MMIO read just because the BD report lists `0xA0000000` and `0xA0001000`**. Physical smoke order, when safe and authorized: identity magic `0x4D303831` at identity base +0x00; signed16 page magic `0x4D303850` at page base +0x00; version/caps/status; only then full 64-word original page load/readback and explicit disabled DISPATCH behavior, with logs and no unowned DDR access.

**Milestone terminology:** This is **one M08.2b implementation/physical deployment objective** with hardware acceptance gates, not additional numbered micro-milestones. A valid .bit does not yet mean real PS-to-PL traffic, a running M06 signed16 accelerator, or kernel-owned DMA/DDR.
