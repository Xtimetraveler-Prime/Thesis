# M08 D2: locate SHA-pinned original PC DTBOs; review PS PL0/HPM0 clock ownership

**2026-11-12 — PC-only, source/evidence investigation.** The user ran
`python3 scripts/m08_d2_offline_ps_pl_contract_audit.py`. Output was
`PS_PL_RUNTIME_CONFIGURATION_AND_TIMEOUT_PROTECTION_UNPROVEN` and both optional
comparators reported `NOT_SUPPLIED`. The original Vivado BD source has
`M_AXI_HPM0_FPD` configured for 128 bits, requests `PSU__FPGA_PL0_ENABLE=1`
at ~100MHz and clocks SmartConnect/AXI peripherals from `ps/pl_clk0`. The
original dual-UIO M08 Linux overlay source has no `assigned-clocks`,
`assigned-clock-rates`, `clocks`, `clock-names`, `xlnx,afi-fpga` or
`config-afi`. **Absence does not prove a stopped clock or wrong AFI**:
stock base DT, FSBL/PMU firmware, bootloader or Linux framework could own them.
Neither the user audit nor original route timing measures the failed boot.

## ORIGINAL DTBO identities independently pinned in repository

`scripts/m08_kv260_physical_uio_operator.py` recorded:

| Image | EXACT basename | Expected original SHA256 |
| --- | --- | --- |
| stock K26 | `k26_starter_kits.dtbo` | `1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1` |
| deployed M08 dual-UIO | `m08-v1-fan-page-uio-review.dtbo` | `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed` |

On the *board during the original hardware phase*, the physical operator expected:
`/lib/firmware/xilinx/k26-starter-kits/k26_starter_kits.dtbo` and
`/lib/firmware/xilinx/m08-v1-fan-page-uio-review/m08-v1-fan-page-uio-review.dtbo`.
Those were **board-side original expectations, not proven PC file paths**. A
PC staging copy of the M08 DTBO may be in prior
`~/Thesis_Evidence/M08/m08_2b_path_a_uio_overlay_REVIEW_ONLY_*`,
but no local directory presence may be inferred from the repository.

Be careful to distinguish the earlier M08 *pre-UIO* DTBO
SHA `2a3608d5c7f84f1c62e4324ca3b5538692b449a6b2b8a1a5a4a0399a5dd6fd4e`,
which is **NOT** the image installed for the failed first physical UIO access.
The source-only `DTS` literal in `scripts/m08_path_a_stage_uio_overlay.py`
defines the UIO candidate; it is NOT an as-applied resolved Linux tree. Even a
SHA-matched DTBO is **only an original overlay**; the parent boot DTB and
runtime overlays may supply clocks or AFI. The original failed Linux
runtime state of PS PL0, HPM0 and ATB instance 4 is **UNKNOWN**.

## New safe discovery workflow

`scripts/m08_d2_locate_and_decompile_owner_dtbos.py` searches only existing
user-PC directories (by default `~/Thesis_Evidence/M08` and
`~/Git/Thesis`) for the two exact basenames. It ignores symlink paths,
never follows symlink directories, ignores `.git`/virtualenv/large vendor
directories and requires **actual original content SHA** before labeling a
match verified. It prints JSON but writes no files in lookup-only mode. If one
or both are missing, it prints `all_originals_located: false`. A stale or
mutated file is explicitly reported as **NOT** the accepted original.

With explicit `--prepare`, requires a unique SHA-matched stock and M08 copy,
local `dtc`, and an existing user-owned evidence parent. It writes only to a
NEW exclusive `m08_d2_OWNER_DTBO_OFFLINE_*` directory. It calls `dtc`
**only on the PC and saved DTBO files**, not installed files or board devices.
It emits `11_stock.dts`, `12_m08.dts`, two original compiler stderr files,
`00_review.json`, `99_evidence_sha256.txt`. It hashes originals again
after decompilation. Warnings remain intact; unresolved overlay fixups do not
prove Linux deployment failure. If a native decompile fails, the new evidence
remains for review, and nothing is accepted. No bitstream, JTAG, MMIO,
FPGA Manager, PS register, shell/fan, SSH or D3 release step is invoked.

### Owner PC commands

