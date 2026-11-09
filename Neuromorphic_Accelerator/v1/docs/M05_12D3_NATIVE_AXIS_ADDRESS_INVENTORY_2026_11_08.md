> **2026-11-09 UTC — ORIGINAL OWNER native grouped-AXIS Vivado graph successfully ran; combined result EXIT1 only because read-only address inventory used empty `PATH` property (CORRECTED in source):** Owner fresh `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_native_axis_20261109T042636Z_NzIAw5` at `0d271faba545c8ede78a7da9936bc16b2c2df3c7` recorded original preflight PASS, actual **four native inferred grouped AXI4-Stream interface LINKs**, 24 original underlying pin width/direction readbacks, seven PS-control + five DMA-memory + four 256-bit DMA AXIS links, 16 clock/8 reset endpoints, real `PASS: M05.12d.3 genuine HLS grouped native AXIS connected`. No new `BD 41-1306` since the shell no longer connects individual AXIS signal pins. But **`result.txt exit_status=1`** because the separate address-inventory/independent audit produced `SLAVE|dma_neurons|dma_neurons/S_AXI_LITE|` and equivalents **for all six**, even though `get_bd_addr_segs -of_objects` found six Vivado segment objects; `get_property PATH $segment` returned the empty string. The PS master space reported correctly `/ps/Data`. Existing independent audit correctly rejected the empty names. AMD UG835 `get_bd_addr_segs` documents returning segment objects (which render canonical `/cell/interface/Reg` names in Tcl). **New source fix:** record the actual returned `segment` object directly as its canonical Tcl name (after checking real cell namespace), *not* the missing `PATH` property; require full original AXI interface ownership in the independent auditor, reject empty/foreign names. Two new host tests reproduce the six blank owner records, show they fail, and verify synthetic correctly scoped object names without claiming PS assignment. Original EXIT1 and all previously accepted proof folders untouched. **A fresh run of the SAME owner command below is mandatory** to prove a full result exit0, six actual segment paths, real audit PASS. No new PS address, BD validation, converter, PS/DDR, or physical board claim.

# M05.12d.3 — Native AXI4-Stream Interface Normalization + Six-Bank Address Inventory

**Status:** source-developed new first offline native-AXIS rewire candidate; genuine **owner Vivado 2025.2 rerun required**. Draft PR #79 stays open/unmerged. No physical FPGA, DDR, Linux PS MMIO, JTAG, bitstream, board power or netlist timing permitted.

## Accepted original-owner evidence (do not rerun/mutate)

