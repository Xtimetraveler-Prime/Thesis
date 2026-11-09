> **CURRENT M05.12d.2d NATIVE CI VERIFIED:** **M05.12d.2d NATIVE CI VERIFIED at source + D2d engineering commit `abb86685aa030ecbdf1cfa3798b9c96a6bb35af2`:** five GitHub Actions workflows **SUCCESS**, including [M05 host stream run 42550140636](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42550140636). The M05 job discovered **299 named test methods**: 298 initially PASS + one optional Icarus preinstall SKIP, followed by mandatory installed Icarus wrapper compilation and 9/9 D1 test rerun PASS. **All eight new D2d synthetic native methods PASS**, including in separate mandatory D2d stage. M01–M04 **91 PASS** (22+28+21+20), hence **390 distinct native methods PASS at least once**. This is **NOT genuine D2d Vivado PS interface activation**; owner D2d scratch Vivado run remains PENDING. Original owner D2c 57-properties/14-targeted-keys audit PASS is genuinely accepted. The genuine offline local PS instance configuration/pin-readback run is next; no connected interconnect/DDR or physical FPGA.

# M05.12d.2d — Controlled K26 PS IP interface enablement (OFFLINE, NO BOARD)

**Status:** Source / native tests developed; **genuine owner Vivado 2025.2 run PENDING**. Branch `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`, draft PR #79 unmerged, M05 OPEN.

## Accepted original prerequisite and why D2d is next

**Genuine owner D2c PASS:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_20261109T020828Z_0qmobg`, checkout `29fa415c6b495042a2cedeba86aa837da43fd98d`; `exit_status=0`, original offline K26 Vivado 2025.2 PS3.5 Tcl PASS + independent 57-properties/14-candidate audit PASS. This is still an *unconfigured DEFAULT PS IP* study, not physical PS/DDR. First old D2c audit-sort failure `neuromorphic_v1_m05_12d2c_ps_properties_20261109T015151Z_BNn7SH` remains **exit1** and immutable. Previously D2a original Vivado PS default interface catalog PASS showed `M_AXI_HPM0_LPD` as sole default enabled PS-to-PL control master, no DDR-facing HP/HPC default interfaces; `pl_clk0` and `pl_resetn0` pins present.

**Confirmed owner's actual D2c property readbacks:**
- `CONFIG.PSU__USE__M_AXI_GP0=0`, `M_AXI_GP1=0`, `M_AXI_GP2=1`. `PSU__MAXIGP0__DATA_WIDTH=128`; GP2's default interface is `M_AXI_HPM0_LPD`.
- `CONFIG.PSU__USE__S_AXI_GP0...GP6=0`. `PSU__SAXIGP2__DATA_WIDTH=128`.
- `PSU__USE__FABRIC__RST=1`; `PSU__FPGA_PL0_ENABLE=1`; `PSU__USE__IRQ0=0`.
- `PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ=100` (requested), `...ACT_FREQMHZ=96.968727` (IP-reported, NOT measured routed clock).
- K26 PS IP VLNV `xilinx.com:ip:zynq_ultra_ps_e:3.5`. No physical PS preset/DDR initialized.

**Planned local port mapping to experimentally verify rather than merely assume:** `PSU__USE__M_AXI_GP0` → `M_AXI_HPM0_FPD` (PS master/AXI control) and `PSU__USE__S_AXI_GP2` → `S_AXI_HP0_FPD` (PL AXI memory master entering PS/FPD). This mapping fits AMD Zynq UltraScale+ PS PS-PL interface categories, but **only real owner Vivado pin readbacks** will accept this D2d experiment. See [UG1085 interface summary](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Functional-Description) and [PS-PL interface specifics](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/PL-PS-Interface-Specifics).

## What is built

`scripts/m05_12d2d_ps_enablement.tcl`:
1. Creates a **brand-new in-memory** K26 Vivado project with automatic source mode, instantiates exactly one PS IP v3.5 cell. No K26/board preset, DDR config or new connected PS/PL BD.
2. Verifies *default* `PSU__USE__M_AXI_GP0=0`, `PSU__USE__S_AXI_GP2=0` and default interface pins for `M_AXI_HPM0_FPD` absent, `S_AXI_HP0_FPD` absent, `M_AXI_HPM0_LPD` present as MASTER.
3. Uses the **two owner-confirmed live CONFIG property names only**, on the scratch PS cell: `set_property -dict [list CONFIG.PSU__USE__M_AXI_GP0 1 CONFIG.PSU__USE__S_AXI_GP2 1] $ps`. Independently reads both properties back and original LPD master enable GP2=1.
4. **Requires actual BD interface pin objects** `ps_probe/M_AXI_HPM0_FPD` MODE MASTER and `ps_probe/S_AXI_HP0_FPD` MODE SLAVE, plus original `M_AXI_HPM0_LPD` MODE MASTER. A successful CONFIG readback WITHOUT true interface pins **cannot pass**.
5. Requires output `pl_clk0`, output `pl_resetn0`, input `maxihpm0_fpd_aclk`, input `saxihp0_fpd_aclk`; both 128-bit confirmed native PS width properties. Records both PL requested and internal actual MHz readbacks WITHOUT pretending they are actual routed/validated clock frequencies or tested reset sequencing.
6. Saves a small original exact report with `META/DEFAULT/BEFORE/READBACK/AFTER/PIN/WIDTH/CLOCKCFG` records, closes scratch project and prints PASS **only after all those readbacks**. Does NOT call `connect_bd_intf_net`, `assign_bd_address`, `validate_bd_design`, instantiate DMA/SmartConnect/shell/HLS, or access any physical hardware.

`scripts/m05_12d2d_ps_enablement_audit.py`: independently rejects incorrect part/VLNV/source mode/scope, erroneous DEFAULT vs READBACK, absent/wrong-direction actual interface pins, missing clock/reset pins, wrong 128-bit data width and nonpositive/non-finite clock parameter values. A source bit set is NOT accepted as equivalent to an enabled physical interface pin.

`scripts/run_m05_12d2d_ps_enablement.sh`: requires sourced Vivado 2025.2 and no CLI options other than `--help`, unique `~/Thesis_Evidence/neuromorphic_v1_m05_12d2d_ps_enablement_<UTC>_XXXXXX` evidence folder, `commit.txt`, `working_tree_status.txt`, `source_sha256.txt`, original `01_ps_enablement.txt`, `02_vivado.log`, `03_independent_audit.log` and fail-closed `result.txt`. Preserves original failure evidence unchanged.

`tests/test_m05_12d2d_ps_enablement.py`: eight synthetic native tests exercising positive exact report, wrong metadata, wrong default/post-config bits, missing/wrong-mode physical AXI pin records, missing/wrong-direction clock/reset and width, malformed/nonfinite clocks, incomplete/duplicate/extra/truncated evidence, independent CLI read-only audit and no-board runner safety. **Neither these tests nor GitHub Actions execute Vivado.**

## Operator local verification (source Vivado 2025.2 first; no hardware)

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
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q

bash -n scripts/run_m05_12d2d_ps_enablement.sh
bash scripts/run_m05_12d2d_ps_enablement.sh

export PS_ENABLEMENT="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d2d_ps_enablement_* | head -n 1)"
echo "$PS_ENABLEMENT"
cat "$PS_ENABLEMENT/result.txt"
cat "$PS_ENABLEMENT/commit.txt"
cat "$PS_ENABLEMENT/working_tree_status.txt"
cat "$PS_ENABLEMENT/01_ps_enablement.txt" 2>/dev/null || true
tail -n 180 "$PS_ENABLEMENT/02_vivado.log" 2>/dev/null || true
cat "$PS_ENABLEMENT/03_independent_audit.log" 2>/dev/null || true
cat "$PS_ENABLEMENT/source_sha256.txt" 2>/dev/null || true
```

