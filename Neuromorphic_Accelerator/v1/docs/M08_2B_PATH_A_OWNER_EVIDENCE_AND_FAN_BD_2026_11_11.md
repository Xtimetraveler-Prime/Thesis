# M08.2b Path A — real KV260 SSH evidence and fan-preserving offline Vivado candidate

**Date: 2026-11-11. ONE consolidated M08.2b objective. PR #83 DRAFT, UNMERGED. This is SOURCE development, NOT M08 hardware programming.**

## Original owner live Linux capture — accepted in READ-ONLY scope only

Source PC commit: 912238d694271ab2d39441fde1ab4105be9d89bf. SSH target: ubuntu@10.42.0.135.

Actual uploaded source files independently hashed and matched the original owner 04_evidence_sha256.txt ledger:

| Uploaded original | Verified SHA256 |
| --- | --- |
| 00_board_probe_source.sh | ba6bc9117f5da0649022dca59328e58f187215390dd4409a1abcbdf3fed5135b |
| 00_input.txt | 4ec3ba2b08be11fea23f93620db02755fceccd9b03771ae0b6e101ed1b72cca0 |
| 01_board_stdout.log | ebf0a7ebcfacea218cba59781ad8b40479f43bc4a5da7dd1bbbdfa6746e0ca87 |
| 03_exit_status.txt | 07110cf21080e754c593deed66fd982df984d2d40893c1ea029ce8aec9ba9e6c |

Owner reports 02_ssh_stderr.log is EMPTY; its receipt row is SHA256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855, exactly the standard empty-file digest. The stderr bytes were NOT uploaded; do not pretend that file was independently rehashed. The ledger itself has SHA256 556df1631df125056b767a4191f1669e58a70c873243df31dde4faef5a0247c4, not self-receipted.

Original physical observations:
- Linux 6.8.0-1036-xilinx, Ubuntu 24.04.2 LTS, ZynqMP KV260 revB. Earlier serial 1035 version is superseded by current SSH readback, without assuming reason for change.
- dfx-mgr.service ACTIVE, fancontrol.service ACTIVE, fpga0 state operating, exact overlay k26-starter-kits_image_1. Earlier dfx-mgrd service-name result of inactive did not indicate absence of the actual dfx-mgr.service.
- Genuine AMD firmware package root /lib/firmware/xilinx with active K26 starter-kit package including k26_starter_kits.bit.bin, k26_starter_kits.dtbo, shell.json. Firmware daemon configuration /etc/dfx-mgrd/daemon.conf confirms this root.
- Existing UIO uio0..uio3 are axi-pmon/xilinx_apm performance-monitor mappings at ffa00000, fd0b0000, fd490000 and ffa10000. NONE are legal M08 identity or page accessors.
- /proc/iomem ranges were largely printed as zeros. No inference of exact registered PL resources is supported by those redacted lines.
- Three observed temperature sensors were 34567, 33355 and 30705 milli-degrees C; no tachometer fan*_input found. Fancontrol ACTIVE and fans spinning apply to CURRENT base image only.
- sudo -n xmutil listapps from redirected SSH input reported password required; original operator earlier obtained valid sudo xmutil listapps in PuTTY showing k26-starter-kits active slot 0. This is a non-interactive sudo limitation, not a Linux hang.
- Original SSH wrapper exit_status=0. No bitstream loading/unloading, DDR operation, M08 AXI access or neural inference occurred.

**Acceptance status: ORIGINAL_OWNER_M08_KV260_LINUX_PATH_A_READONLY_INVENTORY_CONSISTENT_NOT_PROGRAMMED**. Preserve original capture and all previous owner Loihi/M08 artifacts unchanged.

## Why existing accepted M08 bitstream is NOT deployable yet

Official AMD Kria documentation explains current k26-starter-kits base PL supplies fan PWM via PS TTC0 wave-out channel 2 through EMIO to carrier HDA20 / FPGA A12. The original M08 PS-to-identity/page design has no validated A12 fan route, so programming it could disable active fan control. Do not unload the base, run JTAG programming or modify fancontrol at this stage. Even a correctly routed new candidate cannot guarantee cooling is uninterrupted during the reconfiguration gap.

