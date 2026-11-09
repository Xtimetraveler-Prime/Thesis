## 2026-11-08 20:11 local / 2026-11-09 03:11 UTC — second genuine D3 Vivado error and corrected IP reset wiring

**Original failed owner evidence:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_connected_20261109T031117Z_FhjxdG`, checkout `6bc10b3b3a2170a017d79fb7ffae0078da93f0f2`, original `result.txt exit_status=1`. K26 Vivado 2025.2 created the PS/RTL shell + two SmartConnect + `proc_sys_reset` cells, then **`CRITICAL WARNING: [BD 41-737] Cannot set the parameter C_EXT_RESET_HIGH on /pl_reset. It is read-only.`** and `proc_sys_reset external reset polarity readback not active-low`. No `01_connected_graph.txt` and no `03_independent_audit.log` were created. This is a first-error reset parameter mismatch, not proof of defective neural RTL or the previous missing DMA clock bug. Keep the original evidence immutable.

**Architectural diagnosis and correction:** PS `pl_resetn0` output is *active-low*. Vivado 2025.2's Processor System Reset `CONFIG.C_EXT_RESET_HIGH` cannot be set on this IP. If read-only default is high polarity (`1`) as indicated by the failure to read back `0`, the correct configuration is an explicit active-low→active-high **NOT gate**, not modifying the read-only PS reset parameter. This is a K26 in-memory BD only. Official [AMD Processor System Reset PG164](https://docs.amd.com/api/khub/documents/5VcEWg~hYG0gT~7WNDt64g/content) documents active-high/low dependent on external-reset generic, while [AMD Utility Vector Logic DS913](https://docs.amd.com/api/khub/documents/PNkhLUH7WYBuEnDM0sLk0Q/content) explicitly supports `C_OPERATION=not`, `C_SIZE=1`, `Op1`, `Res` for inversion.

Revised `scripts/m05_12d3_connected_candidate.tcl` **does not write `CONFIG.C_EXT_RESET_HIGH`**. It requires property presence and actual read-only `1` before wiring, instantiates genuine 1-bit `xilinx.com:ip:util_vector_logic:2.0`, writes ONLY the new scratch inverter's `C_OPERATION=not` and `C_SIZE=1`, verifies both readbacks, connects `ps/pl_resetn0→reset_inv/Op1`, then `reset_inv/Res→pl_reset/ext_reset_in`. It verifies and reports pin `DIR` outputs/inputs `O,I,O,I` and **two distinct, paired actual BD nets**. Tcl report now includes `RESETCFG|C_EXT_RESET_HIGH|1` (actual read-only PS reset IP), `RESETINV|C_OPERATION|not`, `RESETINV|C_SIZE|1`, four `RESETDIR` records and four `RESETFEED` records (two net pairs). The independent auditor enforces those exact fields, distinguishes both reset segments and checks they cannot alias the PL clock or generated reset nets; no malformed/missing/swapped records can pass.

The first original D3 failed owner run `neuromorphic_v1_m05_12d3_connected_20261109T030211Z_GQaGvt` (exit1, wrong AXI VDMA clock names) also remains immutable. Correct PG021 AXI DMA v7.1 clocks (**15** actual participants, no separate stream clocks), 15 exact AXI/AXIS pair links, seven generated reset consumers, 128-bit PS and 256-bit DMA documented configs remain enforced. This repair touches **no original HLS signed32 kernel, generated RTL or M05 shell**.

**Native regression:** Updated `test_owner_d3_missing_axis_clock_regression_and_reset_polarity` now requires **no read-only `set_property` write**, actual inverter IP v2.0 and two scalar reset net connections in source, plus exact 1-bit NOT parameters, actual read-only reset-input polarity `1`, correct four directions, two distinct reset nets, and negative tests for missing/swapped/incorrect fields. Other eight D3 synthetic methods remain unchanged in scope. Host GitHub Actions can only validate source/schema; **no native CI proves actual Vivado IP pins or real working reset until owner's next original run**.

**Fresh owner offline retry (same D3 milestone, no new submilestone):**

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
# Vivado 2025.2 sourced in the terminal before this step; no board required.
bash -n scripts/run_m05_12d3_connected_candidate.sh
bash scripts/run_m05_12d3_connected_candidate.sh
export PS_GRAPH="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_connected_* | head -n 1)"
echo "$PS_GRAPH"
cat "$PS_GRAPH/result.txt"
cat "$PS_GRAPH/commit.txt"
cat "$PS_GRAPH/working_tree_status.txt"
cat "$PS_GRAPH/01_connected_graph.txt" 2>/dev/null || true
tail -n 240 "$PS_GRAPH/02_vivado.log"
cat "$PS_GRAPH/03_independent_audit.log" 2>/dev/null || true
cat "$PS_GRAPH/source_sha256.txt"
```

