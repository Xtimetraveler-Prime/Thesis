# M05.12d.2c — Passive Zynq UltraScale+ PS CONFIG property discovery (no board)

**Scope: K26 Vivado 2025.2, current Neuromorphic Accelerator v1 M05 branch; PR #79 draft/unmerged.**

## 1. Accepted actual prerequisite and why D2c is needed

Owner original M05.12d.2a genuine K26 Vivado default-PS catalog **PASS**: `~/Thesis_Evidence/neuromorphic_v1_m05_12d2a_ps_inventory_20261109T013033Z_oCd1O9`, checkout `c7dfffb351db3e5779384161a7b45d5968ef95c6`, `exit_status=0`, original Vivado PASS + independent Python audit PASS. PS `xilinx.com:ip:zynq_ultra_ps_e:3.5`, source mode All. Exactly one PS-to-PL master was present by default (`M_AXI_HPM0_LPD`), zero DDR-facing AXI slave interfaces enabled by default, two PL clock/reset outputs (`pl_clk0`, `pl_resetn0`). The previous nine `CONFIG.PCW_*` queried parameter names were all `UNAVAILABLE`. This **does not** mean the ports are absent from silicon: the default/unconfigured PS IP cell has not enabled them.

**Relevant AMD 2025.2 official material** explicitly distinguishes enabling `M_AXI_HPM0_FPD`/`M_AXI_HPM1_FPD` PS→PL controls from enabling `S_AXI_HP*_FPD` and `S_AXI_HPC*_FPD` PL→DDR memory ports: [AMD Vitis Platform Creation 2025.2 — Enable AXI Interfaces](https://docs.amd.com/r/2025.2-English/Vitis-Tutorials-Vitis-Platform-Creation/Enable-AXI-Interfaces-for-the-Platform). The exact local PS IP *parameter names* must be read from the installed Vivado catalog, not guessed from old Zynq-7000 PCW naming.

**Safe next gate:** enumerate the relevant actual `CONFIG.PSU__...` properties from `list_property` and read back their ORIGINAL DEFAULT values. Do not enable anything before understanding this installed version's valid keys and exact clock/reset constraints.

## 2. New implementation and verification boundaries

`scripts/m05_12d2c_ps_properties.tcl`:
- Creates **a separate, in-memory K26 project** and selects automatic source management, detects installed `zynq_ultra_ps_e` IP, creates one default PS cell in scratch BD.
- **Never writes PS configuration properties.** Lists real `CONFIG.PSU__USE__*` values and related PL reference-clock control and AXI-interface configuration keys.
- Records a sorted `PROP|<CONFIG.PSU__ key>|<base64-default>` report; `~` represents an empty default. Base64 preserves raw readback values without newline/field ambiguities.
- Emits `TARGET|<specific key>|0/1` for 14 explicitly tracked candidate names. These include PS AXI master/slave enable candidates `PSU__USE__M_AXI_GP*`, `PSU__USE__S_AXI_GP*`, `PSU__USE__IRQ0`, `PSU__USE__FABRIC__RST`, and `PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ`/fabric clock enable candidates. **A present property does not prove a particular PS AXI interface is enabled:** D2c is a READ-ONLY parameter catalog.
- Rejects empty/oversized discovery instead of silently reporting PASS without a meaningful list. Uses no board preset, no interface connections, no memory mapping, no PCW writes, no I/O.

`scripts/run_m05_12d2c_ps_properties.sh`: requires sourced Vivado 2025.2, no runtime options except `--help`; generates a new `~/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_<UTC>_XXXXXX` folder with `commit.txt`, `working_tree_status.txt`, `source_sha256.txt`, `01_ps_properties.txt`, `02_vivado.log`, `03_independent_audit.log`, and `result.txt`, preserving failure evidence as nonzero exit.

`scripts/m05_12d2c_ps_properties_audit.py`: strict read-only independent parser of actual report shape, exact K26 part/scope/VLNV/source mode, exactly 14 target keys matching property list presence, sorted unique actual properties, canonical base64, count, and no unknown/truncated/oversized rows. Prints plain-English candidate key defaults. Passing audit means **a correct read-only parameter inventory**; it is NOT a connected/validated PS configuration.

`tests/test_m05_12d2c_ps_properties.py`: 8 native host-only regression methods for valid simulated property defaults, missing/duplicate/contradictory target and config rows, wrong part/scope, invalid/unsorted properties, malformed base64 and control characters, CLI read-only failure, and no-board runner Tcl safety. Synthetic fixtures are NOT real IP properties and must not be cited as actual PS defaults.

## 3. User operator local verification (no FPGA needed)

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
python3 -m unittest discover -s tests -p 'test_m05_12d2c*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q

# Source Vivado 2025.2 in your terminal first. Completely offline!
bash -n scripts/run_m05_12d2c_ps_properties.sh
bash scripts/run_m05_12d2c_ps_properties.sh

export PS_PROPERTIES="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_* | head -n 1)"
echo "$PS_PROPERTIES"
cat "$PS_PROPERTIES/result.txt"
cat "$PS_PROPERTIES/commit.txt"
cat "$PS_PROPERTIES/working_tree_status.txt"
cat "$PS_PROPERTIES/01_ps_properties.txt" 2>/dev/null || true
tail -n 160 "$PS_PROPERTIES/02_vivado.log" 2>/dev/null || true
cat "$PS_PROPERTIES/03_independent_audit.log" 2>/dev/null || true
cat "$PS_PROPERTIES/source_sha256.txt" 2>/dev/null || true
```

**D2c acceptance requires all simultaneously:** original `result.txt exit_status=0`, exact real Vivado PASS line `PASS: M05.12d.2c offline K26 PS property names and values discovered (NO WRITE/PRESET/DDR)`, strict independent audit PASS, correct installed K26 PS IP provenance, nonempty actual `CONFIG.PSU__` list, genuine target-presence/default values. Preserve complete original evidence. If failure occurs, inspect first error, fix only justified source logic, create a fresh evidence directory. Do not mark original failed output as passed.

## 4. Next M05.12d.3 after owner property discovery

Only after real D2c evidence should we create **another offline** test that explicitly enables a chosen FPD control master and HP/HPC DDR-facing AXI slave candidate using verified valid `CONFIG.PSU__...` property names, re-reads their actual *interface pins*, and checks PS clock/reset requirements. That becomes a controlled in-memory K26 PS configuration trial; it still does not establish PS DDR boot, physical interface operation, or the final six-bank address map. A subsequent connected BD candidate will need AXI control interconnect, 256→128-bit data-path conversion, mapped address segments, dedicated clock/reset bus association, HLS control and generated signed32 HLS module attachments, and independent DRC/simulation. No physical board work without user approval.

**Keep separate:** DMA data address width is currently 32-bit, DMA 256-bit memory paths require width conversion to max-128-bit PS HP/HPC, and physical buffers need driver-owned DMA mappings, cache/fences, and actual DDR access proof. The M05.12d.2b six-bank host candidate remains arithmetic admission only; do not copy synthetic MMIO addresses to a device.

**Status:** D2a owner default PS catalog accepted; D2b native six-bank admission accepted; D2c new read-only source developed/native tested, **genuine Vivado D2c PENDING**. M05 OPEN, PR #79 DRAFT/UNMERGED.
