> **LATEST CI VERIFIED AND NEXT OWNER GATE:** **M05.12d.2d NATIVE CI VERIFIED at source + D2d engineering commit `abb86685aa030ecbdf1cfa3798b9c96a6bb35af2`:** five GitHub Actions workflows **SUCCESS**, including [M05 host stream run 42550140636](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42550140636). The M05 job discovered **299 named test methods**: 298 initially PASS + one optional Icarus preinstall SKIP, followed by mandatory installed Icarus wrapper compilation and 9/9 D1 test rerun PASS. **All eight new D2d synthetic native methods PASS**, including in separate mandatory D2d stage. M01–M04 **91 PASS** (22+28+21+20), hence **390 distinct native methods PASS at least once**. This is **NOT genuine D2d Vivado PS interface activation**; owner D2d scratch Vivado run remains PENDING. Original owner D2c 57-properties/14-targeted-keys audit PASS is genuinely accepted. After checking out the latest branch, run `bash scripts/run_m05_12d2d_ps_enablement.sh` in sourced Vivado 2025.2, collect original `result.txt`, `commit.txt`, `working_tree_status.txt`, `01_ps_enablement.txt`, `02_vivado.log`, `03_independent_audit.log` and source hashes. If failure, preserve folder and diagnose the first error without weakening required real pin readbacks.

# Current M05.12d.2d handoff — K26 PS FPD control + HP0 memory port offline enablement

**Repository** `Xtimetraveler-Prime/Thesis`; **branch** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`; draft PR #79 OPEN/UNMERGED. M05 OPEN. Applies to `Neuromorphic_Accelerator/v1/`, NOT Loihi digital twin. Preserve existing original signed32 HLS neural engine, generated HLS RTL, original transport shell, earlier evidence. User expects copy-paste local commands and explicit genuine Vivado/host-only boundary. Do not access physical K26 PS/DDR/JTAG/board/bitstream without authorization.

**ACCEPTED previous original owner gates:**
- M05.11c original signed32 HLS generated Verilog + real shell XSim and independent 256-bit frame replay genuine PASS `neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy` (24 status0 committed24, 8 status4 committed0, 148 HLS stalls). 
- M05.12b original K26 AXI DMA v7.1 IP catalog PASS `neuromorphic_v1_m05_12_ip_catalog_20261109T001921Z_4ZocHi`.
- M05.12c genuine four 256bit DMA configured three MM2S-only + one S2MM-only PASS `neuromorphic_v1_m05_12c_dma_candidate_20261109T003049Z_y5AEce` (original read-only-property warnings preserved).
- M05.12d.1 original four 256bit DMA↔shell AXI stream point-to-point nets PASS `neuromorphic_v1_m05_12d1_axis_graph_20261109T011233Z_Qjt8oT`, checkout `c702d1712e153aa283c55f1e35c079738ea1c50e`. Initial manual compile-order failure preserved.
- M05.12d.2a original K26 default PS IP catalogue PASS `neuromorphic_v1_m05_12d2a_ps_inventory_20261109T013033Z_oCd1O9`, checkout `c7dfffb351db3e5779384161a7b45d5968ef95c6`. HPM0_LPD only control master enabled, no HP/HPC PS DDR slave enabled, pl_clk0/resetn0 present.
- **NEW M05.12d.2c ORIGINAL GENUINE PS PROPERTY CATALOG PASS** `~/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_20261109T020828Z_0qmobg`, checkout `29fa415c6b495042a2cedeba86aa837da43fd98d`, `exit_status=0`, independent PASS 57 actual `CONFIG.PSU__` properties, 14 targeted keys present, PS3.5 `source_mgmt_mode=All`. Defaults: `M_AXI_GP0=0`, GP1=0, GP2=1, `S_AXI_GP0..6=0`, IRQ0=0, FABRIC_RST=1, FPGA_PL0_ENABLE=1, request100MHz vs IP ACT_FREQMHZ96.968727 (not measured). Original D2c failed audit-sort first folder `neuromorphic_v1_m05_12d2c_ps_properties_20261109T015151Z_BNn7SH` immutable exit1.

**M05.12d.2b host-only six-bank control aperture admission already accepted native**: four independent AXI DMA control registers, separate shell controller, original Vitis HLS native control all require nonoverlapping 4KiB regions, no real physical addresses or PS driver, unknown generated HLS offsets not guessed.

**M05.12d.2d NEW SOURCE DEVELOPED, OWNER REAL VIVADO PENDING:** `scripts/m05_12d2d_ps_enablement.tcl` + `scripts/run_m05_12d2d_ps_enablement.sh`, independent `scripts/m05_12d2d_ps_enablement_audit.py`, eight native synthetic `tests/test_m05_12d2d_ps_enablement.py`. Fresh in-memory `zynq_ultra_ps_e:3.5` K26 PS cell, confirms owner original disabled defaults `PSU__USE__M_AXI_GP0=0` and `S_AXI_GP2=0`; sets those two enablement properties on SCRATCH IP to1, then demands real `M_AXI_HPM0_FPD` MASTER + `S_AXI_HP0_FPD` SLAVE AXI interface pin readback plus original HPM0_LPD MASTER; required clock/reset pins `pl_clk0`, `pl_resetn0`, `maxihpm0_fpd_aclk`, `saxihp0_fpd_aclk`, 128-bit widths, requested/actual PS clock config. **This does NOT create DDR, PS board preset, connected interconnect, AXI addresses or physical runtime**. Owner genuine Vivado D2d still pending; if it fails, read first log error and preserve original new folder. Strict static tests do not certify Vivado mapping.

**Local operator:**

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
git status --short
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05_12d2d*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
bash -n scripts/run_m05_12d2d_ps_enablement.sh
# source Vivado 2025.2 settings64.sh in this terminal, no FPGA required
bash scripts/run_m05_12d2d_ps_enablement.sh
export PS_ENABLEMENT="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d2d_ps_enablement_* | head -n 1)"
echo "$PS_ENABLEMENT"
cat "$PS_ENABLEMENT/result.txt"
cat "$PS_ENABLEMENT/commit.txt"
cat "$PS_ENABLEMENT/01_ps_enablement.txt" 2>/dev/null || true
tail -n 180 "$PS_ENABLEMENT/02_vivado.log" 2>/dev/null || true
cat "$PS_ENABLEMENT/03_independent_audit.log" 2>/dev/null || true
cat "$PS_ENABLEMENT/source_sha256.txt"
```

**D2d owner acceptance criteria:** original unique `exit_status=0`, genuine Vivado `PASS: M05.12d.2d offline PS HPM0_FPD and HP0_FPD actual pins enabled (NO PS PRESET/DDR/BOARD)`, independent `PASS: M05.12d.2d independent K26 PS interface configuration trial HPM0_FPD MASTER + HP0_FPD SLAVE both 128bit (NO PRESET/DDR/BOARD)`, actual BEFORE/AFTER interface mode and clock/width readbacks, original commit and SHA256. Without owner proof do NOT mark D2d accepted.

**Next after owner D2d:** M05.12d.3 scratch connected PS/PL BD with true six AXI-Lite control banks, SmartConnect 256→128-bit DMA master path into PS HP0_FPD, real address readbacks and all relevant clock/reset bus associations including original D1 warning `IP_Flow 19-11770`, full design validation, simulation. No physical board until explicit authorization; no PR merge. [Engineering report](M05_12D2D_PS_PORT_ENABLEMENT_2026_11_08.md).
