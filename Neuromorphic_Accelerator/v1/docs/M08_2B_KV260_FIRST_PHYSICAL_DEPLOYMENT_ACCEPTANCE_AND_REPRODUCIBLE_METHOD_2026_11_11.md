# M08.2b — FIRST SUCCESSFUL PHYSICAL KV260 Linux-managed PL deployment: acceptance and reproducible procedure

**Reviewed 2026-11-11 America/Denver (owner original terminal journal entries Nov 12 UTC).**
Project: `Neuromorphic_Accelerator/v1`, ONE M08.2b, branch `agent/neuromorphic-accelerator-v1-m08-kv260-bringup`, PR #83 **DRAFT, UNMERGED**.

## 1. Immutable evidence and exact meaning of acceptance

Owner supplied:
- `m08_2b_first_physical_review_m08_2b_first_physical_operator_DKMZ4cEE.tar.gz`; independent tarball SHA256 **`84c53e456fa3f5d58b3200a86063973060d1e653ccf71467aa8a7fd73a9733ed`**.
- `Pasted text.txt`, an operator-copied transcript ending mid-`dfx-mgr` journal. Its text is supporting context, **not** a complete replay or extra hardware proof. The larger original SSH log in the archive contains the entire operator session.

Tarball consists of **SIX files total: FIVE original ledger-covered artifacts plus the SHA ledger itself**, not "six ledger-covered" entries. Independently audited against the original `99_evidence_sha256.txt` (ledger SHA256 **`3bfc2862df8e3953b896ee728c73a80c96ae6a006e298ccf5c19f48dab8d1bbf`**):

