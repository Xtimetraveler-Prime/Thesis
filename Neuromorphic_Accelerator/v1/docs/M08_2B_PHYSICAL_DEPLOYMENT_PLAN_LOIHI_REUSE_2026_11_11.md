# M08.2b — physical KV260 deployment plan (reuse the already-working Loihi JTAG path)

**Status: 2026-11-11, after owner-uploaded ORIGINAL JTAG evidence.** This is one consolidated **M08.2b** physical deployment goal, not another series of numbered micro-milestones. The operator cannot paste text into PuTTY: **keep any commands typed on the serial console short**, and put all long commands, scripts and SHA verifications on the Linux development PC using VS Code terminal.

## Decision in one paragraph

**The JTAG connection problem is solved. Do not repeat cable/driver/server troubleshooting.** Owner-supplied original `03_jtag_inventory.txt` and `04_jtag_console.log` independently prove Vivado 2025.2 connected to `localhost:3121`, opened exactly **one** hardware target `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`, and enumerated `xck26_0|xck26` plus `arm_dap_1|arm_dap`, then closed normally. The K26 programmable FPGA is **`xck26_0`**, not the ARM DAP. Only harmless `open_hw`/`close_hw` **deprecation** warnings occurred. This was read-only enumeration, **not programming or PS clock/MMIO evidence**.

Verified SHA256 of the owner-uploaded originals (locally computed from bytes):
- `03_jtag_inventory.txt`: `c0ef6b6d1e5dd6f58fd042ddd630e86eeae6f3814b083558171530ff9badf4f9`
- `04_jtag_console.log`: `1ead36f4d22dd80e369b09495afd9eb6a77df373fe14f23a6679bd4273ac7a1a`

The previously owner-accepted **offline** M08 bitstream is `/home/dna/Thesis_Evidence/M08/m08_2b_bitstream_20261111T200505Z_nnHihq/05_m08_safe_page.bit`, **7,797,831 bytes**, original audit SHA256 `170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf`. Its original route DCP digest is `516ded0b2b19352952810b8f2a82f15b9eca02b4757cf53c187d179d051c8673`. Real Vivado K26 WNS +5.469ns, WHS +0.015ns; only documented internal SmartConnect `RTSTAT-10` DRC warning. The 7.8MB .bit itself wasn't uploaded; owner must run `sha256sum` against the **actual PC file** before any programming. No FPGA programming, Linux PS MMIO readback, DDR or signed16 neural dispatch is yet proven. The safe shell has **`ENABLE_COMPUTE=0`**.

## Review of EXACT successful Loihi Digital Twin v2 code (reuse proven tools, not incompatible hardware)

* `Loihi_Digital_Twin/v2/hardware/p08_4_3b_physical_conformance.tcl` (accepted P08.4.3b) and `hardware/p03_physical_conformance.tcl` successfully drove **actual** K26 over the same PC Vivado Hardware Manager/JTAG path: `open_hw_manager`; `connect_hw_server -url localhost:3121`; enumerate `get_hw_targets`; `current_hw_target`, `open_hw_target`; select **only the K26 FPGA device** from `get_hw_devices` (exclude ARM DAP); `current_hw_device`; `refresh_hw_device -update_hw_probes false`; `set_property PROGRAM.FILE $bit_file $device`; `program_hw_devices $device`; `refresh_hw_device $device`. No new driver installation, board discovery or bitstream synthesis procedure should be invented.
* `Loihi_Digital_Twin/v2/hardware/run_p08_4_3b_physical.sh` validated **exact SHA** of the previously accepted Loihi `.bit` **and** Loihi-specific `.ltx` before running native Vivado; its actual physical acceptance records a changed PL heartbeat and VIO-based page replacement. Reuse the **SHA-first, fixed-bitstream, hardware-target-exact, original-log** discipline.
* **DO NOT copy Loihi's VIO verification code.** Loihi bitstream includes `vio_p08` and a matching `.ltx`, giving JTAG-hosted reset, heartbeat and host-bank controls. **M08 does not instantiate those debug probes**: the accepted M08 .bit contains a PS-facing AXI4-Lite identity peripheral plus 256B page; a VIO scan or `PROBES.FILE` assignment would be unjustified and fail. Loihi signed24 full-context arithmetic is not M08 signed16 page behavior. M08's PS HPM0 FPD initiator must be live and have a **trusted software/debug access path** before memory reads.
* These Loihi scripts previously worked with `hw_server` and a correctly initialized K26 system; their success does **not** prove the current Linux boot, PS PL0 clock, reset, fan wiring or driver state. Original Loihi evidence is immutable; do not rerun it or reuse its bitstream.