**Acceptance of D2d requires:** fresh original owner `exit_status=0`, exact original real Vivado `PASS: M05.12d.2d offline PS HPM0_FPD and HP0_FPD actual pins enabled (NO PS PRESET/DDR/BOARD)`, independent `PASS: M05.12d.2d independent K26 PS interface configuration trial HPM0_FPD MASTER + HP0_FPD SLAVE both 128bit (NO PRESET/DDR/BOARD)`, actual complete `BEFORE`/post-enabled `AFTER` BD pin and clock/readback rows, commit and hashes. Anything short remains pending; preserve failures and investigate first error (likely IP pin/clock association if mapping differs).

## After accepted D2d: M05.12d.3 connected BD design

Only then attempt genuine scratch design joining PS HPM control master via AXI control interconnect to **six independent control slaves** (DMA×4, custom shell, original signed32 HLS native control). PL DMA AXI-MM 256-bit → verified SmartConnect width conversion → PS HP0_FPD 128-bit DDR slave interface, real associated clocks/reset, address-segment readback/overlap rejection, IRQ, original generated HLS RTL bridge, timing constraints and full BD validation. Each is a separate evidence gate, not part of D2d. The 32-bit DMA DATA address width still limits DMA buffer addresses; cache coherency, OS memory ownership and real buffers/transactions remain a separately authorized hardware phase.

**No real board/JTAG/PS boot/DDR/bitstream used or authorized in D2d; original neural compute remains unchanged.**
