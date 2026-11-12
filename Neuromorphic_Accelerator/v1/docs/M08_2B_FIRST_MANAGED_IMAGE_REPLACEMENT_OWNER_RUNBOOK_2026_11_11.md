# M08.2b — FIRST physical managed Linux image replacement, owner runbook

**2026-11-11 local / 2026-11-12 UTC**. ONE M08.2b, PR #83 DRAFT/UNMERGED. User **explicitly requested** proceeding with the first physical image replacement after reporting an independently powered second cooling fan. This document provides owner-executed commands only; **no ChatGPT board operation occurred**.

## Evidence accepted BEFORE any PL changes

Original owner archive `m08_2b_authenticated_inventory_review_m08_2b_authenticated_inventory_lhjQYj6g.tar.gz` independently SHA-rehashed: all **6/6** original files match `99_evidence_sha256.txt` (ledger itself SHA `ead65dfecf539e023dad7082cfff951d34e76ca3709fa950cebc3b25de437be3`). Both authenticated `sudo xmutil listapps` and `sudo dfx-mgr-client -listPackage -all` returned **exit_status=0** and report `k26-starter-kits` XRT_FLAT loaded in slot `0->0`; `k24-starter-kits` is present but inactive. No M08 registered yet. Exact original local-vs-board SHA rows agree for all three transferred files under `/home/ubuntu/m08_2b_STAGED_ONLY_2IXknEpG`:
- `m08-v1-fan-page-uio-review.bit.bin`: `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b`
- `m08-v1-fan-page-uio-review.dtbo`: `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed`
- `shell.json`: `0377daaf2050b88df14de9a79d120144cf49381d00fa552402395a322cb7b1a3`

These are **original user-recorded hashes** in the uploaded archive; the binary bytes were not uploaded. The previous owner SHA-backed read-only physical baseline shows KV260 revB, Ubuntu 24.04.2 kernel 6.8.0-1036-xilinx, dfx-mgr 2024.2 active and fancontrol active, temperatures ~33–35°C; the stock recovery files were SHA-identified as follows:
- `/lib/firmware/xilinx/k26-starter-kits/k26_starter_kits.bit.bin`: `f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e`
- `/lib/firmware/xilinx/k26-starter-kits/k26_starter_kits.dtbo`: `1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1`
- `/lib/firmware/xilinx/k26-starter-kits/shell.json`: `2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777`

