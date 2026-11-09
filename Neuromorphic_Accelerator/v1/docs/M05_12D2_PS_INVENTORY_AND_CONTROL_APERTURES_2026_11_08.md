# M05.12d.2 — K26 PS interface discovery and six-bank AXI-Lite control admission

**2026-11-08 local / 2026-11-09 UTC · Active M05 branch · PR #79 draft/unmerged · NO BOARD / NO PS DDR**

## 1. Proven prerequisite — M05.12d.1 genuine partial connected AXI4-Stream graph PASS

The operator provided original output from Vivado 2025.2 against `c702d1712e153aa283c55f1e35c079738ea1c50e`: original `~/Thesis_Evidence/neuromorphic_v1_m05_12d1_axis_graph_20261109T011233Z_Qjt8oT`, **`exit_status=0`**. `M05_12D1_SOURCE_MGMT_MODE=All`, AXI DMA 7.1 x4 at 256-bit, three real independent `MM2S→shell` interfaces (neurons, synapses, external) and one real `shell→S2MM` trace interface, exactly four point-to-point BD interface nets. The user's complete original `01_axis_links.txt`, `02_vivado.log` and `03_independent_audit.log` show strict independent **PASS: connections=4**. Preserve this source-revision evidence folder verbatim. Earlier manual compile-order failure evidence `neuromorphic_v1_m05_12d1_axis_graph_20261109T005602Z_nTb0oa` remains `exit_status=1` and is preserved.

**Remaining original D1 warning:** `WARNING: [IP_Flow 19-11770] Clock interface 'clk' has no FREQ_HZ parameter`; auto inferred `ASSOCIATED_BUSIF=S_AXIS_NEURONS` only, while the wrapper actually has four AXIS streams, HLS side streams and `s_axi` AXI4-Lite. The actual final clock frequency, full clock-domain bus associations, reset polarity/CDC/constraints still have to be explicitly verified in a genuine connected PS design. D1 did NOT perform BD validation, AXI-MM memory, PS/DDR or HLS attachment.

**Previous original gates unchanged:** M05.11c owner genuine generated signed32 HLS RTL + transport shell XSim and frame replay PASS in `neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy` (24/status0 committed24, 8/status4 committed0, 148 stalls); M05.12b K26 DMA IP catalog genuine PASS; M05.12c owner genuine four 256-bit direct DMA instance configurations + independent audit PASS. The old 4 read-only-property BD 41-737 warnings from first c owner run were diagnosed and corrected without erasing original evidence.

## 2. Next architecture is TWO DIFFERENT PS/PL AXI paths, not one big DMA stream

**Control plane (PS→PL):** a Zynq UltraScale+ `M_AXI_HPM0_FPD` or another reviewed PS master should access a PL AXI4-Lite interconnect/SmartConnect, then SIX separate, nonoverlapping AXI4-Lite register banks:
1. `dma_neurons` MM2S AXI DMA direct-register interface
2. `dma_synapses` MM2S AXI DMA direct-register interface
3. `dma_external` MM2S AXI DMA direct-register interface
4. `dma_trace` S2MM AXI DMA direct-register interface
5. `shell` custom M05.11b AXI-Lite session controller (VERSION register offset `0x38`)
6. `hls` original generated Vitis signed32 HLS control bank (separate from `shell`; must verify its original regmap before any access)

**Data plane (PL→PS DDR):** four **256-bit AXI memory-master ports** on the DMA IPs require a suitable AXI SmartConnect/interconnect and memory-port path to a PS `S_AXI_HP*_FPD` or `S_AXI_HPC*_FPD` target. The **PS HP/HPC AXI interfaces are max 128-bit**, so this requires deliberate WIDTH conversion and checking throughput/backpressure/clocking; a direct 256-bit width match is impossible. An initial **noncoherent HP** candidate is conservative for software cache ownership, but which actual port is enabled and accessible must be checked from the owner's K26 Vivado PS IP/preset, and whether a coherent HPC path is truly supported/selected must not be inferred from a pin's name. Full Linux buffer ownership/cache clean/invalidate, DMA physical address accessibility and completion fences remain to be implemented.