Relevant references: Loihi v2 `docs/P08_4_3B_ACCEPTANCE.md`, `docs/P08_4_3B_PHYSICAL_MNIST_CONFORMANCE.md`, and `hardware/p08_4_3b_physical_conformance.tcl`.

AMD's official Vivado `program_hw_devices` and `open_hw_manager` Tcl guidance describes the same sequence. AMD's Kria starter-kit documentation also states 2022.1+ base PL images may route the carrier **fan control through TTC0/EMIO and a PL pin**; replacing that PL bitstream without the corresponding fan mapping can disable active fan control. **Do not issue the program command until the actual board image/cooling is known.** See `docs/M08_2B_KV260_PHYSICAL_BRINGUP_2026_11_11.md` for the cautious original hardware boundary.

## Practical ordered execution: one milestone, four acceptance checks
**Source development update (2026-11-11):** The previously proposed one-shot loader now exists, source-only, as scripts/m08_kv260_program_oneshot.tcl and scripts/run_m08_kv260_program_oneshot.sh. Safety gating, exact digest/device selection, owner evidence archiving and pure Tcl mocks are documented at [guarded programming and PS access boundary](M08_2B_GUARDED_PROGRAMMING_AND_ACCESS_GATE_2026_11_11.md). **It has NOT been run on hardware and remains prohibited until original boot/PL/fan status is collected and isolated-JTAG conditions genuinely approved.** The owner-reported read-only JTAG inventory already passed and should not be repeated.




### A. Reuse accepted JTAG identity; collect only MISSING board boot/fan evidence

**Do not re-run** `scripts/m08_kv260_jtag_readonly_inventory.tcl` unless the board/cable/device materially changes. Save the already uploaded original two files and their hashes in the research record; operator's new folder stays immutable. Instead determine what PS is currently doing.

If PuTTY is at a working **KV260 Linux prompt**, only type these *short, read-only, one-line commands*, one at a time:
```text
uname -a
cat /etc/os-release
xmutil listapps
```
`xmutil` may not exist; report the exact error if so. To inspect fan or loaded PL manager state, optionally type **one** of:
```text
systemctl is-active fancontrol
systemctl is-active dfx-mgrd
```
These are **options**, not a block to paste. PuTTY's **Session → Logging → All session output** can capture the result on the PC; send the raw log without manually retyping it. If Linux does **not** boot (e.g. the older FSBL/BL31 stall), **do not type any Linux commands**, don't repeat them, and preserve the raw UART output from power-on to the stopping line. Hardware JTAG enumeration is independent of successful Linux boot.

If Linux is reachable through a supported PC shell/SSH, run the already-written `scripts/m08_kv260_linux_readonly_inventory.sh` ON THE BOARD, or use a PC-launched SSH capture; no need for long PuTTY typing. Confirm board identity, active loaded PL applications, FPGA manager, whether fan depends on PL, and PS boot/clock configuration. **Missing these facts is a programming guard**, not a reason to reinstall Vivado.

### B. Program using the **existing accepted Loihi Hardware Manager sequence**, M08-specific target and SHA

After documenting the actual board state, **explicitly authorize** one of two safe operating modes:

1. **Linux is booted / PL firmware manager active:** first reconcile active `dfx-mgrd`/device-tree/thermal ownership. The custom M08 design has not been packaged as a Kria `bit.bin` + appropriate DT overlay, and may lack TTC/EMIO fan routing; **do not blindly overwrite the current PL image via JTAG**. Either integrate with the actual platform's approved firmware manager and DT overlay, or prepare a documented developer-only board state with independent cooling and no Linux-managed PL user. Neither `xmutil unloadapp` nor `fancontrol` service stop is authorized by this handoff.
2. **Board is intentionally in a development/bootloader/JTAG mode with verified cooling and PS initialization:** use a short, PC-hosted M08 one-shot Tcl script adapted directly from accepted Loihi `p08_4_3b_physical_conformance.tcl`. Guard exact `sha256sum` of the local M08 .bit, Vivado **2025.2**, exactly one selected JTAG target, exactly one FPGA **`xck26_0`** with part `xck26` (never `arm_dap_1`), expected user-supplied bitstream path, and a positive operator `M08_ALLOW_PROGRAM=YES` acknowledgement. Use `open_hw_manager`, `connect_hw_server -url localhost:3121`, `current_hw_target`, `open_hw_target`, `current_hw_device`, `refresh_hw_device -update_hw_probes false`, `set_property PROGRAM.FILE`, **one** `program_hw_devices`, then `refresh_hw_device`. No `.ltx` expected, no `PROBES.FILE`, no flash/QSPI, PS reset, `bootfw_update`, firmware replacement or Linux raw MMIO. Preserve a **new** original program log/result/bitstream SHA ledger. Do not silently rerun on failure.

