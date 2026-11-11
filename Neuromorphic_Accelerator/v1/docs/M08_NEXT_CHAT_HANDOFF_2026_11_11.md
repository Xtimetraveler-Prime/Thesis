# NEXT CHAT HANDOFF — Neuromorphic Accelerator v1, M08 physical KV260 deployment


**MOST RECENT SOURCE-ONLY CONTINUATION (2026-11-11):** Reused the genuine Loihi P08.4.3b Hardware Manager programming sequence to implement first-party scripts/m08_kv260_program_oneshot.tcl and scripts/run_m08_kv260_program_oneshot.sh in THIS SAME branch, guarded by exact original M08 bitstream SHA/size, Vivado 2025.2, exact original target, unique xck26_0 (not ARM DAP), explicit isolated-JTAG approval and an actual reviewed boot/fan/PL state, and a new immutable-style owner evidence folder/ledger. Added pure Tcl source-mock regression tests in tests/test_m08_physical_programming.py and [new operator gate](M08_2B_GUARDED_PROGRAMMING_AND_ACCESS_GATE_2026_11_11.md). These are NOT vendor/physical passes. Live Linux boot, active PL/dfx-mgr/fan state remain UNKNOWN, so the loader MUST NOT be executed yet; no physical M08 programming, physical AXI identity or 64-word page proof exists. The source-only implementation supersedes the older instruction below to "build" the loader; after obtaining genuine state, review/authorize or choose an OS-managed path. Do not repeat already-successful JTAG enumeration. PR #83 stays draft/unmerged; recompute exact head/CI after source changes.


**Current research branch:** `agent/neuromorphic-accelerator-v1-m08-kv260-bringup`  
**Repository:** `Xtimetraveler-Prime/Thesis`, project root `Neuromorphic_Accelerator/v1`  
**PR:** #83, **DRAFT, OPEN, UNMERGED**; user has **not authorized a merge**.  
**Current milestone:** **ONE consolidated M08.2b physical PS→PL state-page deployment and readback goal**. Avoid subdividing each step into new numbered sub-milestones.  
**Current-date context:** 2026-11-11. Source branch HEAD changes as documentation is updated; **always inspect `git rev-parse HEAD` or PR #83 head SHA, and require M01–M08 workflows to be green on that same head**, without pretending queued CI passed.

**LATEST OWNER LIVE BOARD OBSERVATION (2026-11-11; supersedes former UNKNOWN Linux state):** KV260 **DOES BOOT** Ubuntu 24.04.2 LTS, kernel 6.8.0-1035-xilinx. Genuine sudo xmutil listapps shows **k26-starter-kits ACTIVE (slot 0->0,) XRT_FLAT**, k24-starter-kits inactive. systemctl is-active fancontrol is **active**, fans visibly spin. systemctl is-active dfx-mgrd was **inactive**, but AMD documents the unit name **dfx-mgr.service**, to be checked instead. Owner independently verified accepted M08 .bit SHA on PC and reported source tests PASS. All 8 M01–M08 CI previously passed at 372410b4...; reverify latest source HEAD. **Do not issue sudo xmutil unloadapp or reuse the accepted .bit unmodified**: the original M08 PS→identity/page BD has no explicit valid TTC0-Clk2 EMIO fan route to K26 HDA20/A12. Owner chose **Path A Linux-managed deployment**, Path B only if safe and isolated. Implemented NEW source-only scripts/m08_kv260_path_a_readonly.sh, scripts/run_m08_path_a_readonly_pc.sh and tests/test_m08_path_a_readonly.py. [Authoritative Path A operator commands and fan/DT gate](M08_2B_PATH_A_LINUX_MANAGED_DISCOVERY_2026_11_11.md). First short PuTTY command: hostname -I, then PC VS Code launcher via SSH if available. No M08 program, Linux AXI, DDR or inference claimed.


**LATEST DEVELOPMENT / owner original SSH evidence update (2026-11-11):** Owner has verified PC SSH to ubuntu@10.42.0.135; uploaded new original 00_board_probe_source.sh, 00_input.txt, 01_board_stdout.log, 03_exit_status.txt and ledger 04_evidence_sha256.txt. Each of four ledger-covered **uploaded** files independently rehashed; fifth ledger row 02_ssh_stderr.log has SHA256 of empty file and owner states it was empty, but bytes were not uploaded. Ubuntu 24.04.2 kernel 6.8.0-1036-xilinx on ZynqMP KV260 revB, genuine **dfx-mgr.service active, fancontrol.service active, fpga0 operating, k26-starter-kits_image_1 loaded overlay**; K26 firmware triplet lives under /lib/firmware/xilinx. UIO0..3 are **axi-pmon** not 0xA0000000/0xA0001000 M08. Thus original owner SSH **platform discovery read-only PASS**, not FPGA program or PS AXI. The correct Linux fan route is **PS TTC0 wave-out[2] to EMIO to HDA20/A12**; old accepted M08 .bit did not implement it. Owner-selected Path A continues with **new distinct offline TTC fan BD augmenting original dual slave PS source**, scripts/m08_path_a_fan_bd_candidate.tcl, scripts/run_m08_path_a_fan_bd.sh, scripts/m08_path_a_fan_bd_audit.py, and tests/test_m08_path_a_fan_bd.py. No native new BD test yet, no route, no new .bit or physical evidence. New read-only SSH capture also gets installed shell.json + firmware hashes. [Current operator commands, original evidence hashes, acceptance scope](M08_2B_PATH_A_OWNER_EVIDENCE_AND_FAN_BD_2026_11_11.md). Keep old .bit untouched; do not xmutil unloadapp, JTAG program, flash, guess Linux MMIO or merge PR #83.


**LATEST OWNER NATIVE ATTEMPT / SOURCE CORRECTION (2026-11-11):** Owner uploaded original Vivado fan-BD log SHA `a1d27f47f431242d4ddb7e44967df19546e376cbced48b44268f3752ddc90219` with 5-file failure ledger. Genuine Vivado 2025.2 validated original KV260 PS HPM0 -> dual AXI identity/page at 0xA0000000 and 0xA0001000, 99,999,001 Hz, but **fan augmentation did NOT execute** because the source looked for a wrong unprefixed baseline scope marker. NO fan XDC/report/audit can exist for this failed run. New `scripts/m08_path_a_baseline_report_gate.tcl` demands exact original `META|scope|...`, its Tcl test reproduces the regression. Wrapper now archives auditor failure logs and hashes. Second owner SSH confirms installed K26 `XRT_FLAT`/1-slot shell, fancontrol/Cadence TTC; read-only SSH script now includes original K26 dtbo decompilation. Re-run a **fresh** offline Vivado fan BD only, and fresh read-only SSH `ubuntu@10.42.0.135`, never re-use original failed evidence path. [Failure analysis / commands](M08_2B_PATH_A_OWNER_EVIDENCE_AND_FAN_BD_2026_11_11.md). No M08 bitstream physical programming, PS AXI, Linux overlay, DDR or inference acceptance yet. Re-check 8 workflows at exact final HEAD; PR #83 draft unmerged.

## READ THIS FIRST — new original board evidence ALREADY received

User uploaded:
1. `03_jtag_inventory.txt` SHA256 **`c0ef6b6d1e5dd6f58fd042ddd630e86eeae6f3814b083558171530ff9badf4f9`**.
2. `04_jtag_console.log` SHA256 **`1ead36f4d22dd80e369b09495afd9eb6a77df373fe14f23a6679bd4273ac7a1a`**.

Those original files were read directly and their SHA256 independently computed. Their actual Vivado 2025.2 output:
```text
M08_KV260_JTAG_INVENTORY_READ_ONLY_NO_PROGRAMMING
META|vivado_version|2025.2
META|target_count|1
JTAG_TARGET|localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA
META|device_count|2
JTAG_DEVICE|xck26_0|xck26
JTAG_DEVICE|arm_dap_1|arm_dap
M08_JTAG_ENUMERATED_ONLY_NO_BOARD_CONFIGURATION_CHANGE
```
The single target opened successfully, then closed; `open_hw`/`close_hw` emitted only deprecation warnings. **JTAG CABLE/DRIVER/hw_server/device DISCOVERY IS SOLVED. DO NOT HAVE THE USER REPEAT IT OR INSTALL DRIVERS.** Programmable FPGA device is `xck26_0` (**NOT** `arm_dap_1`). This is original read-only hardware enumeration, **NOT** a programmed FPGA or working PS clock/AXI.

