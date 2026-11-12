# M08.2b — corrected native DTC acceptance and injectable PS/page protocol
**Owner evidence reviewed 2026-11-11 America/Denver (uploads dated 2026-11-12 UTC).**
Branch `agent/neuromorphic-accelerator-v1-m08-kv260-bringup`; PR #83 **DRAFT, UNMERGED**. Continue the ONE M08.2b milestone, not a new milestone. This document supersedes the earlier "native correction pending" instruction, but preserves every original owner evidence folder.

## Independently reviewed owner-uploaded archives
Uploaded `m08_2b_corrected_dtc_review.tar.gz` contains four original files:
- `01_dtc_compile.log`: **zero bytes**, SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Native compiler emitted **no diagnostics**; prior `reg_format` and `avoid_default_addr_size` warnings eliminated.
- `02_dtbo_decompiled.log`: SHA256 `1d514318c38be83541aecc48e95c3d309e841c431b7cdbb013d876f58e281b6c`. Both fpga_full and amba fragments declare **#address-cells=2 / #size-cells=2**. Exact two `generic-uio` resources, `m08-identity` at `<0 0xa0000000 0 0x1000>` and `m08-page` at `<0 0xa0001000 0 0x1000>`; `__fixups__` for `fpga_full`, `zynqmp_reset`, `amba`. Exactly one decompile-only `resets_property` unresolved symbolic phandle warning, allowed for unapplied DTBO.
- `03_review.json`: SHA256 `3b9b69c9f07014916ff60eb195e86c856c1d91c575ebafea56ffab3c0a1ec51f`. Status `OFFLINE_DUAL_UIO_CANDIDATE_NOT_INSTALLED`, zero compiler warnings, one allowed decode warning. Records DTBO SHA256 **`2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed`**, and bit.bin SHA256 **`a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b`**.
- `99_evidence_sha256.txt`: independently hashed SHA256 `603c50a40ab9acbd8102c650cc5aef07ae1e44f08ef170090caf1ad25f06173a`. All THREE included ledger-covered artifacts match their SHA256 rows. The ledger lists additional original input/bit.bin/DTBO/shell/source/status files **NOT included in the upload**. Do not claim their binary bytes independently rehashed or the full owner's local receipt rerun.

Uploaded `m08_2b_uio_sysfs_review.tar.gz` contains:
- `01_sysfs_stdout.json` SHA256 `82cf7cc0306320ba396575112a5ad035839ec52c649b39153abce9c894d8855e`: status `UIO_SYSFS_METADATA_INSPECTED_NO_MMIO`, expected `absent`, `m08_bindings={}`. Four existing `axi-pmon` devices uio0–uio3 and their read-only map metadata, none assigned to M08.
- `02_sysfs_stderr.log` is empty SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- `03_exit_status.txt` contains `exit_status=0` SHA256 `ed163d69a09ddc0ffcbdf126a42d5745a93449fa7a39354788e948b7ac795c04`.
- `99_evidence_sha256.txt` SHA256 `72b8fd43f2797865156dc88d5c09164986fa1052ad12e4975f4605b09673bb46`; 3/3 covered originals independently match.

**Acceptance**: new corrected native DTC generation and predeployment UIO sysfs metadata discovery PASS within **offline / read-only scope only**. These uploads are original operator artifacts but are **not** evidence of active FPGA programming, installed PL_FLAT/Linux app support, live M08 binding, mapped PS AXI, fan continuity during reconfiguration, 64-word memory readback, DDR, DMA, energy or inference. Historical warning-bearing candidate `m08_2b_path_a_uio_overlay_REVIEW_ONLY_tuzu33oo` and first-stage package `m08_2b_path_a_linux_package_REVIEW_ONLY_bco0j53i` remain immutable.