- Source contract: `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na`, at commit `f5c305ccb676d30fe8d43fbe09f30b57a4c3eca6`, `result.txt exit_status=0`; exact real Vitis HLS 2025.2 `m05_rolling_replay` ports, 26 Verilog siblings, original generated driver AXI4-Lite map, frozen signed32 CPP SHA256 `24c4de87b5557cd536b33fe518595d56133e2ac737786bdf0d6fdbc53a687073`.
- Original connected partial PS/PL graph (no HLS): `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_connected_20261109T032316Z_WQjAyg`, genuine owner full partial audit PASS, original 15 interface nets.
- **NEW owner accepted REAL HLS module attachment:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_hls_connected_20261109T040940Z_h2Ni5q` at source `e82fd1e9bf364581fc184ca7b523b748d97d73ce`, **`result.txt exit_status=0`**, fresh source preflight, real Vivado six-bank PS graph PASS and independent auditor PASS: 4×256-bit DMA/shell interfaces, 7 PS control interface links (including new sixth HLS AXI4-Lite), 5 DMA/PS memory links, 12 exact original native HLS scalar pair nets (128/192-bit data with individual valid/ready), 16 common clocks, 8 reset consumers, one genuine PS reset inversion chain. The reported PS HP0 is 128-bit while DMA memory AXI-MM is 256-bit. **Real neural attachment is therefore ACCEPTED as a scalar-connected graph only**, not BD validation, address assignment, width converter or DDR.
- The original Vivado transcript of that successful scalar graph has **24 real `WARNING: [BD 41-1306]` warnings** (two endpoints × 12 pair nets). Vivado recognized its grouping as `shell/hls_neuron`, `hls/neurons`, `shell/hls_synapse`, `hls/synapses`, `shell/hls_external`, `hls/external_events`, `hls/trace`, `shell/hls_trace`. Each per-pin `connect_bd_net` overrode the inferred AXI4-Stream interface grouping; AMD UG994 states individually connected pins are removed from the encompassing interface connection and may not be reconstructed on `write_bd_tcl`. **This warning is not a data/RTL error and does not negate owner scalar connectivity PASS; it does need correction before grouping-level BD validation**. Source: [AMD UG994 Connecting Interface Signals](https://docs.amd.com/r/2020.2-English/ug994-vivado-ip-subsystems/Connecting-Interface-Signals).

## New separate warning-free native-AXIS implementation

The new `scripts/m05_12d3_native_axis_candidate.tcl` is a **new source-only candidate**, not a mutation of the accepted Tcl, report, signed32 CPP or 26 generated Verilog siblings. It loads every authentic HLS file only after the existing strict SHA256 source/RTL/register preflight. It reuses the owner-accepted PS/PL topology, real six-bank SmartConnect and genuine 1-bit reset inverter (no guessing of read-only `C_EXT_RESET_HIGH=1`).

For each of the 12 existing neural signal connections, it verifies the **24 original** generated+shell endpoint pin direction and 128/192-bit data widths by real Vivado pin readback, but does **not** call `connect_bd_net` on any of those pins. Instead it requires and connects **four authentic inferred native AXI4-Stream interface pairs**, checking MASTER/SLAVE modes, unique interface nets, and exactly two interface endpoints:

| Original shell HLS native interface | Genuine Vitis HLS interface | Payload |
|---|---|---|
| `shell/hls_neuron` (MASTER) | `hls/neurons` (SLAVE) | 128-bit |
| `shell/hls_synapse` (MASTER) | `hls/synapses` (SLAVE) | 192-bit |
| `shell/hls_external` (MASTER) | `hls/external_events` (SLAVE) | 128-bit |
| `hls/trace` (MASTER) | `shell/hls_trace` (SLAVE) | 192-bit |

Native AXIS streams have TDATA/TVALID/TREADY, no invented TKEEP/TLAST. Four original 256-bit DMA-facing AXIS interfaces remain unchanged; HLS does not inherit DMA padding. The new graph auditor requires exact 4 native interface net pairs, all 24 original signal declaration contracts, 4 DMA shell stream nets, 7 control interfaces, 5 memory links, 16 clock and 8 reset consumers, original PS width 128, original D3 polarity and two distinct inversion nets. It refuses truncated/duplicated/wrong/aliased nets and claims of unassigned addresses or nonexistent width adapters.

The new runner **fails if Vivado emits a `WARNING: [BD 41-1306]`** again. It produces a unique `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_native_axis_<UTC>_XXXXXX` evidence directory, recording result, source commit, repo status, source SHA256, old HLS contract path, preflight PASS, actual Vivado transcript, actual new group-level graph, and independent audit. The original scalar-evidence directory is untouched.

### NEW: read-only Vivado six-bank address inventory

The candidate also reports **actual address-segment objects** exposed by Vivado for each of `dma_neurons/S_AXI_LITE`, `dma_synapses/S_AXI_LITE`, `dma_external/S_AXI_LITE`, `dma_trace/S_AXI_LITE`, `shell/s_axi`, `hls/s_axi_control` and PS control master `ps/M_AXI_HPM0_FPD`. See `05_read_only_address_inventory.txt`. This is **discovery, not address assignment**. If a Verilog Module Reference lacks an address segment, it records `NO_BD_SEGMENT_YET` and no fictitious segment, base or decoder is introduced. The independent audit validates six identities and the PS master inventory, but the number of discovered address segments is only a diagnostic.

Crucial potential finding: Vivado may infer an AXI4-Lite native HLS *interface* without registering its expected IP-XACT *memory-map segment*. If so, a real vendor-generated HLS component packaging step (reusing the exact original Vitis RTL/driver and hash manifest, not fabricating a memory map) might be required before the sixth bank can be address-decoded. No claim is made until original owner Vivado observation.

**Still OPEN:** explicit nonoverlapping *actual* PS AXI4-Lite address segments for six real control banks, HLS native offsets relative to genuine physical base, clock FREQ_HZ propagation, `validate_bd_design`, generated SmartConnect 256-bit DMA to 128-bit PS-HP0 converter, generated IP simulation/output products, reproducible PS/DDR ownership and full system runtime. No physical FPGA operations.

## Operator VS Code verification (new original evidence)

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
python3 -m unittest discover -s tests -p 'test_m05_12d3*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q

# Source Vivado 2025.2 in current terminal first, if necessary.
vivado -version
export AUTH_HLS="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na"
cat "$AUTH_HLS/result.txt"
bash -n scripts/run_m05_12d3_native_axis_candidate.sh

# Only NEW native grouped AXIS graph + discovery, never board/JTAG/DDR.
bash scripts/run_m05_12d3_native_axis_candidate.sh "$AUTH_HLS"

export NEXT_D3="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_native_axis_* | head -n 1)"
echo "$NEXT_D3"
cat "$NEXT_D3/result.txt"
cat "$NEXT_D3/commit.txt"
cat "$NEXT_D3/working_tree_status.txt"
cat "$NEXT_D3/01_hls_preflight.log" 2>/dev/null || true
cat "$NEXT_D3/02_native_axis_graph.txt" 2>/dev/null || true
cat "$NEXT_D3/05_read_only_address_inventory.txt" 2>/dev/null || true
cat "$NEXT_D3/04_independent_audit.log" 2>/dev/null || true
tail -n 240 "$NEXT_D3/03_vivado.log" 2>/dev/null || true
cat "$NEXT_D3/source_sha256.txt"
```

Owner exit0 PLUS genuine unmodified Vivado grouped interface nets PLUS independent auditor PASS PLUS **no BD 41-1306** warnings would constitute this **new native interface cleanup gate**. Otherwise preserve fresh EXIT1 output and diagnose from actual Vivado log; never reinterpret old scalar PASS as new grouped PASS.

## Tests and CI meaning

`tests/test_m05_12d3_native_axis_candidate.py` contains ten additional host **synthetic-only** tests: strict expected grouped axes+six controls+D3 clocks, missing/duplicate/wrong native endpoints, corruption of all scalar data widths and directions, reused DMA/native AXIS net, missing real HLS control/reset/clock, six-bank inventory with a missing segment reported faithfully, rejection of fabricated address assignments, no `connect_bd_net` of native individual signals, BD41-1306 runner guard and no hardware operations, accepted source immutability, and read-only CLI audit failure path. **Tests cannot certify new original grouped Vivado graph.** Run result is needed. Original HLS and old real HLS scalar proofs remain accepted independently.