**USER PREFERENCE / HARD CONSTRAINT:** The user **cannot copy/paste into PuTTY**. Do NOT send multi-line shell blocks to type in PuTTY. Give only 1–3 **short single-line manual commands**, e.g. `uname -a`, `cat /etc/os-release`, `xmutil listapps`; all lengthy checks, hashes, scripting, Vivado work and logs should happen in VS Code on the PC or scripted via an already-working PC-to-board channel. If Linux does not boot, ask for **raw PuTTY serial boot log** instead of pretending these commands can run. User explicitly wants to **reuse previous Loihi digital-twin success and avoid retreading JTAG bitstream-loading battle**.

## Accepted M08 hardware evidence (original owner native boundaries)

- Signed16 256-byte physicalizable single-page state-bank `rtl/m08/m08_host_staged_page_bank.sv`, 32-bit PS AXI-Lite control `rtl/m08/m08_axil_page_control.sv`, compute-disabled `rtl/m08/m08_ps_page_safe_shell.v`: standalone genuine Icarus and local regression accepted by owner. **Compute DISPATCH is deliberately disabled on real PS-only shell**, so neural inference not present.
- Original real Vivado 2025.2 K26 two-slave BD `m08_2b_3_page_bd_20261111T172547Z_ZHe4WE`: PS `M_AXI_HPM0_FPD` → AMD SmartConnect 1×2 → read-only identity **0xA0000000**/4 KiB and signed16 page **0xA0001000**/4 KiB; actual PL0 **99,999,001 Hz**, verified clock propagation, `validate_bd_design` PASS, original independent audit and seven-source SHA PASS. These are **BD address assignments**, NOT authorization of Linux `/dev/mem`.
- Original post-route K26 trial `m08_2b_4_route_20261111T174620Z_9FLCz7`: real synthesis and route completed, WNS **+5.469 ns**, WHS **+0.015 ns**, 0 failing setup/hold and unconstrained endpoints, 0 methodology violations; 1,957 LUTs/1,665 FFs, **0 BRAM/DSP** in this small PS-only shell. **ONE DRC Warning RTSTAT-10**: 15 SmartConnect internal reset-pipeline no-load nets (14 names printed), explicitly recorded, not called DRC-clean. Original DCP SHA **`516ded0b2b19352952810b8f2a82f15b9eca02b4757cf53c187d179d051c8673`**.
- Owner original **real offline bitstream SUCCESS** `m08_2b_bitstream_20261111T200505Z_nnHihq`, `05_m08_safe_page.bit`: 7,797,831 bytes, owner original `write_bitstream` Completed Successfully and independent release audit `M08_ORIGINAL_K26_SAFE_PAGE_BITSTREAM_GENERATED_NOT_PROGRAMMED`. **SHA256 `170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf`**. Source manifest, native original `.bit` and `.dcp` were not individually uploaded; owner script verified original SHA. **Before programming, hash the ACTUAL .bit on PC and compare against this SHA**. Some earlier original owner files were uploaded, others are available only on the owner PC; avoid asserting unuploaded bytes were independently inspected.
- The previous true `.sv` top-module-reference and `NAME`-versus-`TOP` checkpoint guard bugs were fixed, original failures preserved, full source regression/CI accepted prior to the new JTAG inventory. No new design/synthesis/bitstream needed just to repeat JTAG enumeration.
- **NO M08 FPGA programming, PS-to-PL traffic, Linux device binding, kernel DDR, DMA, physical signed16 neuron update or inference has been evidenced.** Do not promote source/nightly test results to real hardware claims.

## EXACT proven Loihi Digital Twin v2 reuse (no reinvention)