| Original archived file | SHA256 | Independent result |
|---|---|---|
| `00_context.txt` | `6721536d8e650bdf0564dc371c2aa17ae80b7327ffbe5bb0d2e9a8dfe3060ca6` | MATCH |
| `01_operator_ssh.log` | `931a6342862396dbc3ac11ba552380eb37d0fa8d8072ce2e610cf7d23398dffb` | MATCH |
| `02_uio_sysfs_stdout.json` | `465aa5f6a8d60752334b1951c235acfb7c2695ea5bed255e4cfe4ac6128cd0dd` | MATCH |
| `03_uio_sysfs_stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) | MATCH |
| `04_uio_exit.txt` | `ed163d69a09ddc0ffcbdf126a42d5745a93449fa7a39354788e948b7ac795c04` (`exit_status=0`) | MATCH |

`00_context.txt` pins operator local source head to `b04cc15064f80bdea154f3182e90c688444d26b5`. Keep the original owner folder and exact downloaded archive immutable. The original PuTTY UART recording was **not included** in the uploaded evidence and was not independently reviewed.

**M08.2b PHYSICAL ACCEPTANCE achieved:** (a) genuine vendor-converted `.bit.bin` and corrected `.dtbo` verified with SHA on the KV260, (b) installed and recognized as `PL_FLAT` by the actual installed `dfx-mgr`, (c) original K26 `XRT_FLAT` unloaded successfully; new M08 flat firmware load returned success and occupies slot0, (d) FPGA manager reports `operating`, services `dfx-mgr` and `fancontrol` active, expected new device-tree overlay active, (e) Linux `generic-uio` maps exactly two M08 4KiB windows. The operator **reports visually that the KV260 fan worked throughout the transition**, with a second independently powered fan also in use.

**Not yet proven:** no `/dev/uioN` device node has been opened for physical register MMIO; no PS AXI RDATA/RRESP, exact identity values or page data have been observed; no 64-word state page readback/COMMIT; no measured PWM or thermal waveform DURING reconfiguration; no actual stock rollback was performed; no DDR, DMA, signed16 neuron inference, event engine, energy/performance claim. Do not interpret the JSON field `physical_fpga_programming: NOT_PERFORMED_BY_THIS_TOOL` as evidence against the operator's documented actual programming: that field correctly scopes **the sysfs-only inspector**, which itself did not program the PL.

## 2. Genuine observed outcome, not expected-only

- Owner PC/candidate and installed board `m08-v1-fan-page-uio-review.bit.bin`: SHA256 `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b`.
- Corrected `m08-v1-fan-page-uio-review.dtbo`: `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed`.
- `shell.json`: `0377daaf2050b88df14de9a79d120144cf49381d00fa552402395a322cb7b1a3`. Exact JSON `{"shell_type":"PL_FLAT","num_slots":"1"}`.
- K26 original starter bit.bin SHA `f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e`; original DTBO SHA `1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1`; original shell SHA `2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777`. All six M08+stock file hashes checked `OK` before registration; installed M08 triplet subsequently hashed to the same three digests.
- Linux host: KV260 revB Ubuntu 24.04.2/kernel `6.8.0-1036-xilinx`; daemon `dfx-mgr 2024.2.0-0ubuntu1~xlnx1`, `fancontrol` active.
- `xmutil listapps` BEFORE: `k26-starter-kits` `XRT_FLAT` slot `0->0`; M08 absent. After placing M08 triplet in its own app folder: M08 appeared as `PL_FLAT`, initially `-1` (not loaded), with stock still active. `STAGE_A_PASS_M08_REGISTERED_STOCK_STILL_RUNNING` printed.
- Actual owner command sequence: `sudo xmutil unloadapp` printed `remove from slot 0 returns: 0 (Ok)`; `sudo xmutil loadapp "$APP"` printed `m08-v1-fan-page-uio-review: Loaded with slot_handle 0`. AFTER: stock row `-1`, M08 row `0->0,`; `/sys/class/fpga_manager/fpga0/state`=`operating`, `/sys/kernel/config/device-tree/overlays/m08-v1-fan-page-uio-review_image_1` exists. Source log recorded `dfx-mgrd` loading request without a reported error. The `xmutil` table's `PL_FLATm08-...` concatenation is **column formatting for a long application name**, not a malformed shell type or error. Normal `id_ok` reported.
- After-load `systemctl is-active dfx-mgr` and `fancontrol`: both `active`. Post-load `hwmon0` temperatures `37085,34194,32718` milli°C = `37.085,34.194,32.718°C`. Compared with genuine earlier predeployment snapshot `35.236,34.319,32.865°C`: `+1.849,-0.125,-0.147°C` (NOT a synchronized before/after time series or guarantee of maximum thermal margin). Owner additionally reports local observation of uninterrupted fan operation; no time-continuous RPM/PWM recording supplied.
- `sudo cat /proc/iomem` before unload showed the **real root-visible** physical reservations; no printed overlapping resource covering `0xA0000000..0xA0001FFF`. **This is only a resource-inventory check, not an exhaustive ownership/physical AXI proof.**
- Genuine `02_uio_sysfs_stdout.json` parsed with exit0, stderr empty: `uio0..uio3` were original `axi-pmon` devices; `uio4` `m08-identity` has unique map0 base `0x00000000a0000000`, size 4096; `uio5` `m08-page` map0 base `0x00000000a0001000`, size 4096. The device-name mappings, rather than fixed indices, MUST be used in future readers. The metadata JSON reports `register_readback: NOT_PERFORMED` / `driver_behavior: NOT_VERIFIED`.

## 3. Working repeatable Linux deployment strategy for FUTURE M08 images

**No more reconfiguration needed to proceed to the next identity read: KEEP this successful M08 image loaded.** Never repeat stock unload merely for validation.

- Compile/place-and-route the **KV260-specific** PS+PL AXI safe shell and fan A12 routed design in genuine Vivado, preserving independent route/timing/DRC receipts; build genuine new `.bit`, exact SHA; bootgen `-arch zynqmp -process_bitstream bin` produces `.bit.bin`, and native DTC `-@` produces `.dtbo` with `&fpga_full`, `&zynqmp_reset`, `&amba` fixups and dual `generic-uio` resources only if linux-owned addresses are independently reviewed. Decode native DTBO, require no compile warnings. Package together with `shell.json` `{"shell_type":"PL_FLAT","num_slots":"1"}`, matching firmware-name, and record all SHA originals.
- Validate current stock baseline and external independent cooling; leave `fancontrol` enabled; capture active firmware manager, version, kernel, serial recovery access, original bitstream and DTBO hashes; use ONLY Linux `dfx-mgr`/ `xmutil` to transition the running PL, NOT parallel JTAG, raw FPGA manager writes, custom `fpgautil` or manual device-tree overlay writes.
- Secure-copy the original SHA-audited triplet first to a fresh **unprivileged owner home folder** (not the active firmware catalog). Independently SHA-rehash on the board.
- Install under **a distinct versioned application name** `/lib/firmware/xilinx/<app_name>/` with filenames `<app_name>.bit.bin`, `<app_name>.dtbo`, `shell.json`; root-owned normal 0755 directory, 0644 files, no overwrite of a registered or loaded app. Validate installed SHA. Important: stage-first then catalog registration allows an atomic "recognize while original still loaded" decision boundary.
- `sudo xmutil listapps`, `sudo dfx-mgr-client -listPackage -all`: require new `PL_FLAT` with no loaded slot and old `XRT_FLAT` still slot0 before programming. Confirm persistent default firmware still points to stock; do not change the default. The `dfx-mgr` daemon's inotify-based package discovery worked on Ubuntu 2024.2 without a daemon restart.
- Use **owner-confirmed independent cooling spanning the PL gap**, visible serial console and log capture, root-visible `/proc/iomem` conflict inspection, stock rollback file hashes and typed operator consent. Execute `sudo xmutil unloadapp` **exactly once**, then `sudo xmutil loadapp <new_name>` **exactly once**. If load fails, do NOT blindly retry. Determine the actual slot state then take the approved recovery action while external cooling stays powered.
- Confirm the new app's `0->0` slot, `fpga_manager operating`, active configfs overlay, `dfx-mgr` and `fancontrol` active, actual thermals and kernel logs; run the **metadata-only first-party** `scripts/m08_path_a_uio_sysfs_readonly.py --expected present`, no /dev/uio registers. Create a fresh SHA ledger for *all* genuine owner terminal and sysfs evidence, and independently review before physical MMIO.
- Fallback with responsive daemon: if M08 active, unload M08 then load original stock; if no app active, directly load stock; if stock already active, leave it. Preserve original `/lib/firmware/xilinx/k26-starter-kits` (do not overwrite stock). The **availability of this rollback path is documented**, but as of this acceptance an actual rollback has NOT been run. If SSH/manager hangs, maintain independent fan, use serial recovery; no improvised JTAG/power reset.
- For future versioned packages, preserve known-good M08 as separate catalog entry when appropriate. Changing `/etc/dfx-mgrd/default_firmware` was not needed and is **not recommended** for initial research runs.

**Avoid two prior pitfalls:** an unprivileged `/proc/iomem` showed all-zero/redacted ranges, so use a root-visible read for ownership review; `sudo -n xmutil listapps` over unattended SSH failed even while manager was healthy, so perform interactive `ssh -tt ... sudo xmutil listapps` when authentication is required. Neither should be misreported as an FPGA failure.

## 4. Next milestone gate — M08 physical identity, then full page (NO M09 YET)

The actual deployed M08 bitstream is deliberately **compute disabled**. No reason to move to M09 neurocomputational physical equivalence until:
1. M08.2b.3: validate independent kernel driver `uio_pdrv_genirq` symlink binding for both M08 devices, real `/dev/uio` access preconditions and the actual loaded firmware/thermal/rollback review; perform **only guarded read-only MMIO** of identity magic `0x4D303831`, version `0x00010000`, no DMA, then page magic `0x4D303850`, version `0x00020002`, capability `1`, EMPTY state, twice. Must note read-only Linux MMIO can SIGBUS or hang an unresponsive AXI bus; no RRESP capture under UIO; original real signed hashes and owner explicit authorization before an attempted read. The pre-existing `scripts/m08_path_a_uio_identity_guard.py` only authorizes identity mode with strict approval record; **do not fabricate any `YES` flags unsupported by original evidence, notably `rollback_to_starter_kit_verified`**. Package-only/metadata-only steps can proceed while these fields remain pending.
2. M08.2b.4 after independently confirmed physical identity: design and approve a safe physical userspace transport for exactly 64x32 bit page write/read with data comparison and fail closed before COMMIT. No raw /dev/mem and no DISPATCH in this compute-disabled image. UIO userspace does not expose AXI BRESP/RRESP.
3. On successful first 256B staging, add M08 physical evidence and only then plan integrating compute, signed16 neuron engine, DDR, DMA and matched M09 studies with new bitstreams; these do not follow from metadata tests.

Previous first-reconfiguration runbook: [first managed M08 image replacement owner runbook](M08_2B_FIRST_MANAGED_IMAGE_REPLACEMENT_OWNER_RUNBOOK_2026_11_11.md). This newer document is authoritative for **accepted** board status and the repeatable deployment strategy.

## 5. Safe PC host-only verification commands

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

No installed M08 firmware, sysfs or UIO changes are made by these commands. All 8 M01-M08 CI workflows must pass on the exact latest GitHub commit. **Physical image load is ACCEPTED; identity and data transactions remain OPEN.**