**Accept the *partial* original graph gate ONLY if** a brand-new `result.txt exit_status=0`, exact existing original Vivado D3 PASS marker, independent strict D3 PASS, 15 actual AXI/AXIS links, 15 common PL clock participant nets, 7 separate reset consumers, 4 actual reset-inverter endpoint directions and two distinct paired reset-input nets, `CONFIG.C_EXT_RESET_HIGH=1` read-only, and verified inverter `C_OPERATION=not`/`C_SIZE=1`. Then continue work on real generated signed32 HLS control and streams, address map, clock frequency association, width conversion, original 2025.2 `xlconstant` deprecation warning and full BD validation **inside the same D3 milestone**. No physical PS/DDR/board/bitstream proof and no permission for physical operations.

---

## Genuine owner offline D3 failure, precise clock/reset repair (2026-11-09 03:02 UTC)

The original user run `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_connected_20261109T030211Z_GQaGvt`, checkout `98aca677f357f27e1b15cf94f6321f249c6c50f9` exited **1**, and its genuine `02_vivado.log` ended with `missing actual Vivado scalar pin dma_neurons/m_axis_mm2s_aclk`. Script created real PS, two SmartConnect, Processor System Reset, DMA×4 and shell; it attempted to gather clock pins **before** writing the graph report and independent audit. Therefore `01_connected_graph.txt` and `03_independent_audit.log` are absent, and original evidence must remain failed and immutable. The Vivado clock metadata warning `IP_Flow 19-11770` and `xlconstant` future-deprecation warnings are distinct nonfatal findings still to resolve in complete D3.

**Root cause:** the Tcl erroneously specified `m_axis_mm2s_aclk` and `s_axis_s2mm_aclk`—AXI **VDMA** (PG020) clock names—on actual AXI **DMA v7.1** (PG021) instances. Official [AXI DMA PG021 Clocking](https://docs.amd.com/r/en-US/pg021_axi_dma/Clocking) lists `s_axi_lite_aclk`, `m_axi_mm2s_aclk` (both MM2S AXI MM and M_AXIS stream), `m_axi_s2mm_aclk` (both S2MM memory and stream), and optional SG clock; [AXI VDMA PG020](https://docs.amd.com/r/en-US/pg020_axi_vdma/Port-Descriptions) is the separate product with independent stream clocks. With SG disabled, 3 MM2S-only and 1 S2MM-only, there are **15 actually expected PL clock participants**, not 19. The corrected Tcl and independent report audit both reject missing, extra, multiple-domain or mislabeled clock entries; not simply skip a failed check.

**Additional reset-polarity correction (precaution, not reached in failed run):** the PS output `pl_resetn0` is **active-low**; Processor System Reset `ext_reset_in` must be configured to accept active-low inputs. D3 script now fails if `CONFIG.C_EXT_RESET_HIGH` absent, sets exactly `0` on scratch `proc_sys_reset`, independently rereads and records `RESETCFG|C_EXT_RESET_HIGH|0`, and reads two actual `RESETFEED` net endpoints `ps/pl_resetn0` and `pl_reset/ext_reset_in`. Strict auditor requires both and the same net; synthetic regression rejects wrong polarity, swapped reset input, missing or duplicated records. This is the documented AMD usage of `C_EXT_RESET_HIGH=0` with active-low PS reset. In-memory only, no board preset and no hardware.

**Native verification after fix:** `python3 -m unittest discover -s tests -p 'test_m05_12d3*.py' -v`; all M05; four previous milestones; GitHub Actions. The added test `test_owner_d3_missing_axis_clock_regression_and_reset_polarity` supplements the original 8 tests, now **9 D3 host tests**. First CI try found an improperly escaped negative-fixture newline (no valid report change), and that test fixture was corrected without changing the Tcl or audit. Await final current HEAD CI.

**Genuine acceptance STILL PENDING:** rerun `bash scripts/run_m05_12d3_connected_candidate.sh` from a clean pulled checkout, Vivado 2025.2 sourced. Preserve new folder and return `result.txt`, `commit.txt`, actual `01_connected_graph.txt`, last 200+ lines `02_vivado.log`, `03_independent_audit.log`, `source_sha256.txt`. Require fresh `exit_status=0`, original TCL PASS, strict independently audited 15 actual AXI/AXIS links, 15 clock members, 7 resets, 2 PS reset input net endpoints and active-low reset CFG. **Only partial D3 graph**, not six-bank HLS AXI control, DDR, physical clock timing, full BD validation, native 256→128 converter or real inference.

---

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
