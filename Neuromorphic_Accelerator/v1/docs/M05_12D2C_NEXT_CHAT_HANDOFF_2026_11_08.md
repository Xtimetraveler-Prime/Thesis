# M05.12d.2c — CURRENT NEXT CHAT HANDOFF (2026-11-08 local / 2026-11-09 UTC)

**Repo** `Xtimetraveler-Prime/Thesis`; **branch** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`; **draft PR #79, OPEN/UNMERGED**; M05 OPEN. This is `Neuromorphic_Accelerator/v1/`, not the separate Loihi digital twin. Always include local pull/test commands; preserve original owner evidence; only host-native and explicitly approved OFFLINE Vivado without hardware/PS/DDR. Never touch original signed32 HLS kernel or original generated RTL. No board permissions.

**M05.11c accepted owner Vivado real generated HLS RTL+shell XSim and 256-bit frame replay** `neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy` (24 successful trace rows/committed24 and late fault status4 committed0). **M05.12b accepted original K26 AXI DMA 7.1 catalog** `neuromorphic_v1_m05_12_ip_catalog_20261109T001921Z_4ZocHi`. **M05.12c accepted genuine 3 MM2S/1 S2MM DMA v7.1 x4 IP config** `neuromorphic_v1_m05_12c_dma_candidate_20261109T003049Z_y5AEce` (256-bit AXIS/AXI-MM, length24, SG0). **M05.12d.1 accepted genuine four connected AXIS nets** `neuromorphic_v1_m05_12d1_axis_graph_20261109T011233Z_Qjt8oT`, commit `c702d1712e153aa283c55f1e35c079738ea1c50e`, exit0, strict independent graph audit PASS. Clock FREQ_HZ missing warning from partial original D1 still unresolved; no PS/HLS/DDR or bus maps in D1.

**LATEST M05.12d.2a original owner Vivado PS CATALOG ACCEPTED:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d2a_ps_inventory_20261109T013033Z_oCd1O9`, checkout `c7dfffb351db3e5779384161a7b45d5968ef95c6`, `exit_status=0`, original `PASS: M05.12d.2a original offline K26 PS IP inventory (CATALOG ONLY, NO PRESET/DDR)` and strict independent `ps_to_pl_master_defaults=1, pl_to_ps_slave_defaults=0, pin_defaults=2` PASS. Exact default enabled PS-to-PL master: `M_AXI_HPM0_LPD`; **none** of 9 examined PS DDR-facing AXI slave port pins enabled by default. `pl_clk0`, `pl_resetn0` outputs present; IRQ and FPD clock pins absent. PS IP v3.5; all nine guessed `CONFIG.PCW_*` property keys unavailable; do not use them to set actual FPD/HP/HPC PS ports. Default absent != hardware unsupported. Previous genuine evidence folder immutable.

**M05.12d.2b host-only control admission COMPLETE native:** `src/neuromorphic_accelerator_v1/m05_12d2_control_map.py`: explicit six disjoint 4KiB-aligned control slave candidates (DMA3 MM2S + DMA trace S2MM + shell + original HLS). No default physical addresses, no driver, no actual MMIO/DDR, no generated HLS control-offset guesses. Do not confuse PS control map with DMA 32-bit DATA address width.

**M05.12d.2c NEW DEVELOPED, ORIGINAL VIVADO PENDING:** `scripts/m05_12d2c_ps_properties.tcl` (another offline in-memory K26 default PS IP) passively lists actual `CONFIG.PSU__USE__` and clock/AXI relevant keys and default readback, base64-encoded and sorted, with 14 explicit candidate presence checks; `scripts/run_m05_12d2c_ps_properties.sh` original evidence runner, independent `scripts/m05_12d2c_ps_properties_audit.py`, 8 native strict synthetic tests `tests/test_m05_12d2c_ps_properties.py`. **DO NOT claim real property names are present until genuine owner run**. No IP CONFIG writes, preset, PS DDR, board, or connected BD. [D2c runbook](M05_12D2C_PS_PROPERTY_DISCOVERY_2026_11_08.md).

**Next genuine operator offline command:** with clean checkout and sourced Vivado 2025.2:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05_12d2c*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
bash -n scripts/run_m05_12d2c_ps_properties.sh
bash scripts/run_m05_12d2c_ps_properties.sh
export PS_PROPERTIES="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_* | head -n 1)"
echo "$PS_PROPERTIES"
cat "$PS_PROPERTIES/result.txt"
cat "$PS_PROPERTIES/commit.txt"
cat "$PS_PROPERTIES/01_ps_properties.txt" 2>/dev/null || true
tail -n 160 "$PS_PROPERTIES/02_vivado.log" 2>/dev/null || true
cat "$PS_PROPERTIES/03_independent_audit.log" 2>/dev/null || true
cat "$PS_PROPERTIES/source_sha256.txt"
```

**D2c acceptance**: fresh genuine original exit0, original Tcl PASS, nonempty actual PSU property keys/default values, independent audit PASS with all 14 candidate checks consistent, provenance. Then and ONLY then, develop **D2d** offline controlled K26 PS config experiment: enable an FPD master and at least HP0 DDR-facing slave via verified local property keys, reread IF pins/modes/clock/reset, with no DDR/board; choose future SmartConnect width conversion/clock system in D3. No physical hardware without approval; M05 open, PR #79 draft/unmerged.