References:
- https://xilinx-wiki.atlassian.net/wiki/plugins/viewsource/viewpagesrc.action?pageId=2471788698
- https://docs.amd.com/r/en-US/pg201-zynq-ultrascale-plus-processing-system/User-Parameters
- https://github.com/Xilinx/kria-vitis-platforms/blob/main/kv260/platforms/kv260_bist/xdc/pin.xdc

## New original owner trial: FIRST FAN-BD ATTEMPT FAILED AT SOURCE REPORT GATE (2026-11-11)

Original user-uploaded Vivado log from the PC, exact original bytes SHA256 `a1d27f47f431242d4ddb7e44967df19546e376cbced48b44268f3752ddc90219` (22,766 bytes); the original failure-only 30_evidence_sha256.txt recorded the identical log digest and identical pre/post source-manifest digests `d9367d08b75b850c1758ecf8469c3ed0f54fc627e65ab20c481e869dc2a4018f`. The user did NOT upload 00_source_sha256_before, 00_source_head or 03_run_result separately, so their bytes have NOT been independently checked; preserve originals. Original failed run folder from native vendor log: `/home/dna/Thesis_Evidence/M08/m08_2b_path_a_fan_bd_20261111T215739Z_hTrRuu`.

- Native Vivado 2025.2 did create project with KV260 SOM board_part 1.4, apply board preset, report 99,999,001 Hz clock, validate original PS FPD-HPM0-to-two-slave 4KiB BD, and assign ID `0xA0000000`/4KiB and page `0xA0001000`/4KiB.
- The subsequent fan augmentation NEVER STARTED: original baseline text stores the exact line `META|scope|M08_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD`, but new fan Tcl looked for the unprefixed `M08_PAGE_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD`. Fail-closed stop occurred at original Tcl line 41, before setting TTC0 EMIO, adding A12 constraints or writing any fan artifacts. The absence of fan report/audit/XDC is therefore EXPECTED, not missing owner submission. **Fan BD native PASS NOT claimed.**
- The new owner read-only SSH `01_board_stdout.log` was supplied without its second-run SHA receipt. It reports unchanged services/base and `shell.json` with `shell_type=XRT_FLAT`, `num_slots=1`, base K26 DTBO SHA `1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1` and base K26 bit.bin SHA `f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e`. The Linux `file` identification of the bit.bin as Photoshop swatch is an **unreliable magic heuristic**, not a validated bitstream-format analysis. TTC PWM uses `pwmchip0` Cadence compatible, 3 outputs; stock fancontrol configuration spans temperature 35–45C, with active fancontrol and hwmon 32873/33526/31264 millidegrees C in the owner log. These are NOT post-M08 fan-continuity measurements.

**Corrective source change:** added pure Tcl `scripts/m08_path_a_baseline_report_gate.tcl`, called from `m08_path_a_fan_bd_candidate.tcl`, to require the correctly prefixed scope and exactly one of each original report contract line before touching fan wiring. New mock Tcl tests reproduce the original missing-prefix failure and reject duplicated/partial markers, plus standalone audit tamper checks. Runner source manifest SHA-pins this new gate. Runner also retains audit diagnostic console and SHA hashes of every available evidence file if the independent audit fails. Latest Linux read-only probe now decompiles the installed K26 DTBO to **stdout only** with dtc, to design matching managed overlay only after actual base contents are known. **Neither new native Vivado run nor any PL/DT Linux modification has occurred.**

Next owner action: pull the latest branch, rerun source tests; then call `bash scripts/run_m08_path_a_fan_bd.sh` from PC with Vivado 2025.2 sourced, creating a new evidence directory (never reuse prior failed folder). Also run `bash scripts/run_m08_path_a_readonly_pc.sh ubuntu@10.42.0.135` from PC for the new DTBO decompile evidence. If the vendor next stops at unavailable TTC PS property, preserve the genuine log for targeted adaptation; never assume Native PASS from source mocks. Keep current k26-starter-kits active.

