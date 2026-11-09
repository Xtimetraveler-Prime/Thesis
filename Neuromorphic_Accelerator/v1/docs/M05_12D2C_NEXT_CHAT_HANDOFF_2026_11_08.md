> **SUPERSEDED (D2c genuine original owner PASS):** [new current D2d next-chat handoff](M05_12D2D_NEXT_CHAT_HANDOFF_2026_11_08.md). Old original D2c failed report remains immutable; follow-up clean D2c original owner audit PASS. Next gate is **scratch in-memory PS enablement** only, not hardware.

> **2026-11-08 18:51 local / 2026-11-09 01:51 UTC — M05.12d.2c ORIGINAL OWNER VIVADO PROPERTY DISCOVERY SUCCEEDED; INDEPENDENT AUDIT FAILED (NOT YET ACCEPTED):** Original immutable evidence `~/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_20261109T015151Z_BNn7SH`, checkout `b2ad947c952b515acec3c061df2e04d6ddc3aba8`, **`result.txt exit_status=1`**. Genuine Vivado 2025.2 `zynq_ultra_ps_e:3.5` on K26 correctly produced `01_ps_properties.txt` with **57 named properties**, all **14 tracked candidate keys present**, and original Tcl emitted its exact discovery PASS marker. Python auditor erroneously demanded `sorted(values, key=str.lower)` while Tcl actually emitted `lsort` (case-sensitive ASCII). In original report `PSU__USE__STM` precedes `PSU__USE__S_AXI_ACE` — valid under Tcl order, invalid under Python lowercase order. Original independent audit printed `property records not sorted as the original Tcl contract`; **NO other failure identified**. Focused fix uses `sorted(values)` to match Tcl, preserving strict ordering/duplicate/malformed-value checks, and adds actual-owner-key regression with reversed-order negative case. Original evidence remains exit1 and unmodified; **fresh real Vivado runner exit0 plus independent PASS still required**. Actual discovered default values include `PSU__USE__M_AXI_GP2=1`, `M_AXI_GP0=0`, `M_AXI_GP1=0`, `S_AXI_GP0..6=0`, `IRQ0=0`, `FABRIC__RST=1`, `PL0_REF_CTRL__FREQMHZ=100`, `FPGA_PL0_ENABLE=1`; these are an UNCONFIGURED IP catalog only, not PS/DDR enablement or actual PL clock measurement. M05 OPEN; PR #79 DRAFT/unmerged; no hardware.

> **FIRST TASK:** keep original D2c evidence immutable; the targeted sort bug in independent auditor is fixed and has an owner-key native regression. Pull latest branch and rerun `bash scripts/run_m05_12d2c_ps_properties.sh` with sourced Vivado 2025.2. Require NEW original exit0, Tcl PASS, corrected independent Python PASS, verified property values, source hashes. Do not proceed to PS port enablement until audited new PASS. [Incident](M05_12D2C_FIRST_AUDIT_SORT_FAILURE_2026_11_08.md).

> **CURRENT SOURCE-CI STATUS AND OPERATOR NEXT STEP:** **LATEST D2c NATIVE CI VERIFIED (source+docs `9718afc5929437a3601bb08c72762d095426dd81`):** Five GitHub Actions workflows SUCCESS, [M05 run 42546806598](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42546806598). **290 M05 named methods** (289 PASS +1 preinstall Icarus skip; mandatory postinstall Icarus elaboration + 9/9 original D1 tests PASS) plus **91 M01–M04** (22+28+21+20) = **381 distinct native methods PASS at least once**. New D2c synthetic PSU property-catalog regression **8/8 PASS** (also checked in mandatory separate CI stage). Actual original D2a owner Vivado PS default catalog already accepted; D2c **genuine owner Vivado CONFIG.PSU__ discovery NOT YET RUN**. This CI does not run Vivado/PS/DDR and does not attest to enabled FPD/HP/HPC ports. Pull latest same branch, test, run `bash scripts/run_m05_12d2c_ps_properties.sh` in offline Vivado 2025.2; bring back `result.txt`, `commit.txt`, `01_ps_properties.txt`, full `02_vivado.log`, `03_independent_audit.log`, `source_sha256.txt`. Preserve original D2a accepted log; D2c still pending.

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