Upstream AMD **2024.2** DFX-MGR README explicitly supports `PL_FLAT` as a static bitstream type, recognizes bit.bin+dtbo+shell.json in `/lib/firmware/xilinx/<app>` and documents `-listPackage` and `xmutil` manager. [2024.2 source](https://github.com/Xilinx/dfx-mgr/tree/xlnx_rel_v2024.2); [AMD Ubuntu guide](https://docs.amd.com/r/en-US/ug1630-kria-som-apps-developer-ubuntu/dfx-mgrd). **The installed daemon's runtime acceptance of THIS package and subsequent load/rollback is NOT proven until run.** AMD's K26 active fan path traverses TTC0/PL A12 and may be interrupted during image swap. The user's second independent fan must stay physically on and effective; never drive board PWM lines externally.

## Operator preparations (STOP if any fails)

1. External independent fan visibly running with airflow over K26 heatsink, powered independently of PL PWM. Leave it running throughout test AND any rollback. Do not modify fancontrol settings.
2. Attach a PC serial PuTTY session with **all session output** logging enabled so recovery is possible even if SSH/dfx-mgr fails. Do not disconnect board power or restart Linux during first attempt.
3. Keep original stock `/lib/firmware/xilinx/k26-starter-kits` and `/etc/dfx-mgrd/default_firmware` unchanged. Ensure visible board temperature monitoring, and use conservative judgement if temperature rises or fan airflow changes; no fabricated absolute temperature limit.
4. Never access /dev/mem or /dev/uio, write M08 page or issue DISPATCH during first PL programming experiment. Only manager and read-only sysfs.
5. M08 bitstream is full/flat, not partial. This is one manager-controlled stock unload followed by one target load. Avoid JTAG reconfiguration, FPGA sysfs firmware writes, manual overlay applying, automatic repeated retries.

## Stage A — install triplet to manager catalog WITHOUT programming FPGA

On the **PC VS Code terminal**, using the existing checked-out M08 branch, record the operator SSH session to a NEW evidence directory:

```bash
EVIDENCE_BASE=/home/dna/Thesis_Evidence/M08
PHYSICAL_LOG="$(mktemp -d "$EVIDENCE_BASE/m08_2b_first_physical_operator_XXXXXXXX")"
printf 'operator_phase=MANAGED_LINUX_FIRST_LOAD\nsource_head=%s\n' "$(git rev-parse HEAD)" > "$PHYSICAL_LOG/00_context.txt"
ssh -tt ubuntu@10.42.0.135 2>&1 | tee "$PHYSICAL_LOG/01_operator_ssh.log"
```

Inside this **interactive SSH terminal** (NOT in PuTTY), authenticate via `sudo -v` and execute these commands. `set -euo pipefail` quits on unexpected guard failure rather than continuing toward PL unload:

```bash
set -euo pipefail
sudo -v
APP=m08-v1-fan-page-uio-review
STAGED=/home/ubuntu/m08_2b_STAGED_ONLY_2IXknEpG
DEST=/lib/firmware/xilinx/$APP

test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating
test "$(systemctl is-active dfx-mgr)" = active
test "$(systemctl is-active fancontrol)" = active

printf '%s  %s\n' a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b "$STAGED/$APP.bit.bin" | sha256sum -c -
printf '%s  %s\n' 2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed "$STAGED/$APP.dtbo" | sha256sum -c -
printf '%s  %s\n' 0377daaf2050b88df14de9a79d120144cf49381d00fa552402395a322cb7b1a3 "$STAGED/shell.json" | sha256sum -c -

STOCK=/lib/firmware/xilinx/k26-starter-kits
printf '%s  %s\n' f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e "$STOCK/k26_starter_kits.bit.bin" | sha256sum -c -
printf '%s  %s\n' 1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1 "$STOCK/k26_starter_kits.dtbo" | sha256sum -c -
printf '%s  %s\n' 2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777 "$STOCK/shell.json" | sha256sum -c -

LIST="$(sudo xmutil listapps)"
printf '%s\n' "$LIST"
printf '%s\n' "$LIST" | grep -Eq '^[[:space:]]*k26-starter-kits[[:space:]]+XRT_FLAT.*0->0'
test "$(tr -d '\r\n' < /etc/dfx-mgrd/default_firmware)" = k26-starter-kits

if sudo test -e "$DEST" || sudo test -L "$DEST"; then
    echo 'STOP: target M08 catalog directory already exists; inspect it, never overwrite'
    exit 2
fi

sudo install -d -m 0755 "$DEST"
sudo install -m 0644 "$STAGED/$APP.bit.bin" "$DEST/$APP.bit.bin"
sudo install -m 0644 "$STAGED/$APP.dtbo" "$DEST/$APP.dtbo"
sudo install -m 0644 "$STAGED/shell.json" "$DEST/shell.json"

printf '%s  %s\n' a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b "$DEST/$APP.bit.bin" | sha256sum -c -
printf '%s  %s\n' 2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed "$DEST/$APP.dtbo" | sha256sum -c -
printf '%s  %s\n' 0377daaf2050b88df14de9a79d120144cf49381d00fa552402395a322cb7b1a3 "$DEST/shell.json" | sha256sum -c -

LIST="$(sudo xmutil listapps)"
printf '%s\n' "$LIST"
sudo dfx-mgr-client -listPackage -all
printf '%s\n' "$LIST" | grep -Eq '^[[:space:]]*m08-v1-fan-page-uio-review[[:space:]]+PL_FLAT'
printf '%s\n' "$LIST" | grep -Eq '^[[:space:]]*k26-starter-kits[[:space:]]+XRT_FLAT.*0->0'
test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating

echo 'STAGE_A_PASS_M08_REGISTERED_STOCK_STILL_RUNNING'
```

**HARD STOP:** If no exact M08 `PL_FLAT` catalog row appears, the daemon crashes, either hash differs, or the stock app stops being active, do NOT attempt unload/load. A package being staged in `/lib/firmware/xilinx` is NOT equivalent to its successful registration.

**Before Stage B**, while stock is still running, separately inspect read-only root-visible resource ownership with `sudo cat /proc/iomem`; previous nonroot capture redacted addresses to zeros. If any driver currently owns an overlapping `0xA0000000..0xA0001FFF` range, STOP. Do not assume absence of rows is complete Linux DT/driver proof.

## Stage B — explicitly consented one-shot physical image replacement

Proceed **ONLY** after Stage A prints its PASS marker, cooling is independently verified operational, PuTTY UART logging is on, stock recovery is available, and the resource inspection does not show conflicting owners. Still inside the operator SSH shell:

```bash
echo 'Confirm external powered fan is spinning, UART is recording, stock rollback files are verified.'
read -r -p 'Type LOAD_M08 to perform the first full PL replacement: ' CONFIRM
test "$CONFIRM" = LOAD_M08

sudo xmutil unloadapp
if ! sudo xmutil loadapp "$APP"; then
    echo 'M08_LOAD_FAILED_STOP_KEEP_EXTERNAL_FAN_ON'
    sudo xmutil listapps || true
    exit 30
fi

test "$(cat /sys/class/fpga_manager/fpga0/state)" = operating
LIST="$(sudo xmutil listapps)"
printf '%s\n' "$LIST"
printf '%s\n' "$LIST" | grep -Eq '^[[:space:]]*m08-v1-fan-page-uio-review[[:space:]]+PL_FLAT.*0->'
systemctl is-active dfx-mgr fancontrol
for p in /sys/class/hwmon/hwmon*/temp*_input; do
    if test -r "$p"; then printf '%s=' "$p"; cat "$p"; fi
done
for p in /sys/kernel/config/device-tree/overlays/*; do
    if test -d "$p"; then echo "ACTIVE_OVERLAY=$p"; fi
done
sudo journalctl -u dfx-mgr -n 60 --no-pager
echo 'M08_IMAGE_REPLACEMENT_MANAGER_CLAIMS_SUCCESS_METADATA_ONLY'
```

**The marker is not physical AXI proof.** No /dev/uio read, no RAM access, no DISPATCH. If a step fails, or heat/fan behavior is concerning, preserve original logs and follow the manual rollback case below rather than retrying M08.

After exiting SSH (`exit`), preserve **fresh** PC-side metadata-only M08 sysfs evidence:

```bash
ssh -T -o ConnectTimeout=10 ubuntu@10.42.0.135 \
  'PYTHONDONTWRITEBYTECODE=1 python3 - --expected present' \
  < scripts/m08_path_a_uio_sysfs_readonly.py \
  > "$PHYSICAL_LOG/02_uio_sysfs_stdout.json" \
  2> "$PHYSICAL_LOG/03_uio_sysfs_stderr.log"
UIO_RC=$?
printf 'exit_status=%d\n' "$UIO_RC" > "$PHYSICAL_LOG/04_uio_exit.txt"
(cd "$PHYSICAL_LOG" && sha256sum -- 00_context.txt 01_operator_ssh.log \
    02_uio_sysfs_stdout.json 03_uio_sysfs_stderr.log 04_uio_exit.txt \
    > 99_evidence_sha256.txt)
echo "PHYSICAL_EVIDENCE_DIR=$PHYSICAL_LOG"
```

For `UIO_RC=0`, the inspector must return exact two names and map0 4KiB bases `0xA0000000` and `0xA0001000`. Existing UIO0..3 axi-pmon may remain; NEVER infer new `/dev/uioN` index from memory or guess. Metadata alone does not confirm that the PS can read those addresses. Stop and return **all original 00–04 outputs and ledger**, plus original PuTTY serial log, for independent first physical acceptance review **before any MMIO**.

## Manual rollback — select according to real manager state

Leave the independent fan ON throughout. For SSH- or serial-accessible, responsive manager:
- First inspect `sudo xmutil listapps` and `cat /sys/class/fpga_manager/fpga0/state`; identify which application (if any) is active.
- **If M08 is active:** `sudo xmutil unloadapp`, then `sudo xmutil loadapp k26-starter-kits`.
- **If no image is active after M08 failed:** `sudo xmutil loadapp k26-starter-kits` **without an unnecessary unload**.
- **If stock is already active:** do not unload again.
- Verify `sudo xmutil listapps` prints stock XRT_FLAT in slot 0, `fpga_manager` operating, fancontrol running, thermal stabilization; check stock original hashes remain as above.
- If manager/SSH becomes unresponsive, continue external cooling and switch to already-proven PuTTY UART login/recovery. Do not power-cycle, flash QSPI or issue JTAG hot programming as an unplanned recovery attempt.
- No automatic retry and no automatic claim of rollback success; preserve exact first failed command and original logs.

## Physical acceptance scope

On first operator success the **strongest permitted result** is “M08 Linux-managed PL image reported loaded and both UIO map descriptors are present, original logs SHA-verified.” A real PS-to-PL **identity register read** is the subsequent **separately reviewed** step, followed by a distinct 64×32-bit page verification later; standalone UIO mmap can SIGBUS/hang and does not expose AXI BRESP/RRESP. Signed16 neural compute, DMA/DDR and comparative performance remain OPEN. PR #83 stays DRAFT/UNMERGED pending owner first physical evidence.