```bash
cd /home/dna/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-kv260-bringup
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
cd Neuromorphic_Accelerator/v1

python3 -m unittest discover -s tests -p 'test_m08_d2_locate_offline_dtbos.py' -v
python3 scripts/m08_d2_locate_and_decompile_owner_dtbos.py

# If BOTH originals are found with true SHA and dtc is installed:
command -v dtc || echo 'Install with sudo apt install device-tree-compiler on PC'
python3 scripts/m08_d2_locate_and_decompile_owner_dtbos.py --prepare
# Use exactly the printed NEW evidence directory:
OUT="/actual/new/m08_d2_OWNER_DTBO_OFFLINE_folder"
cd "$OUT"
sha256sum -c 99_evidence_sha256.txt

# Compare generated DT sources, using a static text audit only:
cd /home/dna/Git/Thesis/Neuromorphic_Accelerator/v1
python3 scripts/m08_d2_offline_ps_pl_contract_audit.py \
  --stock-dts "$OUT/11_stock.dts" \
  --deployed-m08-dts "$OUT/12_m08.dts"
```

If stock is absent from the two defaults, expand the PC-only search using
`--search-root "$HOME"` (may take longer), or check specific directories such
as an old PC stock package. Do NOT ask to access the K26's
`/lib/firmware/xilinx` to resolve the first search. If only the original M08
DTBO is on the PC, we can still verify its SHA and audit the declared source,
but cannot present a stock-vs-M08 **binary** comparison.

## Engineering interpretation, NOT proof of root cause

- Generic Linux `uio_pdrv_genirq` does use runtime PM (`pm_runtime_enable`,
  `pm_runtime_get_sync` on open). That **does not guarantee** that the
  upstream clock resource for `M_AXI_HPM0_FPD` and every PS PL0 fabric
  consumer is associated with each dynamically created UIO platform device.
  Each M08 UIO node lacks even a `clocks` property in its own overlay.
  Linux PM and the stock board could still manage PL0 elsewhere. Do not
  equate `UIO node bound` with `PL0 running`.
- **Concrete 2025.2 AMD generator behavior:** the public
  `Xilinx/system-device-tree-xlnx` `xlnx_rel_v2025.2`
  `device_tree/data/device_tree.tcl`, `gen_afi_node` implementation, generates
  `xlnx,fclk` and `assigned-clocks`/`assigned-clock-rates` when
  `CONFIG.C_PL_CLK0_BUF` is enabled, with the ZynqMP clock identifier
  computed as **71 + clock index**; it generates `xlnx,afi-fpga` /
  `config-afi` from PS AXI widths, including
  `CONFIG.C_MAXIGP0_DATA_WIDTH` and `CONFIG.C_MAXIGP1_DATA_WIDTH`
  combined into an AFI value at **index 14**. This makes the originally
  manually authored M08 overlay's missing clock/AFI fragment a
  *specific, plausible* runtime-configuration omission to compare against
  stock/HSI-generated source — NOT a proven mismatch in the failed boot.
  See:
  https://github.com/Xilinx/system-device-tree-xlnx/blob/xlnx_rel_v2025.2/device_tree/data/device_tree.tcl
  (`gen_afi_node`). **Do not copy those AFI values into M08 blindly.**
- AMD's ZynqMP Linux FPGA Manager example shows `xlnx,fclk` with
  `assigned-clocks/assigned-clock-rates` and an `xlnx,afi-fpga` fragment
  during PS→PL reconfiguration. That is an **example**, not evidence
  that these MUST be supplied by the M08 overlay. The original
  stock firmware boot DT/overlay and OS component ownership must be
  compared before modifying any device tree.
- ATB instance 4 is upstream of `M_AXI_HPM0_FPD` in the FPD PS clock domain,
  a promising independent failure boundary; we do not know if it was enabled
  during the incident or whether a failing read could have received a
  bounded error. A PL-clocked watchdog cannot guarantee a response if PL0
  stops.
- The original Linux SSH/RCU stall was temporally associated with a first
  identity read but **no faulting address, AXI waveform or PS register values
  survived**. Runtime clock failure remains a leading working hypothesis
  and not a diagnosis.
- Next D2 action after offline DTBO review: determine firmware-owned clock,
  AFI and HPM0 reset responsibilities, and write independently clocked bounded
  failure/isolation tests before proposing a fresh D3 image. No original
  bit.bin reload or old board MMIO is permitted.

References: AMD ZynqMP FPGA Manager example
https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18841847 ;
Linux generic UIO driver
https://github.com/torvalds/linux/blob/master/drivers/uio/uio_pdrv_genirq.c ;
AMD UG1085 PS AXI Timeout Block instances
https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances .
