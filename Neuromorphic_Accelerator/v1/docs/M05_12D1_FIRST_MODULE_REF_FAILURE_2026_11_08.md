# M05.12d.1 first owner Vivado 2025.2 module-reference failure — forensic record

**Incident observed:** 2026-11-08 17:56 local / 2026-11-09 00:56 UTC.  
**Branch:** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`.  
**Original checkout:** `eea1a56f6486365e22211f525c1d5eaecfc5fea0`.  
**Original full evidence path:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d1_axis_graph_20261109T005602Z_nTb0oa`.  
**Overall result:** **`exit_status=1`** — *D1 genuinely failed, remains UNACCEPTED*.  
**Original owner artifacts:** `result.txt`, `commit.txt`, `02_vivado.log`, `source_sha256.txt`; `01_axis_links.txt` and `03_independent_audit.log` are ABSENT because the script failed prior to that stage. NEVER alter original evidence.

## 1. Exact original failure and what did / did not run

Original Vivado command completed source registration and created a temporary in-memory block-design file within the unique evidence directory, then failed on the very first RTL Module Reference step:

```text
CRITICAL WARNING: [filemgmt 56-176] Module references are not supported in manual compile order mode and will be ignored.
ERROR: [filemgmt 56-587] Failed to resolve reference. Nothing was found in the project to match the name m05_12d_axis_shell_ref Try changing the compile order from manual to automatic.
ERROR: [BD 41-1690] Unable to resolve module-source based on inputs: m05_12d_axis_shell_ref
ERROR: [BD 5-7] Error: running create_bd_cell -type module -reference m05_12d_axis_shell_ref -name shell .
ERROR: [Common 17-39] 'create_bd_cell' failed due to earlier errors.
```

**What was not tested:** no `connect_bd_intf_net` calls, no four DMA↔shell interface net list, no independent Python graph audit, no completed PS DDR wiring, no real DMA, no RTL HLS inference regression. This incident is *project source-management configuration*, not evidence against the previous **accepted** M05.11c generated-HLS+shell XSim, M05.12c actual four unconnected AXI DMA 7.1 configurations, or the signed32 kernel.

## 2. Root cause

The M05.12d.1 script created an in-memory Vivado project, added five existing Verilog sources, ran `update_compile_order -fileset sources_1`, then requested `create_bd_cell -type module -reference m05_12d_axis_shell_ref shell`. It did **not explicitly configure automatic source management**. The owner's Vivado 2025.2 session reports a **manual compile-order mode**, and Vivado expressly refuses to resolve Module References in that mode. Merely running `update_compile_order` does not prove that module references are enabled. The error suggests automatic ordering.

This precisely matches AMD's documented RTL Module Reference requirement (UG994, [Module Reference in a Non-Project Flow](https://docs.amd.com/r/2022.2-English/ug994-vivado-ip-subsystems/Module-Reference-in-a-Non-Project-Flow)): `set_property source_mgmt_mode All [current_project]` is required before RTL source loading. AMD also documents manual-compile-order incompatibility: [support article 000040784](https://adaptivesupport.amd.com/s/article/000040784?language=en_US).

## 3. Minimal code fix, regression and evidence tightening

**Fix to `scripts/m05_12d1_axis_graph.tcl`:**
- Immediately after `create_project -in_memory -part $part`, perform `set_property source_mgmt_mode All [current_project]`.
- Immediately read and require `get_property source_mgmt_mode [current_project]` equals `All` **before adding RTL**, preventing a repeat of the exact root cause.
- After file registration and `update_compile_order -fileset sources_1`, read and require `All` again, **before** creating the Module Reference.
- Print `M05_12D1_SOURCE_MGMT_MODE=All` in genuine Vivado log and place `META|source_mgmt_mode|All` into the original exact report. That report metadata is based on `get_property` actual readback, not an assumed literal.
- Extend independent `m05_12d1_axis_graph_audit.py` to reject missing/incorrect source-mode metadata. A mock/manual source-mode transcript cannot pass.
- Add one regression `test_auto_source_management_before_module_reference_regression` checking the property set, two independent guard reads, ordering and source-report fields; augment existing provenance-negative tests for wrong/missing mode.

No changes to `hls/m05_rolling/m05_rolling.cpp`, original generated Verilog, original RTL transport shell, four 256-bit DMA channel width/length/readback requirements, AXIS net endpoint names, or real board. The separate M05.12c read-only `c_prmry_is_aclk_async` warning fix remains intact.

**Native proof boundary:** Python tests and separate Icarus elaboration exercise source logic; neither runs Vivado IP Integrator on the owner's workstation. A fresh genuine Vivado run must demonstrate whether automatic source mode resolves module inference; further unrelated Vivado errors, if any, require separate investigations and original evidence preservation.

## 4. Fresh owner-only genuine Vivado check — NO BOARD / NO PS DDR

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05_12d1_axis_graph.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q

# Vivado 2025.2 sourced; no board required.
bash -n scripts/run_m05_12d1_axis_graph.sh
bash scripts/run_m05_12d1_axis_graph.sh

export AXIS_GRAPH="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d1_axis_graph_* | head -n 1)"
echo "$AXIS_GRAPH"
cat "$AXIS_GRAPH/result.txt"
cat "$AXIS_GRAPH/commit.txt"
cat "$AXIS_GRAPH/working_tree_status.txt"
cat "$AXIS_GRAPH/01_axis_links.txt" 2>/dev/null || true
tail -n 180 "$AXIS_GRAPH/02_vivado.log"
cat "$AXIS_GRAPH/03_independent_audit.log" 2>/dev/null || true
cat "$AXIS_GRAPH/source_sha256.txt"
```

**Real D1 acceptance remains:** fresh unique `exit_status=0`; real Vivado log shows **`M05_12D1_SOURCE_MGMT_MODE=All`**, real four-link connectivity PASS marker; exact `META|source_mgmt_mode|All`, four correct AXIS endpoint/net readbacks; independent Python PASS. No board or PS DDR operation; design remains only partially connected and unvalidated for synthesis. On a fresh failure, keep the new evidence folder and investigate the first new error; **do not retrofit the failed `~/Thesis_Evidence/neuromorphic_v1_m05_12d1_axis_graph_20261109T005602Z_nTb0oa` into a PASS**.

**M05 stays OPEN, PR #79 stays DRAFT/UNMERGED.**