Read these actual GitHub branch files **before writing new physical Tcl**:
- `Loihi_Digital_Twin/v2/hardware/p08_4_3b_physical_conformance.tcl`: accepted Loihi real Vivado/JTAG process.
- `Loihi_Digital_Twin/v2/hardware/run_p08_4_3b_physical.sh`: exact accepted bitstream/probes SHA gates + original hardware logs.
- `Loihi_Digital_Twin/v2/hardware/p03_physical_conformance.tcl` and `hardware/run_p03_physical.sh`: earlier accepted K26 K26 target selection and programming.
- `Loihi_Digital_Twin/v2/docs/P08_4_3B_ACCEPTANCE.md` and `docs/P08_4_3B_PHYSICAL_MNIST_CONFORMANCE.md`: exact physical acceptance scope.

**Use Loihi's already-proven programming sequence:** `open_hw_manager`, `connect_hw_server -url localhost:3121`, `get_hw_targets`, `current_hw_target`, `open_hw_target`, enumerate `get_hw_devices` and choose **`xck26_0`** only, `current_hw_device`, `refresh_hw_device -update_hw_probes false`, `set_property PROGRAM.FILE $bitfile $device`, **one** `program_hw_devices $device`, `refresh_hw_device`, preserve log/hash. Use exact target/part/bitstream SHA guards, unique fresh evidence, and explicit owner approval. The ARM DAP is a separate JTAG device, NOT another FPGA. This eliminates prior cable/driver setup and does not require Loihi bitstream or Loihi RTL.

**Critical difference from Loihi:** Loihi had `vio_p08` and accepted `.ltx`, JTAG-VIO reset/heartbeat and live host-bank instrumentation. **M08 .bit has NO matching `.ltx`/VIO debug bridge**: do NOT request `p08_host_paged.ltx`, search for `vio_p08`, or claim a JTAG heartbeat. Real M08 page registers need an actual **PS FPD HPM0 AXI initiator**, ready clocks/reset, and a supported software/debug accessor. Programming alone doesn't prove the page works. Reusing Loihi physical programming **does not** equate M08 signed16 page design with Loihi signed24 host-paged engine.

## Unresolved physical safety dependency (DO NOT IGNORE)

Live KV260 **boot/Linux or serial state, active PL app and fan-control ownership remain UNKNOWN** in this project. Historical user conversation showed PS boot stalled near BL31/FSBL on a prior occasion; do not assume today's boot state. AMD Kria 2022.1+ starter-kit Linux's `k26-starter-kits` base PL image can map TTC0 fan control via EMIO to carrier PL pin. Replacing that active PL image with M08 custom .bit (no verified EMIO fan routing) can disable active cooling or confuse Linux `dfx-mgrd` and device tree. Do not execute `program_hw_devices`, `xmutil unloadapp`, raw `devmem`/`/dev/mem`, firmware/QSPI/BOOT.BIN writes, PS reset or DDR writes until the actual board boot/image/cooling state is known and an operator authorizes a safe setup.

**NEXT USER-REACHABLE ACTION should NOT be JTAG re-enumeration.** Instead gather the missing **short PuTTY Linux/boot evidence**:
- If Linux shell: `uname -a`, `cat /etc/os-release`, `xmutil listapps` (if command exists). Optionally `systemctl is-active fancontrol` and `systemctl is-active dfx-mgrd` as **single short lines**. Enable PuTTY session logging in GUI and send log; don't manually transcribe long output.
- If NO Linux prompt: preserve entire raw PuTTY serial boot log, tell us where boot stops. **Do not ask to run Linux commands on a bootloader prompt.**
- If SSH or a supported PC-to-board command path is confirmed, run `scripts/m08_kv260_linux_readonly_inventory.sh` on board or from PC instead of lengthy PuTTY typing.
- User already ran and uploaded `scripts/m08_kv260_jtag_readonly_inventory.tcl` result; **DO NOT repeat** absent a changed connection.

## Ordered execution for the ONE remaining M08.2b goal

