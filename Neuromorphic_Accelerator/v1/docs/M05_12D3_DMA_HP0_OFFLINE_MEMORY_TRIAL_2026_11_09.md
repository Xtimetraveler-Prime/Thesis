# M05.12d.3 — DMA HP0 DDR_LOW addressing and OCM-exclusion offline trial

**2026-11-09 UTC; same M05.12d.3 milestone. SOURCE-ONLY candidate; no genuine owner Vivado execution yet.** PR #79 stays OPEN/DRAFT/UNMERGED. No physical board, DDR traffic, A53/Linux control, bitstream, JTAG or hardware operation.

## Starting evidence, already proven by real owner Vivado 2025.2

The owner's newest run at commit `884dc66cd2d8267a1786571b1ca8f4ba51c43900` recorded `result.txt exit_status=0`, all **six actual** PS `/ps/Data` AXI-Lite control segments (four DMA registers, shell, original signed32 HLS), independent six-bank audit PASS, `VALIDATION|PASS|FULL_BD_VALIDATE_FORCE`, and authentic `hls/ap_clk` associations at the **actual PS 96,968,727 Hz** clock. The original signed32 HLS top only gained one external *clock metadata* attribute in a separate evidence-local copy; no neural RTL logic changes. This evidence **does not** validate DMA DDR addressing: Vivado emitted eight `CRITICAL WARNING [BD 41-1356]` for unassigned PS HP0 DDR_LOW and OCM into the four DMA master address spaces and `CRITICAL WARNING [BD 41-2909]` for undefined `mem_sc`. It **also does not prove** a generated 256-to-128-bit SmartConnect width adapter, any Linux DDR buffer ownership, or physical inference.

## Narrow source-only trial and evidence contract

Preserve the owner-PASS `scripts/m05_12d3_address_validate_candidate.tcl` and previous evidence unchanged. The new standalone runner `scripts/run_m05_12d3_dma_memory_candidate.sh`:

1. Creates a **NEW unique** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_dma_memory_<UTC>_XXXXXX` folder; preserves source git SHA, original file hashes, earlier HLS provenance and original independent audits. Uses genuine Vitis-generated HLS sibling RTL untouched, with the existing evidence-local one-attribute HLS clock top derivative.
2. Stages **a second derivative Tcl**, `10_dma_memory_trial_generated.tcl`, using `scripts/m05_12d3_dma_memory_trial.py`. This adds *only* a ninth output arg and one DMA HP0 memory section **before** the original `validate_bd_design -force`. `10_dma_memory_trial_source_manifest.txt` holds the original and derived SHA256 values; never edit/overwrite the accepted original Tcl.
3. Gets exact original PS HP0 slave segments `/ps/SAXIGP2/HP0_DDR_LOW` and `/ps/SAXIGP2/HP0_LPS_OCM` from real Vivado; obtains each DMA master address space from its real master interface. Uses documented Vivado `assign_bd_address -target_address_space` for **DDR_LOW only**. Allows Vivado to choose the actual segment offset/range; does not invent or promise DDR addresses. Checks actual master-to-slave reverse paths, OFFSET and RANGE; rejects any range outside the 32-bit address limit configured on all four DMA engines.
4. Calls `exclude_bd_addr_seg -target_address_space` for each DMA's OCM slave. Checks **excluded actual master segments** through `get_bd_addr_segs -excluded` and rejects accidentally mapped-accessible OCM, excluded DDR, missing/extra memory segments. Writes actual four `DDR|` and four `OCM_EXCLUDED|` rows to `11_dma_hp0_memory_readback.txt`.
5. Runs the actual `validate_bd_design -force`, the original independent native grouped-AXIS graph+segment inventory audit, the independent original six-control-address audit, and the **new strict independent** `scripts/m05_12d3_dma_memory_audit.py`. This last requires four real DDR readbacks, four OCM exclusions, full BD PASS, original Tcl success marker and **no** `BD 41-1356` or `BD 41-2909` remaining in the original Vivado log. Fails closed and preserves incomplete original evidence on any problem.

**This trial is NOT SmartConnect output product generation.** A later separate offline evidence gate must generate actual vendor SmartConnect output products and inspect the realized **256-bit DMA AXI-MM → 128-bit PS HP0** adapter, rather than treating passing BD validation as hardware proof. The original 2025.2 SmartConnect auto-config warnings `BD 41-3281` should also be investigated, not silently accepted as generated width conversion.

## Operator: Ubuntu VS Code, genuine Vivado 2025.2, offline only

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
bash -n scripts/run_m05_12d3_dma_memory_candidate.sh

# Source your own Vivado 2025.2 settings64.sh if the command is missing.
vivado -version
export AUTH_HLS="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na"
export CTRL_PLAN="$PWD/scripts/m05_12d3_control_apertures_candidate.txt"
cat "$AUTH_HLS/result.txt"
python3 scripts/m05_12d3_address_validate_audit.py --plan "$CTRL_PLAN" --plan-only

# New offline candidate; never runs physical DDR/JTAG or creates a bitstream.
bash scripts/run_m05_12d3_dma_memory_candidate.sh "$AUTH_HLS" "$CTRL_PLAN"
echo "offline trial returned: $?"

export DMA_D3="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_dma_memory_* | head -n 1)"
echo "New evidence: $DMA_D3"
cat "$DMA_D3/result.txt"
cat "$DMA_D3/commit.txt"
cat "$DMA_D3/working_tree_status.txt"
cat "$DMA_D3/10_dma_memory_trial_stage.log" 2>/dev/null || true
cat "$DMA_D3/10_dma_memory_trial_source_manifest.txt" 2>/dev/null || true
cat "$DMA_D3/11_dma_hp0_memory_readback.txt" 2>/dev/null || true
cat "$DMA_D3/07_full_bd_validation.txt" 2>/dev/null || true
cat "$DMA_D3/04_independent_original_graph_audit.log" 2>/dev/null || true
cat "$DMA_D3/08_independent_address_validation_audit.log" 2>/dev/null || true
cat "$DMA_D3/12_independent_dma_hp0_memory_audit.log" 2>/dev/null || true
grep -E 'M05_D3_DMA_HP0_|ERROR:|CRITICAL WARNING:|PASS:' "$DMA_D3/03_vivado.log" | tail -n 110 || true
```

**Acceptance for this NEXT single candidate (not yet established):** fresh owner evidence `result.txt exit_status=0`, correct git SHA, both original audits PASS, 4 mapped HP0 DDR_LOW ranges and 4 excluded HP0 OCM segments as authentic Vivado master/slave readbacks, new audit PASS, full BD validation PASS and no residual memory critical warning. If anything fails, preserve full evidence, examine original `03_vivado.log`, correct the first real Vivado error; DO NOT weaken audit to match preselected or imaginary DDR addresses.

## Static source documentation

Relevant AMD Vivado 2025.2 Tcl commands: `assign_bd_address`, `exclude_bd_addr_seg`, `get_bd_addr_segs -excluded/-addressing`, `get_bd_addr_spaces` in UG835. `validate_bd_design -force` verifies design rule consistency; generated SmartConnect width conversion and physical DDR remain independent future evidence.
