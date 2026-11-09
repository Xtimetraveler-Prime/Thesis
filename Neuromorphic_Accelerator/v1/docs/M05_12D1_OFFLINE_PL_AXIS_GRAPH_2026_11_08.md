# M05.12d.1 — Genuine Vivado offline four-DMA to M05.11 shell AXI4-Stream connectivity

**2026-11-08 local / 2026-11-09 UTC · Active M05 branch · Draft PR #79 · NO BOARD**

## 0. Accepted source prerequisites and provenance

**M05.11c** owner genuine original Vitis signed32 HLS generated RTL + stream shell XSim and independent 256-bit raw frame replay `exit_status=0` PASS, original `neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy` on checkout `bf20f33aa07df2b187bfb837ee5ba2a946cb7098`: valid 24 trace rows/status0/commit24, late failure 8 provisional rows/status4/commit0, same RTL instances back-to-back, 148 HLS/output stalls. Generated RTL and neural kernel are unchanged.

**M05.12b** owner real Vivado catalog discovery PASS, original `neuromorphic_v1_m05_12_ip_catalog_20261109T001921Z_4ZocHi`, checkout `1dc439c9e06e8580008857db52ccba63d25965ca`, exact AXI DMA 7.1 IP catalog with uncustomized SG1, 32b width, length14 defaults.

**M05.12c** owner real Vivado 2025.2 four-DMA IP configuration and independent audit PASS, original `~/Thesis_Evidence/neuromorphic_v1_m05_12c_dma_candidate_20261109T003049Z_y5AEce`, checkout `0ea2178c71023250150609a2983a67bbd6c84ef2`, `exit_status=0`. Three MM2S-only and one S2MM-only, 256b AXIS/AXI-MM, direct SG0, length24, addr32, micro0, DRE0, async readback0. **Qualification:** original Vivado logged four `CRITICAL WARNING: [BD 41-737]` because script tried to write read-only clock-async config; actual value remained0 and all readback/independent audit passed. Subsequent source removed this invalid write (regression added), leaving readback required. Do not overwrite original evidence or silently say the first M05.12c run was warning-free.

## 1. Why we are not calling this an end-to-end connected PS/PL BD yet

The required four AXI4-Stream paths are already exercised in standalone/generated-HLS XSim, but the DMA IPs were only unconnected catalog candidates in M05.12c. To establish real **IP Integrator net connectivity** without guessing K26 PS DDR addresses, build an isolated, in-memory **PL data-path subset**:

```text
AXI DMA neurons  M_AXIS_MM2S (256b) ──► shell/S_AXIS_NEURONS
AXI DMA synapses M_AXIS_MM2S (256b) ──► shell/S_AXIS_SYNAPSES
AXI DMA external M_AXIS_MM2S (256b) ──► shell/S_AXIS_EXTERNAL
shell/M_AXIS_TRACE              (256b) ──► AXI DMA trace/S_AXIS_S2MM
```

The `shell` RTL reference instantiates the **existing, unchanged** `m05_11_stream_shell`, which contains the three 256-to-128/192bit ingress unpadders, AXI4-Lite session controller and 192-to-256bit trace packetizer. Unlike a hand-drawn diagram, Vivado must **create** four AXI4-Stream interface nets and read back both endpoints on each exact net. It must find four distinct point-to-point nets. This does NOT exercise AXI-MM read/write transfers yet.

The deliberately UNCONNECTED pieces are: actual signed32 HLS generated RTL and native HLS AXIS ports, its independently mapped AXI-Lite control bank, shell AXI-Lite control bank, all DMA control AXI-Lite banks, DMA four AXI-MM DDR master interfaces, K26 PS block and HP/HPC bus, physical address ranges, system clock/reset and CDC, PS interrupts, Linux DMA/cache ownership, actual descriptors/buffers, full BD DRC/synth/route, JTAG and FPGA execution. Those are subsequent M05.12d gates; `validate_bd_design` is deliberately not claimed or invoked while required connections are absent. No full-system Fmax can be inferred from this stage.

## 2. New code and independent checks