**32-bit DMA addressing is a separate limit:** genuine M05.12c/D1 DMA `c_addr_width=32` only covers physical DMA buffers whose full *DMA transaction* falls below `0x1_0000_0000`; it is not proof Linux can provide suitable 32-byte aligned, contiguous/dma-mapped low-memory buffers. The proposed PS **control** address contract uses the PS maximum physical-address width (**40-bit upper bound**) only as a mathematical limit; it is NOT a real legal address-map entitlement. Never mistake PS MMIO address bounds for the narrower DMA DATA address width.

**Run-sequence constraints remain:** real S2MM receive arm first, source MM2S per nonempty channel, HLS ap_done/ap_return separately read before shell FINISH, TLAST+footer+quiescence and full cache/write fence before atomic acceptance/ACK. Missing source stream must be skipped, not submitted as zero-length DMA. A PS driver does not exist yet.

AMD primary references: [UG1085 PS-PL Interface Summary](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Functional-Description); [PG201 Slave Interface](https://docs.amd.com/r/en-US/pg201-zynq-ultrascale-plus-processing-system/Slave-Interface); [UG1085 PL Accelerator and FPD](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/PL-Accelerator-Block-and-FPD-Interaction); [PG021 AXI DMA](https://docs.amd.com/r/en-US/pg021_axi_dma/Direct-Register-Mode-Simple-DMA).

## 3. What D2a actually builds (Vivado owner gate PENDING)

- `scripts/m05_12d2a_ps_inventory.tcl`: creates ONLY a new scratch **`create_project -in_memory -part xck26-sfvc784-2LV-c`**, sets source-management `All`, locates installed `xilinx.com:ip:zynq_ultra_ps_e:*`, adds a **single DEFAULT/unconfigured** PS IP cell, and **READS**, without writing PCW setup, the presence/direction of the three possible HPM control AXI ports, PS DDR slave HP/HPC/LPD/ACP/ACE interfaces, available PS `pl_clk0`/`pl_resetn0`/`pl_ps_irq0` clock/reset/interrupt signals and input AXI clocks, and a small inventory of PCW configuration/property *availability*. Missing-by-default ports are recorded as `IF|...|0|NA`, **NOT proof of absence from silicon or unavailable when enabled**. No PS preset/board automation applied, so this run will NOT tell us K26 boot/DDR power-up configuration.
- `scripts/run_m05_12d2a_ps_inventory.sh`: requires sourced Vivado 2025.2, no args other than `--help`, unique `~/Thesis_Evidence/neuromorphic_v1_m05_12d2a_ps_inventory_<UTC>_XXXXXX`, actual `commit.txt`, clean/dirty `working_tree_status.txt`, SHA256 of script/Tcl/auditor, original `01_ps_inventory.txt`, original `02_vivado.log`, separate `03_independent_audit.log` and `result.txt` exit code even on post-creation failure.
- `scripts/m05_12d2a_ps_inventory_audit.py`: Python fail-closed schema validator; records EXACT 12 PS AXI interfaces, 7 clock/reset/interrupt pins, 9 candidate PCW property names; requires actual K26 part, `zynq_ultra_ps_e` VLNV, source mode All, `UNCONNECTED_PS_CATALOG_DEFAULTS_NO_PRESET_DDR` scope; rejects missing/duplicate/wrong roles, malformed/truncated files or unaudited extra entries. It accepts 0-default ports because this is intentionally ONLY discovery, **NOT** integration proof.
- `tests/test_m05_12d2a_ps_inventory.py`: SEVEN **synthetic host** tests of positive/default schemas, manually enabled candidate (synthetic), bad direction, missing/duplicate/extra fields, wrong VLNV/scope, read-only CLI failure, bash help/safety check. Native CI does NOT execute Vivado.

**D2a acceptance requires genuine operator** `result.txt exit_status=0`, original Vivado PASS, complete actual PS catalogue text and independently passing audit plus source/commit provenance. On failure, preserve all original evidence and inspect first Vivado error; do not mark D2a passed from fake fixture tests.

## 4. What D2b host-only control plan validates (native, NO hardware)

`src/neuromorphic_accelerator_v1/m05_12d2_control_map.py` defines a frozen `ProposedAperture(bank, base, length_bytes=4096)` and `ProposedControlMap(tuple_of_six)` plus `propose_control_map`. No default addresses or MMIO calls. The caller must explicitly provide exactly SIX distinct banks (four DMA + shell + original HLS), positive integer **4KiB-aligned** bases and 4KiB-granular apertures, upper numerical 40bit PS address bound, nonoverlap including different-length windows, and known register-offset coverage. It distinguishes MM2S `LENGTH 0x28`, S2MM `LENGTH 0x58`, and shell `VERSION 0x38`. Generated HLS AP_CTRL and status-offset addresses are intentionally NOT filled in without actual HLS register-map proof.

`tests/test_m05_12d2_control_map.py`: SEVEN native methods for six-bank admission, duplicate/overlap/missing region rejection, bounds/overflow/type rejection, touching aperture acceptance, immutability and no unknown-HLS-offset access, absence of physical driver or implicit bases. Test `0xB000....` values are **fictional fixtures**—never use on board, no Xilinx assigned address ranges claimed.

**D2b source-native correctness != physical**: only a future connected Vivado BD with real `assign_bd_address`, readable address segment table, OS memory map/driver permissions, and independent decode tests can authorize actual MMIO.

## 5. Operator no-board verification commands

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
python3 -m unittest discover -s tests -p 'test_m05_12d2*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q

# Source your OWN installed Vivado 2025.2 settings64.sh first.
# Genuine offline IP catalog ONLY. No cable, PS boot, DDR or FPGA is accessed.
bash -n scripts/run_m05_12d2a_ps_inventory.sh
bash scripts/run_m05_12d2a_ps_inventory.sh

export PS_INVENTORY="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d2a_ps_inventory_* | head -n 1)"
echo "$PS_INVENTORY"
cat "$PS_INVENTORY/result.txt"
cat "$PS_INVENTORY/commit.txt"
cat "$PS_INVENTORY/working_tree_status.txt"
cat "$PS_INVENTORY/01_ps_inventory.txt" 2>/dev/null || true
tail -n 160 "$PS_INVENTORY/02_vivado.log" 2>/dev/null || true
cat "$PS_INVENTORY/03_independent_audit.log" 2>/dev/null || true
cat "$PS_INVENTORY/source_sha256.txt" 2>/dev/null || true
```

**First real proof expected:** source IP version, actual default-enabled HPM/HP/HPC and clock/reset pin availability, PCW properties available for later explicit activation, independent audit and proper provenance. A `PASS` does NOT assert the real KV260/K26 PS preset was applied or that actual DDR ports are enabled, clocks configured or 256↔128 conversion implemented. Real D2a still pending owner until new log.

## 6. Next M05.12d.3 after owner D2a

Using the actual Vivado PS inventory, choose a **specific verified PS control master and DDR slave data port**, then create a SEPARATE offline connected clock/reset/address interconnect candidate with original HLS module reference and new shell, final clock `FREQ_HZ` and `ASSOCIATED_BUSIF` for every relevant AXIS/AXI-Lite, independent DMA width conversion and address-decoder readback, error/IRQ wiring and genuine full-BD validation. PS boot/DDR operating system driver resource maps must be reconciled before claiming any physical transfer. Later full XSim and physical board deployment stay separate approvals. Do not merge PR #79 or declare M05 complete.