1. **Immediately:** inspect current board boot, fan, loaded app/FPGA manager from simple PuTTY commands or raw boot log; review against accepted Kria cooling and original OS constraints. Retain original transcript/hash. If Linux is not booting, choose deliberately prepared JTAG/bare-metal PS init + independent cooling rather than guessing.
2. **Then build a ONE-SHOT M08 PC-side bitstream programming script** by adapting Loihi `p08_4_3b_physical_conformance.tcl` to actual discovered K26 target `xck26_0`. Guard exact M08 .bit SHA, exact version and part, only one target and FPGA, and explicit `M08_ALLOW_PROGRAM=YES`; **no `.ltx`, no firmware flash, no bare PS memory writes, no silent retries**. Run only after operator approves current image/cooling/boot impact. This should be one real programming step, not a new milestone.
3. **Validate AXI initiator:** if Linux is healthy, inspect actual device tree/UIO/kernel driver binding; create a dedicated appropriate OS-safe user/kernel interface rather than guessing `/dev/uio0` or using raw `/dev/mem`. If Linux can't boot, evaluate original PS initialization and a safe debug/SW AXI master path; if none exists, integrate a **new M08-specific JTAG AXI/VIO debug bridge** as a separate explicitly labeled hardware revision (Loihi's VIO cannot interrogate current M08 bitstream).
4. **Capture actual physical PS→PL measurements:** identity magic `0x4D303831`/version `0x00010000` at `0xA0000000` design aperture; page magic `0x4D303850`/version `0x00020002` at `0xA0001000`, distinct windows; then safe 64×32-bit 256B staged fill/readback/COMMIT with byte-for-byte comparison and disabled DISPATCH rejection. Owner logs/bit SHA and file receipts required. Don't claim inference, DDR or DMA.
5. Once real physical page roundtrip is accepted, proceed to signed16 M06 service integration and eventually Linux-owned DDR/DMA and matched M08 benchmarking, preserving independent numerical/software reference and original owner evidence.

## Read these current docs / avoid stale handoffs

1. **Authoritative current physical plan:** `docs/M08_2B_PHYSICAL_DEPLOYMENT_PLAN_LOIHI_REUSE_2026_11_11.md`.
2. **Latest hands-on physical runbook:** `docs/M08_2B_KV260_PHYSICAL_BRINGUP_2026_11_11.md` (new JTAG evidence now supersedes its old 'please run JTAG' instructions).
3. **Research status and scope:** `roadmap.md`; implementation acceptance: `docs/M08_2B_POST_ROUTE_ACCEPTANCE_AND_WARNINGS_2026_11_11.md`; bitstream acceptance: `docs/M08_2B_BITSTREAM_AND_BOARD_HANDOFF_2026_11_11.md`.
4. Original earlier `M08_2_BD_FAILURE_NEXT_CHAT_HANDOFF_2026_11_10.md` is **historical**, not the current next chat source.
5. `docs/M08_TESTS_EXPLAINED.md` and `docs/M08_PHASED_HARDWARE_PLAN.md`; preserve all genuine owner Loihi/K26 evidence folders and previous trial failure logs immutable.

## Development/verification discipline

Existing branch/PR only; do not merge without explicit user command. Use GitHub connector and check actual PR head; source test command examples from PC root:
```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
git status --short
git fetch origin
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_physical_inventory.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
```
Check **all eight M01–M08 workflows on exact HEAD**, explicitly record pending/failed rather than assuming green. No physical operations from GitHub Actions. All fresh owner hardware runs in new exclusive timestamped SHA-pinned evidence directories, no mutation of previously accepted directories. No unsupported claims of bitstream programming, neural inference, PS DDR, DMA kernel ownership, Loihi arithmetic compatibility or Linux MMIO authorization.

**Next assistant behavior:** Start by acknowledging the owner's **JTAG SUCCESS**, **do not ask the user to repeat it**. Ask for only the *missing board Linux/boot/fan status*, using short PuTTY lines and logging. Use Loihi's exact already-successful JTAG programming commands after safety state is resolved. Keep developing toward actual physical M08 PS identity + 256B state-page evidence under one milestone. Give precise VS Code terminal verification commands whenever committing source, and a readily actionable plan in the same response.