| File | Contract |
| --- | --- |
| `rtl/m05_12/m05_12d_axis_shell_ref.v` | Vivado RTL Module Reference wrapper with **exactly the 54 existing shell ports connected 1:1**, and explicit `X_INTERFACE_INFO` attributes for 20 AXIS signals across four named 256b interfaces. It **does not modify or instantiate HLS**. |
| `scripts/m05_12d1_axis_graph.tcl` | K26 2025.2 in-memory scratch project, add exact shell/module RTL sources, create module reference and four genuine AXI DMA 7.1 IPs with readback, connect and check four directed point-to-point interface nets. No address/clock/DDR/PS attachment. |
| `scripts/run_m05_12d1_axis_graph.sh` | Genuine offline Vivado operator runner: unique evidence folder, source SHA256, commit, tree status, original Tcl log and readback report, independent checker, nonzero failure `result.txt`. Does not touch board or existing project. |
| `scripts/m05_12d1_axis_graph_audit.py` | Strict independent read-only report parser rejecting any missing/duplicate/mismatched IP, shell, config, net, direction, net alias, part/version/scope. |
| `tests/test_m05_12d1_axis_graph.py` | 8 named native methods with synthetic transcript and negative cases, full 54-port equivalence and 20 signal attributes; **native Icarus wrapper compile is required in CI after `iverilog` installation**. None of these is a real Vivado BD run. |
| `.github/workflows/neuromorphic_accelerator_m05_host_only.yml` | Mandatory native Icarus elaboration of the new wrapper using unchanged real M05.11 RTL; separate repeat of 8 tests after installation ensures no optional Icarus skip goes unchecked. No Vivado in GitHub CI. |

Source safety gate also fixes the four original M05.12c `BD 41-737` warnings by **not setting** the read-only `CONFIG.c_prmry_is_aclk_async`; its readback value **must** equal0. All other original M05.12c config and source proof are unchanged.

## 3. Genuine local no-board verification

Pull the latest active source branch; preserve any untracked evidence and avoid overwriting local modifications:

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
python3 -m unittest discover -s tests -p 'test_m05_12*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q
```

If `iverilog` is installed locally, the wrapper-native-elaboration test runs instead of skipping. GitHub CI additionally installs Icarus and mandates compile as a separate step.

With genuine **Vivado 2025.2 previously sourced** (only offline; no FPGA power or cable needed):

```bash
bash -n scripts/run_m05_12d1_axis_graph.sh
bash scripts/run_m05_12d1_axis_graph.sh
export AXIS_GRAPH="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d1_axis_graph_* | head -n 1)"
echo "$AXIS_GRAPH"
cat "$AXIS_GRAPH/result.txt"
cat "$AXIS_GRAPH/commit.txt"
cat "$AXIS_GRAPH/working_tree_status.txt"
cat "$AXIS_GRAPH/01_axis_links.txt" 2>/dev/null || true
tail -n 160 "$AXIS_GRAPH/02_vivado.log" 2>/dev/null || true
cat "$AXIS_GRAPH/03_independent_audit.log" 2>/dev/null || true
cat "$AXIS_GRAPH/source_sha256.txt" 2>/dev/null || true
```

**Full M05.12d.1 PASS requires:** `result.txt exit_status=0`; original Vivado marker `PASS: M05.12d.1 genuine offline DMA-to-shell four AXIS nets (PARTIAL PL BD, NO PS/DDR)`; independent Python `PASS: M05.12d.1 independent Vivado graph audit`; four real nonshared directed interface links from the original BD readback; correct K26/Vivado/AXI DMA 7.1 and 256b/length24/SG0. Inspect Vivado warnings and failure logs before closing. On fail, **do not change the original signed32 engine, generated RTL, prior evidence, or pass criteria**; preserve new evidence dir, diagnose real first error.

**M05.12d.1 is CURRENTLY IMPLEMENTED AND NATIVE-CI TESTED, BUT GENUINE VIVADO GRAPH VALIDATION REMAINS PENDING OPERATOR.** M05 full PS/PL DMA integration and M05.13 routed/physical timing remain NOT ACCEPTED. PR #79 draft/unmerged; no board authorization.

## 4. Architectural decisions remaining for M05.12d.2 and later

Next work, contingent on original AXIS graph: independent K26 PS topology and memory-access review, a single verified clock domain or explicit CDC, PS reset/isolation, actual AXI control and DMA register maps with nonoverlapping ranges, DDR master SmartConnect/HP/HPC paths, interrupts and privileged Linux buffer ownership, explicit DMA cache clean/invalidate and fence, DMA status errors/short read handling, S2MM arm-first and concurrent trace drain, HLS ap_done/ap_return-before-FINISH, custom shell COMPLETE+ACK, status4 quarantine/recovery. Only after independent full BD DRC and adequate testbench coverage may full-system synth/route or physical transfer be considered, under separate authorization.

References: AMD UG994 2025.2 on [referencing RTL modules](https://docs.amd.com/r/2025.2-English/ug994-vivado-ip-subsystems/Adding-RTL-Modules-to-the-Block-Design) and [interface inference attributes](https://docs.amd.com/r/2025.1-English/ug994-vivado-ip-subsystems/Prioritizing-Interfaces-for-Automatic-Inference); UG835 [connect_bd_intf_net](https://docs.amd.com/r/2024.1-English/ug835-vivado-tcl-commands/connect_bd_intf_net), AMD PG021 AXI DMA v7.1 for mandatory four-direction AXI4-Stream handshake framing. These public references explain expected commands; only owner Vivado results verify actual design.
