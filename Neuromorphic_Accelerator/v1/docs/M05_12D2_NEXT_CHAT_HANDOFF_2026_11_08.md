> **SUPERSEDED: D2a owner genuine PASS; NEW D2c handoff** [M05.12d.2c current operator handoff](M05_12D2C_NEXT_CHAT_HANDOFF_2026_11_08.md). Historical D2a-pending commands retained below for audit only, do not rerun D2a as next milestone.

> **CURRENT CI VERIFIED:** **NATIVE VERIFICATION VERIFIED at implementation+doc commit `338b1406da363a2ae33f14868143a750aa68debf`:** all five GitHub Actions workflows **SUCCESS**, including [M05 workflow 42545536913](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42545536913). **282 named M05 methods** were discovered (281 PASS + one early pre-install Icarus SKIP, later mandatory `iverilog` and 9/9 original D1 module-ref tests PASS); **91 M01–M04 methods PASS** (22+28+21+20). Thus all **373 distinct native methods PASS at least once**, including 14/14 brand-new D2a/D2b tests and exact source fingerprints. Native CI uses synthetic PS catalogs; **NO genuine M05.12d.2a Vivado PS IP run has been provided**, so the PS inventory gate remains PENDING. D2b pure-host admission is native verified only. Original genuine D1 partial four-AXIS net PASS remains accepted. Next user proof: source Vivado 2025.2; run new `bash scripts/run_m05_12d2a_ps_inventory.sh`, return original `result.txt`, `commit.txt`, `01_ps_inventory.txt`, `02_vivado.log`, `03_independent_audit.log`, `source_sha256.txt`. D2a catalog is OFFLINE/NO BOARD/NO PRESET and cannot establish DDR interface configuration yet.

# CURRENT NEUROMORPHIC ACCELERATOR v1 M05.12d.2 HANDOFF — 2026-11-08 local / 2026-11-09 UTC

**GitHub:** `Xtimetraveler-Prime/Thesis`; exact active branch `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`, draft PR #79 OPEN/UNMERGED; M05 OPEN. This is the *Neuromorphic Accelerator v1*, NOT the separate Loihi Digital Twin. Do not touch original `hls/m05_rolling/m05_rolling.cpp`, real generated signed32 HLS Verilog, or accepted original tests. Do not access JTAG/XSDB, physical FPGA, PS DDR or bootloader without user consent. Keep all original evidence immutable and add new unique evidence dirs only.

**Earlier accepted evidence:** M05.11c original generated signed32 HLS + M05.11 transport shell genuine Vivado XSim and independent raw 256bit frame replay PASS (24 status0/committed24, 8 status4/committed0) `neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy`. M05.12b K26 AXI DMA 7.1 catalog owner PASS `neuromorphic_v1_m05_12_ip_catalog_20261109T001921Z_4ZocHi`. M05.12c owner four 256b simple AXI DMA configuration/independent audit PASS `neuromorphic_v1_m05_12c_dma_candidate_20261109T003049Z_y5AEce`, preserved four original read-only property Vivado warnings; Tcl now only READS `c_prmry_is_aclk_async=0`.

**NEWLY ACCEPTED GENUINE M05.12d.1 D1:** operator original `~/Thesis_Evidence/neuromorphic_v1_m05_12d1_axis_graph_20261109T011233Z_Qjt8oT`, source `c702d1712e153aa283c55f1e35c079738ea1c50e`, `exit_status=0`, actual `M05_12D1_SOURCE_MGMT_MODE=All`, four 256bit AXIS point-to-point connected DMA-to-shell interfaces and independent audit `connections=4` PASS. Earlier genuine failed first attempt `neuromorphic_v1_m05_12d1_axis_graph_20261109T005602Z_nTb0oa` remains exit1 preserved. Partial PL graph ONLY: clocks, AXI-Lite, PS, DDR, HLS control/RTL attachment and system validation absent. Actual source `clk` FREQ_HZ missing `IP_Flow 19-11770` and auto-associated just neurons; must fix when clock/reset topology chosen.

**M05.12d.2a NEW IMPLEMENTATION, GENUINE VIVADO PENDING:** Source `scripts/m05_12d2a_ps_inventory.tcl`, operator wrapper `scripts/run_m05_12d2a_ps_inventory.sh`, independent parser `scripts/m05_12d2a_ps_inventory_audit.py`, seven synthetic native methods `tests/test_m05_12d2a_ps_inventory.py`. Offline in-memory K26 PS `zynq_ultra_ps_e` instance with NO board preset and no IP config writes; read actual *default* HPM controls, HP/HPC DDR port presence, clock/reset/IRQ pins and available PCW names. Absent defaults ≠ absent hardware capability. Strict manifest, fresh evidence on owner workstation; no physical FPGA/DDR. Do not call this connected PS architecture or D2a accepted before operator genuine Vivado PASS. Use [full runbook](M05_12D2_PS_INVENTORY_AND_CONTROL_APERTURES_2026_11_08.md).

**M05.12d.2b NEW HOST-ONLY PROPOSAL:** `src/neuromorphic_accelerator_v1/m05_12d2_control_map.py`, seven native synthetic tests `tests/test_m05_12d2_control_map.py`. Immutable explicit SIX AXI4-Lite control aperture model (MM2S DMA×3, trace S2MM DMA, shell session MMIO, native HLS AXI-Lite), 4KiB alignment, range/nonoverlap and correct independent offset checks. **No DEFAULT physical addresses**, no `assign_bd_address`, no Linux MMIO or DDR/cache driver, no guessed HLS generated offsets. PS physical 40-bit bound is only arithmetic, not actual address entitlement. Each 256bit DMA AXI-MM memory master needs a reviewed width-converting interconnect to ≤128bit PS HP/HPC DDR slave ports and separate 32bit data addressing limit. Noncoherent HP is a possible initial candidate, not proven selected.

**Next operator commands (Vivado 2025.2 sourced):**

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05_12d2*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
bash -n scripts/run_m05_12d2a_ps_inventory.sh
bash scripts/run_m05_12d2a_ps_inventory.sh
export PS_INVENTORY="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d2a_ps_inventory_* | head -n 1)"
cat "$PS_INVENTORY/result.txt"
cat "$PS_INVENTORY/commit.txt"
cat "$PS_INVENTORY/01_ps_inventory.txt" 2>/dev/null || true
tail -n 160 "$PS_INVENTORY/02_vivado.log" 2>/dev/null || true
cat "$PS_INVENTORY/03_independent_audit.log" 2>/dev/null || true
cat "$PS_INVENTORY/source_sha256.txt"
```

**D2a PASS** requires original fresh `exit_status=0`, PS IP original Vivado PASS, independent PS catalog audit PASS, source commit/hashes and full raw report. Real PS connectivity, clock frequency, Linux DMA address map, routing and physical hardware need distinct future gates. On failure, original logs, no weakened tests. Once real PS capability output is available, move to **M05.12d.3** properly *connected* PS-to-PL control and PL-to-PS DDR interconnect with clocks, reset, width conversion and real address readback; full BD validation separate. Do not merge PR until explicit user authorization.
