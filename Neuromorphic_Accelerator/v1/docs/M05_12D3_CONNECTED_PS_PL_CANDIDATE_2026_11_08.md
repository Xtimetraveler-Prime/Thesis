# M05.12d.3 — Integrated PS/PL interconnect candidate (single milestone, no milestone sprawl)

**Active branch:** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip` · **Draft PR #79** open/unmerged · **M05 OPEN** · **K26 Vivado 2025.2** · **no board/DDR/bitstream/PS boot.**

## Accepted prerequisite: genuine M05.12d.2d

Owner original offline Vivado evidence `~/Thesis_Evidence/neuromorphic_v1_m05_12d2d_ps_enablement_20261109T023754Z_ak6kLz`, checkout `176ba0e99f500a391d7c00459b7e357a813e0e07`, `result.txt exit_status=0`, genuine `zynq_ultra_ps_e:3.5` K26 Tcl PASS and independent Python PASS. Verified actual *scratch PS IP* interface pins after setting `PSU__USE__M_AXI_GP0=1` and `PSU__USE__S_AXI_GP2=1`: `M_AXI_HPM0_FPD MASTER`, `S_AXI_HP0_FPD SLAVE`, original `M_AXI_HPM0_LPD MASTER`. Clock and reset pins `pl_clk0`/ `pl_resetn0`, `maxihpm0_fpd_aclk`/`saxihp0_fpd_aclk` present/directions checked, PS AXI widths 128 bits, PL0 requested 100MHz and IP-reported actual 96.968727MHz. This is NOT a physical clock measurement, DDR proof or a connected runnable design.

Earlier genuine accepted owner gates remain untouched: M05.11c real signed32 generated HLS RTL + M05 shell XSim 24 rows status0 and 8 rows status4, M05.12b IP catalog, M05.12c four configured 256-bit DMA IPs, M05.12d.1 four real connected DMA-to-shell AXI4-Stream nets, M05.12d.2a default PS IP pins, M05.12d.2c 57 actual PS PSU configuration properties. First original failed evidence folders remain preserved as failures, never rewritten.

## Unified D3 design and what is actually connected

**Goal:** Build one offline K26 Vivado PS→DMA→shell control/stream/memory interconnect candidate with actual BD net readback. Do not divide this milestone into more numbered submilestones; record ongoing D3 work as tests/implementation commits under **M05.12d.3**.

The new `scripts/m05_12d3_connected_candidate.tcl` creates a fresh in-memory project and reads original unchanged shell sources. It sets source-management mode `All`, creates verified K26 PS `zynq_ultra_ps_e:3.5`, actual DMA IP v7.1 ×4 (3 MM2S and 1 S2MM, 256-bit stream and MM data, length24, SG0, addr32), and the same original annotated shell module reference that genuine M05.12d.1 connected.

The **control fabric** `ctrl_sc` is AXI SmartConnect 1 SI → **5 MI**, with 6 actual point-to-point AXI links including `ps/M_AXI_HPM0_FPD→ctrl_sc/S00_AXI` and `ctrl_sc/M00..M04_AXI→dma_neurons/S_AXI_LITE, dma_synapses/S_AXI_LITE, dma_external/S_AXI_LITE, dma_trace/S_AXI_LITE, shell/s_axi`. The **sixth originally planned control bank is native generated signed32 HLS AXI-Lite**, not present as generated RTL in the Git branch. It is explicitly **NOT** connected or faked; a live HLS module must be sourced from original generated vendor output with its own regmap.

The **memory fabric** `mem_sc` is AXI SmartConnect 4 SI → 1 MI, with 5 actual point-to-point AXI links: each of four 256-bit AXI DMA memory-master interfaces → `mem_sc/S00..S03_AXI` → PS `S_AXI_HP0_FPD` slave (128-bit). **SmartConnect instantiation does NOT yet prove internal 256→128 converter is generated**: require actual generated IP outputs, BD validation and data-path simulation later in this SAME D3 milestone. No real PS DDR initialized, Linux buffers, cache fences, 32-bit DMA data buffer addresses or transfer transactions have been tested.

The original **stream fabric** retains 4 real D1 AXI4-Stream links (3 MM2S→shell inputs, shell trace→S2MM). Combined **15 AXI/AXIS point-to-point interfaces** are required. The Tcl checks actual pins, post-connection identical Vivado net names and exactly two interface endpoints for every link. It does not treat success from `connect_bd_intf_net` alone as proof.

The **clock and reset fabric** connects `ps/pl_clk0` to two PS AXI clock inputs, both SmartConnect `aclk`, shell `clk`, processor-system-reset `slowest_sync_clk`, all DMA AXI-Lite/AXI-MM/AXIS clocks: **19 named clock participants** on the same real BD net. It connects `ps/pl_resetn0` to Processor System Reset `ext_reset_in`, fixed `dcm_locked=1`, `aux_reset_in=0`, `mb_debug_sys_rst=0`, routes separate `interconnect_aresetn` to two SmartConnect blocks and `peripheral_aresetn` to shell and four DMA IPs: **7 independently recorded reset consumers**. This only proves net connectivity; clock FREQ_HZ metadata on the M05.12d.1 module and reset synchronization/timing still require a real full BD design review, especially original `IP_Flow 19-11770` warning and 100 vs 96.968727MHz PS clock readbacks. AMD documentation connects `pl_clk0` to AXI clocks and routes PS reset via Processor System Reset IP; final board reset policy must be separately validated. [AMD PS/PL reset](https://docs.amd.com/r/2025.2-English/ug1137-zynq-ultrascale-mpsoc-swdev/GPIO-Reset-to-PL).

**Important explicit non-goals and remaining SAME-milestone requirements:** Generated signed32 HLS IP attachment, its 128/192-bit native AXIS + AXI-Lite control interface, HLS `ap_done`/`ap_return` interpretation, sixth AXI-Lite address region, actual Vivado `assign_bd_address` readbacks and nonoverlap, width-converter implementation proof, fully validated BD, clock frequency/domain association and real PS boot/DDR/cache/buffer transfers are **not done**. This is a **partial connected graph candidate**, not a runnable device. Do NOT mark M05.12d.3 complete or claim a physical neural inference solely from a PASS of this script.

## Implementation, evidence and testing

- **Tcl:** `scripts/m05_12d3_connected_candidate.tcl` (new in-memory IP Integrator graph; explicit PS/4DMA/shell/2 SmartConnect/Reset/constant instances; strict real interface and scalar-net readbacks; no full BD validation).
- **Runner:** `scripts/run_m05_12d3_connected_candidate.sh`: sourced Vivado 2025.2, zero CLI args, preserves unique `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_connected_<UTC>_XXXXXX`, original `commit.txt`, `working_tree_status.txt`, `source_sha256.txt` of runner/Tcl/audit/wrapper/shell, actual `01_connected_graph.txt`, `02_vivado.log`, separate `03_independent_audit.log`, and `result.txt exit_status` even on failure. Never reuses/overwrites original evidence.
- **Independent audit:** `scripts/m05_12d3_connected_candidate_audit.py` validates exact 4 stream +6 control +5 memory links, 19 same-clock participants, 7 proper reset groups, four DMA role/width/length/addr configs, 128-bit PS interface readbacks, and all explicit negative M05.12d.3 scope flags. Duplicates, wrong endpoints, net alias collisions, incorrect resets, missing rows and unsupported claims fail closed.
- **Native tests:** `tests/test_m05_12d3_connected_candidate.py` (8 synthetic-only methods; exact schema, missing fake HLS/addr proof, wrong link/role/clock reset, malformed/truncated report and no-board script safety). Native CI does **not** run real Vivado, generate SmartConnect output products, validate a BD, or operate PS DDR.

### Operator verification commands — same ONE D3 milestone

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

# Source your locally installed Vivado 2025.2 settings64.sh first.
# Genuine offline K26 PS/PL IP Integrator graph only. NO physical device.
bash -n scripts/run_m05_12d3_connected_candidate.sh
bash scripts/run_m05_12d3_connected_candidate.sh

export PS_GRAPH="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_connected_* | head -n 1)"
echo "$PS_GRAPH"
cat "$PS_GRAPH/result.txt"
cat "$PS_GRAPH/commit.txt"
cat "$PS_GRAPH/working_tree_status.txt"
cat "$PS_GRAPH/01_connected_graph.txt" 2>/dev/null || true
tail -n 200 "$PS_GRAPH/02_vivado.log"
cat "$PS_GRAPH/03_independent_audit.log" 2>/dev/null || true
cat "$PS_GRAPH/source_sha256.txt"
```

The **limited graph connectivity gate** requires new original `exit_status=0`, exact Vivado `PASS: M05.12d.3 offline PS/PL four-DMA control/memory/stream/clock graph (PARTIAL: NO HLS/ADDR/DDR)`, strict independent `PASS: M05.12d.3 independent partial PS/PL graph audit`, all 15 actual point-to-point nets, 19 clock members/7 resets, true K26 PS DMA source mode and original checksums. **Do not call the entire M05.12d.3 milestone COMPLETE on this alone.** After genuine graph proof, next work stays in D3 until native generated HLS block, 6-bank address map, converter and BD validation exist. If Vivado fails, preserve original failed folder and fix first actual IP Integrator error with regression tests; no fabricated success.

**Current status:** D2d original owner accepted; D3 candidate source + host tests developed, owner original Vivado gate **PENDING**; M05 OPEN PR draft/unmerged. No FPGA/DDR/PS physical operations.
