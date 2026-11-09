# M05.12d.3 — genuine Vivado SmartConnect output products (offline owner trial)

**Source candidate, not yet genuine-Vivado accepted.** In the owner's newest real Vivado 2025.2 run at commit `1344574f035e75831064903bd4ecefab92f4c860`, four DDR_LOW 2GiB regions were assigned at 0x00000000 to each genuine DMA AXI-MM master, four HP0 OCM segments were explicitly excluded, full BD validation PASS, and strict independent memory audit PASS. Earlier six control-bank/HLS native grouped AXIS audits also remain green. The owner log retains `BD 41-3281` SmartConnect endpoint-auto-configuration and `BD 41-237` AWUSER/ARUSER mismatch *warnings*. **Those warnings must not be mistaken for generated-width-conversion evidence.**

The next trial produces **real file-backed Vivado output-product evidence only**. It never targets the physical board, Linux, DDR, bitstream, JTAG or synthesis. Do not edit existing owner-PASS in-memory Tcl, generated Vitis HLS RTL or older evidence.

## Actual new candidate and required proof

- `scripts/run_m05_12d3_ip_output_candidate.sh`: same authentic original-HLS preflight, original graph and six-control/4-DMA address independent audits. Creates a NEW `neuromorphic_v1_m05_12d3_ip_output_<UTC>_<random>` evidence folder (registered in strict HLS preflight).
- `scripts/m05_12d3_ip_output_trial.py`: stages `14_ip_output_trial_generated.tcl` plus original+derived SHA manifest under evidence. Derives original tested in-memory source exactly (six banks + four DMA and OCM exclusions), changing only to an isolated **file-backed** `create_project` and output-product pass. The only project destination is evidence-local `13_file_backed_project/`, rejected if pre-existing. Owner can inspect the .xpr and .bd.
- Tcl calls `save_bd_design` and requires exactly one saved actual .bd, queries **ten actual native AXI widths** (all four DMA MM and mem_sc SI = 256; mem_sc MI and PS HP0 = 128), and then uses `generate_target all [get_files *.bd]` without suppressing Vivado errors. `15_ip_output_width_readback.txt` records actual readbacks; no hardcoded PASS in place of genuine tool output.
- `scripts/m05_12d3_ip_output_audit.py`: checks the actual vendor-created .xpr, .bd and .gen tree, a generated memory SmartConnect IP product, endpoint widths, vendor pass log, and archives SHA256 of real generated IP artifacts in `16_ip_output_sha256_manifest.txt`. Requires original 3 independent audits and success exit0. Any vendor failure or missing actual output is a FAIL.

**Scientific boundary:** AMD PG247 explains 256→128 conversion is automatically required when the SI and MI widths differ, but SmartConnect's internal conversion elements are not a published exposed RTL hierarchy. A passing generation and endpoint-contract report is **not** proof of netlist implementation, functional conversion under bursts/backpressure, synthesized timing or physical DMA data transfer. Those are distinct further gates. `BD 41-3281` and user-signal width warnings remain for evaluation; no blanket waiver.

## Owner commands (Ubuntu VS Code, Vivado/Vitis 2025.2)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05_12d3*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
bash -n scripts/run_m05_12d3_ip_output_candidate.sh
vivado -version

export AUTH_HLS="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na"
export CTRL_PLAN="$PWD/scripts/m05_12d3_control_apertures_candidate.txt"
cat "$AUTH_HLS/result.txt"
# OFFLINE file-backed Vivado project; NO bitstream, physical board or synthesis
bash scripts/run_m05_12d3_ip_output_candidate.sh "$AUTH_HLS" "$CTRL_PLAN"
echo "owner offline trial exit status=$?"

export IP_D3="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_* | head -n 1)"
echo "$IP_D3"
cat "$IP_D3/commit.txt"
cat "$IP_D3/result.txt"
cat "$IP_D3/14_ip_output_trial_stage.log" 2>/dev/null || true
cat "$IP_D3/14_ip_output_trial_source_manifest.txt" 2>/dev/null || true
cat "$IP_D3/15_ip_output_width_readback.txt" 2>/dev/null || true
cat "$IP_D3/16_ip_output_sha256_manifest.txt" 2>/dev/null | head -n 30 || true
cat "$IP_D3/17_independent_ip_output_audit.log" 2>/dev/null || true
cat "$IP_D3/07_full_bd_validation.txt" 2>/dev/null || true
cat "$IP_D3/08_independent_address_validation_audit.log" 2>/dev/null || true
cat "$IP_D3/12_independent_dma_hp0_memory_audit.log" 2>/dev/null || true
grep -E '^M05_D3_IP_OUTPUT_|^ERROR:|^CRITICAL WARNING:|^WARNING: \[BD 41-237\]|^WARNING: \[BD 41-3281\]|^PASS:' "$IP_D3/03_vivado.log" | tail -n 100 || true
tail -n 90 "$IP_D3/03_vivado.log"
```

**Do not close M05.12d.3 from host CI.** If genuine output generation fails, preserve new original evidence and inspect first vendor error. Do not disable validation or fabricate vendor-generated files to pass the audit. No merge / physical board / DDR transfer authorization.

Sources: AMD Vivado Tcl UG835 2025.2 `generate_target` (`https://docs.amd.com/r/en-US/Vivado-Design-Suite-Tcl-Command-Reference-Guide-UG835/generate_target`), `save_bd_design`; AMD SmartConnect PG247 `Width Conversion` and `Feature Comparison`.