## New software-only page transaction contract
`src/neuromorphic_accelerator_v1/m08_uio_page_protocol.py` accepts independently supplied `read32`/`write32` transports and **contains no Linux MMIO backend or CLI physical mode**. It uses the existing first-party identity client:
1. Verify read-only identity twice (magic `0x4D303831`, version `0x00010000`, no DMA). Existing RTL defaults BUILD_ID words to zero: **record as unprovisioned**, never treat it as bitstream authentication. Read page header twice: `0x4D303850`, `0x00020002`, capability 1; only start from strictly EMPTY status and zero loaded bytes.
2. Require explicit caller transport-write gate; validate exactly 64 uint32 words and logical ID before issuing a write. Set SELECTED `0x010`, read it back, BEGIN command 1 at `0x014`, require LOADING.
3. Write 64 words in ascending order, full 32-bit writes to `0x100..0x1fc`. Require loaded bytes 256 at `0x01c`. Read **all 64 freshly returned words**, independently compare each; **withhold COMMIT on any mismatch**.
4. Only after comparison, COMMIT command 2; require READY/valid, matching resident ID at `0x018` and still 256 bytes. Return SHA256 over 256 **little-endian** readback bytes, explicit `physical_ps_axi_verified=false`, `axi_bresp_or_rresp_observed=false` and `neural_inference_verified=false`. Never attempt DISPATCH.
5. Fail closed on malformed/unstable headers, poison/busy/fault/status, short data, wrong word, missing load count or injected read/write errors. The protocol cannot itself ensure a physical bus timeout or recover a kernel-aborted MMIO load; that belongs to a reviewed transport/driver layer.

`tests/test_m08_uio_page_protocol.py` exercises synthetic positive and negative transports, no real /dev/uio or FPGA. The existing `scripts/m08_path_a_uio_sysfs_readonly.py` remains metadata-only and checks exact UIO names, map0 bases and 4KiB lengths when M08 is eventually present. Neither a sysfs match nor a memory-map read is an AXI protocol response trace: **UIO mmap cannot expose BRESP/RRESP SLVERR**. Negative DISPATCH error-conformance requires a separately instrumented or appropriate kernel/bus initiator; a Linux bus fault must not be provoked merely to test SLVERR.

## Safe physical transition and rollback gate (NOT authorized)
1. Preserve a known-good serial/SSH access path, hashes of current `k26-starter-kits` installed artifacts, and documented working `xmutil listapps`/dfx-mgr/fancontrol state. Verify the future Linux manager's **PL_FLAT** acceptance independently of current **XRT_FLAT** starter-kit format. Map resources under kernel driver ownership and record current `/proc/iomem`, loaded overlay, bound platform driver and sysfs names (without accesses to other drivers).
2. Establish **independently powered/controlled fan or a separately verified cooling method spanning the complete PL reconfiguration gap**. A12 routed in the M08 bitstream does NOT preserve cooling during reconfiguration. Record temperature before/during/after, expected fan fallback, allowed duration and operator-controlled **rollback** to the exact existing starter-kit image. **Do not** disable fancontrol or use JTAG to swap the active Linux-managed PL.
3. Obtain **explicit owner authorization** for each actual reconfiguration after the plan is independently checked. On any mismatch, failure, overtemperature, failed load or lost management ownership, stop and execute the approved rollback, not an automatic retry. No Linux firmware install/FPGA unload/load/reboot/flash/JTAG change is authorized by this documentation.
4. Only after safe physical deployment and genuine UIO binding: first read exact identity/page headers via a separately reviewed guarded transport; archive original raw values and SHA. Then after another authorization perform full 64-word roundtrip under kernel ownership. Never conflate write32() success with AXI BRESP.
5. M08.2b hardware proof is strictly identity + 256B staging (compute disabled); full M05 event engine, M06 signed16 physical DDR/cache/queue service, and matched M09 hardware comparisons remain later work.

## PC verification commands (local source only)
```bash
cd /home/dna/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_uio_page_protocol.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```
Run on the Linux PC only; do not install the candidate Linux overlay. Require all eight M01–M08 GitHub Actions workflows green on the **exact final HEAD** and owner local results before physical integration continues.