## New fan-preserving offline K26 source candidate

Scripts:
- scripts/m08_path_a_fan_bd_candidate.tcl
- scripts/run_m08_path_a_fan_bd.sh
- scripts/m08_path_a_fan_bd_audit.py
- tests/test_m08_path_a_fan_bd.py

The first-party new Tcl script SOURCES the existing, accepted original M08 dual-AXI PS BD Tcl into a fresh evidence project, then adds PS TTC0 channel 2 wave-out output using genuine AMD xlslice on EMIO. The required net is ps/emio_ttc0_wave_o[2] -> m08_ttc0_fan_slice -> M08_FAN_PWM top port. Exact K26 pin constraints generated are PACKAGE_PIN A12, IOSTANDARD LVCMOS33, SLEW SLOW, DRIVE 4.

It reruns genuine Vivado 2025.2 validate_bd_design, preserves two distinct original PS HPM0 4KiB AXI windows, leaves compute disabled, exports the fan-enhanced BD, emits a new fan-pin XDC, checks source SHA before/after and independently audits original outputs. Source regression has purely synthetic negative/tamper fixtures and is NOT physical proof.

**No new bitstream was generated.** No native Vivado run by owner on this new candidate, synthesis, place/route, actual pin fit, DRC, timing, Linux managed overlay, physical fan output, legal MMIO or PS-to-PL traffic is yet accepted.

### Exact owner PC commands (NOT PuTTY)

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
python3 -m compileall -q src scripts tests
bash -n scripts/run_m08_path_a_fan_bd.sh
python3 -m unittest discover -s tests -p 'test_m08_path_a_fan_bd.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
bash scripts/run_m08_path_a_fan_bd.sh
~~~

The LAST line executes offline Vivado **BD validation only**, not hardware programming. It creates one fresh immutable-style owner original evidence folder and prints its exact path. Preserve its 01_vivado_fan_bd.log, 02_vivado_page_bd_readback.txt, 20_m08_fan_bd_readback.txt, 21_m08_fan_pwm_a12.xdc, 22_m08_fan_bd_export.tcl, 23_independent_fan_bd_audit.json and 30_evidence_sha256.txt. On failure, preserve the original vendor log; don't suppress errors or rewrite the accepted M08 .bit.

### Refresh READ-ONLY SSH package evidence from PC

The previously working scripts/m08_kv260_path_a_readonly.sh probe now also captures the actual active starter-kit shell.json schema, K26 firmware .dtbo/.bit.bin SHA, PWM sysfs/fancontrol metadata and installed packaging tools. The wrapper automatically logs results without touching board filesystem/FPGA:

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
bash scripts/run_m08_path_a_readonly_pc.sh ubuntu@10.42.0.135
~~~

Return its original new 01_board_stdout.log, 02_ssh_stderr.log and 04_evidence_sha256.txt, not the previous immutable folder. This establishes actual package schema before creating matching managed .bit.bin/.dtbo/shell.json for new hardware. No guessed Linux binding or devmem allowed.

## Remaining M08.2b gates

1. Genuine native new fan+dual-AXI BD, then new genuine synth/route/timing/DRC and **separately identified new bitstream**. Original accepted M08 7,797,831-byte SHA-pinned bitstream is preserved.
2. Match installed Linux firmware package and device tree using captured original metadata. Create explicit Linux-owned identity/page (0xA0000000 and 0xA0001000, both 4KiB) UIO/kernel bindings after checking conflicts. Existing axi-pmon UIO nodes are NOT appropriate.
3. Operator-approved fan-safe PL transition and rollback with measured continuity; even correct output wiring may have an interval where fan PWM is absent. No unloadapp or program until safe cooling plan.
4. Real PS-to-PL identity magic reads, 64-word/256-byte write-READBACK/COMMIT, disabled DISPATCH SLVERR and immutable original transaction logs. NO neural HLS, DMA or physical DDR acceptance yet.

PR #83 remains DRAFT/UNMERGED pending explicit user approval.
