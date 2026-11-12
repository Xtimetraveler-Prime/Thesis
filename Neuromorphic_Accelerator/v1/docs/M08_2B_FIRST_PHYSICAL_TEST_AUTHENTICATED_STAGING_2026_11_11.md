# M08.2b first physical deployment — original live preflight audit and gated operator steps

**2026-11-11 Denver local / November 12 UTC.** ONE M08.2b, PR #83 DRAFT/UNMERGED. User reports independent second cooling fan installed and ready for the first physical test. Treat this as owner-reported extra cooling, **not instrumented evidence that it remains independently powered and effective throughout PL reconfiguration**. No M08 PL load, UIO read or physical page write has occurred in this review.

## Received and independently audited original preflight archive
`m08_2b_physical_preflight_review_m08_2b_physical_READONLY_6dtf4u1r.tar.gz` unpacked without paths/symlinks. Its original `99_evidence_sha256.txt` SHA256: `72a94c9fe67827296e7e71ebb2c651ccd47b72505a89d198eedeef5e053c3261`. **6/6 covered files independently hashed and MATCH**:
- `00_board_source.sh` `df1fb966c8b94569f5274150b0b868da2c369e6a05a51f25b0cd21c7f72889f1`
- `00_inputs.json` `4e39193c56216b8423381baa9acf7e1ee5a019c1f87acaeb5b39a0a038a0dc90`
- `01_ssh_stdout.log` `8e0502ff2e9196d2833e345011b5993238fd1daabc2251fa43636cceacf01993`
- `02_ssh_stderr.log` empty `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `03_ssh_exit.txt` `ed163d69a09ddc0ffcbdf126a42d5745a93449fa7a39354788e948b7ac795c04`, `exit_status=0`
- `04_review.json` `1da554213a6f5f0294a112eb3a775ce96f43f1fe6d415803f3f7525293f465cc`

`00_inputs.json` records actual owner-PC SHA rehash checks for corrected M08 `m08-v1-fan-page-uio-review.bit.bin` = `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b` and DTBO = `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed`, corrected ORIGINAL candidate directory `/home/dna/Thesis_Evidence/M08/m08_2b_path_a_uio_overlay_REVIEW_ONLY_oh3lt8_m`, original candidate SHA ledger `603c50a40ab9acbd8102c650cc5aef07ae1e44f08ef170090caf1ad25f06173a`. The uploaded archive **does not include** those original binary bytes and therefore only proves that the owner's audited PC runner reported rehash; user retains original binary files locally.

Genuine KV260 revB Ubuntu 24.04.2 kernel `6.8.0-1036-xilinx`, Linux `dfx-mgr 2024.2.0-0ubuntu1~xlnx1` and `dfx-mgr.service` active, `/sys/class/fpga_manager/fpga0/state=operating`, active `k26-starter-kits_image_1`. `/etc/dfx-mgrd/default_firmware` contains `k26-starter-kits`. `fancontrol.service` is active and `/etc/fancontrol` refers to PS/PL TTC0 PWM. Three real read-only AMS sensors report **35.236 C, 34.319 C, 32.865 C** at this capture (not absolute max ratings or proven gap thermal margins). `/sys/class/hwmon/hwmon1/pwm1=15`, `pwm1_enable=1`, no fan RPM captured. Generic UIO kernel driver present, four original `axi-pmon` UIO nodes (not M08). `/proc/iomem` address ranges are ZEROED in the unprivileged original output, **so no conclusion that 0xA0000000 / 0xA0001000 are unclaimed** can be drawn.

The original exact stock baseline is present on board:
- `/lib/firmware/xilinx/k26-starter-kits/k26_starter_kits.bit.bin` SHA `f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e`;
- `k26_starter_kits.dtbo` SHA `1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1`;
- `shell.json` SHA `2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777`, `XRT_FLAT` one slot.

**CRITICAL NONPASS:** individual original read-only probe `xmutil_listapps` ended `rc=1` because `sudo -n` refused with `sudo: a password is required`. This does **not** invalidate the successful SSH evidence capture, but it **does** mean the authenticated manager inventory / manager-controlled rollback / `PL_FLAT` registration are still OPEN. The receipt's `READ_ONLY_BASELINE_CAPTURED_FOR_OPERATOR_REVIEW` and shell exit 0 are NOT an all-probes PASS or permission to unload the active bitstream. `/proc/iomem` zeros likewise are not address ownership evidence.

## AMD technical sources and safety boundary
- AMD UG1630: https://docs.amd.com/r/en-US/ug1630-kria-som-apps-developer-ubuntu/dfx-mgrd confirms `xmutil listapps/loadapp/unloadapp` call `dfx-mgrd`; firmware must be under `/lib/firmware/xilinx/<app_name>` with `*.bit.bin`, `*.dtbo`, and `shell.json`; `*.xclbin` optional for non-XRT.
- Upstream: https://github.com/Xilinx/dfx-mgr describes `PL_FLAT` as a supported static bitstream type and documents `dfx-mgr-client -listPackage -all`. This does NOT prove the exact Ubuntu 2024.2 daemon's runtime acceptance.
- AMD K26 fan bitstream guidance: https://xilinx-wiki.atlassian.net/wiki/plugins/viewsource/viewpagesrc.action?pageId=2471788698 warns removing `k26-starter-kits` breaks the carrier's TTC0 EMIO to A12 PL fan-control route. Independent external cooling must actually be observed spinning and powered separately throughout the gap. Do not drive external voltage into PWM/PL pins.

## First **authenticated** owner inventory (read-only, next step)

Use the PC's VS Code terminal, NOT PuTTY multiline. Leave the stock FPGA loaded. Make a NEW local evidence dir and allow the remote `sudo` password prompt to use a real SSH PTY, not `sudo -n`/stdin-script. Never send the password via files, env vars, here-documents or logged command lines:

```bash
EVIDENCE_BASE=/home/dna/Thesis_Evidence/M08
LIVE="$(mktemp -d "$EVIDENCE_BASE/m08_2b_authenticated_inventory_XXXXXXXX")"
ssh -tt -o ConnectTimeout=12 ubuntu@10.42.0.135 'sudo xmutil listapps' 2>&1 | tee "$LIVE/01_xmutil_listapps.log"
XMUTIL_RC=${PIPESTATUS[0]}
printf 'exit_status=%s\n' "$XMUTIL_RC" > "$LIVE/02_xmutil_exit.txt"
if [ "$XMUTIL_RC" -ne 0 ]; then echo "STOP: authenticated xmutil inventory failed"; fi
ssh -tt -o ConnectTimeout=12 ubuntu@10.42.0.135 'sudo dfx-mgr-client -listPackage -all' 2>&1 | tee "$LIVE/03_dfx_listpackage.log"
DFX_RC=${PIPESTATUS[0]}
printf 'exit_status=%s\n' "$DFX_RC" > "$LIVE/04_dfx_exit.txt"
(cd "$LIVE" && sha256sum 01_xmutil_listapps.log 02_xmutil_exit.txt 03_dfx_listpackage.log 04_dfx_exit.txt > 99_evidence_sha256.txt)
echo "INVENTORY_DIR=$LIVE"
```

Both commands **query** manager registration; neither unloads or loads an FPGA bitstream. The owner should review both return codes and verify the stock baseline is listed as active; if output is surprising, STOP and share genuine terminal evidence. `ssh -tt` enables interactive sudo; the log must not contain password input. Two separate sudo commands may prompt, which is expected.

## Optional strictly non-deploying firmware transfer to user-home staging

**Only after the authenticated inventory is successful** and stock is still active. No `/lib/firmware/xilinx` write, manager register, unload, load, JTAG or UIO open:

```bash
CANDIDATE=/home/dna/Thesis_Evidence/M08/m08_2b_path_a_uio_overlay_REVIEW_ONLY_oh3lt8_m
STEM=m08-v1-fan-page-uio-review
test -f "$CANDIDATE/$STEM/$STEM.bit.bin" || exit 2
test -f "$CANDIDATE/$STEM/$STEM.dtbo" || exit 2
test -f "$CANDIDATE/$STEM/shell.json" || exit 2
(cd "$CANDIDATE" && sha256sum -c 99_evidence_sha256.txt) || exit 2
REMOTE_DIR="$(ssh -T ubuntu@10.42.0.135 'mktemp -d "$HOME/m08_2b_STAGED_ONLY_XXXXXXXX"')" || exit 2
[[ "$REMOTE_DIR" =~ ^/home/ubuntu/m08_2b_STAGED_ONLY_[A-Za-z0-9]+$ ]] || { echo "STOP invalid remote path"; exit 2; }
scp -p "$CANDIDATE/$STEM/$STEM.bit.bin" "$CANDIDATE/$STEM/$STEM.dtbo" "$CANDIDATE/$STEM/shell.json" "ubuntu@10.42.0.135:$REMOTE_DIR/" || exit 2
ssh -T ubuntu@10.42.0.135 "sha256sum '$REMOTE_DIR/$STEM.bit.bin' '$REMOTE_DIR/$STEM.dtbo' '$REMOTE_DIR/shell.json'"
```

Compare remote bit.bin hash **a8ed0e4...**, DTBO **2b779805...**, and shell SHA to your original local copy. Record output. This step transfers **only files into the regular user's home**, so it is not the first FPGA programming experiment. Do not overwrite or touch the original stock firmware.

## First real PL reconfiguration gate (not yet executed)

Before using any active manager command, explicitly establish:
1. Authenticated `xmutil listapps` and `dfx-mgr-client -listPackage -all` succeed and show active stock firmware; stock hashes still match above. The new M08 `PL_FLAT` package must be independently confirmed as recognized by the exact installed manager **after separately reviewed package registration**.
2. Independently powered second fan visibly runs continuously, reaches KV260 heatsink and remains operative when PL PWM changes. Keep serial log and temperature monitoring while the PL is replaced; no unverified thermal limits.
3. Record known manager-controlled stock restore method and keep independent cooling if manager becomes unavailable; ensure functioning PC serial/UART and out-of-band power recovery. Firmware files present on disk are **not** rollback proof on their own.
4. No address collision in effective live DT or existing Linux driver resource claims; `/proc/iomem` zero redaction is NOT clearance to assume free address space.
5. Owner reviews and approves the specific planned unload/load and recovery commands. NEVER execute blind `xmutil unloadapp` while the stock fan routing is needed. Preserve logs and halt on failed registration/ownership.

Once these gates pass, the **first physical experiment** is one manager-controlled M08 load plus immediate inspection of `fpga_manager`, active DT overlay, original thermals, current fan behavior and **metadata-only** exact UIO mapping; stop before MMIO read/write. Identity-only UIO read is the next separately logged/approved action. Physical M08 page writes, compute DISPATCH, and neural/DDR claims remain open.

## GitHub/local verification scope
PR #83 stays DRAFT and unmerged. Changes at this point are original owner evidence acceptance and operator instructions; no byte changes to M08 .bit.bin, native DTBO, Linux packaging or verified RTL. Do not recalculate bitstream hashes or regenerate original candidate just to perform preflight. Current hardware state remains the live `k26-starter-kits` image.