**This file is a PLAN, not authorization or execution of programming.** The M08-specific one-shot programming harness is **not yet implemented** and should only be authored after review of the on-board PS/PL/cooling evidence; use the exact Loihi script pattern, not new connection experiments.

### C. Real PS→PL register access: choose an actual master and legal interface (no Loihi VIO shortcut)

The current Vivado-derived AXI-Lite map is **design-local**, not a Linux-registered device:
- `identity/S_AXI` PS FPD HPM0, **4 KiB at 0xA0000000**; read-only magic `0x4D303831` ("M081") at offset `0x00`, version `0x00010000` at `0x04`, no-DMA capability and default unprovisioned build-ID fields.
- `page/S_AXI` PS FPD HPM0, **4 KiB at 0xA0001000**; magic `0x4D303850` ("M08P") at `0x00`, version `0x00020002` at `0x04`, `0x008` capability, `0x00C` status, `0x010` logical ID, `0x014` BEGIN/COMMIT/DISPATCH/SAVE, `0x018` resident logical ID, `0x01C` loaded bytes, `0x100..0x1FC` exactly 64 page words.

**No active M08 VIO, AXI JTAG master or `.ltx` exists.** Therefore programming the `.bit` **does not** itself supply a testbench/PS master that can issue these reads. Based on the observed running mode, choose:
- **Best when Linux boots:** create/review an explicit UIO or kernel driver/device-tree binding with exclusive memory resource ownership for the exact checked BD-aperture ranges; then use a PC-launched shell/board-side script to read identity and page through that approved interface. Do **not** guess `/dev/uio0`, use `/dev/mem`, or claim PS DDR.
- **If Linux cannot boot but PS debug/initialization can be proved:** evaluate a contained XSCT/PS DAP AXI access route **only** after verifying actual PS initialization, FPD HPM0 enable, PL0 99,999,001 Hz and reset; distinguish real bare-metal PS transactions from unsafe guessed `mrd/mwr`.
- **Fallback if no trusted PS master/driver exists:** build an **M08-specific** explicit debug bridge (e.g. JTAG AXI Master IP or minimalist VIO page controller), then rerun its own RTL/Vivado/route/bitstream evidence. This is **different hardware** and cannot be asserted to exist in the already-accepted .bit. Leverage Loihi's already-written VIO host-access implementation and safety protocol, not its numeric Loihi neuron logic.

Never claim neural inference or DMA based on the first page readback.

### D. Physical M08.2b success evidence and follow-on architecture

After safe configuration **and** confirmed PS FPD HPM0 clock/reset/access:
1. Read two identity magic/version/capability words from both **different** AXI windows, check the exact expected values and no alias.
2. Test read-only identity writes are rejected through the approved AXI API (without rewriting a live reserved register).
3. Under the page RTL's documented ownership state machine, select a logical context, BEGIN a staged page, write **64 deterministic 32-bit words** with full byte strobes, read back all 64 and compare word-for-word, COMMIT only after verified coverage, read loaded-byte/resident/status; ensure disabled DISPATCH returns SLVERR and does not move page to RUNNING. This stage uses physical hardware and **does not dispatch real neurons**.
4. Save original FPGA application/state/exception logs and the page write/read transcript to a new immutable owner evidence folder, with exact program-bit SHA, true device `xck26_0`, original JTAG programming success, proven AXI accessor provenance, no unexpected fan loss, readback parity, and independent SHA audit.
5. Mark **M08.2b PHYSICAL PS→PL PAGE** accepted ONLY if all actual owner results pass. Then integrate the real signed16 M06 compute service/actual DMA/DDR ownership in the broader M08 physical benchmark workflow; do not describe this PS-only shell as already executing inference.

## State/constraints for next chat

- **Do not repeat cable-driver/JTAG enumeration.** The owner already provided exact original read-only `xck26_0`/ARM DAP proof.
- **Do not require PuTTY copy/paste.** Maximum 1 line per manually typed serial command; all long operations run as scripts in VS Code on PC (or via a supported PC-to-board command channel).
- Preserve all accepted and failed owner M08 and Loihi evidence folders unchanged. No merge without owner explicit approval; PR #83 DRAFT.
- One consolidated **M08.2b** goal; no unnecessary numbered micro-milestones. Original byte/evidence provenance before any hardware claim.
- Priorities: missing live boot/fan/app state → safe JTAG/Linux-managed loader decision → **first actual FPGA programming** → authorized PS AXI ID/page verification. A new handoff file identifies owner-provided JTAG hashes, exact Loihi scripts, branch/CI and actionable first tools.
